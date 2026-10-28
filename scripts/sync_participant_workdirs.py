#!/usr/bin/env python3
"""Assign OFS participants to jupyter-training-ofs-{1..8} and sync workdirs.

Each participant gets:
  /home/jupyter-training-ofs-<N>/<namadepan-namabelakang>/training-ofs-2026

Repos are cloned/pulled from a local mirror (default: this repo) so we do not
need per-account GitHub SSH keys. Run as root (sudo).

Examples:
  sudo python3 scripts/sync_participant_workdirs.py --dry-run
  sudo python3 scripts/sync_participant_workdirs.py
  sudo python3 scripts/sync_participant_workdirs.py --pull-only
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import pwd
import re
import shutil
import subprocess
import sys
import unicodedata
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Optional


REPO_DIRNAME = "training-ofs-2026"
DEFAULT_CSV = Path(__file__).resolve().parents[1] / "OFS2026-Pre-Test-nilai.csv"
DEFAULT_MIRROR = Path(__file__).resolve().parents[1]
DEFAULT_GROUPS = 8
HOME_PREFIX = "jupyter-training-ofs-"

TITLE_COMPACT = {
    "str",
    "strmet",
    "msi",
    "ssi",
    "msc",
    "mgeo",
    "skom",
    "st",
    "mt",
    "sp",
    "sst",
    "amd",
    "drs",
    "dr",
    "ir",
    "prof",
}


@dataclass
class Participant:
    nip: str
    full_name: str
    workdir: str
    group: int
    jupyter_user: str
    home: Path
    workdir_path: Path
    repo_path: Path


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = text.lower()
    return re.sub(r"[^a-z0-9]+", "-", text).strip("-")


def workdir_name(full_name: str) -> str:
    """Build namadepan-namabelakang from Moodle-style display name."""
    base = full_name.split(",")[0].strip()
    raw = [t for t in re.split(r"\s+", base) if t]
    tokens: list[str] = []
    for tok in raw:
        compact = re.sub(r"[^a-z]", "", tok.lower())
        if compact in TITLE_COMPACT:
            continue
        tokens.append(tok.strip("."))

    # Drop leading single-letter initials (M., I. as particle handled below)
    while tokens and len(re.sub(r"[^A-Za-z]", "", tokens[0])) <= 1:
        tokens.pop(0)
    # Drop trailing short uppercase initials (HB, ZA)
    while (
        len(tokens) > 1
        and len(re.sub(r"[^A-Za-z]", "", tokens[-1])) <= 2
        and tokens[-1].isupper()
    ):
        tokens.pop()

    if not tokens:
        return "peserta"
    if len(tokens) == 1:
        return slugify(tokens[0])
    return f"{slugify(tokens[0])}-{slugify(tokens[-1])}"


def ensure_unique(names: Iterable[str]) -> list[str]:
    seen: dict[str, int] = {}
    out: list[str] = []
    for name in names:
        n = seen.get(name, 0) + 1
        seen[name] = n
        out.append(name if n == 1 else f"{name}-{n}")
    return out


def load_participants(csv_path: Path) -> list[tuple[str, str, str]]:
    with csv_path.open(encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    triples = []
    for row in rows:
        nip = (row.get("Nama akhir") or "").strip()
        full = (row.get("Nama Depan") or "").strip()
        if not full:
            continue
        triples.append((nip, full, workdir_name(full)))
    unique = ensure_unique(t[2] for t in triples)
    return [(n, f, w) for (n, f, _), w in zip(triples, unique)]


def assign_groups(
    people: list[tuple[str, str, str]], n_groups: int
) -> list[Participant]:
    """Round-robin into groups so sizes stay balanced (~6 each)."""
    assigned: list[Participant] = []
    for idx, (nip, full, wd) in enumerate(people):
        group = (idx % n_groups) + 1
        user = f"{HOME_PREFIX}{group}"
        home = Path("/home") / user
        workdir_path = home / wd
        assigned.append(
            Participant(
                nip=nip,
                full_name=full,
                workdir=wd,
                group=group,
                jupyter_user=user,
                home=home,
                workdir_path=workdir_path,
                repo_path=workdir_path / REPO_DIRNAME,
            )
        )
    return sorted(assigned, key=lambda p: (p.group, p.workdir))


def run(cmd: list[str], *, dry_run: bool = False, cwd: Optional[Path] = None) -> None:
    print("+", " ".join(cmd))
    if dry_run:
        return
    subprocess.run(cmd, check=True, cwd=str(cwd) if cwd else None)


def ensure_git_safe_directories(paths: Iterable[Path], *, dry_run: bool) -> None:
    """Allow root to operate on repos owned by jupyter-* users."""
    if dry_run or os.geteuid() != 0:
        return
    try:
        existing = subprocess.check_output(
            ["git", "config", "--global", "--get-all", "safe.directory"],
            text=True,
        ).splitlines()
    except subprocess.CalledProcessError:
        existing = []
    wanted = {"*"}
    wanted.update(str(p.resolve()) for p in paths)
    for path in sorted(wanted):
        if path in existing:
            continue
        run(["git", "config", "--global", "--add", "safe.directory", path])


def chown_path(path: Path, user: str, dry_run: bool) -> None:
    run(["chown", "-R", f"{user}:{user}", str(path)], dry_run=dry_run)


def sync_repo(participant: Participant, mirror: Path, *, dry_run: bool, pull_only: bool) -> str:
    user = participant.jupyter_user
    repo = participant.repo_path
    workdir = participant.workdir_path

    if not participant.home.is_dir():
        raise FileNotFoundError(f"Missing jupyter home: {participant.home}")

    if dry_run:
        if repo.is_dir():
            action = "pulled"
        elif pull_only:
            action = "skipped"
        else:
            action = "cloned"
        print(f"[dry-run] {user}:{participant.workdir} -> {action} {repo}")
        return action

    workdir.mkdir(parents=True, exist_ok=True)
    chown_path(workdir, user, dry_run=False)

    if repo.is_dir() and (repo / ".git").exists():
        # Fast-forward from local mirror
        run(
            [
                "git",
                "-C",
                str(repo),
                "fetch",
                str(mirror),
                "+refs/heads/*:refs/remotes/mirror/*",
            ]
        )
        # Detect default branch on mirror
        branch = (
            subprocess.check_output(
                ["git", "-C", str(mirror), "rev-parse", "--abbrev-ref", "HEAD"],
                text=True,
            ).strip()
            or "main"
        )
        run(["git", "-C", str(repo), "checkout", branch])
        run(
            [
                "git",
                "-C",
                str(repo),
                "merge",
                "--ff-only",
                f"refs/remotes/mirror/{branch}",
            ]
        )
        chown_path(repo, user, dry_run=False)
        return "pulled"

    if pull_only:
        print(f"[skip] missing repo for {user}/{participant.workdir}")
        return "skipped"

    # Clone from local mirror (no GitHub SSH needed on training accounts)
    run(["git", "clone", "--local", str(mirror), str(repo)])
    # Keep origin pointing at GitHub for documentation; updates use mirror fetch
    run(
        [
            "git",
            "-C",
            str(repo),
            "remote",
            "add",
            "mirror",
            str(mirror),
        ]
    )
    chown_path(repo, user, dry_run=False)
    return "cloned"


def write_manifest(path: Path, participants: list[Participant], dry_run: bool) -> None:
    rows = [asdict(p) for p in participants]
    for row in rows:
        row["home"] = str(row["home"])
        row["workdir_path"] = str(row["workdir_path"])
        row["repo_path"] = str(row["repo_path"])
    text_json = json.dumps(rows, indent=2, ensure_ascii=False) + "\n"
    # CSV summary
    import io

    buf = io.StringIO()
    w = csv.DictWriter(
        buf,
        fieldnames=[
            "group",
            "jupyter_user",
            "workdir",
            "full_name",
            "nip",
            "repo_path",
        ],
    )
    w.writeheader()
    for p in participants:
        w.writerow(
            {
                "group": p.group,
                "jupyter_user": p.jupyter_user,
                "workdir": p.workdir,
                "full_name": p.full_name,
                "nip": p.nip,
                "repo_path": str(p.repo_path),
            }
        )
    print(f"Manifest -> {path} (+ .csv)")
    if dry_run:
        print(buf.getvalue())
        return
    path.write_text(text_json, encoding="utf-8")
    path.with_suffix(".csv").write_text(buf.getvalue(), encoding="utf-8")


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--mirror", type=Path, default=DEFAULT_MIRROR)
    parser.add_argument("--groups", type=int, default=DEFAULT_GROUPS)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MIRROR / "scripts" / "participant-groups.json",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--pull-only",
        action="store_true",
        help="Only update existing clones; do not create new ones",
    )
    parser.add_argument(
        "--group",
        type=int,
        action="append",
        help="Limit to one or more group numbers (repeatable)",
    )
    args = parser.parse_args(argv)

    if os.geteuid() != 0 and not args.dry_run:
        print("ERROR: run with sudo (needs write access to /home/jupyter-training-ofs-*)", file=sys.stderr)
        return 2

    if not args.csv.is_file():
        print(f"ERROR: CSV not found: {args.csv}", file=sys.stderr)
        return 2
    if not (args.mirror / ".git").exists():
        print(f"ERROR: mirror is not a git repo: {args.mirror}", file=sys.stderr)
        return 2

    people = load_participants(args.csv)
    participants = assign_groups(people, args.groups)
    if args.group:
        want = set(args.group)
        participants = [p for p in participants if p.group in want]

    write_manifest(args.manifest, participants, dry_run=args.dry_run)

    # Summary
    from collections import Counter

    counts = Counter(p.group for p in participants)
    print("Group sizes:", dict(sorted(counts.items())))

    ensure_git_safe_directories(
        [args.mirror, *[p.repo_path for p in participants]],
        dry_run=args.dry_run,
    )

    stats = {"cloned": 0, "pulled": 0, "skipped": 0}
    for p in participants:
        try:
            pwd.getpwnam(p.jupyter_user)
        except KeyError:
            print(f"ERROR: system user missing: {p.jupyter_user}", file=sys.stderr)
            return 2
        action = sync_repo(
            p, args.mirror.resolve(), dry_run=args.dry_run, pull_only=args.pull_only
        )
        stats[action if action in stats else "skipped"] = stats.get(action, 0) + 1

    print("Done:", stats)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

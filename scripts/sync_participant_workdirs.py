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
  sudo python3 scripts/sync_participant_workdirs.py --workdir 'andi-*'
  sudo python3 scripts/sync_participant_workdirs.py --workdir '*pratama*' --pull-only
  sudo python3 scripts/sync_participant_workdirs.py --group 3 --workdir 'rangga-*'
  sudo python3 scripts/sync_participant_workdirs.py --pull-only --force
  sudo python3 scripts/sync_participant_workdirs.py --env-only --provision-env

Participant clones always track branch ``main`` (even if the admin mirror
is checked out on ``admin``). Optional: ``--clear-outputs`` strips notebook
outputs after sync.
"""

from __future__ import annotations

import argparse
import csv
import fnmatch
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

try:
    import nbformat
except ImportError:  # pragma: no cover
    nbformat = None  # type: ignore


REPO_DIRNAME = "training-ofs-2026"
DEFAULT_CSV = Path(__file__).resolve().parents[1] / "OFS2026-Pre-Test-nilai.csv"
DEFAULT_MIRROR = Path(__file__).resolve().parents[1]
DEFAULT_GROUPS = 8
DEFAULT_PARTICIPANT_BRANCH = "main"
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


def sync_repo(
    participant: Participant,
    mirror: Path,
    *,
    dry_run: bool,
    pull_only: bool,
    force: bool = False,
    branch: str = DEFAULT_PARTICIPANT_BRANCH,
) -> str:
    user = participant.jupyter_user
    repo = participant.repo_path
    workdir = participant.workdir_path

    if not participant.home.is_dir():
        raise FileNotFoundError(f"Missing jupyter home: {participant.home}")

    if dry_run:
        try:
            has_repo = repo.is_dir() and (repo / ".git").is_dir()
        except OSError:
            has_repo = None
        if has_repo is True:
            action = "force-reset" if force else "pulled"
        elif has_repo is False and pull_only:
            action = "skipped"
        elif has_repo is False:
            action = "cloned"
        else:
            # Cannot inspect under /home/jupyter-* without root
            if force:
                action = "force-reset"
            else:
                action = "pulled" if pull_only else "synced"
        print(f"[dry-run] {user}:{participant.workdir} -> {action} {repo}")
        if action == "force-reset":
            return "pulled"
        return action if action in {"pulled", "cloned", "skipped"} else "pulled"

    workdir.mkdir(parents=True, exist_ok=True)
    chown_path(workdir, user, dry_run=False)

    if repo.is_dir() and (repo / ".git").exists():
        # Fast-forward (or hard-reset) from local mirror
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
        # Always sync the participant-facing branch (default: main), not
        # whatever branch the admin mirror currently has checked out (e.g. admin).
        mirror_ref = f"refs/remotes/mirror/{branch}"
        if force:
            # Discard local commits + tracked edits (e.g. dirty .ipynb).
            # Untracked files (.env, new notebooks) are kept.
            run(
                [
                    "git",
                    "-C",
                    str(repo),
                    "checkout",
                    "-f",
                    "-B",
                    branch,
                    mirror_ref,
                ]
            )
        else:
            run(["git", "-C", str(repo), "checkout", branch])
            run(
                [
                    "git",
                    "-C",
                    str(repo),
                    "merge",
                    "--ff-only",
                    mirror_ref,
                ]
            )
        chown_path(repo, user, dry_run=False)
        return "pulled"

    if pull_only:
        print(f"[skip] missing repo for {user}/{participant.workdir}")
        return "skipped"

    # Clone participant-facing branch only (no GitHub SSH needed)
    run(
        [
            "git",
            "clone",
            "--local",
            "--branch",
            branch,
            str(mirror),
            str(repo),
        ]
    )
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


def clear_notebook_outputs(repo: Path, *, dry_run: bool) -> int:
    """Strip outputs/execution_count from top-level *.ipynb in a participant repo.

    Mirror/GitHub keep executed previews; participant workdirs start blank.
    Leaves the working tree dirty vs HEAD (expected; participants do not push).
    """
    if nbformat is None:
        print(
            "WARNING: nbformat not installed; cannot clear notebook outputs",
            file=sys.stderr,
        )
        return 0

    cleared = 0
    for path in sorted(repo.glob("*.ipynb")):
        if dry_run:
            print(f"[dry-run] clear-outputs {path}")
            cleared += 1
            continue
        nb = nbformat.read(path, as_version=4)
        changed = False
        for cell in nb.cells:
            if cell.get("cell_type") != "code":
                continue
            if cell.get("outputs") or cell.get("execution_count") is not None:
                cell["outputs"] = []
                cell["execution_count"] = None
                changed = True
            # Drop transient metadata that often reappears after Run
            meta = cell.get("metadata") or {}
            if "execution" in meta:
                del meta["execution"]
                cell["metadata"] = meta
                changed = True
        if changed:
            nbformat.write(nb, path)
            print(f"+ clear-outputs {path.name}")
            cleared += 1
    return cleared


def provision_env(
    participant: Participant,
    env_src: Path,
    *,
    dry_run: bool,
) -> str:
    """Copy parent .env into participant repo (untracked; survives --force)."""
    dest = participant.repo_path / ".env"
    if dry_run:
        exists = participant.repo_path.is_dir()
        action = "env-copied" if exists else "env-skipped"
        print(
            f"[dry-run] {participant.jupyter_user}:{participant.workdir} "
            f"-> {action} {dest}"
        )
        return action if exists else "env-skipped"

    if not participant.repo_path.is_dir():
        print(f"[skip-env] missing repo {participant.repo_path}")
        return "env-skipped"

    shutil.copy2(env_src, dest)
    os.chmod(dest, 0o600)
    chown_path(dest, participant.jupyter_user, dry_run=False)
    print(f"+ env -> {dest}")
    return "env-copied"


def matches_workdir(workdir: str, patterns: list[str]) -> bool:
    """True if workdir matches any fnmatch pattern (case-insensitive)."""
    name = workdir.lower()
    return any(fnmatch.fnmatchcase(name, pat.lower()) for pat in patterns)


def filter_participants(
    participants: list[Participant],
    *,
    groups: Optional[list[int]] = None,
    workdir_patterns: Optional[list[str]] = None,
) -> list[Participant]:
    selected = participants
    if groups:
        want = set(groups)
        selected = [p for p in selected if p.group in want]
    if workdir_patterns:
        selected = [
            p for p in selected if matches_workdir(p.workdir, workdir_patterns)
        ]
    return selected


def merge_manifest_extras(
    participants: list[Participant], manifest_path: Path
) -> list[Participant]:
    """Keep manually added workdirs (e.g. john-doe) that are not in the pretest CSV."""
    if not manifest_path.is_file():
        return participants
    try:
        raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return participants
    known = {p.workdir for p in participants}
    extras: list[Participant] = []
    for row in raw:
        wd = row.get("workdir")
        if not wd or wd in known:
            continue
        extras.append(
            Participant(
                nip=str(row.get("nip") or "manual"),
                full_name=str(row.get("full_name") or wd),
                workdir=str(wd),
                group=int(row["group"]),
                jupyter_user=str(row["jupyter_user"]),
                home=Path(row["home"]),
                workdir_path=Path(row["workdir_path"]),
                repo_path=Path(row["repo_path"]),
            )
        )
    if not extras:
        return participants
    merged = participants + extras
    return sorted(merged, key=lambda p: (p.group, p.workdir))


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
        help="Limit sync to one or more group numbers (repeatable)",
    )
    parser.add_argument(
        "--workdir",
        "-w",
        action="append",
        dest="workdir_patterns",
        metavar="PATTERN",
        help=(
            "Limit sync to workdirs matching fnmatch PATTERN "
            "(repeatable, case-insensitive). "
            "Examples: 'andi-*', '*pratama*', 'rangga-pratama'"
        ),
    )
    parser.add_argument(
        "--no-manifest",
        action="store_true",
        help="Do not rewrite participant-groups.json/.csv",
    )
    parser.add_argument(
        "--force",
        "-f",
        action="store_true",
        help=(
            "On existing clones: hard-reset to mirror branch "
            "(discards local commits and tracked-file edits such as dirty .ipynb; "
            "keeps untracked files like .env)"
        ),
    )
    parser.add_argument(
        "--provision-env",
        action="store_true",
        help="Copy --env-file into each participant repo as .env (chmod 600)",
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        default=DEFAULT_MIRROR / ".env",
        help="Source .env to provision (default: mirror/.env)",
    )
    parser.add_argument(
        "--env-only",
        action="store_true",
        help="Only provision .env; skip clone/pull (implies --provision-env)",
    )
    parser.add_argument(
        "--branch",
        default=DEFAULT_PARTICIPANT_BRANCH,
        help=(
            "Git branch to sync into participant workdirs "
            f"(default: {DEFAULT_PARTICIPANT_BRANCH}; ignore admin checkout)"
        ),
    )
    parser.add_argument(
        "--clear-outputs",
        action="store_true",
        help="After sync, strip outputs from top-level *.ipynb in participant clones",
    )
    parser.add_argument(
        "--clear-outputs-only",
        action="store_true",
        help="Only strip notebook outputs; skip clone/pull/env (implies --clear-outputs)",
    )
    args = parser.parse_args(argv)

    if args.env_only:
        args.provision_env = True
    if args.clear_outputs_only:
        args.clear_outputs = True
    clear_outputs = args.clear_outputs

    if os.geteuid() != 0 and not args.dry_run:
        print("ERROR: run with sudo (needs write access to /home/jupyter-training-ofs-*)", file=sys.stderr)
        return 2

    if not args.csv.is_file():
        print(f"ERROR: CSV not found: {args.csv}", file=sys.stderr)
        return 2
    if not (args.mirror / ".git").exists():
        print(f"ERROR: mirror is not a git repo: {args.mirror}", file=sys.stderr)
        return 2
    if args.provision_env and not args.env_file.is_file():
        print(f"ERROR: --env-file not found: {args.env_file}", file=sys.stderr)
        return 2

    people = load_participants(args.csv)
    all_participants = merge_manifest_extras(
        assign_groups(people, args.groups), args.manifest
    )

    # Always keep the full assignment in the manifest; filters only affect sync.
    if not args.no_manifest:
        write_manifest(args.manifest, all_participants, dry_run=args.dry_run)

    participants = filter_participants(
        all_participants,
        groups=args.group,
        workdir_patterns=args.workdir_patterns,
    )

    # Summary
    from collections import Counter

    if args.group or args.workdir_patterns:
        print(
            f"Filter: groups={args.group or 'all'} "
            f"workdir={args.workdir_patterns or 'all'} "
            f"-> {len(participants)}/{len(all_participants)} participants",
            flush=True,
        )
        for p in participants:
            print(f"  - g{p.group} {p.jupyter_user}/{p.workdir}", flush=True)
        if not participants:
            print("ERROR: no participants matched the filter", file=sys.stderr)
            return 2
    else:
        counts = Counter(p.group for p in participants)
        print("Group sizes:", dict(sorted(counts.items())))

    do_git = not args.env_only and not args.clear_outputs_only
    if do_git:
        ensure_git_safe_directories(
            [args.mirror, *[p.repo_path for p in participants]],
            dry_run=args.dry_run,
        )

    stats = {
        "cloned": 0,
        "pulled": 0,
        "skipped": 0,
        "env-copied": 0,
        "env-skipped": 0,
        "outputs-cleared": 0,
    }
    for p in participants:
        try:
            pwd.getpwnam(p.jupyter_user)
        except KeyError:
            print(f"ERROR: system user missing: {p.jupyter_user}", file=sys.stderr)
            return 2
        synced = False
        if do_git:
            action = sync_repo(
                p,
                args.mirror.resolve(),
                dry_run=args.dry_run,
                pull_only=args.pull_only,
                force=args.force,
                branch=args.branch,
            )
            stats[action if action in stats else "skipped"] = stats.get(action, 0) + 1
            synced = action in {"cloned", "pulled"}
        if args.provision_env and not args.clear_outputs_only:
            env_action = provision_env(
                p, args.env_file.resolve(), dry_run=args.dry_run
            )
            stats[env_action] = stats.get(env_action, 0) + 1
        # Strip outputs on participant clones (mirror/GitHub keep previews).
        if clear_outputs and (args.clear_outputs_only or synced):
            if p.repo_path.is_dir() or args.dry_run:
                n = clear_notebook_outputs(p.repo_path, dry_run=args.dry_run)
                stats["outputs-cleared"] += n
                if not args.dry_run and n and p.repo_path.is_dir():
                    chown_path(p.repo_path, p.jupyter_user, dry_run=False)

    print("Done:", stats)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

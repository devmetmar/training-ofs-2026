#!/usr/bin/env python3
"""Staged concurrency load test against participant workdirs.

Simulates many participants running training work at once. Prefer ramping
workers (8 → 16 → 32 → 45) while watching `htop` / `free -h` / OPeNDAP+S3.

Modes:
  synth     — local CPU/RAM/plot only (no remote). Safe first pass.
  opendap   — execute a minimal OPeNDAP open+subset cell (needs .env).
  mandala   — execute a minimal Mandala load cell (needs VAULT_TOKEN).
  notebook  — nbclient-execute full notebook (heaviest; needs deps + .env).

Examples:
  sudo python3 scripts/loadtest_concurrent.py --mode synth --workers 8
  sudo python3 scripts/loadtest_concurrent.py --mode synth --workers 45
  sudo python3 scripts/loadtest_concurrent.py --mode opendap --workers 16 \\
      --env-file /home/jupyter-tyo/training-ofs-2026/.env
  sudo python3 scripts/loadtest_concurrent.py --mode notebook \\
      --notebook opendap-tutorial.ipynb --workers 8 --timeout 600
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import statistics
import subprocess
import sys
import tempfile
import textwrap
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


DEFAULT_MANIFEST = Path(__file__).resolve().parent / "participant-groups.csv"
DEFAULT_MIRROR = Path(__file__).resolve().parents[1]
DEFAULT_PYTHON = Path("/opt/tljh/user/envs/mandala_env/bin/python")


@dataclass
class Target:
    jupyter_user: str
    workdir: str
    repo_path: Path


def load_targets(manifest: Path, limit: Optional[int] = None) -> list[Target]:
    rows: list[Target] = []
    with manifest.open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            rows.append(
                Target(
                    jupyter_user=row["jupyter_user"],
                    workdir=row["workdir"],
                    repo_path=Path(row["repo_path"]),
                )
            )
    if limit is not None:
        rows = rows[:limit]
    return rows


def write_worker_script(mode: str, notebook: str, env_file: Optional[Path]) -> Path:
    """Python snippet executed as the training user inside their repo."""
    env_load = ""
    if env_file is not None:
        env_load = f"""
from pathlib import Path
env_path = Path({str(env_file)!r})
if env_path.is_file():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
"""

    if mode == "synth":
        body = textwrap.dedent(
            """\
            import numpy as np
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            from datetime import datetime, timezone
            from training_ofs import plot_ofs_map

            # Fake coastal field ~ tutorial case-study subset size
            lat = np.linspace(-7.0, -3.0, 81)
            lon = np.linspace(106.0, 115.0, 181)
            Lon, Lat = np.meshgrid(lon, lat)
            data = 1.2 + 0.4 * np.sin(Lon / 8.0) * np.cos(Lat)
            now = datetime.now(timezone.utc)
            fig, ax = plot_ofs_map(
                lon,
                lat,
                data,
                param="swh",
                baserun=now,
                forecast=now,
                map_area="Loadtest",
            )
            plt.close(fig)
            print("OK synth", data.shape)
            """
        )
    elif mode == "opendap":
        body = textwrap.dedent(
            """\
            import os
            from urllib.parse import quote
            import xarray as xr

            user = os.environ["USEROPENDAP"]
            pw = os.environ["PASSOPENDAP"]
            # Same cycle / path pattern as opendap-tutorial.ipynb
            year, month, cycle = 2026, 9, "20260912_0000"
            rel = f"{year}/{month:02d}/InaCAWOAtmos_{cycle}.nc"
            url = (
                f"https://{quote(user, safe='')}:{quote(pw, safe='')}"
                f"@maritim.bmkg.go.id/opendap/inaCawo/{rel}"
            )
            ds = xr.open_dataset(url, decode_times=False)
            # Tutorial-like Selat Sunda subset on first timestep
            var = "uwnd" if "uwnd" in ds.data_vars else next(iter(ds.data_vars))
            sample = ds[var]
            if "time" in sample.dims:
                sample = sample.isel(time=0)
            sample = sample.sel(lat=slice(-7.0, -3.0), lon=slice(106.0, 115.0))
            mean = float(sample.mean())
            print("OK opendap", rel, var, sample.shape, round(mean, 4))
            ds.close()
            """
        )
    elif mode == "mandala":
        body = textwrap.dedent(
            """\
            import os
            import numpy as np
            import fsspec
            import zcollection as zc
            import zcollection.fs_utils as zc_fs
            from training_ofs import load_s3_options_from_vault

            token = os.environ.get("VAULT_TOKEN")
            if not token:
                raise RuntimeError("VAULT_TOKEN missing")

            s3_options = load_s3_options_from_vault(token=token)
            fs = fsspec.filesystem(
                "s3",
                key=s3_options["key"],
                secret=s3_options["secret"],
                client_kwargs=s3_options["client_kwargs"],
            )
            fs.invalidate_cache()
            ocean2d = zc.open_collection(
                path="mandala-prod1/datalake/model/collections/inacawo_ocean_2d",
                mode="r",
                filesystem=zc_fs.get_fs(filesystem=fs),
            )
            # Same narrow window as mandala-tutorial.ipynb
            date_filter = (
                "(year == 2026 and month == 9 and day >= 12) or "
                "(year == 2026 and month == 9 and day <= 13)"
            )
            dset = ocean2d.load(delayed=True, filters=date_filter).to_xarray()
            sample = dset["sig_wave_height"].isel(
                TSTEP=min(10, dset.sizes["TSTEP"] - 1)
            )
            sample = sample.sel(ROW=slice(-7.0, -3.0), COL=slice(106.0, 115.0))
            if "LAY" in sample.dims:
                sample = sample.isel(LAY=0)
            # Force compute of the cropped field
            field = np.asarray(sample.values)
            mean = float(np.nanmean(field))
            print(
                "OK mandala",
                "TSTEP",
                dset.sizes.get("TSTEP"),
                "shape",
                field.shape,
                "mean",
                round(mean, 4),
            )
            dset.close()
            """
        )
    elif mode == "notebook":
        body = textwrap.dedent(
            f"""\
            from pathlib import Path
            import nbformat
            from nbclient import NotebookClient

            nb_path = Path({notebook!r})
            if not nb_path.is_file():
                raise FileNotFoundError(nb_path)
            nb = nbformat.read(nb_path, as_version=4)
            client = NotebookClient(
                nb,
                timeout=int(os.environ.get("LOADTEST_TIMEOUT", "600")),
                kernel_name=os.environ.get(
                    "LOADTEST_KERNEL", "conda-env-mandala_env-py"
                ),
                resources={{"metadata": {{"path": str(Path.cwd())}}}},
            )
            client.execute()
            print("OK notebook", nb_path.name)
            """
        )
    else:
        raise ValueError(mode)

    header = textwrap.dedent(
        """\
        import os, sys
        from pathlib import Path
        os.chdir(Path(sys.argv[1]))
        sys.path.insert(0, str(Path.cwd()))
        """
    )
    script = header + textwrap.dedent(env_load) + "\n" + textwrap.dedent(body)
    fd, path = tempfile.mkstemp(prefix="ofs-loadtest-", suffix=".py")
    os.close(fd)
    Path(path).write_text(script, encoding="utf-8")
    os.chmod(path, 0o644)
    return Path(path)


def run_one(
    target: Target,
    worker_script: Path,
    timeout: int,
    env_file: Optional[Path],
    python_bin: Path,
) -> dict:
    t0 = time.perf_counter()
    if not target.repo_path.is_dir():
        return {
            "workdir": target.workdir,
            "user": target.jupyter_user,
            "ok": False,
            "seconds": 0.0,
            "error": f"missing repo {target.repo_path}",
        }

    env_args = [
        f"HOME=/home/{target.jupyter_user}",
        f"LOADTEST_TIMEOUT={timeout}",
        "MPLBACKEND=Agg",
    ]
    # Inject secrets into the training-user process (do not rely on sudo env passthrough).
    if env_file and env_file.is_file():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            k, v = k.strip(), v.strip().strip('"').strip("'")
            if k:
                env_args.append(f"{k}={v}")

    cmd = [
        "sudo",
        "-u",
        target.jupyter_user,
        "-H",
        "env",
        *env_args,
        str(python_bin),
        str(worker_script),
        str(target.repo_path),
    ]

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout + 30,
        )
        ok = proc.returncode == 0
        err = (proc.stderr or proc.stdout or "").strip()
        if ok:
            err = (proc.stdout or "").strip().splitlines()[-1] if proc.stdout else "ok"
        return {
            "workdir": target.workdir,
            "user": target.jupyter_user,
            "ok": ok,
            "seconds": round(time.perf_counter() - t0, 2),
            "error": err[-500:] if not ok else err[-200:],
        }
    except subprocess.TimeoutExpired:
        return {
            "workdir": target.workdir,
            "user": target.jupyter_user,
            "ok": False,
            "seconds": round(time.perf_counter() - t0, 2),
            "error": "timeout",
        }


def host_snapshot() -> dict:
    mem = {}
    try:
        out = subprocess.check_output(["free", "-m"], text=True).splitlines()
        #              total  used  free  shared  buff/cache  available
        parts = out[1].split()
        mem = {
            "mem_total_mb": int(parts[1]),
            "mem_used_mb": int(parts[2]),
            "mem_available_mb": int(parts[6]),
        }
    except Exception:  # noqa: BLE001
        pass
    load1, load5, load15 = os.getloadavg()
    return {"load": [load1, load5, load15], **mem}


def main(argv: Optional[list[str]] = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    p.add_argument(
        "--mode",
        choices=["synth", "opendap", "mandala", "notebook"],
        default="synth",
    )
    p.add_argument("--workers", type=int, default=8, help="Max concurrent jobs")
    p.add_argument("--limit", type=int, default=None, help="Only first N participants")
    p.add_argument("--notebook", default="opendap-tutorial.ipynb")
    p.add_argument("--timeout", type=int, default=300)
    p.add_argument(
        "--python",
        type=Path,
        default=DEFAULT_PYTHON,
        help="Interpreter used inside each worker (default: mandala_env)",
    )
    p.add_argument(
        "--env-file",
        type=Path,
        default=DEFAULT_MIRROR / ".env",
        help="Credentials for opendap/mandala/notebook modes",
    )
    p.add_argument("--json-out", type=Path, default=None)
    args = p.parse_args(argv)

    if os.geteuid() != 0:
        print("ERROR: run with sudo (needs sudo -u jupyter-training-ofs-*)", file=sys.stderr)
        return 2
    if not args.manifest.is_file():
        print(f"ERROR: missing manifest {args.manifest}", file=sys.stderr)
        return 2

    targets = load_targets(args.manifest, limit=args.limit)
    if not targets:
        print("ERROR: no targets", file=sys.stderr)
        return 2

    env_file = args.env_file if args.mode != "synth" else None
    if env_file and not env_file.is_file():
        print(f"ERROR: --env-file not found: {env_file}", file=sys.stderr)
        return 2
    if not args.python.is_file():
        print(f"ERROR: python not found: {args.python}", file=sys.stderr)
        return 2

    # training users must read the worker script
    worker_script = write_worker_script(args.mode, args.notebook, env_file)
    os.chmod(worker_script, 0o644)

    print(
        f"Loadtest mode={args.mode} targets={len(targets)} "
        f"workers={args.workers} timeout={args.timeout}s python={args.python}"
    )
    print("host before:", host_snapshot(), flush=True)

    results: list[dict] = []
    t0 = time.perf_counter()
    try:
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futs = {
                pool.submit(
                    run_one, t, worker_script, args.timeout, env_file, args.python
                ): t
                for t in targets
            }
            for fut in as_completed(futs):
                r = fut.result()
                results.append(r)
                flag = "OK" if r["ok"] else "FAIL"
                print(
                    f"[{flag}] {r['user']}/{r['workdir']} {r['seconds']}s {r['error']}",
                    flush=True,
                )
    finally:
        try:
            worker_script.unlink()
        except OSError:
            pass

    wall = round(time.perf_counter() - t0, 2)
    oks = [r for r in results if r["ok"]]
    fails = [r for r in results if not r["ok"]]
    secs = [r["seconds"] for r in oks] or [0.0]
    summary = {
        "mode": args.mode,
        "targets": len(targets),
        "workers": args.workers,
        "wall_seconds": wall,
        "ok": len(oks),
        "fail": len(fails),
        "seconds_min": min(secs),
        "seconds_median": round(statistics.median(secs), 2),
        "seconds_max": max(secs),
        "host_after": host_snapshot(),
        "results": results,
    }
    print("\nSUMMARY", json.dumps({k: v for k, v in summary.items() if k != "results"}, indent=2))
    if args.json_out:
        args.json_out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print("wrote", args.json_out)
    return 0 if not fails else 1


if __name__ == "__main__":
    raise SystemExit(main())

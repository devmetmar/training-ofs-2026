# Admin only — branch `admin`

Folder ini **tidak** ada di branch `main` (peserta). Di-track hanya di branch **`admin`**.

```bash
# Kerja admin (scripts, loadtest, manifest, notebook ber-output untuk preview)
git checkout admin
git pull

# Materi peserta / sync workdir → selalu dari main
git checkout main
# ... edit notebook bersih, commit, push main ...

# Preview ber-output di GitHub: buka branch `admin` di UI
```

## Sync workdir peserta

Sync **selalu** mengambil branch `main` dari mirror, meski working tree sedang di `admin`.

```bash
cd /home/jupyter-tyo/training-ofs-2026

# Semua peserta
sudo ./scripts/sync-participant-workdirs.sh --dry-run
sudo ./scripts/sync-participant-workdirs.sh --pull-only --force

# Filter
sudo ./scripts/sync-participant-workdirs.sh -w 'john-doe' --pull-only --force
sudo ./scripts/sync-participant-workdirs.sh --group 6 --pull-only

# .env dari repo induk (untracked; aman dari --force)
sudo ./scripts/sync-participant-workdirs.sh --env-only

# Opsional: strip output cell di clone peserta
sudo ./scripts/sync-participant-workdirs.sh --pull-only --force --clear-outputs
sudo ./scripts/sync-participant-workdirs.sh --clear-outputs-only -w 'john-doe'
```

## Branch layout

| Branch | Isi | Siapa |
|---|---|---|
| `main` | Notebook (bersih), `training_ofs/`, README peserta | Peserta + GitHub default |
| `admin` | Semua di `main` **+** `scripts/` (sync, loadtest, manifest) | Admin saja |

- `.env` dan `OFS2026-Pre-Test-nilai.csv` tetap di-gitignore di kedua branch (secret/PII).
- Preview notebook ber-output: commit ke `admin`, lalu di GitHub pilih branch `admin`.

## Load test

```bash
sudo python3 scripts/loadtest_concurrent.py --mode synth --workers 8
sudo python3 scripts/loadtest_concurrent.py --mode opendap --workers 8 --env-file .env
sudo python3 scripts/loadtest_concurrent.py --mode mandala --workers 8 --env-file .env
```

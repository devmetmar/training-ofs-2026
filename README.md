# training-ofs-2026

Materi hands-on **Akses Data INACAWO** untuk pelatihan OFS (menyambung PPT *Rantai Produksi dan Metode Akses Data INACAWO*).

## Notebook

| Urutan | File | Isi |
|---|---|---|
| 1 | [`opendap-tutorial.ipynb`](opendap-tutorial.ipynb) | OPeNDAP Hyrax: Atmos / Wave / Flows, struktur data, case study Selat Sunda |
| 2 | [`mandala-tutorial.ipynb`](mandala-tutorial.ipynb) | Mandala S3 + zcollection/Zarr, bandingkan naming/satuan vs OPeNDAP, case study Laut Jawa |

Jalankan keduanya dengan kernel / environment **`mandala_env`** di Mandalahub:
https://api-maritim.bmkg.go.id/mandalahub

## Multi-user / workdir

Materi ini **portable** — tidak bergantung pada path home akun Jupyter tertentu.

Setiap peserta memakai **workdir sendiri** di akun kelompok `jupyter-training-ofs-1` … `jupyter-training-ofs-8`, dengan pola folder `namadepan-namabelakang/training-ofs-2026`.

### Provisioning (admin)

Daftar peserta diambil dari `OFS2026-Pre-Test-nilai.csv`, dibagi 8 kelompok (round-robin), lalu di-clone/pull otomatis:

```bash
# Preview
sudo ./scripts/sync-participant-workdirs.sh --dry-run

# Clone / update semua workdir dari mirror lokal (repo ini)
sudo ./scripts/sync-participant-workdirs.sh

# Hanya update clone yang sudah ada
sudo ./scripts/sync-participant-workdirs.sh --pull-only
```

Manifest kelompok: [`scripts/participant-groups.csv`](scripts/participant-groups.csv).

Alur update materi untuk semua peserta:

1. Commit + push perubahan di mirror admin.
2. `sudo ./scripts/sync-participant-workdirs.sh --pull-only`

Peserta lalu:

1. Login ke akun kelompok yang sesuai.
2. Buka folder `namadepan-namabelakang/training-ofs-2026`.
3. Buat `.env` sendiri di root proyek itu (jangan share).

Notebook mencari root proyek lewat folder `training_ofs/`, lalu memuat `.env` dari situ (`training_ofs.load_project_env`).

## Prasyarat `.env`

Buat file `.env` di root proyek workdir Anda (sudah di-ignore git):

```bash
USEROPENDAP=...
PASSOPENDAP=...
VAULT_TOKEN=...
```

| Variabel | Dipakai oleh |
|---|---|
| `USEROPENDAP` / `PASSOPENDAP` | Tutorial OPeNDAP |
| `VAULT_TOKEN` | Tutorial Mandala (kredensial S3 dari Vault) |

Katalog OPeNDAP: https://maritim.bmkg.go.id/opendap/inaCawo/contents.html

## Helper plotting (gaya operasional OFS)

Package [`training_ofs`](training_ofs/) memuat:

- `ofs_plot_style.py` — **semua** parameter `mapCollection` (colormap, levels, title, unit) dari [devmetmar/ofs-plotter](https://github.com/devmetmar/ofs-plotter)
- `ofs_plot_layout.py` — layout peta (logo BMKG, title, time box, colorbar/legend, basemap, footer)
- `assets/logo60k.png` — logo untuk header peta
- `envfile.py` — pencarian project root + load `.env` portable

```python
from training_ofs import plot_ofs_map, list_params, get_param, find_project_root
print(find_project_root())
print(list_params())
```

Konversi satuan yang didukung helper:

- angin m/s → knot (`wind_in_mps=True`, faktor `1.94384`)
- arus m/s → cm/s (`current_in_mps=True`)

## Perbedaan singkat OPeNDAP vs Mandala

| | OPeNDAP | Mandala |
|---|---|---|
| Kemasan | NetCDF per cycle (Atmos/Wave/Flows) | Living `zcollection` / Zarr |
| Dimensi | `time`, `lat`, `lon` (+ `depth`) | `TSTEP`, `LAY`, `ROW`, `COL` |
| Contoh SWH | `hs` | `sig_wave_height` |
| Retensi | Pendek (forecast operasional) | Panjang (living + hindcast) |

Detail satuan, mapping nama, dan konvensi arah dijelaskan di markdown kedua notebook — **selalu cek `.attrs`** sebelum membandingkan angka antar sumber.

## Best practice

- OPeNDAP: subset di server; jangan unduh file utuh multi-GB.
- Mandala: baca langsung dari S3 di Mandalahub; filter tanggal sempit.
- Satu workdir / satu `.env` per peserta; jangan commit `.env`, token Vault, atau secret S3.

# training-ofs-2026

Materi hands-on **Akses Data INACAWO** untuk pelatihan OFS (menyambung PPT *Rantai Produksi dan Metode Akses Data INACAWO*).

## Notebook

| Urutan | File | Isi |
|---|---|---|
| 1 | [`opendap-inacawo-tutorial.ipynb`](opendap-inacawo-tutorial.ipynb) | OPeNDAP Hyrax: Atmos / Wave / Flows, struktur data, case study Selat Sunda |
| 2 | [`mandala-tutorial.ipynb`](mandala-tutorial.ipynb) | Mandala S3 + zcollection/Zarr, bandingkan naming/satuan vs OPeNDAP, case study Laut Jawa |

Jalankan keduanya dengan kernel / environment **`mandala_env`** di Mandalahub:
https://api-maritim.bmkg.go.id/mandalahub

## Prasyarat `.env`

Buat file `.env` di root proyek (sudah di-ignore git):

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

```python
from training_ofs import plot_ofs_map, list_params, get_param
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
- Jangan commit `.env`, token Vault, atau secret S3.

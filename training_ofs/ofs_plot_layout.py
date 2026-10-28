"""OFS-style map layout for training notebooks.

Layout elements (logo, title, time box, colorbar, vector legend, footer,
basemap) follow ``devmetmar/ofs-plotter`` spatial plotter conventions so
training plots match operational products.

Credit: BMKG Center for Marine Meteorology / ofs-plotter.
"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, Sequence, Union

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import BoundaryNorm, LinearSegmentedColormap, ListedColormap
from matplotlib.offsetbox import (
    AnchoredOffsetbox,
    HPacker,
    OffsetImage,
    TextArea,
)
from matplotlib.ticker import FuncFormatter

import cartopy.crs as ccrs
import cartopy.feature as cfeature
from cartopy.mpl.gridliner import LATITUDE_FORMATTER, LONGITUDE_FORMATTER

from training_ofs.ofs_plot_style import get_param, mapCollection

# m/s → knot (same factor used in OFS plot pipelines)
MPS_TO_KNOT = 1.94384
# m/s → cm/s
MPS_TO_CMS = 100.0

_ASSETS = Path(__file__).resolve().parent / "assets"
_DEFAULT_LOGO = _ASSETS / "logo60k.png"
_LOGO_CACHE: dict[str, np.ndarray] = {}
_CMAP_NORM_CACHE: dict[tuple, tuple] = {}


def _logo_rgba() -> np.ndarray:
    path = os.environ.get("LOGO_BMKG", str(_DEFAULT_LOGO))
    cached = _LOGO_CACHE.get(path)
    if cached is None:
        cached = plt.imread(path)
        _LOGO_CACHE[path] = cached
    return cached


def _as_cmap(color_map: Any) -> matplotlib.colors.Colormap:
    if isinstance(color_map, ListedColormap):
        return color_map
    if isinstance(color_map, matplotlib.colors.Colormap):
        return color_map
    return LinearSegmentedColormap.from_list("ofs_custom", list(color_map))


def _get_cmap_norm(color_map: Any, bounds: Sequence[float], mode: str):
    key = (id(color_map), tuple(bounds), mode)
    hit = _CMAP_NORM_CACHE.get(key)
    if hit is not None:
        return hit
    cmap = _as_cmap(color_map)
    norm = BoundaryNorm(list(bounds), cmap.N)
    if mode == "quiver":
        cmap.set_over("indigo")
    else:
        cmap.set_over("indigo")
        cmap.set_under("indigo")
    _CMAP_NORM_CACHE[key] = (cmap, norm)
    return cmap, norm


def _format_tick(x: float, _pos: int) -> str:
    if float(x).is_integer():
        return f"{int(x)}"
    return f"{x:g}"


def _add_basemap(ax, lon: np.ndarray, lat: np.ndarray) -> None:
    lon0, lon1 = float(np.nanmin(lon)), float(np.nanmax(lon))
    lat0, lat1 = float(np.nanmin(lat)), float(np.nanmax(lat))
    pad_x = max((lon1 - lon0) * 0.02, 0.05)
    pad_y = max((lat1 - lat0) * 0.02, 0.05)
    ax.set_extent(
        [lon0 - pad_x, lon1 + pad_x, lat0 - pad_y, lat1 + pad_y],
        crs=ccrs.PlateCarree(),
    )
    ax.add_feature(cfeature.LAND, facecolor="gray", edgecolor="black", zorder=3)
    ax.add_feature(cfeature.COASTLINE, linewidth=1.0, edgecolor="black", zorder=4)
    ax.add_feature(cfeature.BORDERS, linewidth=0.4, edgecolor="black", zorder=4)


def _prepare_fields(
    param: mapCollection,
    magnitude: np.ndarray,
    u: Optional[np.ndarray],
    v: Optional[np.ndarray],
    direction: Optional[np.ndarray],
    wind_in_mps: bool,
    current_in_mps: bool,
    wave_dir_convention: str = "meteo_from",
) -> tuple[np.ndarray, Optional[np.ndarray], Optional[np.ndarray]]:
    """Return (magnitude, u_quiver, v_quiver) in OFS display units."""
    mag = np.asarray(magnitude, dtype=float)
    datatype = getattr(param, "datatype", "magnitude")

    if datatype == "vector":
        if u is None or v is None:
            raise ValueError(f"param {param.savename!r} needs u and v components")
        uu = np.asarray(u, dtype=float)
        vv = np.asarray(v, dtype=float)
        if param.unit == "knot" and wind_in_mps:
            uu = uu * MPS_TO_KNOT
            vv = vv * MPS_TO_KNOT
        if param.unit == "cm/s" and current_in_mps:
            uu = uu * MPS_TO_CMS
            vv = vv * MPS_TO_CMS
        if param.unit == "knot" and current_in_mps and param.savename == "csd":
            # csdk path: m/s → knot
            uu = uu * MPS_TO_KNOT
            vv = vv * MPS_TO_KNOT
        mag = np.sqrt(uu**2 + vv**2)
        # unit vectors scaled for quiver (OFS convention)
        with np.errstate(invalid="ignore", divide="ignore"):
            uq = np.where(mag > 0, 2.0 * uu / mag, 0.0)
            vq = np.where(mag > 0, 2.0 * vv / mag, 0.0)
        return mag, uq, vq

    if datatype == "direction":
        if direction is None:
            return mag, None, None
        dire = np.asarray(direction, dtype=float)
        conv = (wave_dir_convention or "meteo_from").strip().lower()
        if conv in ("math_to", "cartesian_to", "opendap_hyrax"):
            # Hyrax OPeNDAP `dir` (attrs often empty): degrees CCW from East,
            # already the propagation / "going to" angle. Matches Mandala
            # meteo-from via: meteo_from = (270 - dir) % 360.
            uq = 2.0 * np.cos(np.deg2rad(dire))
            vq = 2.0 * np.sin(np.deg2rad(dire))
            return mag, uq, vq
        if conv not in ("meteo_from", "from", "cf_from", "ofs"):
            raise ValueError(
                "wave_dir_convention must be 'meteo_from' (Mandala/CF/OFS) "
                "or 'math_to' (OPeNDAP Hyrax dir); "
                f"got {wave_dir_convention!r}"
            )
        # Meteorological "coming from" (deg CW from N), CF *_from_direction.
        # Quiver points "going to" — matches inaflows/OFS plotter:
        #   u0,v0 = cos(dir), sin(dir); phi = atan2(u0, v0); quiver = -2*(cos|sin)(phi)
        # Equivalent: u,v = -sin(dir), -cos(dir).
        u0 = np.cos(np.deg2rad(dire))
        v0 = np.sin(np.deg2rad(dire))
        phi = np.arctan2(u0, v0)
        uq = -2.0 * np.cos(phi)
        vq = -2.0 * np.sin(phi)
        return mag, uq, vq

    return mag, None, None


def plot_ofs_map(
    lon: Union[np.ndarray, Any],
    lat: Union[np.ndarray, Any],
    magnitude: Union[np.ndarray, Any],
    *,
    param: Union[str, mapCollection] = "swh",
    u: Optional[Union[np.ndarray, Any]] = None,
    v: Optional[Union[np.ndarray, Any]] = None,
    direction: Optional[Union[np.ndarray, Any]] = None,
    baserun: Optional[datetime] = None,
    forecast: Optional[datetime] = None,
    wind_input: str = "INACAWO",
    map_area: str = "",
    wind_in_mps: bool = False,
    current_in_mps: bool = False,
    wave_dir_convention: str = "meteo_from",
    quiver_skip: int = 8,
    quiver_scale: int = 20,
    figsize: tuple[float, float] = (10, 10),
) -> tuple[plt.Figure, Any]:
    """Plot a field with operational OFS layout.

    Parameters
    ----------
    lon, lat:
        1-D coordinate arrays matching the spatial axes of ``magnitude``.
    magnitude:
        2-D field already subsetted (training notebooks must crop first).
    param:
        ``mapCollection`` key (e.g. ``swh``, ``ws``, ``csd``) or instance.
    u, v:
        Eastward/northward components for vector products (wind/current).
    direction:
        Wave direction (degrees) for ``datatype='direction'`` products.
    wind_in_mps / current_in_mps:
        Set True when source data are in m/s so values are converted to the
        OFS colorbar unit (knot or cm/s).
    wave_dir_convention:
        ``meteo_from`` (default): Mandala/CF ``*_from_direction`` / OFS plotter
        (deg CW from N, coming from). ``math_to``: OPeNDAP Hyrax ``dir``
        (deg CCW from East, already going to).
    """
    if isinstance(param, str):
        param = get_param(param)

    lon_a = np.asarray(lon, dtype=float)
    lat_a = np.asarray(lat, dtype=float)
    mag_a = np.asarray(magnitude, dtype=float)
    u_a = None if u is None else np.asarray(u, dtype=float)
    v_a = None if v is None else np.asarray(v, dtype=float)
    d_a = None if direction is None else np.asarray(direction, dtype=float)

    # Squeeze leading singleton dims (e.g. time=1, depth=1)
    while mag_a.ndim > 2:
        mag_a = np.squeeze(mag_a)
    if u_a is not None:
        while u_a.ndim > 2:
            u_a = np.squeeze(u_a)
    if v_a is not None:
        while v_a.ndim > 2:
            v_a = np.squeeze(v_a)
    if d_a is not None:
        while d_a.ndim > 2:
            d_a = np.squeeze(d_a)

    mag_a, uq, vq = _prepare_fields(
        param,
        mag_a,
        u_a,
        v_a,
        d_a,
        wind_in_mps,
        current_in_mps,
        wave_dir_convention=wave_dir_convention,
    )

    bounds = list(param.clev)
    extend = getattr(param, "extend", "max") or "neither"
    if extend == "":
        extend = "neither"

    fig, ax = plt.subplots(
        subplot_kw={"projection": ccrs.PlateCarree()},
        figsize=figsize,
    )
    gl = ax.gridlines(
        crs=ccrs.PlateCarree(), draw_labels=True, linewidth=0.2, color="w"
    )
    gl.top_labels = False
    gl.right_labels = False
    gl.xformatter = LONGITUDE_FORMATTER
    gl.yformatter = LATITUDE_FORMATTER
    gl.xlabel_style = {"size": 7}
    gl.ylabel_style = {"size": 7}

    _add_basemap(ax, lon_a, lat_a)

    has_quiver = uq is not None and vq is not None
    mode = "quiver" if has_quiver else "scalar"
    cmap, norm = _get_cmap_norm(param.colorbar, bounds, mode)

    Lon, Lat = np.meshgrid(lon_a, lat_a)
    wv_map = ax.contourf(
        Lon,
        Lat,
        mag_a,
        cmap=cmap,
        norm=norm,
        levels=bounds,
        transform=ccrs.PlateCarree(),
        zorder=1,
        extend=extend if extend != "neither" else "neither",
    )

    if has_quiver:
        skip = max(int(quiver_skip), 1)
        ax.quiver(
            Lon[::skip, ::skip],
            Lat[::skip, ::skip],
            uq[::skip, ::skip],
            vq[::skip, ::skip],
            units="inches",
            scale=quiver_scale,
            pivot="mid",
            width=0.01,
            headwidth=5.5,
            headlength=6,
            headaxislength=4,
            minlength=1,
            minshaft=1,
            transform=ccrs.PlateCarree(),
            zorder=2,
        )

    # --- Title / logo / time (OFS layout) ---
    title_core = param.figtitle
    if map_area:
        title_core = f"{title_core}\n{map_area}"

    logobox = OffsetImage(_logo_rgba(), zoom=0.5)
    varbox = TextArea(
        f"BADAN METEOROLOGI KLIMATOLOGI DAN GEOFISIKA\n{title_core}",
        textprops=dict(color="k", weight="bold", family="monospace"),
    )

    now_fc = forecast or baserun or datetime.utcnow()
    now_br = baserun or now_fc
    time_delta = (now_fc - now_br).total_seconds() / 3600.0
    initime = (
        f"Forced by: {wind_input.upper()}\n"
        f'Initial: {now_br.strftime("%HUTC %Y-%m-%d")}'
    )
    if now_fc == now_br:
        fcstime = f'Analysis: {now_fc.strftime("%HUTC %Y-%m-%d")} (t+0)'
    else:
        fcstime = (
            f'Forecast: {now_fc.strftime("%HUTC %Y-%m-%d")} '
            f"(t+{time_delta:g})"
        )
    timebox = TextArea(
        f"{initime}\n{fcstime}",
        textprops=dict(
            color="k", size=9, family="monospace", horizontalalignment="right"
        ),
    )

    logovarbox = HPacker(children=[logobox, varbox], align="center", pad=0, sep=2)
    uleftbox = AnchoredOffsetbox(
        loc="lower left",
        child=logovarbox,
        pad=0.0,
        frameon=False,
        bbox_to_anchor=(0, 1.0),
        bbox_transform=ax.transAxes,
        borderpad=0.1,
    )
    urightbox = AnchoredOffsetbox(
        loc="lower right",
        child=HPacker(children=[timebox], align="center", pad=0, sep=2),
        pad=0.0,
        frameon=False,
        bbox_to_anchor=(1.0, 1.01),
        bbox_transform=ax.transAxes,
        borderpad=0.1,
    )
    ax.add_artist(uleftbox)
    ax.add_artist(urightbox)

    source = "Source: BMKG Ocean Forecast System (BMKG-OFS)"
    credit = (
        f"Created by Center for Marine Meteorology. "
        f"\u00A9{datetime.now().year}"
    )
    sourcecredittext = TextArea(
        f"{source}\n{credit}",
        textprops=dict(
            color="k", size=5.5, family="monospace", horizontalalignment="left"
        ),
    )
    lleftbox = AnchoredOffsetbox(
        loc="upper left",
        child=HPacker(children=[sourcecredittext], align="center", pad=0, sep=2),
        pad=0.0,
        frameon=False,
        bbox_to_anchor=(0.0, -0.06),
        bbox_transform=ax.transAxes,
        borderpad=0.1,
    )
    ax.add_artist(lleftbox)

    # --- Colorbar ---
    bbox = ax.get_position()
    cbar_width = bbox.width - (bbox.width * 0.5)
    cbar_left = bbox.x0 + (bbox.width * 0.5)
    cbar_bottom = bbox.y0 - 0.06
    cbar_height = 0.015
    legend = f"{param.cbrtitle} ({param.unit})"

    if has_quiver:
        cbar_ax = fig.add_axes([cbar_left, cbar_bottom, cbar_width, cbar_height])
        cbar_extend = "max"
    else:
        cbar_ax = fig.add_axes(
            [cbar_left - 0.1, cbar_bottom, cbar_width + 0.1, cbar_height]
        )
        cbar_extend = extend if extend != "neither" else "neither"

    cbar = fig.colorbar(
        wv_map,
        cax=cbar_ax,
        ticks=bounds,
        norm=norm,
        orientation="horizontal",
        pad=0.05,
        extend=cbar_extend,
    )
    cbar.set_label(legend, fontsize=9, fontname="monospace", labelpad=-36)
    cbar.ax.tick_params(labelsize=8)
    cbar.ax.xaxis.set_major_formatter(FuncFormatter(_format_tick))

    if has_quiver and getattr(param, "dirtitle", None):
        cbar_bbox = cbar_ax.get_position()
        arrow_x = cbar_bbox.x0 - 0.06
        arrow_y = cbar_bbox.y0 + (cbar_bbox.height / 2) - 0.01
        fig.text(
            arrow_x,
            arrow_y + 0.02,
            param.dirtitle,
            fontsize=8,
            ha="center",
            va="center",
        )
        arrax = fig.add_axes(
            [arrow_x - 0.01, arrow_y - 0.008, 0.014, 0.01], frameon=True
        )
        arrax.arrow(
            0,
            0,
            0.02,
            0.01,
            head_width=0.006,
            head_length=0.01,
            fc="k",
            ec="k",
        )
        arrax.set_xlim(-0.005, 0.035)
        arrax.set_ylim(-0.01, 0.02)
        arrax.set_xticks([])
        arrax.set_yticks([])

    # Wave-warning categorical colorbar labels
    if param.savename == "ww":
        cbar.set_ticks([0.625, 1.875, 3.25, 5.0, 7.5])
        cbar.set_ticklabels(
            ["Tenang -\nRendah", "Sedang", "Tinggi", "Sangat\nTinggi", "Ekstrem"]
        )

    return fig, ax

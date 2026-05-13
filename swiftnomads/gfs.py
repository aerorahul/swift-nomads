from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import fsspec
import xarray as xr

from .common import build_reference_metadata as _build_reference_metadata
from .common import default_reference_cache_path as _default_reference_cache_path
from .common import get_or_build_kerchunk_refs as _get_or_build_kerchunk_refs
from .common import (
    open_reference_dataset,
)
from .common import should_refresh_reference as _should_refresh_reference


@dataclass(frozen=True)
class GFSConfig:
    forecast_date: str
    forecast_component: str = "atmos"
    bucket: str = "noaa-gfs-bdp-pds"

    @property
    def ymd(self) -> str:
        return self.forecast_date[:8]

    @property
    def cycle(self) -> str:
        return self.forecast_date[9:11]

    @property
    def prefix(self) -> str:
        return f"gfs.{self.ymd}/{self.cycle}/{self.forecast_component}"


def gfs_file_name(cycle: str, forecast_hour: int) -> str:
    return f"gfs.t{cycle}z.pgrb2.0p25.f{forecast_hour:03d}"


def gfs_s3_url(cfg: GFSConfig, forecast_hour: int) -> str:
    file_name = gfs_file_name(cfg.cycle, forecast_hour)
    return f"s3://{cfg.bucket}/{cfg.prefix}/{file_name}"


def list_gfs_forecast_hours(cfg: GFSConfig, anon: bool = True) -> list[int]:
    fs = fsspec.filesystem("s3", anon=anon)
    files = fs.ls(f"{cfg.bucket}/{cfg.prefix}", detail=False)
    hours: list[int] = []
    for path in files:
        name = path.rsplit("/", maxsplit=1)[-1]
        if ".f" not in name:
            continue
        try:
            hours.append(int(name.rsplit(".f", maxsplit=1)[-1]))
        except ValueError:
            continue
    return sorted(set(hours))


def build_gfs_refs(
    cfg: GFSConfig,
    forecast_hours: list[int],
    anon: bool = True,
) -> dict[str, Any]:
    from kerchunk.grib2 import grib_tree, scan_grib

    if not forecast_hours:
        raise ValueError("forecast_hours cannot be empty")

    storage_options = {"anon": anon}
    message_groups = []
    for hour in forecast_hours:
        message_groups.extend(
            scan_grib(gfs_s3_url(cfg, hour), storage_options=storage_options)
        )

    def _build() -> dict[str, Any]:
        return grib_tree(message_groups, remote_options=storage_options)

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return _build()

    with ThreadPoolExecutor(max_workers=1) as executor:
        return executor.submit(_build).result()


def gfs_identity(cfg: GFSConfig) -> dict[str, Any]:
    return {
        "forecast_date": cfg.forecast_date,
        "forecast_component": cfg.forecast_component,
        "bucket": cfg.bucket,
        "cycle": cfg.cycle,
    }


def default_gfs_cache_path(
    cfg: GFSConfig,
    forecast_hours: list[int],
    cache_dir: str | Path = ".cache/swiftnomads/refs",
):
    return _default_reference_cache_path(
        model_name="gfs",
        identity=gfs_identity(cfg),
        forecast_hours=forecast_hours,
        cache_dir=cache_dir,
    )


def build_gfs_reference_metadata(
    cfg: GFSConfig,
    forecast_hours: list[int],
    anon: bool = True,
) -> dict[str, Any]:
    return _build_reference_metadata(
        model_name="gfs",
        identity=gfs_identity(cfg),
        forecast_hours=forecast_hours,
        anon=anon,
    )


def should_refresh_gfs_reference(
    cached_meta: dict[str, Any],
    cfg: GFSConfig,
    forecast_hours: list[int],
    ttl_hours: int | None = 24,
) -> bool:
    return _should_refresh_reference(
        cached_meta=cached_meta,
        model_name="gfs",
        identity=gfs_identity(cfg),
        forecast_hours=forecast_hours,
        ttl_hours=ttl_hours,
    )


def get_or_build_gfs_refs(
    cfg: GFSConfig,
    forecast_hours: list[int],
    cache_dir: str | Path = ".cache/swiftnomads/refs",
    anon: bool = True,
    ttl_hours: int | None = 24,
    force_refresh: bool = False,
) -> dict[str, Any]:
    return _get_or_build_kerchunk_refs(
        model_name="gfs",
        identity=gfs_identity(cfg),
        forecast_hours=forecast_hours,
        build_reference_fn=lambda hrs, is_anon: build_gfs_refs(cfg, hrs, anon=is_anon),
        cache_dir=cache_dir,
        anon=anon,
        ttl_hours=ttl_hours,
        force_refresh=force_refresh,
    )


def open_gfs_dataset(
    cfg: GFSConfig,
    forecast_hours: list[int],
    anon: bool = True,
    group: str | None = None,
) -> xr.Dataset:
    ref = build_gfs_refs(cfg, forecast_hours=forecast_hours, anon=anon)
    return open_reference_dataset(ref, anon=anon, group=group)


def open_gfs_dataset_cached(
    cfg: GFSConfig,
    forecast_hours: list[int],
    cache_dir: str | Path = ".cache/swiftnomads/refs",
    anon: bool = True,
    group: str | None = None,
    ttl_hours: int | None = 24,
    force_refresh: bool = False,
) -> xr.Dataset:
    ref = get_or_build_gfs_refs(
        cfg=cfg,
        forecast_hours=forecast_hours,
        cache_dir=cache_dir,
        anon=anon,
        ttl_hours=ttl_hours,
        force_refresh=force_refresh,
    )
    return open_reference_dataset(ref, anon=anon, group=group)

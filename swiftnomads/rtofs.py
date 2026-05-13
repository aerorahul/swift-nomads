from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import fsspec
import xarray as xr

from .common import default_reference_cache_path as _default_reference_cache_path
from .common import get_or_build_kerchunk_refs as _get_or_build_kerchunk_refs
from .common import (
    open_reference_dataset,
)
from .common import should_refresh_reference as _should_refresh_reference

logger = logging.getLogger('swiftnomads.rtofs')


@dataclass(frozen=True)
class RTOFSConfig:
    forecast_date: str
    bucket: str = "noaa-nodd-kerchunk-pds"

    @property
    def ymd(self) -> str:
        return self.forecast_date[:8]


def rtofs_reference_url(cfg: RTOFSConfig, forecast_hour: int) -> str:
    return (
        f"s3://{cfg.bucket}/rtofs/"
        f"rtofs.{cfg.ymd}.rtofs_glo_2ds_f{forecast_hour:03d}_hunk.json"
    )


def rtofs_identity(cfg: RTOFSConfig) -> dict[str, Any]:
    return {
        "forecast_date": cfg.forecast_date,
        "bucket": cfg.bucket,
    }


def list_rtofs_forecast_hours(cfg: RTOFSConfig, anon: bool = True) -> list[int]:
    fs = fsspec.filesystem("s3", anon=anon)
    files = fs.ls(f"{cfg.bucket}/rtofs", detail=False)
    pat = re.compile(rf"rtofs\.{cfg.ymd}\.rtofs_glo_2ds_f(\d{{3}})_hunk\.json$")

    hours: list[int] = []
    for path in files:
        name = path.rsplit("/", maxsplit=1)[-1]
        match = pat.match(name)
        if not match:
            continue
        hours.append(int(match.group(1)))

    return sorted(set(hours))


def build_rtofs_refs(
    cfg: RTOFSConfig,
    forecast_hours: list[int],
    anon: bool = True,
) -> dict[str, Any]:
    if not forecast_hours:
        raise ValueError("forecast_hours cannot be empty")
    if len(forecast_hours) != 1:
        raise ValueError("RTOFS currently supports one forecast hour per reference file")

    fs = fsspec.filesystem("s3", anon=anon)
    path = rtofs_reference_url(cfg, forecast_hours[0]).replace("s3://", "", 1)
    if not fs.exists(path):
        raise FileNotFoundError(f"RTOFS reference not found: s3://{path}")

    with fs.open(path, "r") as fp:
        reference = json.load(fp)

    if not isinstance(reference, dict) or "refs" not in reference:
        raise ValueError("Invalid RTOFS reference payload: expected kerchunk-like JSON")
    return reference


def default_rtofs_cache_path(
    cfg: RTOFSConfig,
    forecast_hours: list[int],
    cache_dir: str | Path = ".cache/swiftnomads/refs",
):
    return _default_reference_cache_path(
        model_name="rtofs",
        identity=rtofs_identity(cfg),
        forecast_hours=forecast_hours,
        cache_dir=cache_dir,
    )


def should_refresh_rtofs_reference(
    cached_meta: dict[str, Any],
    cfg: RTOFSConfig,
    forecast_hours: list[int],
    ttl_hours: int | None = 24,
) -> bool:
    return _should_refresh_reference(
        cached_meta=cached_meta,
        model_name="rtofs",
        identity=rtofs_identity(cfg),
        forecast_hours=forecast_hours,
        ttl_hours=ttl_hours,
    )


def get_or_build_rtofs_refs(
    cfg: RTOFSConfig,
    forecast_hours: list[int],
    cache_dir: str | Path = ".cache/swiftnomads/refs",
    anon: bool = True,
    ttl_hours: int | None = 24,
    force_refresh: bool = False,
) -> dict[str, Any]:
    return _get_or_build_kerchunk_refs(
        model_name="rtofs",
        identity=rtofs_identity(cfg),
        forecast_hours=forecast_hours,
        build_reference_fn=lambda hrs, is_anon: build_rtofs_refs(cfg, hrs, anon=is_anon),
        cache_dir=cache_dir,
        anon=anon,
        ttl_hours=ttl_hours,
        force_refresh=force_refresh,
    )


def open_rtofs_dataset(
    cfg: RTOFSConfig,
    forecast_hours: list[int],
    anon: bool = True,
    group: str | None = None,
) -> xr.Dataset:
    ref = build_rtofs_refs(cfg, forecast_hours=forecast_hours, anon=anon)
    return open_reference_dataset(ref, anon=anon, group=group)


def open_rtofs_dataset_cached(
    cfg: RTOFSConfig,
    forecast_hours: list[int],
    cache_dir: str | Path = ".cache/swiftnomads/refs",
    anon: bool = True,
    group: str | None = None,
    ttl_hours: int | None = 24,
    force_refresh: bool = False,
) -> xr.Dataset:
    ref = get_or_build_rtofs_refs(
        cfg=cfg,
        forecast_hours=forecast_hours,
        cache_dir=cache_dir,
        anon=anon,
        ttl_hours=ttl_hours,
        force_refresh=force_refresh,
    )
    return open_reference_dataset(ref, anon=anon, group=group)

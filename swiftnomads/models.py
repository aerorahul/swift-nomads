from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, Union

import xarray as xr

from .gfs import (
    GFSConfig,
    default_gfs_cache_path,
    get_or_build_gfs_refs,
    list_gfs_forecast_hours,
    open_gfs_dataset_cached,
    should_refresh_gfs_reference,
)
from .rtofs import (
    RTOFSConfig,
    default_rtofs_cache_path,
    get_or_build_rtofs_refs,
    list_rtofs_forecast_hours,
    open_rtofs_dataset_cached,
    should_refresh_rtofs_reference,
)

ModelConfig = Union[GFSConfig, RTOFSConfig]


class ModelAdapter(Protocol):
    def make_config(self, forecast_date: str, **kwargs: Any) -> ModelConfig: ...

    def list_forecast_hours(self, cfg: Any, anon: bool = True) -> list[int]: ...

    def select_forecast_hours(self, hours: list[int], count: int = 2) -> list[int]: ...

    def default_cache_path(
        self,
        cfg: Any,
        forecast_hours: list[int],
        cache_dir: str | Path = ".cache/swiftnomads/refs",
    ) -> Path: ...

    def should_refresh_reference(
        self,
        cached_meta: dict[str, Any],
        cfg: Any,
        forecast_hours: list[int],
        ttl_hours: int | None = 24,
    ) -> bool: ...

    def get_or_build_refs(
        self,
        cfg: Any,
        forecast_hours: list[int],
        cache_dir: str | Path = ".cache/swiftnomads/refs",
        anon: bool = True,
        ttl_hours: int | None = 24,
        force_refresh: bool = False,
    ) -> dict[str, Any]: ...

    def open_dataset_cached(
        self,
        cfg: Any,
        forecast_hours: list[int],
        cache_dir: str | Path = ".cache/swiftnomads/refs",
        anon: bool = True,
        group: str | None = None,
        ttl_hours: int | None = 24,
        force_refresh: bool = False,
    ) -> xr.Dataset: ...


@dataclass(frozen=True)
class GFSModelAdapter:
    name: str = "gfs"

    def make_config(self, forecast_date: str, **kwargs: Any) -> GFSConfig:
        return GFSConfig(forecast_date=forecast_date, **kwargs)

    def list_forecast_hours(self, cfg: GFSConfig, anon: bool = True) -> list[int]:
        return list_gfs_forecast_hours(cfg, anon=anon)

    def select_forecast_hours(self, hours: list[int], count: int = 2) -> list[int]:
        return hours[:count]

    def default_cache_path(
        self,
        cfg: GFSConfig,
        forecast_hours: list[int],
        cache_dir: str | Path = ".cache/swiftnomads/refs",
    ) -> Path:
        return default_gfs_cache_path(cfg, forecast_hours, cache_dir=cache_dir)

    def should_refresh_reference(
        self,
        cached_meta: dict[str, Any],
        cfg: GFSConfig,
        forecast_hours: list[int],
        ttl_hours: int | None = 24,
    ) -> bool:
        return should_refresh_gfs_reference(
            cached_meta,
            cfg,
            forecast_hours,
            ttl_hours=ttl_hours,
        )

    def get_or_build_refs(
        self,
        cfg: GFSConfig,
        forecast_hours: list[int],
        cache_dir: str | Path = ".cache/swiftnomads/refs",
        anon: bool = True,
        ttl_hours: int | None = 24,
        force_refresh: bool = False,
    ) -> dict[str, Any]:
        return get_or_build_gfs_refs(
            cfg=cfg,
            forecast_hours=forecast_hours,
            cache_dir=cache_dir,
            anon=anon,
            ttl_hours=ttl_hours,
            force_refresh=force_refresh,
        )

    def open_dataset_cached(
        self,
        cfg: GFSConfig,
        forecast_hours: list[int],
        cache_dir: str | Path = ".cache/swiftnomads/refs",
        anon: bool = True,
        group: str | None = None,
        ttl_hours: int | None = 24,
        force_refresh: bool = False,
    ) -> xr.Dataset:
        return open_gfs_dataset_cached(
            cfg=cfg,
            forecast_hours=forecast_hours,
            cache_dir=cache_dir,
            anon=anon,
            group=group,
            ttl_hours=ttl_hours,
            force_refresh=force_refresh,
        )


@dataclass(frozen=True)
class RTOFSModelAdapter:
    name: str = "rtofs"

    def make_config(self, forecast_date: str, **kwargs: Any) -> RTOFSConfig:
        return RTOFSConfig(forecast_date=forecast_date, **kwargs)

    def list_forecast_hours(self, cfg: RTOFSConfig, anon: bool = True) -> list[int]:
        return list_rtofs_forecast_hours(cfg, anon=anon)

    def select_forecast_hours(self, hours: list[int], count: int = 2) -> list[int]:
        if not hours:
            return []
        return [hours[0]]

    def default_cache_path(
        self,
        cfg: RTOFSConfig,
        forecast_hours: list[int],
        cache_dir: str | Path = ".cache/swiftnomads/refs",
    ) -> Path:
        return default_rtofs_cache_path(cfg, forecast_hours, cache_dir=cache_dir)

    def should_refresh_reference(
        self,
        cached_meta: dict[str, Any],
        cfg: RTOFSConfig,
        forecast_hours: list[int],
        ttl_hours: int | None = 24,
    ) -> bool:
        return should_refresh_rtofs_reference(
            cached_meta,
            cfg,
            forecast_hours,
            ttl_hours=ttl_hours,
        )

    def get_or_build_refs(
        self,
        cfg: RTOFSConfig,
        forecast_hours: list[int],
        cache_dir: str | Path = ".cache/swiftnomads/refs",
        anon: bool = True,
        ttl_hours: int | None = 24,
        force_refresh: bool = False,
    ) -> dict[str, Any]:
        return get_or_build_rtofs_refs(
            cfg=cfg,
            forecast_hours=forecast_hours,
            cache_dir=cache_dir,
            anon=anon,
            ttl_hours=ttl_hours,
            force_refresh=force_refresh,
        )

    def open_dataset_cached(
        self,
        cfg: RTOFSConfig,
        forecast_hours: list[int],
        cache_dir: str | Path = ".cache/swiftnomads/refs",
        anon: bool = True,
        group: str | None = None,
        ttl_hours: int | None = 24,
        force_refresh: bool = False,
    ) -> xr.Dataset:
        return open_rtofs_dataset_cached(
            cfg=cfg,
            forecast_hours=forecast_hours,
            cache_dir=cache_dir,
            anon=anon,
            group=group,
            ttl_hours=ttl_hours,
            force_refresh=force_refresh,
        )


MODEL_ADAPTERS: dict[str, ModelAdapter] = {
    "gfs": GFSModelAdapter(),
    "rtofs": RTOFSModelAdapter(),
}


def get_model_adapter(model: str) -> ModelAdapter:
    model_name = model.strip().lower()
    adapter = MODEL_ADAPTERS.get(model_name)
    if adapter is None:
        raise ValueError(
            f"Unsupported model '{model}'. Available models: {', '.join(available_models())}"
        )
    return adapter


def available_models() -> list[str]:
    return sorted(MODEL_ADAPTERS)


def open_model_dataset_cached(
    model: str,
    cfg: ModelConfig,
    forecast_hours: list[int],
    cache_dir: str | Path = ".cache/swiftnomads/refs",
    anon: bool = True,
    group: str | None = None,
    ttl_hours: int | None = 24,
    force_refresh: bool = False,
) -> xr.Dataset:
    adapter = get_model_adapter(model)
    return adapter.open_dataset_cached(
        cfg=cfg,
        forecast_hours=forecast_hours,
        cache_dir=cache_dir,
        anon=anon,
        group=group,
        ttl_hours=ttl_hours,
        force_refresh=force_refresh,
    )


def infer_model_config(model: str, forecast_date: str, **kwargs: Any) -> ModelConfig:
    adapter = get_model_adapter(model)
    return adapter.make_config(forecast_date=forecast_date, **kwargs)

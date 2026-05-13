from __future__ import annotations

import base64
import json
from datetime import datetime, timedelta, timezone
from importlib import metadata
from pathlib import Path
from typing import Any, Callable

import fsspec
import xarray as xr


def normalize_forecast_hours(forecast_hours: list[int]) -> list[int]:
    return sorted(set(forecast_hours))


def _json_safe(value: Any) -> Any:
    if isinstance(value, bytes):
        try:
            return value.decode("utf-8")
        except UnicodeDecodeError:
            return {"__bytes__": base64.b64encode(value).decode("ascii")}
    if isinstance(value, dict):
        return {key: _json_safe(inner_value) for key, inner_value in value.items()}
    if isinstance(value, list):
        return [_json_safe(inner_value) for inner_value in value]
    if isinstance(value, tuple):
        return [_json_safe(inner_value) for inner_value in value]
    return value


def _cache_file_name(
    model_name: str,
    identity: dict[str, Any],
    forecast_hours: list[int],
) -> str:
    hours = "-".join(f"{hour:03d}" for hour in normalize_forecast_hours(forecast_hours))
    identity_parts = "_".join(
        f"{key}-{identity[key]}" for key in sorted(identity) if identity.get(key) is not None
    )
    return f"{model_name}_{identity_parts}_{hours}.kerchunk.json"


def reference_metadata_path(reference_path: Path) -> Path:
    return reference_path.with_suffix(".meta.json")


def default_reference_cache_path(
    model_name: str,
    identity: dict[str, Any],
    forecast_hours: list[int],
    cache_dir: str | Path = ".cache/swiftnomads/refs",
) -> Path:
    cache_root = Path(cache_dir)
    return cache_root / _cache_file_name(model_name, identity, forecast_hours)


def save_kerchunk_refs(reference: dict[str, Any], filepath: str | Path) -> None:
    if "refs" not in reference:
        raise ValueError("Invalid kerchunk reference: expected top-level 'refs' key")

    target = Path(filepath)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as fp:
        json.dump(_json_safe(reference), fp)


def load_kerchunk_refs(filepath: str | Path) -> dict[str, Any]:
    source = Path(filepath)
    if not source.exists():
        raise FileNotFoundError(f"Kerchunk reference file not found: {source}")

    with source.open("r", encoding="utf-8") as fp:
        payload = json.load(fp)

    if not isinstance(payload, dict) or "refs" not in payload:
        raise ValueError(
            "Invalid kerchunk reference payload: expected a dict with top-level 'refs' key"
        )
    return payload


def build_reference_metadata(
    model_name: str,
    identity: dict[str, Any],
    forecast_hours: list[int],
    anon: bool = True,
) -> dict[str, Any]:
    grib2io_available = False
    grib2io_version = None
    try:
        import grib2io  # type: ignore

        grib2io_available = True
        grib2io_version = getattr(grib2io, "__version__", None)
        if not grib2io_version:
            grib2io_version = metadata.version("grib2io")
    except Exception:
        grib2io_available = False
        grib2io_version = None

    return {
        "model": model_name,
        "identity": identity,
        "forecast_hours": normalize_forecast_hours(forecast_hours),
        "anon": anon,
        "built_at": datetime.now(timezone.utc).isoformat(),
        "grib2io_available": grib2io_available,
        "grib2io_version": grib2io_version,
        "kerchunk_version": metadata.version("kerchunk"),
        "cache_schema_version": 1,
    }


def save_reference_metadata(metadata_obj: dict[str, Any], filepath: str | Path) -> None:
    target = Path(filepath)
    meta_path = reference_metadata_path(target)
    meta_path.parent.mkdir(parents=True, exist_ok=True)
    with meta_path.open("w", encoding="utf-8") as fp:
        json.dump(metadata_obj, fp)


def load_reference_metadata(filepath: str | Path) -> dict[str, Any]:
    meta_path = reference_metadata_path(Path(filepath))
    if not meta_path.exists():
        return {}

    with meta_path.open("r", encoding="utf-8") as fp:
        payload = json.load(fp)

    if not isinstance(payload, dict):
        raise ValueError("Invalid metadata payload: expected JSON object")
    return payload


def should_refresh_reference(
    cached_meta: dict[str, Any],
    model_name: str,
    identity: dict[str, Any],
    forecast_hours: list[int],
    ttl_hours: int | None = 24,
) -> bool:
    if not cached_meta:
        return True

    if cached_meta.get("model") != model_name:
        return True
    if cached_meta.get("identity") != identity:
        return True
    if cached_meta.get("forecast_hours") != normalize_forecast_hours(forecast_hours):
        return True

    if ttl_hours is None:
        return False

    built_at = cached_meta.get("built_at")
    if not isinstance(built_at, str):
        return True

    try:
        built_dt = datetime.fromisoformat(built_at)
    except ValueError:
        return True

    if built_dt.tzinfo is None:
        built_dt = built_dt.replace(tzinfo=timezone.utc)

    return datetime.now(timezone.utc) - built_dt >= timedelta(hours=ttl_hours)


def get_or_build_kerchunk_refs(
    model_name: str,
    identity: dict[str, Any],
    forecast_hours: list[int],
    build_reference_fn: Callable[[list[int], bool], dict[str, Any]],
    cache_dir: str | Path = ".cache/swiftnomads/refs",
    anon: bool = True,
    ttl_hours: int | None = 24,
    force_refresh: bool = False,
) -> dict[str, Any]:
    cache_path = default_reference_cache_path(
        model_name=model_name,
        identity=identity,
        forecast_hours=forecast_hours,
        cache_dir=cache_dir,
    )
    metadata_obj = load_reference_metadata(cache_path)

    if not force_refresh and cache_path.exists() and not should_refresh_reference(
        metadata_obj,
        model_name=model_name,
        identity=identity,
        forecast_hours=forecast_hours,
        ttl_hours=ttl_hours,
    ):
        return load_kerchunk_refs(cache_path)

    reference = build_reference_fn(normalize_forecast_hours(forecast_hours), anon)
    save_kerchunk_refs(reference, cache_path)
    save_reference_metadata(
        build_reference_metadata(
            model_name=model_name,
            identity=identity,
            forecast_hours=forecast_hours,
            anon=anon,
        ),
        cache_path,
    )
    return reference


def list_reference_groups(reference: dict[str, Any]) -> list[str]:
    refs = reference.get("refs", {})
    groups = []
    for key in refs:
        if not key.endswith("/.zgroup"):
            continue
        group = key[: -len("/.zgroup")]
        if group:
            groups.append(group)
    return sorted(set(groups))


def open_reference_dataset(
    reference: dict[str, Any],
    anon: bool = True,
    group: str | None = None,
) -> xr.Dataset:
    groups = list_reference_groups(reference)
    selected_group = group or (groups[0] if groups else None)

    fs = fsspec.filesystem(
        "reference",
        fo=reference,
        remote_protocol="s3",
        remote_options={"anon": anon, "asynchronous": True},
        asynchronous=True,
    )
    mapper = fs.get_mapper(selected_group or "")
    return xr.open_dataset(
        mapper,
        engine="zarr",
        backend_kwargs={"consolidated": False},
    )

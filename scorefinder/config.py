from __future__ import annotations

import json
import os
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path


APP_HOME = Path(os.environ.get("SCOREFINDER_HOME", Path.home() / ".scorefinder")).expanduser()
DEFAULT_STORAGE_ROOT = APP_HOME / "storage"
BOOTSTRAP_PATH = APP_HOME / "bootstrap.json"
LEGACY_LOCAL_CONFIG_PATH = APP_HOME / "config.json"
LEGACY_DB_PATH = APP_HOME / "scorefinder.sqlite3"
DB_FILENAME = "scorefinder.sqlite3"
CONFIG_FILENAME = "scorefinder.config.json"


@dataclass(slots=True)
class AppConfig:
    storage_root: str = str(DEFAULT_STORAGE_ROOT)


def ensure_app_home() -> None:
    APP_HOME.mkdir(parents=True, exist_ok=True)


def get_config_path(config: AppConfig | None = None) -> Path:
    resolved_config = config or AppConfig(storage_root=_load_bootstrap_storage_root())
    storage_root = Path(resolved_config.storage_root).expanduser().resolve()
    return storage_root / CONFIG_FILENAME


def get_db_path(config: AppConfig | None = None) -> Path:
    resolved_config = config or load_config()
    storage_root = Path(resolved_config.storage_root).expanduser().resolve()
    return storage_root / DB_FILENAME


def ensure_database_location(
    config: AppConfig,
    *,
    previous_storage_root: str | None = None,
) -> Path:
    target_path = get_db_path(config)
    target_path.parent.mkdir(parents=True, exist_ok=True)

    candidates: list[Path] = []
    if previous_storage_root:
        previous_root = Path(previous_storage_root).expanduser().resolve()
        for previous_path in (
            previous_root / DB_FILENAME,
            previous_root / ".scorefinder" / DB_FILENAME,
        ):
            if previous_path != target_path:
                candidates.append(previous_path)
    if LEGACY_DB_PATH != target_path:
        candidates.append(LEGACY_DB_PATH)
    transitional_hidden_path = target_path.parent / ".scorefinder" / DB_FILENAME
    if transitional_hidden_path != target_path:
        candidates.append(transitional_hidden_path)

    for candidate in candidates:
        if not candidate.exists() or target_path.exists():
            continue
        _move_sqlite_files(candidate, target_path)
        break

    return target_path


def load_config() -> AppConfig:
    ensure_app_home()
    bootstrap_storage_root = _load_bootstrap_storage_root()
    config = AppConfig(storage_root=bootstrap_storage_root)
    config_path = get_config_path(config)

    if config_path.exists():
        data = json.loads(config_path.read_text(encoding="utf-8"))
        storage_root = data.get("storage_root") or bootstrap_storage_root
        normalized = AppConfig(storage_root=str(Path(storage_root).expanduser().resolve()))
        _write_bootstrap(normalized.storage_root)
        return normalized

    if LEGACY_LOCAL_CONFIG_PATH.exists():
        data = json.loads(LEGACY_LOCAL_CONFIG_PATH.read_text(encoding="utf-8"))
        storage_root = data.get("storage_root") or bootstrap_storage_root
        normalized = AppConfig(storage_root=str(Path(storage_root).expanduser().resolve()))
        save_config(normalized)
        return normalized

    normalized = AppConfig(storage_root=str(Path(bootstrap_storage_root).expanduser().resolve()))
    save_config(normalized)
    return normalized


def save_config(config: AppConfig) -> AppConfig:
    ensure_app_home()
    normalized_root = Path(config.storage_root).expanduser().resolve()
    normalized_root.mkdir(parents=True, exist_ok=True)
    normalized = AppConfig(storage_root=str(normalized_root))
    config_path = get_config_path(normalized)
    config_path.write_text(
        json.dumps(asdict(normalized), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    _write_bootstrap(normalized.storage_root)
    return normalized


def get_bootstrap_path() -> Path:
    ensure_app_home()
    return BOOTSTRAP_PATH


def _load_bootstrap_storage_root() -> str:
    ensure_app_home()
    for path in (BOOTSTRAP_PATH, LEGACY_LOCAL_CONFIG_PATH):
        if not path.exists():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        storage_root = data.get("storage_root")
        if storage_root:
            return str(Path(storage_root).expanduser().resolve())
    return str(DEFAULT_STORAGE_ROOT.resolve())


def _write_bootstrap(storage_root: str) -> None:
    BOOTSTRAP_PATH.write_text(
        json.dumps({"storage_root": storage_root}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    if LEGACY_LOCAL_CONFIG_PATH != BOOTSTRAP_PATH and LEGACY_LOCAL_CONFIG_PATH.exists():
        LEGACY_LOCAL_CONFIG_PATH.unlink(missing_ok=True)


def _move_sqlite_files(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    for source_path, target_path in (
        (source, target),
        (source.with_name(f"{source.name}-wal"), target.with_name(f"{target.name}-wal")),
        (source.with_name(f"{source.name}-shm"), target.with_name(f"{target.name}-shm")),
    ):
        if not source_path.exists():
            continue
        if target_path.exists():
            source_path.unlink(missing_ok=True)
            continue

        temp_path = target_path.with_name(f".{target_path.name}.tmp")
        shutil.copyfile(source_path, temp_path)
        temp_path.replace(target_path)
        source_path.unlink(missing_ok=True)

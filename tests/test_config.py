from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import scorefinder.config as config_module
from scorefinder.config import AppConfig, ensure_database_location, get_config_path, get_db_path, load_config, save_config


class ConfigTests(unittest.TestCase):
    def test_get_config_path_uses_storage_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            storage_root = Path(tmp_dir) / "nas" / "scores"
            config = AppConfig(storage_root=str(storage_root))
            config_path = get_config_path(config)
            self.assertEqual(
                config_path,
                storage_root.resolve() / "scorefinder.config.json",
            )

    def test_get_db_path_uses_storage_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            storage_root = Path(tmp_dir) / "nas" / "scores"
            config = AppConfig(storage_root=str(storage_root))
            db_path = get_db_path(config)
            self.assertEqual(
                db_path,
                storage_root.resolve() / "scorefinder.sqlite3",
            )

    def test_legacy_database_is_moved_to_storage_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            storage_root = Path(tmp_dir) / "nas" / "scores"
            legacy_db_path = Path(tmp_dir) / "local" / "scorefinder.sqlite3"
            legacy_db_path.parent.mkdir(parents=True, exist_ok=True)
            legacy_db_path.write_text("legacy-db", encoding="utf-8")

            original_legacy = config_module.LEGACY_DB_PATH
            config_module.LEGACY_DB_PATH = legacy_db_path
            try:
                target_path = ensure_database_location(AppConfig(storage_root=str(storage_root)))
            finally:
                config_module.LEGACY_DB_PATH = original_legacy

            self.assertEqual(target_path.read_text(encoding="utf-8"), "legacy-db")
            self.assertFalse(legacy_db_path.exists())

    def test_save_and_load_config_use_storage_root_file_and_bootstrap(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            app_home = Path(tmp_dir) / "app-home"
            storage_root = Path(tmp_dir) / "nas" / "scores"

            original_app_home = config_module.APP_HOME
            original_bootstrap_path = config_module.BOOTSTRAP_PATH
            original_legacy_config_path = config_module.LEGACY_LOCAL_CONFIG_PATH
            original_default_storage_root = config_module.DEFAULT_STORAGE_ROOT
            try:
                config_module.APP_HOME = app_home
                config_module.BOOTSTRAP_PATH = app_home / "bootstrap.json"
                config_module.LEGACY_LOCAL_CONFIG_PATH = app_home / "config.json"
                config_module.DEFAULT_STORAGE_ROOT = app_home / "storage"

                saved = save_config(AppConfig(storage_root=str(storage_root)))
                loaded = load_config()
            finally:
                config_module.APP_HOME = original_app_home
                config_module.BOOTSTRAP_PATH = original_bootstrap_path
                config_module.LEGACY_LOCAL_CONFIG_PATH = original_legacy_config_path
                config_module.DEFAULT_STORAGE_ROOT = original_default_storage_root

            self.assertEqual(saved.storage_root, str(storage_root.resolve()))
            self.assertEqual(loaded.storage_root, str(storage_root.resolve()))
            self.assertTrue((storage_root / "scorefinder.config.json").exists())
            self.assertTrue((app_home / "bootstrap.json").exists())


if __name__ == "__main__":
    unittest.main()

# -*- coding: utf-8 -*-
"""Veri ve ayar dosyalarının konumları.

Paket içi salt-okunur dosyalar (lang/, icons/, style.qss) modül yanında durur;
değişebilir kullanıcı verisi (playlist.db) XDG veri dizinine yazılır.
"""

import os
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent

# Salt-okunur paket kaynakları
LANG_DIR = PACKAGE_DIR / 'lang'
ICON_DIR = PACKAGE_DIR / 'icons'
QSS_PATH = PACKAGE_DIR / 'style.qss'

# Kullanıcı verileri (değrşebilir)
DATA_DIR = Path(os.environ.get("XDG_DATA_HOME") or (Path.home() / ".local" / "share")) / "RadioTR"
DB_PATH = DATA_DIR / "playlist.db"
# Eski sürümde veritabanı komut dizininde tutuluyordu; ilk açılışta taşınır.
LEGACY_DB = PACKAGE_DIR.parent / 'playlist.db'

# Masaüstü entegrasyonu
ICON_INSTALL_DIR = (Path(os.environ.get("XDG_DATA_HOME") or (Path.home() / ".local" / "share"))
                    / "icons" / "hicolor" / "128x128" / "apps")
APPLICATIONS_DIR = (Path(os.environ.get("XDG_DATA_HOME") or (Path.home() / ".local" / "share"))
                    / "applications")


def ensure_data_dir():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
# -*- coding: utf-8 -*-
"""Türkçe/İngilizce çeviri desteği (lang/*.json).

Ayarlardan seçilen dil (``dil`` ayarı: auto|tr|en) saklanır. ``auto`` veya
ayar yoksa ilk açılışta sistem dili denenir; Türkçe değilse İngilizce'ye düşülür.
Çeviri dosyaları ``lang/`` klasöründen (tr.json, en.json) yüklenir.
"""

import json
import locale
import sqlite3

from radiotr.paths import LANG_DIR
LANG_TR = 'tr'
LANG_EN = 'en'
SUPPORTED = (LANG_TR, LANG_EN)
DEFAULT = LANG_EN


def _load_lang(lang):
    try:
        with open(LANG_DIR / f'{lang}.json', encoding='utf-8') as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


EN_DICT = _load_lang(LANG_EN)
TR_DICT = _load_lang(LANG_TR)


def system_language():
    """Sistem dilini döner; desteklenmiyorsa None."""
    try:
        loc, _ = locale.getdefaultlocale()
    except Exception:
        loc = ''
    code = (loc or '').split('_')[0].lower()
    return code if code in SUPPORTED else None


class I18n:
    def __init__(self, db_path):
        self.lang = self._from_db(db_path) or system_language() or DEFAULT
        self._dict = TR_DICT if self.lang == LANG_TR else EN_DICT

    def _from_db(self, db_path):
        try:
            conn = sqlite3.connect(db_path)
            row = conn.execute(
                "SELECT deger FROM ayarlar WHERE ayar_adi = 'dil'").fetchone()
            conn.close()
            if row and row[0] in SUPPORTED:
                return row[0]
        except sqlite3.Error:
            pass
        return None

    def set_lang(self, lang):
        if lang in SUPPORTED:
            self.lang = lang
        else:
            self.lang = system_language() or DEFAULT
        self._dict = TR_DICT if self.lang == LANG_TR else EN_DICT

    def t(self, key, **kwargs):
        text = self._dict.get(key) or EN_DICT.get(key) or key
        if kwargs:
            try:
                return text.format(**kwargs)
            except (KeyError, IndexError):
                return text
        return text

    def g(self, genre):
        """Tür adını seçili dile göre görüntüler (kayıt Türkçe kalır)."""
        return self._dict.get('genre.' + genre) or EN_DICT.get('genre.' + genre) or genre

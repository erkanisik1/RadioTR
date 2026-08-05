#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / 'playlist.db'


def veritabani_olustur():
    """Eksik tabloları oluşturur; mevcut istasyon verilerini silmez."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('''
    CREATE TABLE IF NOT EXISTS istasyonlar (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        isim TEXT NOT NULL,
        url TEXT NOT NULL UNIQUE,
        tur TEXT NOT NULL DEFAULT 'Müzik'
    )
    ''')
    cur.execute('''
    CREATE TABLE IF NOT EXISTS ayarlar (
        ayar_adi TEXT PRIMARY KEY,
        deger TEXT
    )
    ''')
    conn.commit()
    conn.close()


def ayarlar_tablosunu_onar():
    """Eski şemadaki ayarlar(anahtar, deger) tablosunu ayar_adi düzenine taşır."""
    db_path = Path(DB_PATH)
    if not db_path.exists():
        return
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cols = [row[1] for row in cur.execute("PRAGMA table_info(ayarlar)").fetchall()]
    if cols and 'ayar_adi' not in cols and 'anahtar' in cols:
        cur.execute("ALTER TABLE ayarlar RENAME TO ayarlar_eski")
        cur.execute("""
        CREATE TABLE ayarlar (
            ayar_adi TEXT PRIMARY KEY,
            deger TEXT
        )
        """)
        cur.execute("INSERT INTO ayarlar (ayar_adi, deger) SELECT anahtar, deger FROM ayarlar_eski")
        cur.execute("DROP TABLE ayarlar_eski")
        conn.commit()
        print("ayarlar tablosu yeni şemaya taşındı (ayar_adi).")
    conn.close()


def veritabani_sifirla():
    """Veritabanını sıfırlar ve varsayılan istasyonlarla yeniden oluşturur."""
    if DB_PATH.exists():
        os.remove(DB_PATH)
        print("Eski veritabanı silindi.")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
    CREATE TABLE istasyonlar (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        isim TEXT NOT NULL,
        url TEXT NOT NULL UNIQUE,
        tur TEXT NOT NULL
    )
    ''')

    cursor.execute('''
    CREATE TABLE ayarlar (
        ayar_adi TEXT PRIMARY KEY,
        deger TEXT
    )
    ''')

    varsayilan_istasyonlar = [
        ('Power FM', 'http://listen.powerapp.com.tr/powerturk/mpeg/icecast.audio', 'Müzik'),
        ('Radyo D', 'http://46.20.3.201:80/', 'Haber'),
        ('NTV Radyo', 'http://ntvrdwmp.radyotvonline.com/ntv/ntvrdwmp/playlist.m3u8', 'Haber'),
        ('TRT FM', 'http://trt-trtfm-live.mediatriple.net/video/index.m3u8', 'Pop'),
        ('Slow Türk', 'https://radyo.duhnet.tv/slowturk', 'Slow'),
        ('Fenomen', 'http://fenomen.listenfenomen.com/fenomen/128/icecast.audio', 'Yabancı Pop'),
        ('Joy FM', 'https://playerservices.streamtheworld.com/api/livestream-redirect/JOY_FM_SC', 'Yabancı Slow'),
        ('Kral Pop', 'http://kralpop.live.mediatriple.net/video/index.m3u8', 'Pop'),
        ('Metro FM', 'https://playerservices.streamtheworld.com/api/livestream-redirect/METRO_FM_SC', 'Yabancı Pop'),
        ('ALEM FM', 'https://edge1.radyotvonline.net/shoutcast/play/alemfm', 'Türkçe Pop'),
        ('Kafa Radyo', 'https://moondigitaledge2.radyotvonline.net/kafaradyo/playlist.m3u8', 'Türkçe Pop'),
    ]

    cursor.executemany("INSERT INTO istasyonlar (isim, url, tur) VALUES (?, ?, ?)", varsayilan_istasyonlar)
    cursor.execute("INSERT INTO ayarlar (ayar_adi, deger) VALUES (?, ?)", ('output', '0'))
    cursor.execute("INSERT INTO ayarlar (ayar_adi, deger) VALUES (?, ?)", ('ses_seviyesi', '50'))

    conn.commit()
    conn.close()

    print("Veritabanı başarıyla oluşturuldu ve varsayılan istasyonlar eklendi.")
    print(f"Veritabanı konumu: {DB_PATH}")


if __name__ == "__main__":
    veritabani_sifirla()
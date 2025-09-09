#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sqlite3

def veritabani_sifirla():
    """Veritabanını sıfırlar ve varsayılan istasyonlarla yeniden oluşturur"""
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'playlist.db')
    
    # Eğer veritabanı dosyası varsa sil
    if os.path.exists(db_path):
        os.remove(db_path)
        print("Eski veritabanı silindi.")
    
    # Yeni bağlantı oluştur
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # İstasyonlar tablosu
    cursor.execute('''
    CREATE TABLE istasyonlar (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        isim TEXT NOT NULL,
        url TEXT NOT NULL UNIQUE,
        tur TEXT NOT NULL
    )
    ''')
    
    # Ayarlar tablosu
    cursor.execute('''
    CREATE TABLE ayarlar (
        anahtar TEXT PRIMARY KEY,
        deger TEXT
    )
    ''')
    
    # Varsayılan istasyonlar
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
        ('Kafa Radyo', 'https://moondigitaledge2.radyotvonline.net/kafaradyo/playlist.m3u8', 'Türkçe Pop')
    ]
    
    # İstasyonları ekle
    cursor.executemany("INSERT INTO istasyonlar (isim, url, tur) VALUES (?, ?, ?)", varsayilan_istasyonlar)
    
    # Varsayılan ayarları ekle
    cursor.execute("INSERT INTO ayarlar (anahtar, deger) VALUES (?, ?)", ('output_device', '0'))
    
    conn.commit()
    conn.close()
    
    print("Veritabanı başarıyla oluşturuldu ve varsayılan istasyonlar eklendi.")
    print(f"Veritabanı konumu: {db_path}")

if __name__ == "__main__":
    veritabani_sifirla()
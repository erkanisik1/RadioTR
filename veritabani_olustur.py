import sqlite3

def veritabani_olustur():
    conn = sqlite3.connect('playlist.db')
    cursor = conn.cursor()
    
    # İstasyonlar tablosu
    cursor.execute('''CREATE TABLE IF NOT EXISTS istasyonlar
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      isim TEXT NOT NULL,
                      url TEXT UNIQUE NOT NULL,
                      tur TEXT DEFAULT 'Müzik')''')
    
    # Ayarlar tablosu
    cursor.execute('''CREATE TABLE IF NOT EXISTS ayarlar
                     (ayar_adi TEXT PRIMARY KEY,
                      deger TEXT)''')
    
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
    
    # Eğer tablo boşsa varsayılan istasyonları ekle
    cursor.execute("SELECT COUNT(*) FROM istasyonlar")
    if cursor.fetchone()[0] == 0:
        cursor.executemany("INSERT INTO istasyonlar (isim, url, tur) VALUES (?, ?, ?)", varsayilan_istasyonlar)
    
    # Varsayılan ses seviyesi ayarını ekle (eğer yoksa)
    cursor.execute("INSERT OR IGNORE INTO ayarlar (ayar_adi, deger) VALUES (?, ?)", ("ses_seviyesi", "50"))
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    veritabani_olustur()
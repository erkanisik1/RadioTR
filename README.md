# RadioTR Player

RadioTR Player, internet radyolarını dinleyebileceğiniz, istasyon ekleyip düzenleyebileceğiniz ve ses seviyesini görsel olarak takip edebileceğiniz modern bir masaüstü uygulamasıdır.

## Özellikler

- Radyo istasyonu ekleme, düzenleme ve silme
- SQLite veritabanında istasyon saklama
- VLC tabanlı radyo yayını oynatma
- VU metre (ses seviyesi göstergesi)
- Modern ve sade PyQt6 arayüzü
- Favori istasyonlarınızı hızlıca seçme ve oynatma
- Oynat/Durdur için tek buton ve ikon desteği
- Kanal listesinde fareyle üzerine gelince bilgi gösteren tooltip

## Kurulum

### Gereksinimler

- Python 3.8+
- [VLC](https://www.videolan.org/vlc/) (sistemde kurulu olmalı)
- Gerekli Python paketleri:  
  - PyQt6  
  - python-vlc  
  - pyaudio  
  - numpy  

### Bağımlılıkların kurulumu

Önce sistem paketlerini yükleyin (Linux için):
```bash
portaudio
vlc
```

Sonra Python paketlerini yükleyin:

```bash
pip install -r requirements.txt
```

### İkonlar

`icons/play-green.png` ve `icons/stop-green.png` dosyalarını `icons/` klasörüne ekleyin.  
Kendi ikonlarınızı kullanabilirsiniz.

## Kullanım

```bash
./player-v3.py
```

- Yeni istasyon eklemek için "Yeni İstasyon Ekle" butonunu kullanın.
- Listeden bir istasyon seçip oynatmak için oynat/durdur butonunu kullanın.
- İstasyon üzerinde sağ tıklayarak düzenleyebilir veya silebilirsiniz.
- VU metre ile ses seviyesini görsel olarak takip edebilirsiniz.

## Veritabanı

İstasyonlar `playlist.db` dosyasında saklanır.  
Veritabanı otomatik olarak oluşturulur.

## Katkı ve Lisans

Bu proje MIT lisansı ile yayınlanmıştır.  
Katkıda bulunmak için pull request gönderebilirsiniz.

---

**Geliştirici:** Erkan Işık  
GitHub: [github.com/erkanisik](https://github.com/erkanisik1)

# Değişiklik Günlüğü

Bu projedeki tüm önemli değişiklikler bu dosyada belgelenir. Format
[Keep a Changelog](https://keepachangelog.com/tr/1.1.0/) ve
[Semantic Versioning](https://semver.org/lang/tr/) temel alınır.

## [0.3.0] - 2026-08-05

### Eklendi
- **Çok dilli arayüz (Türkçe / İngilizce):** Ayarlar → Dil menüsünden dil
  seçilebilir (Otomatik / Türkçe / İngilizce). "Otomatik" sistem dilini kullanır;
  desteklenmeyen dilde İngilizce'ye düşülür. Seçim `ayarlar.dil` alanına
  kaydedilir ve açılışta geri yüklenir.
- **`lang/` çeviri dosyaları:** Tüm çeviriler `lang/tr.json` ve `lang/en.json`
  dosyalarında JSON olarak tutulur; `dil.py` bu dosyaları okur, eksik anahtar
  için İngilizce fallback kullanır. Tür adları veritabanında Türkçe kalır,
  arayüzde `genre.*` anahtarıyla görüntülenir.

### Değişti
- **Tüm arayüz metinleri çevrilebilir:** Pencere başlığı, menüler, butonlar,
  mesaj kutuları, tepsi menüsü/tooltip'i ve VU metre hata yazıları dinamik çeviri
  kullanır; dil değişince anında güncellenir.
- **VU metre çeviri desteği:** Hata yazıları (`vu.*` anahtarları) dile göre
  gösterilir; `set_language()` ile dil değişimi anında yansır.

### Teknik / Altyapı
- Yeni modül `dil.py`: `I18n(db_path)`, `t()` (değer/çeviri), `g()` (tür çevirisi),
  `system_language()` sistem dili algılama.

## [0.2.0] - 2026-08-05

### Eklendi
- **Tepsi istasyon menüsü:** Sistem tepsisi ikonuna sağ tıklayınca "İstasyonlar"
  alt menüsü gelir; menüden istasyona tıklayarak radyo değiştirilebilir. Çalan
  istasyon menüde işaretlenir (✓), tepsi tooltip'i istasyon adını gösterir.
  İstasyon ekleme/düzenleme/silme sonrası menü otomatik yenilenir.
- **VU metre için otomatik kaynak seçimi:** Başlangıçta varsayılan hoparlörün
  `.monitor` kaynağı otomatik seçilir; varsayılan hoparlör değişirse
  (bluetooth bağlanma/kopma, kablo değişimi) 3 saniyede bir kontrol ederek
  kendiliğinden yeni kaynağa geçer.
- **Ses seviyesi kaydırıcısı:** Arayüze ses kaydırıcısı eklendi; değer ayarlar
  tablosundaki `ses_seviyesi` alanına yazılır ve açılışta geri yüklenir.
- **Ayar şeması onarımı:** Eski `ayarlar(anahtar, deger)` şeması otomatik olarak
  yeni `ayarlar(ayar_adi, deger)` şemasına taşınır (`ayarlar_tablosunu_onar`).
- **Ayarlar menüsü:** "VU Metre Yakalama Kaynağı" seçici diyaloğu PulseAudio
  monitor kaynaklarını `pactl` ile listeler ve "Otomatik (varsayılan hoparlör)"
  seçeneği sunar.

### Değişti
- **VU metre artık gerçek sesle çalışıyor:** Sahte/rastgele veri mantığı
  (`update_visualizer` timer'ı) kaldırıldı; seviye gerçek yakalanan PCM'den,
  RMS'in dB ölçeğine çevrilmesiyle hesaplanıyor.
- **Yakalama yöntemi:** PortAudio'nun ALSA backend'i PulseAudio monitor'ünü
  göremediği için yakalama `parecord` + isimli FIFO ile yapılıyor (bu sistemde
  `parecord` stdout'a yazmıyor). `parecord` yoksa PortAudio'ya geri düşülür.
- **Mutlak dosya yolları:** `playlist.db`, `style.qss` ve `icons/` artık betiğin
  bulunduğu dizine göre mutlak yoldan çözümleniyor; uygulama hangi dizinden
  başlatılırsa çalışsın.
- **Çalma mantığı tekileşti:** Listeden çift tık ve tepsi menüsü ortak
  `play_station(isim, url)` fonksiyonunu kullanıyor.
- **İkon/yalnızca durdur butonu durumu tutarlı:** `stop_station`'ın yanlış
  ikon/tooltip eşleşmesi düzeltildi; durdurma sırasında çalan istasyon temizlenir.
- **Kaynak temizliği:** Çıkışta VLC player ve VU metre kaynakları (parecord
  süreci, FIFO, akışlar) serbest bırakılıyor; süreç/FIFO sızıntısı yok.

### Düzeltilen
- Veritabanı şema uyumsuzluğu (kod `ayar_adi` kullanıyor, üretici `anahtar`
  üretiyordu).
- Eksik `veritabani_olustur()` fonksiyonu (önceden import ediliyordu ama tanımlı
  değildi).
- VU yakalama cihazı seçici diyaloğunun `Device unavailable` hatası vermesi.
- `load_stations`'ın tepsi menüsü kurulmadan önce çağrılıp başlangıçta hata
  kutusu açması.
- Göreli yol nedeniyle başka dizinden başlatıldığında DB/QSS bulunamaması.
- Kullanılmayan kod (`get_device_channels`, gereksiz `pyaudio` importu).

### Teknik / Altyapı
- `vumetre.py`, `veritabani_olustur.py` okunabilirlik için yeniden yapılandırıldı;
  ayar yardımcıları (`get_setting`/`save_setting`) merkezileştirildi.

## [0.1.0] - 2025-08-25

- İlk sürüm: PyQt6 + VLC tabanlı internet radyo oynatıcısı. İstasyon ekleme,
  düzenleme ve silme; SQLite saklama; sistem tepsisi; koyu tema.
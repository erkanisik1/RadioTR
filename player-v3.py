#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# RadioTR - İnternet Radyo Oynatıcısı
# Geliştirici: Erkan Işık
# GitHub:

import subprocess
import sys
import sqlite3
from pathlib import Path

import vlc
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtWidgets import (
    QApplication, QComboBox, QDialog, QDialogButtonBox, QHBoxLayout,
    QLabel, QLineEdit, QListWidget, QListWidgetItem, QMainWindow,
    QMenu, QMessageBox, QPushButton, QSlider, QSystemTrayIcon, QToolButton,
    QVBoxLayout, QWidget,
)

from vumetre import VUMeterWidget

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / 'playlist.db'
ICON_DIR = BASE_DIR / 'icons'
QSS_PATH = BASE_DIR / 'style.qss'


def get_setting(name, default=None):
    try:
        conn = sqlite3.connect(DB_PATH)
        row = conn.execute("SELECT deger FROM ayarlar WHERE ayar_adi = ?", (name,)).fetchone()
        conn.close()
        return row[0] if row else default
    except sqlite3.Error:
        return default


def save_setting(name, value):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("INSERT OR REPLACE INTO ayarlar (ayar_adi, deger) VALUES (?, ?)", (name, str(value)))
    conn.commit()
    conn.close()

# IstasyonDialog sınıfı aynı...
class IstasyonDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("İstasyon Bilgileri")
        self.layout = QVBoxLayout(self)
        self.layout.addWidget(QLabel("İstasyon Adı:"))
        self.isim_input = QLineEdit()
        self.isim_input.setPlaceholderText("Örn: Power FM")
        self.layout.addWidget(self.isim_input)
        self.layout.addWidget(QLabel("Yayın URL'si:"))
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("http://...")
        self.layout.addWidget(self.url_input)
        self.layout.addWidget(QLabel("Tür:"))
        self.tur_combo = QComboBox()
        self.tur_combo.addItems(["Müzik", "Haber", "Spor", "Türkçe Pop", "Yabancı Müzik", "Slow", "Türk Sanat Müziği", "Türk Halk Müziği", "Diğer"])
        self.layout.addWidget(self.tur_combo)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        self.layout.addWidget(buttons)

    def get_data(self):
        return (self.isim_input.text().strip(), self.url_input.text().strip(), self.tur_combo.currentText())
        
    def set_data(self, isim, url, tur):
        self.isim_input.setText(isim)
        self.url_input.setText(url)
        index = self.tur_combo.findText(tur)
        if index >= 0:
            self.tur_combo.setCurrentIndex(index)

class RadyoPlayer(QMainWindow):
    playback_error_signal = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("RadioTR - İnternet Radyo Oynatıcısı")
        self.setWindowIcon(QIcon(str(ICON_DIR / 'radio-icon.png')))
        self.setMinimumSize(400, 500)
        self.veritabani_kontrol_et()

        self.vlc_instance = vlc.Instance("--quiet")
        self.player = self.vlc_instance.media_player_new()
        self.event_manager = self.player.event_manager()
        self.event_manager.event_attach(
            vlc.EventType.MediaPlayerEncounteredError, self.handle_playback_error
        )
        self.playback_error_signal.connect(self.show_error_message)

        self.init_ui()
        self.load_stations()

        # Ses seviyesini ayarlardan yükle
        saved_volume = int(get_setting('ses_seviyesi', 50))
        self.player.audio_set_volume(saved_volume)
        self.volume_slider.setValue(saved_volume)

        # --- SİSTEM TRAY İKONU ---
        self.playing_url = None
        self.playing_name = None
        self.tray_icon = QSystemTrayIcon(QIcon(str(ICON_DIR / 'radio-icon.png')), self)
        self.tray_menu = QMenu()
        self.tray_stations_menu = self.tray_menu.addMenu("İstasyonlar")
        show_action = QAction("Göster", self)
        quit_action = QAction("Çıkış", self)
        self.tray_menu.addSeparator()
        self.tray_menu.addAction(show_action)
        self.tray_menu.addAction(quit_action)
        self.tray_icon.setContextMenu(self.tray_menu)
        self._build_tray_stations()

        show_action.triggered.connect(self.showNormal)
        quit_action.triggered.connect(QApplication.quit)

        self.tray_icon.setToolTip("RadioTR - İnternet Radyo Oynatıcısı")
        self.tray_icon.show()

        # Çift tık ile pencereyi geri getirme
        self.tray_icon.activated.connect(self.on_tray_activated)

    def _build_tray_stations(self):
        """Tepsi menüsündeki istasyon alt menüsünü yeniden oluşturur."""
        if not hasattr(self, 'tray_stations_menu'):
            return  # tray menüsü henüz kurulmadı (ilk load_stations çağrısı)
        self.tray_stations_menu.clear()
        try:
            conn = sqlite3.connect(DB_PATH)
            rows = conn.execute(
                "SELECT isim, url, tur FROM istasyonlar ORDER BY isim").fetchall()
            conn.close()
        except sqlite3.Error:
            rows = []
        if not rows:
            self.tray_stations_menu.addAction("(İstasyon yok)").setEnabled(False)
            return
        for isim, url, tur in rows:
            act = QAction(f"{isim} ({tur})", self)
            act.setCheckable(True)
            act.setData(url)
            act.setChecked(url == self.playing_url)
            act.triggered.connect(
                lambda checked, u=url, n=isim: self.play_station(n, u))
            self.tray_stations_menu.addAction(act)

    def _refresh_tray_checked(self):
        for act in self.tray_stations_menu.actions():
            act.setChecked(act.data() == self.playing_url)

    def on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            if self.isHidden():
                self.showNormal()
                self.activateWindow()
            else:
                self.hide()
    
    def hideEvent(self, event):
        # Pencere gizlendiğinde çalma durumunu koru
        if hasattr(self, 'player') and self.player.is_playing():
            self.was_playing = True
        super().hideEvent(event)

    def showEvent(self, event):
        # Pencere tekrar gösterildiğinde çalma durumunu güncelle
        if hasattr(self, 'was_playing') and self.was_playing:
            self.was_playing = False
            if not self.player.is_playing():
                self.player.play()
        super().showEvent(event)

    def closeEvent(self, event):
        if self.tray_icon.isVisible():
            self.hide()
            event.ignore()   # uygulamayı kapatma
        else:
            self._cleanup()
            super().closeEvent(event)

    def _cleanup(self):
        """VLC player ve VU metre kaynaklarını serbest bırak."""
        if hasattr(self, 'player') and self.player is not None:
            try:
                self.player.stop()
                self.player.release()
            except Exception:
                pass
            self.player = None
        if hasattr(self, 'vumetre') and self.vumetre is not None:
            try:
                self.vumetre.close()
            except Exception:
                pass

    def veritabani_kontrol_et(self):
        """DB yoksa oluştur; eski şemayı yeni şemaya onar."""
        try:
            if not Path(DB_PATH).exists():
                from veritabani_olustur import veritabani_olustur
                veritabani_olustur()
            from veritabani_olustur import ayarlar_tablosunu_onar
            ayarlar_tablosunu_onar()
        except Exception as e:
            QMessageBox.critical(self, "Veritabanı Hatası", f"Veritabanı hazırlanamadı: {e}")
            sys.exit()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # --- Üst bar: şu an çalan + ayarlar çarkı ---
        top_layout = QHBoxLayout()
        self.su_an_calan_label = QLabel("Bir istasyon seçin...")
        font = self.su_an_calan_label.font()
        font.setPointSize(12)
        self.su_an_calan_label.setFont(font)
        top_layout.addWidget(self.su_an_calan_label, 1)

        self.settings_button = QToolButton()
        self.settings_button.setIcon(self.style().standardIcon(self.style().StandardPixmap.SP_FileDialogDetailedView))
        self.settings_button.setToolTip("Ayarlar")
        self.settings_menu = QMenu()
        self.capture_action = QAction("VU Metre Yakalama Cihazı Seç", self)
        self.capture_action.triggered.connect(self.select_capture_device)
        self.add_station_action = QAction("Yeni İstasyon Ekle", self)
        self.add_station_action.triggered.connect(self.open_add_station_dialog)
        self.settings_menu.addAction(self.capture_action)
        self.settings_menu.addAction(self.add_station_action)
        self.settings_button.setMenu(self.settings_menu)
        self.settings_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        top_layout.addWidget(self.settings_button)
        main_layout.addLayout(top_layout)

        # --- Ses seviyesi ---
        ses_layout = QHBoxLayout()
        ses_layout.addWidget(QLabel("Ses:"))
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(50)
        self.volume_slider.valueChanged.connect(self.on_volume_changed)
        ses_layout.addWidget(self.volume_slider, 1)
        main_layout.addLayout(ses_layout)

        # --- VU metre (gerçek yakalama, otomatik cihaz seçimi) ---
        self.vumetre = VUMeterWidget(parent=self)
        main_layout.addWidget(self.vumetre)

        # --- İstasyon listesi ---
        self.istasyon_listesi = QListWidget()
        list_font = self.istasyon_listesi.font()
        list_font.setPointSize(11)
        self.istasyon_listesi.setFont(list_font)
        self.istasyon_listesi.itemDoubleClicked.connect(self.play_selected_station)
        self.istasyon_listesi.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.istasyon_listesi.customContextMenuRequested.connect(self.show_context_menu)
        main_layout.addWidget(self.istasyon_listesi, 1)

        # --- Oynat/Durdur ---
        self.play_stop_button = QPushButton()
        self.play_stop_button.setIcon(QIcon(str(ICON_DIR / 'play-green.png')))
        self.play_stop_button.setToolTip("Oynat")
        self.play_stop_button.clicked.connect(self.toggle_play_stop)
        main_layout.addWidget(self.play_stop_button)

    def on_volume_changed(self, value):
        self.player.audio_set_volume(value)
        save_setting('ses_seviyesi', value)

    def toggle_play_stop(self):
        if self.player.is_playing():
            self.player.stop()
            self.playing_url = None
            self.playing_name = None
            self.su_an_calan_label.setText("Durduruldu")
            self.play_stop_button.setIcon(QIcon(str(ICON_DIR / 'play-green.png')))
            self.play_stop_button.setToolTip("Oynat")
            self._refresh_tray_checked()
            self.tray_icon.setToolTip("RadioTR - İnternet Radyo Oynatıcısı")
        else:
            self.play_selected_station()
            self.play_stop_button.setIcon(QIcon(str(ICON_DIR / 'stop-green.png')))
            self.play_stop_button.setToolTip("Durdur")

    def play_selected_station(self):
        current_item = self.istasyon_listesi.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Uyarı", "Lütfen listeden bir istasyon seçin!")
            return
        full_text = current_item.text()
        isim = full_text.rsplit(' (', 1)[0]
        url = current_item.data(Qt.ItemDataRole.UserRole)
        self.play_station(isim, url)

    def play_station(self, isim, url):
        """Belirli bir istasyonu çalar (liste, tepsi menüsü ortak)."""
        self.playing_url = url
        self.playing_name = isim
        self.su_an_calan_label.setText(f"Bağlanılıyor: {isim}...")
        media = self.vlc_instance.media_new(url)
        self.player.set_media(media)
        self.player.play()
        self.su_an_calan_label.setText(f"Şu An Çalıyor: {isim}")
        self.play_stop_button.setIcon(QIcon(str(ICON_DIR / 'stop-green.png')))
        self.play_stop_button.setToolTip("Durdur")
        self._refresh_tray_checked()
        self.tray_icon.setToolTip(f"RadioTR - {isim}")

    def stop_station(self):
        self.player.stop()
        self.playing_url = None
        self.playing_name = None
        self.su_an_calan_label.setText("Durduruldu")
        self.play_stop_button.setIcon(QIcon(str(ICON_DIR / 'play-green.png')))
        self.play_stop_button.setToolTip("Oynat")
        self._refresh_tray_checked()
        self.tray_icon.setToolTip("RadioTR - İnternet Radyo Oynatıcısı")

    def load_stations(self):
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT isim, url, tur FROM istasyonlar ORDER BY isim")
            istasyonlar = cursor.fetchall()
            conn.close()
            self.istasyon_listesi.clear()
            for isim, url, tur in istasyonlar:
                item = QListWidgetItem(f"{isim} ({tur})")
                item.setData(Qt.ItemDataRole.UserRole, url)
                item.setToolTip("Dinlemek için çift tıklayın.\nDüzenlemek veya silmek için sağ tıklayın.")
                self.istasyon_listesi.addItem(item)
            self._build_tray_stations()
        except Exception as e:
            QMessageBox.critical(self, "Veritabanı Hatası", f"İstasyonlar yüklenemedi: {e}")
    
    def show_context_menu(self, position):
        item = self.istasyon_listesi.itemAt(position)
        if not item: return
        menu = QMenu()
        edit_action = menu.addAction("Düzenle")
        delete_action = menu.addAction("Sil")
        global_position = self.istasyon_listesi.mapToGlobal(position)
        selected_action = menu.exec(global_position)
        if selected_action == edit_action: self.open_edit_station_dialog(item)
        elif selected_action == delete_action: self.delete_station(item)

    def open_add_station_dialog(self):
        dialog = IstasyonDialog(self)
        dialog.setWindowTitle("Yeni İstasyon Ekle")
        if dialog.exec():
            isim, url, tur = dialog.get_data()
            if isim and url: self.add_station_to_db(isim, url, tur)
            else: QMessageBox.warning(self, "Eksik Bilgi", "İstasyon adı ve URL'si boş bırakılamaz.")

    def add_station_to_db(self, isim, url, tur):
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("INSERT INTO istasyonlar (isim, url, tur) VALUES (?, ?, ?)", (isim, url, tur))
            conn.commit()
            conn.close()
            self.load_stations()
        except sqlite3.IntegrityError: 
            QMessageBox.warning(self, "Hata", "Bu URL zaten veritabanında mevcut.")
        except Exception as e: 
            QMessageBox.critical(self, "Veritabanı Hatası", f"İstasyon eklenemedi: {e}")

    def open_edit_station_dialog(self, item):
        dialog = IstasyonDialog(self)
        dialog.setWindowTitle("İstasyonu Düzenle")
        full_text = item.text()
        current_name = full_text.rsplit(' (', 1)[0]
        current_tur = full_text.rsplit(' (', 1)[1].strip(')')
        current_url = item.data(Qt.ItemDataRole.UserRole)
        dialog.set_data(current_name, current_url, current_tur)
        if dialog.exec():
            new_name, new_url, new_tur = dialog.get_data()
            if new_name and new_url: self.update_station_in_db(current_url, new_name, new_url, new_tur)
            else: QMessageBox.warning(self, "Eksik Bilgi", "İstasyon adı ve URL'si boş bırakılamaz.")

    def update_station_in_db(self, old_url, new_name, new_url, new_tur):
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("UPDATE istasyonlar SET isim = ?, url = ?, tur = ? WHERE url = ?", (new_name, new_url, new_tur, old_url))
            conn.commit()
            conn.close()
            self.load_stations()
        except Exception as e: 
            QMessageBox.critical(self, "Veritabanı Hatası", f"İstasyon güncellenemedi: {e}")

    def delete_station(self, item):
        isim = item.text().rsplit(' (', 1)[0]
        url = item.data(Qt.ItemDataRole.UserRole)
        cevap = QMessageBox.question(self, "Silme Onayı", f"'{isim}' istasyonunu silmek istediğinizden emin misiniz?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if cevap == QMessageBox.StandardButton.Yes:
            try:
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute("DELETE FROM istasyonlar WHERE url = ?", (url,))
                conn.commit()
                conn.close()
                self.load_stations()
                self.su_an_calan_label.setText("İstasyon silindi.")
            except Exception as e: 
                QMessageBox.critical(self, "Veritabanı Hatası", f"İstasyon silinemedi: {e}")

    def handle_playback_error(self, event):
        self.playback_error_signal.emit()

    def show_error_message(self):
        self.su_an_calan_label.setText("Hata: Yayın açılamadı. Başka bir istasyon seçin.")

    def select_capture_device(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("VU Metre Yakalama Kaynağı")
        layout = QVBoxLayout(dialog)
        label = QLabel("Monitor kaynakları (varsayılan hoparlörün sesini dinler):")
        layout.addWidget(label)
        combo = QComboBox()
        layout.addWidget(combo)
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        layout.addWidget(button_box)

        # Otomatik: varsayılan hoparlörün monitor'ü (BT bağlanınca kendisi geçer)
        combo.addItem("Otomatik (varsayılan hoparlör)", userData=None)

        try:
            out = subprocess.check_output(['pactl', 'list', 'sources', 'short'],
                                          text=True, stderr=subprocess.DEVNULL)
            for line in out.splitlines():
                parts = line.split()
                if len(parts) >= 2 and 'monitor' in parts[1]:
                    combo.addItem(parts[1], userData=parts[1])
        except Exception as e:
            QMessageBox.critical(self, "pactl Hatası", f"Monitor kaynakları alınamadı: {e}")

        current = self.vumetre._manual_source
        if current:
            idx = combo.findData(current)
            if idx >= 0:
                combo.setCurrentIndex(idx)

        def on_ok():
            selected = combo.currentData()
            self.vumetre.set_capture(selected)  # None => otomatik mod
            dialog.accept()

        button_box.button(QDialogButtonBox.StandardButton.Ok).clicked.connect(on_ok)
        button_box.button(QDialogButtonBox.StandardButton.Cancel).clicked.connect(dialog.reject)

        dialog.exec()
if __name__ == '__main__':
    app = QApplication(sys.argv)
    QApplication.setQuitOnLastWindowClosed(False)  # tepsi ile çalışmak için önemli
    try:
        with open(QSS_PATH, 'r') as f:
            app.setStyleSheet(f.read())
    except FileNotFoundError:
        pass

    player_window = RadyoPlayer()
    app.aboutToQuit.connect(player_window._cleanup)
    player_window.show()
    sys.exit(app.exec())
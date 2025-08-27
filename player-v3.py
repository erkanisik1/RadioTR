#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# RadioTR - İnternet Radyo Oynatıcısı
# Geliştirici: Erkan Işık
# GitHub:

import sys
import sqlite3
import vlc
import os
import random
import pyaudio
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QListWidget, QLabel, QListWidgetItem,
    QDialog, QLineEdit, QMessageBox, QDialogButtonBox, QComboBox, QMenu,
    QToolButton
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QIcon, QAction

from vumetre import VUMeterWidget

def get_saved_output_device():
    conn = sqlite3.connect('playlist.db')
    cursor = conn.cursor()
    cursor.execute("SELECT deger FROM ayarlar WHERE ayar_adi = ?", ("output",))
    row = cursor.fetchone()
    conn.close()
    return int(row[0]) if row else None

def get_device_channels(device_index):
    p = pyaudio.PyAudio()
    info = p.get_device_info_by_index(device_index)
    return info.get("maxInputChannels", 0)

def save_output_device(device_index):
        conn = sqlite3.connect('playlist.db')
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO ayarlar (ayar_adi, deger) VALUES (?, ?)", ("output", str(device_index)))
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
        self.setWindowIcon(QIcon("icons/radio-icon.png"))
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
        
        # --- YENİ ve BASİT GÖRSELLEŞTİRİCİ TİMER'I ---
        self.vu_timer = QTimer(self)
        self.vu_timer.timeout.connect(self.update_visualizer)
        self.vu_timer.start(75) # 75 milisaniyede bir, daha yumuşak bir ritim için

    def update_visualizer(self):
        """Müzik çalarken VU metreye ritmik bir hareket verir."""
        if self.player.is_playing():
            # Ses ayarını temel seviye olarak al
            base_level = self.player.audio_get_volume() / 150.0
            
            # Bu temel seviyenin etrafında rastgele bir "zıplama" yarat
            # 0.7 ile 1.1 arasında bir çarpanla
            flicker = 0.7 + random.random() * 0.7
            level = base_level * flicker
            
            # Seviyenin 1.0'ı geçmediğinden emin ol
            level = min(level, 1.0)
            
            # Stereo efekti için sağ kanalı biraz farklı yap
            self.vumetre.update_levels(level, level * 1.0)
        else:
            # Müzik çalmıyorsa, VU metreyi sıfırla
            self.vumetre.update_levels(0, 0)

    def veritabani_kontrol_et(self):
        if not os.path.exists('playlist.db'):
            try:
                from veritabani_olustur import veritabani_olustur
                veritabani_olustur()
            except Exception as e:
                QMessageBox.critical(self, "Veritabanı Hatası", f"Veritabanı oluşturulamadı: {e}")
                sys.exit()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        self.su_an_calan_label = QLabel("Bir istasyon seçin...")
        font = self.su_an_calan_label.font()
        font.setPointSize(12)
        self.su_an_calan_label.setFont(font)
        self.su_an_calan_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.su_an_calan_label)
        saved_index = get_saved_output_device()
        self.vumetre = VUMeterWidget(device_index=saved_index)
        main_layout.addWidget(self.vumetre)
        self.istasyon_listesi = QListWidget()
        list_font = self.istasyon_listesi.font()
        list_font.setPointSize(11)
        self.istasyon_listesi.setFont(list_font)
        self.istasyon_listesi.itemDoubleClicked.connect(self.play_selected_station)
        self.istasyon_listesi.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.istasyon_listesi.customContextMenuRequested.connect(self.show_context_menu)
        main_layout.addWidget(self.istasyon_listesi)
        top_button_layout = QHBoxLayout()
        
        
        # --- Tek Oynat/Durdur butonu ---
        kontrol_layout = QHBoxLayout()
        self.play_stop_button = QPushButton()
        self.play_stop_button.setIcon(QIcon("icons/play-green.png"))
        self.play_stop_button.setToolTip("Oynat")
        self.play_stop_button.clicked.connect(self.toggle_play_stop)
        kontrol_layout.addWidget(self.play_stop_button)
        main_layout.addLayout(kontrol_layout)

        # Sağ üst köşeye çark ikonu
        self.settings_button = QToolButton()
        self.settings_button.setIcon(self.style().standardIcon(self.style().StandardPixmap.SP_FileDialogDetailedView))
        self.settings_button.setToolTip("Ayarlar")
        self.settings_menu = QMenu()
        self.device_action = QAction("Ses Cihazı Seç", self)
        self.device_action.triggered.connect(self.select_audio_device)
        self.add_station_action = QAction("Yeni İstasyon Ekle", self)
        self.add_station_action.triggered.connect(self.open_add_station_dialog)
        self.settings_menu.addAction(self.device_action)
        self.settings_menu.addAction(self.add_station_action)
        self.settings_button.setMenu(self.settings_menu)
        self.settings_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        # Sağ üst köşeye yerleştir
        top_layout = QHBoxLayout()
        top_layout.addWidget(self.su_an_calan_label)
        top_layout.addWidget(self.settings_button)
        main_layout.addLayout(top_layout)

    def toggle_play_stop(self):
        if self.player.is_playing():
            self.player.stop()
            self.su_an_calan_label.setText("Durduruldu")
            self.play_stop_button.setIcon(QIcon("icons/play-green.png"))
            self.play_stop_button.setToolTip("Oynat")
        else:
            self.play_selected_station()
            self.play_stop_button.setIcon(QIcon("icons/stop-green.png"))
            self.play_stop_button.setToolTip("Durdur")

    def play_selected_station(self):
        current_item = self.istasyon_listesi.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Uyarı", "Lütfen listeden bir istasyon seçin!")
            return
        full_text = current_item.text()
        isim = full_text.rsplit(' (', 1)[0]
        url = current_item.data(Qt.ItemDataRole.UserRole)
        self.su_an_calan_label.setText(f"Bağlanılıyor: {isim}...")
        media = self.vlc_instance.media_new(url)
        self.player.set_media(media)
        self.player.play()
        self.su_an_calan_label.setText(f"Şu An Çalıyor: {isim}")
        self.play_stop_button.setIcon(QIcon("icons/stop-green.png"))
        self.play_stop_button.setToolTip("Durdur")
        
    def stop_station(self):
        self.player.stop()
        self.su_an_calan_label.setText("Durduruldu")
        self.play_stop_button.setIcon(QIcon("icons/stop-green.png"))
        self.play_stop_button.setToolTip("Oynat")
    
    def load_stations(self):
        try:
            conn = sqlite3.connect('playlist.db')
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
            conn = sqlite3.connect('playlist.db')
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
            conn = sqlite3.connect('playlist.db')
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
                conn = sqlite3.connect('playlist.db')
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

    def closeEvent(self, event):
        self.stop_station()
        event.accept()

   

    def select_audio_device(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Ses Çıkış Cihazı Seçin")
        layout = QVBoxLayout(dialog)
        label = QLabel("Lütfen bir ses çıkış cihazı seçin:")
        layout.addWidget(label)
        combo = QComboBox()
        layout.addWidget(combo)
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        layout.addWidget(button_box)

        # Mevcut çıkış aygıtlarını al
        try:
            pyaudio_instance = pyaudio.PyAudio()
            device_count = pyaudio_instance.get_device_count()
            for i in range(device_count):
                device_info = pyaudio_instance.get_device_info_by_index(i)
                if device_info["maxOutputChannels"] > 0:
                    combo.addItem(device_info["name"], userData=device_info["index"])
        except Exception as e:
            QMessageBox.critical(self, "PyAudio Hatası", f"Ses aygıtları alınamadı: {e}")

        def on_ok():
            selected_index = combo.currentData()
            # Seçilen cihazla test stream açmayı dene
            test_p = pyaudio.PyAudio()
            try:
                test_stream = test_p.open(
                    format=pyaudio.paInt16,
                    channels=2,
                    rate=44100,
                    input=True,
                    frames_per_buffer=1024,
                    input_device_index=selected_index
                )
                test_stream.close()
                test_p.terminate()
            except Exception as e:
                QMessageBox.warning(dialog, "Geçersiz Çıkış", f"Seçilen cihaz çalışmıyor veya erişilemiyor!\n\n{e}")
                return  # Diyalog açık kalır, seçim iptal edilir

            save_output_device(selected_index)
            dialog.accept()

        button_box.button(QDialogButtonBox.StandardButton.Ok).clicked.connect(on_ok)
        button_box.button(QDialogButtonBox.StandardButton.Cancel).clicked.connect(dialog.reject)

        dialog.exec()
if __name__ == '__main__':
    app = QApplication(sys.argv)
    try:
        with open('style.qss', 'r') as f:
            app.setStyleSheet(f.read())
    except FileNotFoundError:
        pass
        
    player_window = RadyoPlayer()
    player_window.show()
    sys.exit(app.exec())
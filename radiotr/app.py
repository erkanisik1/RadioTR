#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# RadioTR - İnternet Radyo Oynatıcısı
# Geliştirici: Erkan Işık
# GitHub:

import subprocess
import sys
import sqlite3

import vlc
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction, QActionGroup, QIcon
from PyQt6.QtWidgets import (
    QApplication, QComboBox, QDialog, QDialogButtonBox, QHBoxLayout,
    QLabel, QLineEdit, QListWidget, QListWidgetItem, QMainWindow,
    QMenu, QMessageBox, QPushButton, QSlider, QSystemTrayIcon, QToolButton,
    QVBoxLayout, QWidget,
)

from radiotr.dil import I18n
from radiotr import paths, APP_ID
from radiotr.vumetre import VUMeterWidget

BASE_DIR = paths.PACKAGE_DIR
DB_PATH = paths.DB_PATH
ICON_DIR = paths.ICON_DIR
QSS_PATH = paths.QSS_PATH
LEGACY_DB = paths.LEGACY_DB

GENRELER = ["Müzik", "Haber", "Spor", "Türkçe Pop", "Yabancı Müzik", "Slow",
            "Türk Sanat Müziği", "Türk Halk Müziği", "Diğer"]


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


class IstasyonDialog(QDialog):
    def __init__(self, i18n, parent=None):
        super().__init__(parent)
        self.i18n = i18n
        self.setWindowTitle(self.i18n.t('dialog.info'))
        self.layout = QVBoxLayout(self)
        self.layout.addWidget(QLabel(self.i18n.t('dialog.name')))
        self.isim_input = QLineEdit()
        self.isim_input.setPlaceholderText(self.i18n.t('dialog.name_placeholder'))
        self.layout.addWidget(self.isim_input)
        self.layout.addWidget(QLabel(self.i18n.t('dialog.url')))
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText(self.i18n.t('dialog.url_placeholder'))
        self.layout.addWidget(self.url_input)
        self.layout.addWidget(QLabel(self.i18n.t('dialog.genre')))
        self.tur_combo = QComboBox()
        for genre in GENRELER:
            self.tur_combo.addItem(self.i18n.g(genre), userData=genre)
        self.layout.addWidget(self.tur_combo)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Save).setText(self.i18n.t('common.save'))
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText(self.i18n.t('common.cancel'))
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        self.layout.addWidget(buttons)

    def get_data(self):
        return (self.isim_input.text().strip(), self.url_input.text().strip(), self.tur_combo.currentData())

    def set_data(self, isim, url, tur):
        self.isim_input.setText(isim)
        self.url_input.setText(url)
        index = self.tur_combo.findData(tur)
        if index >= 0:
            self.tur_combo.setCurrentIndex(index)


class RadyoPlayer(QMainWindow):
    playback_error_signal = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.i18n = I18n(DB_PATH)
        self._lang_setting = get_setting('dil', 'auto')
        self.setWindowIcon(QIcon(str(ICON_DIR / 'radio-icon.png')))
        self.setWindowTitle(self.i18n.t('app.title'))
        self.setMinimumSize(400, 500)
        self.veritabani_kontrol_et()

        self.vlc_instance = vlc.Instance("--quiet")
        self.player = self.vlc_instance.media_player_new()
        self.event_manager = self.player.event_manager()
        self.event_manager.event_attach(
            vlc.EventType.MediaPlayerEncounteredError, self.handle_playback_error
        )
        self.playback_error_signal.connect(self.show_error_message)

        self.playing_url = None
        self.playing_name = None
        self._now_key = 'now.none'
        self._now_isim = None

        self.init_ui()
        self.load_stations()

        # Ses seviyesini ayarlardan yükle
        saved_volume = int(get_setting('ses_seviyesi', 50))
        self.player.audio_set_volume(saved_volume)
        self.volume_slider.setValue(saved_volume)

        # --- SİSTEM TRAY İKONU ---
        self.tray_icon = QSystemTrayIcon(QIcon(str(ICON_DIR / 'radio-icon.png')), self)
        self.tray_menu = QMenu()
        self.tray_stations_menu = self.tray_menu.addMenu(self.i18n.t('tray.stations'))
        self.show_action = QAction(self.i18n.t('tray.show'), self)
        self.quit_action = QAction(self.i18n.t('tray.quit'), self)
        self.tray_menu.addSeparator()
        self.tray_menu.addAction(self.show_action)
        self.tray_menu.addAction(self.quit_action)
        self.tray_icon.setContextMenu(self.tray_menu)
        self._build_tray_stations()

        self.show_action.triggered.connect(self.showNormal)
        self.quit_action.triggered.connect(QApplication.quit)

        self.tray_icon.setToolTip(self.i18n.t('app.title'))
        self.tray_icon.show()

        # Çift tık ile pencereyi geri getirme
        self.tray_icon.activated.connect(self.on_tray_activated)

        self._render_now()
        self._set_play_button(self.player.is_playing())

    # ------------------------------------------------------------------
    #  Dil
    # ------------------------------------------------------------------
    def _select_language(self, value):
        self._lang_setting = value
        save_setting('dil', value)
        if value == 'auto':
            self.i18n.set_lang(None)
        else:
            self.i18n.set_lang(value)
        self._retranslate_ui()

    def _retranslate_ui(self):
        self.setWindowTitle(self.i18n.t('app.title'))
        self._render_now()
        self.settings_button.setToolTip(self.i18n.t('settings.tooltip'))
        self.capture_action.setText(self.i18n.t('settings.capture_source'))
        self.add_station_action.setText(self.i18n.t('settings.add_station'))
        self.lang_menu.setTitle(self.i18n.t('settings.language'))
        self.volume_label.setText(self.i18n.t('volume.label'))
        self._set_play_button(self.player.is_playing())
        self.tray_stations_menu.setTitle(self.i18n.t('tray.stations'))
        self.show_action.setText(self.i18n.t('tray.show'))
        self.quit_action.setText(self.i18n.t('tray.quit'))
        self._set_tray_tooltip()
        self._refresh_list_texts()
        self._build_tray_stations()
        self._refresh_tray_checked()
        self.vumetre.set_language(self.i18n)
        for act, value in self._lang_actions:
            if value == 'auto':
                act.setText(self.i18n.t('lang.auto'))
            act.setChecked(value == self._lang_setting)

    # ------------------------------------------------------------------
    def _render_now(self):
        if self._now_key in ('now.connecting', 'now.playing') and self._now_isim:
            text = self.i18n.t(self._now_key, isim=self._now_isim)
        else:
            text = self.i18n.t(self._now_key)
        self.su_an_calan_label.setText(text)

    def _set_now(self, key, isim=None):
        self._now_key = key
        self._now_isim = isim
        self._render_now()

    def _set_play_button(self, playing):
        icon = 'stop-green.png' if playing else 'play-green.png'
        tip = 'btn.stop' if playing else 'btn.play'
        self.play_stop_button.setIcon(QIcon(str(ICON_DIR / icon)))
        self.play_stop_button.setToolTip(self.i18n.t(tip))

    def _set_tray_tooltip(self):
        if self.playing_name:
            self.tray_icon.setToolTip(self.i18n.t('tray.tooltip.playing', isim=self.playing_name))
        else:
            self.tray_icon.setToolTip(self.i18n.t('app.title'))

    # ------------------------------------------------------------------
    #  Tepsi
    # ------------------------------------------------------------------
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
            self.tray_stations_menu.addAction(self.i18n.t('tray.no_stations')).setEnabled(False)
            return
        for isim, url, tur in rows:
            act = QAction(f"{isim} ({self.i18n.g(tur)})", self)
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
            if not DB_PATH.exists():
                paths.ensure_data_dir()
                if LEGACY_DB.exists():
                    import shutil
                    shutil.copy2(LEGACY_DB, DB_PATH)
            from radiotr.veritabani_olustur import veritabani_olustur
            veritabani_olustur()
            from radiotr.veritabani_olustur import ayarlar_tablosunu_onar
            ayarlar_tablosunu_onar()
        except Exception as e:
            QMessageBox.critical(self, self.i18n.t('error.db'),
                                 self.i18n.t('error.db_prepare', e=e))
            sys.exit()

    # ------------------------------------------------------------------
    #  Arayüz
    # ------------------------------------------------------------------
    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # --- Üst bar: şu an çalan + ayarlar çarkı ---
        top_layout = QHBoxLayout()
        self.su_an_calan_label = QLabel(self.i18n.t('now.none'))
        font = self.su_an_calan_label.font()
        font.setPointSize(12)
        self.su_an_calan_label.setFont(font)
        top_layout.addWidget(self.su_an_calan_label, 1)

        self.settings_button = QToolButton()
        self.settings_button.setIcon(self.style().standardIcon(self.style().StandardPixmap.SP_FileDialogDetailedView))
        self.settings_button.setToolTip(self.i18n.t('settings.tooltip'))
        self.settings_menu = QMenu()

        self.lang_menu = self.settings_menu.addMenu(self.i18n.t('settings.language'))
        lang_group = QActionGroup(self.lang_menu)
        lang_group.setExclusive(True)
        self._lang_actions = []
        for value, label in [('auto', self.i18n.t('lang.auto')), ('tr', 'Türkçe'), ('en', 'English')]:
            act = QAction(label, self)
            act.setCheckable(True)
            act.triggered.connect(lambda checked, v=value: self._select_language(v))
            self.lang_group = lang_group
            lang_group.addAction(act)
            self.lang_menu.addAction(act)
            self._lang_actions.append((act, value))

        self.capture_action = QAction(self.i18n.t('settings.capture_source'), self)
        self.capture_action.triggered.connect(self.select_capture_device)
        self.add_station_action = QAction(self.i18n.t('settings.add_station'), self)
        self.add_station_action.triggered.connect(self.open_add_station_dialog)
        self.settings_menu.addSeparator()
        self.settings_menu.addAction(self.capture_action)
        self.settings_menu.addAction(self.add_station_action)
        self.settings_button.setMenu(self.settings_menu)
        self.settings_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        top_layout.addWidget(self.settings_button)
        main_layout.addLayout(top_layout)

        # --- Ses seviyesi ---
        ses_layout = QHBoxLayout()
        self.volume_label = QLabel(self.i18n.t('volume.label'))
        ses_layout.addWidget(self.volume_label)
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(50)
        self.volume_slider.valueChanged.connect(self.on_volume_changed)
        ses_layout.addWidget(self.volume_slider, 1)
        main_layout.addLayout(ses_layout)

        # --- VU metre (gerçek yakalama, otomatik cihaz seçimi) ---
        self.vumetre = VUMeterWidget(translator=self.i18n, parent=self)
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
        self.play_stop_button.setToolTip(self.i18n.t('btn.play'))
        self.play_stop_button.clicked.connect(self.toggle_play_stop)
        main_layout.addWidget(self.play_stop_button)

        self._lang_actions.sort(key=lambda pair: pair[1] != 'auto')
        for act, value in self._lang_actions:
            act.setChecked(value == self._lang_setting)

    def on_volume_changed(self, value):
        self.player.audio_set_volume(value)
        save_setting('ses_seviyesi', value)

    # ------------------------------------------------------------------
    #  Çalma
    # ------------------------------------------------------------------
    def toggle_play_stop(self):
        if self.player.is_playing():
            self.player.stop()
            self.playing_url = None
            self.playing_name = None
            self._set_now('now.stopped')
            self._set_play_button(False)
            self._refresh_tray_checked()
            self._set_tray_tooltip()
        else:
            self.play_selected_station()

    def play_selected_station(self):
        current_item = self.istasyon_listesi.currentItem()
        if not current_item:
            QMessageBox.warning(self, self.i18n.t('warn.title'),
                                self.i18n.t('warn.no_selection'))
            return
        full_text = current_item.text()
        isim = full_text.rsplit(' (', 1)[0]
        url = current_item.data(Qt.ItemDataRole.UserRole)
        self.play_station(isim, url)

    def play_station(self, isim, url):
        """Belirli bir istasyonu çalar (liste, tepsi menüsü ortak)."""
        self.playing_url = url
        self.playing_name = isim
        self._set_now('now.connecting', isim=isim)
        media = self.vlc_instance.media_new(url)
        self.player.set_media(media)
        self.player.play()
        self._set_now('now.playing', isim=isim)
        self._set_play_button(True)
        self._refresh_tray_checked()
        self._set_tray_tooltip()

    def stop_station(self):
        self.player.stop()
        self.playing_url = None
        self.playing_name = None
        self._set_now('now.stopped')
        self._set_play_button(False)
        self._refresh_tray_checked()
        self._set_tray_tooltip()

    # ------------------------------------------------------------------
    #  İstasyon yönetimi
    # ------------------------------------------------------------------
    def load_stations(self):
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT isim, url, tur FROM istasyonlar ORDER BY isim")
            istasyonlar = cursor.fetchall()
            conn.close()
            self.istasyon_listesi.clear()
            for isim, url, tur in istasyonlar:
                item = QListWidgetItem(f"{isim} ({self.i18n.g(tur)})")
                item.setData(Qt.ItemDataRole.UserRole, url)
                item.setData(Qt.ItemDataRole.UserRole + 1, tur)
                item.setData(Qt.ItemDataRole.UserRole + 2, isim)
                item.setToolTip(self.i18n.t('list.tooltip'))
                self.istasyon_listesi.addItem(item)
            self._build_tray_stations()
        except Exception as e:
            QMessageBox.critical(self, self.i18n.t('error.db'),
                                 self.i18n.t('error.load_stations', e=e))

    def _refresh_list_texts(self):
        """Dil değişince istasyon listesindeki metin/cinsi yeniden oluştur."""
        for i in range(self.istasyon_listesi.count()):
            item = self.istasyon_listesi.item(i)
            isim = item.data(Qt.ItemDataRole.UserRole + 2) or ''
            tur = item.data(Qt.ItemDataRole.UserRole + 1) or ''
            item.setText(f"{isim} ({self.i18n.g(tur)})")
            item.setToolTip(self.i18n.t('list.tooltip'))

    def show_context_menu(self, position):
        item = self.istasyon_listesi.itemAt(position)
        if not item:
            return
        menu = QMenu()
        edit_action = menu.addAction(self.i18n.t('menu.edit'))
        delete_action = menu.addAction(self.i18n.t('menu.delete'))
        global_position = self.istasyon_listesi.mapToGlobal(position)
        selected_action = menu.exec(global_position)
        if selected_action == edit_action:
            self.open_edit_station_dialog(item)
        elif selected_action == delete_action:
            self.delete_station(item)

    def open_add_station_dialog(self):
        dialog = IstasyonDialog(self.i18n, self)
        dialog.setWindowTitle(self.i18n.t('dialog.add'))
        if dialog.exec():
            isim, url, tur = dialog.get_data()
            if isim and url:
                self.add_station_to_db(isim, url, tur)
            else:
                QMessageBox.warning(self, self.i18n.t('warn.missing'),
                                    self.i18n.t('warn.missing_text'))

    def add_station_to_db(self, isim, url, tur):
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("INSERT INTO istasyonlar (isim, url, tur) VALUES (?, ?, ?)", (isim, url, tur))
            conn.commit()
            conn.close()
            self.load_stations()
        except sqlite3.IntegrityError:
            QMessageBox.warning(self, self.i18n.t('warn.title'),
                                self.i18n.t('warn.dup_url'))
        except Exception as e:
            QMessageBox.critical(self, self.i18n.t('error.db'),
                                 self.i18n.t('error.add_failed', e=e))

    def open_edit_station_dialog(self, item):
        dialog = IstasyonDialog(self.i18n, self)
        dialog.setWindowTitle(self.i18n.t('dialog.edit'))
        full_text = item.text()
        current_name = full_text.rsplit(' (', 1)[0]
        current_tur = item.data(Qt.ItemDataRole.UserRole + 1) or ''
        current_url = item.data(Qt.ItemDataRole.UserRole)
        dialog.set_data(current_name, current_url, current_tur)
        if dialog.exec():
            new_name, new_url, new_tur = dialog.get_data()
            if new_name and new_url:
                self.update_station_in_db(current_url, new_name, new_url, new_tur)
            else:
                QMessageBox.warning(self, self.i18n.t('warn.missing'),
                                    self.i18n.t('warn.missing_text'))

    def update_station_in_db(self, old_url, new_name, new_url, new_tur):
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("UPDATE istasyonlar SET isim = ?, url = ?, tur = ? WHERE url = ?", (new_name, new_url, new_tur, old_url))
            conn.commit()
            conn.close()
            self.load_stations()
        except Exception as e:
            QMessageBox.critical(self, self.i18n.t('error.db'),
                                 self.i18n.t('error.update_failed', e=e))

    def delete_station(self, item):
        isim = item.text().rsplit(' (', 1)[0]
        url = item.data(Qt.ItemDataRole.UserRole)
        box = QMessageBox(self)
        box.setWindowTitle(self.i18n.t('confirm.delete_title'))
        box.setText(self.i18n.t('confirm.delete_text', isim=isim))
        box.setIcon(QMessageBox.Icon.Question)
        yes = box.addButton(self.i18n.t('common.yes'), QMessageBox.ButtonRole.YesRole)
        box.addButton(self.i18n.t('common.no'), QMessageBox.ButtonRole.NoRole)
        box.exec()
        if box.clickedButton() == yes:
            try:
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute("DELETE FROM istasyonlar WHERE url = ?", (url,))
                conn.commit()
                conn.close()
                self.load_stations()
                self._set_now('now.deleted')
            except Exception as e:
                QMessageBox.critical(self, self.i18n.t('error.db'),
                                     self.i18n.t('error.delete_failed', e=e))

    # ------------------------------------------------------------------
    def handle_playback_error(self, event):
        self.playback_error_signal.emit()

    def show_error_message(self):
        self._set_now('now.error')

    def select_capture_device(self):
        dialog = QDialog(self)
        dialog.setWindowTitle(self.i18n.t('capture.title'))
        layout = QVBoxLayout(dialog)
        label = QLabel(self.i18n.t('capture.label'))
        layout.addWidget(label)
        combo = QComboBox()
        layout.addWidget(combo)
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        layout.addWidget(button_box)

        # Otomatik: varsayılan hoparlörün monitor'ü (BT bağlanınca kendisi geçer)
        combo.addItem(self.i18n.t('capture.auto'), userData=None)

        try:
            out = subprocess.check_output(['pactl', 'list', 'sources', 'short'],
                                          text=True, stderr=subprocess.DEVNULL)
            for line in out.splitlines():
                parts = line.split()
                if len(parts) >= 2 and 'monitor' in parts[1]:
                    combo.addItem(parts[1], userData=parts[1])
        except Exception as e:
            QMessageBox.critical(self, self.i18n.t('capture.pactl_err'),
                                 self.i18n.t('capture.pactl_err_text', e=e))

        current = self.vumetre._manual_source
        if current:
            idx = combo.findData(current)
            if idx >= 0:
                combo.setCurrentIndex(idx)

        def on_ok():
            selected = combo.currentData()
            self.vumetre.set_capture(selected)  # None => otomatik mod
            dialog.accept()

        button_box.button(QDialogButtonBox.StandardButton.Ok).setText(self.i18n.t('common.ok'))
        button_box.button(QDialogButtonBox.StandardButton.Cancel).setText(self.i18n.t('common.cancel'))
        button_box.button(QDialogButtonBox.StandardButton.Ok).clicked.connect(on_ok)
        button_box.button(QDialogButtonBox.StandardButton.Cancel).clicked.connect(dialog.reject)

        dialog.exec()


def main():
    import argparse
    parser = argparse.ArgumentParser(prog=APP_ID, description="RadioTR internet radyo oynatıcısı")
    parser.add_argument("--version", action="store_true", help="sürümü yazdır ve çık")
    args = parser.parse_args()
    if args.version:
        from radiotr import __version__
        print(f"{APP_ID} {__version__}")
        return

    try:
        from radiotr.desktop import ensure_desktop_integration
        ensure_desktop_integration()
    except Exception:
        pass

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


if __name__ == '__main__':
    main()

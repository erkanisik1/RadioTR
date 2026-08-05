# -*- coding: utf-8 -*-
import math
import os
import select
import subprocess
import tempfile
import threading
import time

import numpy as np

try:
    import pyaudio
except ImportError:
    pyaudio = None

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QBrush, QColor, QPainter
from PyQt6.QtWidgets import QLabel, QWidget


class VUMeterWidget(QWidget):
    """Gerçek zamanlı VU metre.

    Birinci tercih: PulseAudio monitor kaynağını ``parecord`` subprocess'i ile
    okuyup sol/sağ kanal seviyesini dB ölçeğine çevirir (PulseAudio'lu
    sistemlerde portaudio ALSA backend'i monitor göremez, o yüzden CLI ile
    yapılır). ``parecord`` yoksa ya da monitor bulunamazsa ikincil olarak
    PortAudio ile uygun bir giriş cihazı dener. Hiçbir yöntem çalışmazsa
    metreyi 0'da tutar, sahte veri üretmez.
    """

    NUM_SEGMENTS = 20
    GREEN_THRESHOLD = 0.6
    YELLOW_THRESHOLD = 0.85

    RATE = 44100
    CHANNELS = 2
    SMOOTHING = 0.7
    DB_FLOOR = -60.0  # bu dB'in altı seviye sıfıra düşer

    def __init__(self, capture_source=None, parent=None):
        super().__init__(parent)
        self.level_l = 0.0
        self.level_r = 0.0
        self.setMinimumHeight(56)

        self._backend = None          # "parecord" | "pyaudio" | None
        self._proc = None             # parecord process
        self._reader = None           # reader thread
        self._fifo_path = None        # parecord'un yazdığı named pipe
        self._fifo_fd = None
        self._stop = False
        self._latest = (0.0, 0.0)
        self._lock = threading.Lock()

        self._manual_source = None    # menüden elle seçilirse buraya gelir
        self._current_source = None   # şu an yakalanan monitor kaynağı

        self._pa = None               # pyaudio instance
        self._stream = None
        self._channels = self.CHANNELS

        self._label = QLabel(self)
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label.setStyleSheet("color: #888888; font-size: 11px; background: transparent;")
        self._label.hide()
        self._resize_label()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(50)

        # Varsayılan hoparlör değişirse (BT bağlan/kop vb.) otomatik geçiş
        self.auto_timer = QTimer(self)
        self.auto_timer.timeout.connect(self._auto_recheck)
        self.auto_timer.start(3000)

        if capture_source:
            self.set_capture(capture_source)
        else:
            self._auto_capture()

    # ------------------------------------------------------------------
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._resize_label()

    def _resize_label(self):
        self._label.setGeometry(0, self.height() // 2 - 8, self.width(), 20)

    @property
    def active(self):
        return self._backend is not None

    # ------------------------------------------------------------------
    #  Yakalama başlatma / durdurma
    # ------------------------------------------------------------------
    def _auto_capture(self):
        source = self._manual_source or self._monitor_source()
        if source and self._start_parecord(source):
            return
        if pyaudio is not None and self._start_pyaudio():
            return
        self._set_disabled("Ses yakalama cihazı bulunamadı")

    def _auto_recheck(self):
        """Varsayılan hoparlör değiştiyse yakalamayı yeni monitor'e geçir."""
        if self._manual_source is not None:
            return
        new_source = self._monitor_source()
        if not new_source or new_source == self._current_source:
            return
        if self._backend == "parecord":
            self._close_capture()
        if not self._start_parecord(new_source):
            self._set_disabled("Ses yakalama cihazı bulunamadı")

    @staticmethod
    def _monitor_source():
        """Varsayılan hoparlöre (default sink) bağlı .monitor kaynağını bulur."""
        try:
            default_sink = subprocess.check_output(
                ['pactl', 'get-default-sink'], text=True,
                stderr=subprocess.DEVNULL).strip()
            out = subprocess.check_output(
                ['pactl', 'list', 'sources', 'short'], text=True,
                stderr=subprocess.DEVNULL)
            for line in out.splitlines():
                parts = line.split()
                if len(parts) >= 2 and 'monitor' in parts[1] and parts[1].startswith(default_sink + '.'):
                    return parts[1]
            for line in out.splitlines():
                parts = line.split()
                if len(parts) >= 2 and 'monitor' in parts[1]:
                    return parts[1]
        except Exception:
            pass
        return None

    def _start_parecord(self, source):
        # named pipe: parecord bu ortamda stdout'a değil dosyaya yazar
        try:
            self._fifo_path = os.path.join(
                tempfile.gettempdir(), f'vumeter_{os.getpid()}.fifo')
            try:
                os.remove(self._fifo_path)
            except FileNotFoundError:
                pass
            os.mkfifo(self._fifo_path)
            self._proc = subprocess.Popen(
                ['parecord', f'--device={source}', '--raw',
                 '--format=s16le', f'--rate={self.RATE}',
                 f'--channels={self.CHANNELS}', '--file-format=raw',
                 self._fifo_path],
                stderr=subprocess.DEVNULL)
            self._fifo_fd = os.open(
                self._fifo_path, os.O_RDONLY | os.O_NONBLOCK)
        except Exception as exc:
            print("parecord başlatılamadı:", exc)
            self._clean_fifo()
            return False
        self._stop = False
        self._latest = (0.0, 0.0)
        self._reader = threading.Thread(
            target=self._parecord_loop, args=(self._fifo_fd,), daemon=True)
        self._reader.start()
        self._backend = "parecord"
        self._current_source = source
        self._label.hide()
        return True

    def _parecord_loop(self, fd):
        """FIFO'dan PCM okur, her parçanın seviyesini _latest'e yazar."""
        buf = b''
        frame_bytes = self.CHANNELS * 2  # s16le
        while not self._stop:
            if self._proc is None or self._proc.poll() is not None:
                time.sleep(0.1)
                break
            readable, _, _ = select.select([fd], [], [], 0.3)
            if not readable:
                continue
            try:
                chunk = os.read(fd, 4096)
            except BlockingIOError:
                continue
            if not chunk:
                break
            buf += chunk
            n = len(buf) - (len(buf) % frame_bytes)
            if n <= 0:
                continue
            data, buf = buf[:n], buf[n:]
            audio = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0
            left = audio[0::2]
            right = audio[1::2]
            l = self._rms_to_level(float(np.sqrt(np.mean(left * left))))
            r = self._rms_to_level(float(np.sqrt(np.mean(right * right))))
            with self._lock:
                self._latest = (l, r)
        try:
            os.close(fd)
        except Exception:
            pass

    def _start_pyaudio(self):
        try:
            self._pa = pyaudio.PyAudio()
        except Exception as exc:
            self._set_disabled(f"PyAudio başlatılamadı: {exc}")
            return False
        index = self._find_pyaudio_input(self._pa)
        if index is None:
            self._set_disabled("Ses yakalama cihazı bulunamadı")
            return False
        try:
            info = self._pa.get_device_info_by_index(index)
            channels = min(2, int(info.get('maxInputChannels', 1)))
            self._stream = self._pa.open(
                format=pyaudio.paInt16, channels=channels, rate=self.RATE,
                input=True, frames_per_buffer=1024, input_device_index=index)
            self._channels = channels
            self._backend = "pyaudio"
            self._label.hide()
            return True
        except Exception as exc:
            print("PyAudio yakalama açılamadı:", exc)
            self._set_disabled("Yakalama cihazı açılamadı")
            return False

    @staticmethod
    def _find_pyaudio_input(pa):
        for i in range(pa.get_device_count()):
            if pa.get_device_info_by_index(i).get('maxInputChannels', 0) >= 2:
                return i
        return None

    def set_capture(self, source):
        """Yakalama kaynağını değiştir. source=None => otomatik mod."""
        self._manual_source = source
        self._close_capture()
        if source:
            if not self._start_parecord(source):
                self._set_disabled("Yakalama cihazı açılamadı")
        else:
            self._auto_capture()

    def _set_disabled(self, message):
        self._close_capture()
        self._label.setText(message)
        self._label.show()
        self.update()

    def _close_capture(self):
        self._stop = True
        if self._proc is not None:
            try:
                self._proc.terminate()
                self._proc.kill()
            except Exception:
                pass
            self._proc = None
        if self._reader is not None:
            self._reader.join(timeout=1.0)
            self._reader = None
        self._clean_fifo()
        if self._stream is not None:
            try:
                self._stream.stop_stream()
                self._stream.close()
            except Exception:
                pass
            self._stream = None
        if self._pa is not None:
            try:
                self._pa.terminate()
            except Exception:
                pass
            self._pa = None
        self._backend = None
        self._latest = (0.0, 0.0)

    def _clean_fifo(self):
        if self._fifo_fd is not None:
            try:
                os.close(self._fifo_fd)
            except Exception:
                pass
            self._fifo_fd = None
        if self._fifo_path is not None:
            try:
                os.remove(self._fifo_path)
            except FileNotFoundError:
                pass
            self._fifo_path = None

    def close(self):
        self.timer.stop()
        self.auto_timer.stop()
        self._close_capture()

    # ------------------------------------------------------------------
    #  Seviye hesaplama ve çizim
    # ------------------------------------------------------------------
    @staticmethod
    def _rms_to_level(rms):
        if rms <= 0:
            return 0.0
        db = 20.0 * math.log10(rms)  # -inf .. 0
        return min(max((db - VUMeterWidget.DB_FLOOR) / -VUMeterWidget.DB_FLOOR, 0.0), 1.0)

    def _tick(self):
        if self._backend == "parecord":
            if self._proc is None or self._proc.poll() is not None:
                self.update_levels(0.0, 0.0)
                return
            with self._lock:
                l, r = self._latest
            self.update_levels(l, r)
            return
        if self._backend != "pyaudio" or self._stream is None:
            self.update_levels(0.0, 0.0)
            return
        try:
            data = self._stream.read(1024, exception_on_overflow=False)
        except Exception:
            self.update_levels(0.0, 0.0)
            return
        audio = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0
        if self._channels >= 2:
            left = audio[0::2]
            right = audio[1::2]
            if left.size and right.size:
                l = self._rms_to_level(float(np.sqrt(np.mean(left * left))))
                r = self._rms_to_level(float(np.sqrt(np.mean(right * right))))
            else:
                l = r = 0.0
        else:
            lvl = self._rms_to_level(float(np.sqrt(np.mean(audio * audio))))
            l = r = lvl
        self.update_levels(l, r)

    def update_levels(self, new_level_l, new_level_r):
        t = self.SMOOTHING
        self.level_l = self.level_l * t + new_level_l * (1.0 - t)
        self.level_r = self.level_r * t + new_level_r * (1.0 - t)
        self.update()

    def paintEvent(self, event):
        if self._backend is None:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        width, height = self.width(), self.height()
        bar_height = (height - 10) / 2
        self._draw_bar(painter, 5, 5, width - 10, bar_height, self.level_l)
        self._draw_bar(painter, 5, 10 + bar_height, width - 10, bar_height, self.level_r)

    def _draw_bar(self, painter, x, y, width, height, level):
        segment_width = width / self.NUM_SEGMENTS
        for i in range(self.NUM_SEGMENTS):
            seg_x = x + (i * segment_width)
            threshold = (i + 1) / self.NUM_SEGMENTS
            if threshold > self.YELLOW_THRESHOLD:
                color_on = QColor("red")
            elif threshold > self.GREEN_THRESHOLD:
                color_on = QColor("yellow")
            else:
                color_on = QColor("lime")
            color_off = QColor(40, 40, 40)
            painter.setBrush(QBrush(color_on) if level >= threshold else QBrush(color_off))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRect(int(seg_x), int(y), int(segment_width * 0.85), int(height))

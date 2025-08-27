import subprocess
import pyaudio
import numpy as np
from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPainter, QColor, QBrush
from PyQt6.QtCore import Qt, QTimer

class VUMeterWidget(QWidget):
    NUM_SEGMENTS = 20
    GREEN_THRESHOLD = 0.6
    YELLOW_THRESHOLD = 0.85

    def __init__(self, device_index=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.level_l = 0.0
        self.level_r = 0.0
        self.setMinimumHeight(40)
        self.smoothing_factor = 0.7

        self.p = pyaudio.PyAudio()
        
        # Eğer device_index verilmişse onu kullan, yoksa monitor cihazı bulmaya çalış
        if device_index is not None and 0 <= device_index < self.p.get_device_count():
            info = self.p.get_device_info_by_index(device_index)
            if info.get("maxInputChannels", 0) >= 2:
                self.stream = self.p.open(
                    format=pyaudio.paInt16,
                    channels=2,
                    rate=44100,
                    input=True,
                    frames_per_buffer=1024,
                    input_device_index=device_index
                )
            else:
                print("Seçilen cihaz stereo desteklemiyor! VU metre devre dışı.")
                self.stream = None
        else:
            # 1. pactl ile monitor cihazını bul
            monitor_name = None
            try:
                output = subprocess.check_output(['pactl', 'list', 'sources', 'short'], text=True)
                for line in output.splitlines():
                    if 'monitor' in line:
                        monitor_name = line.split()[1]
                        break
            except Exception as e:
                print("PulseAudio kaynakları alınamadı:", e)

            monitor_index = None
            if monitor_name:
                for i in range(self.p.get_device_count()):
                    info = self.p.get_device_info_by_index(i)
                    if monitor_name in info["name"]:
                        monitor_index = i
                        break

            if monitor_index is not None:
                self.stream = self.p.open(
                    format=pyaudio.paInt16,
                    channels=2,
                    rate=44100,
                    input=True,
                    frames_per_buffer=1024,
                    input_device_index=monitor_index
                )
            else:
                print("Geçersiz cihaz seçimi veya monitor cihazı bulunamadı! VU metre devre dışı.")
                self.stream = None

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_from_audio)
        self.timer.start(50)  # 20 Hz

    def update_from_audio(self):
        if self.stream is None:
            import random
            fake_level = random.uniform(0.1, 0.7)
            self.update_levels(fake_level, fake_level)
            return
        try:
            data = self.stream.read(1024, exception_on_overflow=False)
            audio = np.frombuffer(data, dtype=np.int16)
            # Stereo ise: [L, R, L, R, ...]
            left = audio[::2]
            right = audio[1::2]
            level_l = np.abs(left).mean() / 32768.0
            level_r = np.abs(right).mean() / 32768.0
            self.update_levels(level_l, level_r)
        except Exception:
            self.update_levels(0, 0)

    def update_levels(self, new_level_l, new_level_r):
        self.level_l = (self.level_l * self.smoothing_factor) + (new_level_l * (1 - self.smoothing_factor))
        self.level_r = (self.level_r * self.smoothing_factor) + (new_level_r * (1 - self.smoothing_factor))
        self.update()

    def paintEvent(self, event):
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
            if threshold > self.YELLOW_THRESHOLD: color_on = QColor("red")
            elif threshold > self.GREEN_THRESHOLD: color_on = QColor("yellow")
            else: color_on = QColor("lime")
            color_off = QColor(40, 40, 40)
            painter.setBrush(QBrush(color_on) if level >= threshold else QBrush(color_off))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRect(int(seg_x), int(y), int(segment_width * 0.85), int(height))

    def close(self):
        self.timer.stop()
        if self.stream is not None:
            self.stream.stop_stream()
            self.stream.close()
        self.p.terminate()


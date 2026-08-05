# -*- coding: utf-8 -*-
"""Masaüstü entegrasyonu: .desktop dosyası ve uygulama ikonu.

Kullanıcı başına (root gerekmeden) ``~/.local/share`` altına yazılır ve
uygulama menüsünde görünmesi sağlanır. Dosya zaten varsa üzerine yazılmaz.
"""

from radiotr import APP_ID
from radiotr import paths

DESKTOP_TEMPLATE = """\
[Desktop Entry]
Type=Application
Name=RadioTR
GenericName=Internet Radio Player
GenericName[tr]=İnternet Radyo Oynatıcısı
Comment=Internet radio player with real-time VU meter
Comment[tr]=Gerçek zamanlı VU metrelik internet radyo oynatıcısı
Exec={app_id}
Icon={app_id}
Terminal=false
Categories=AudioVideo;Audio;Player;
StartupNotify=true
"""


def ensure_desktop_integration():
    desktop = paths.APPLICATIONS_DIR / f"{APP_ID}.desktop"
    if desktop.exists():
        return
    try:
        import shutil
        paths.APPLICATIONS_DIR.mkdir(parents=True, exist_ok=True)
        paths.ICON_INSTALL_DIR.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(paths.ICON_DIR / "radio-icon.png",
                        paths.ICON_INSTALL_DIR / f"{APP_ID}.png")
        desktop.write_text(DESKTOP_TEMPLATE.format(app_id=APP_ID), encoding="utf-8")
    except OSError:
        return

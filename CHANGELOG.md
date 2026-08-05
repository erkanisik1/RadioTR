<div align="center">

**[Türkçe](CHANGELOG.tr.md)**

</div>

# Changelog

All notable changes to this project are documented in this file. The format is
based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0] - 2026-08-05

### Added
- **Installable package:** pip install via `pyproject.toml` (`pip install .`) and
  the `radiotr` command; the code was moved into the `radiotr/` package. `lang/`,
  `icons/` and `style.qss` are bundled as package data.
- **Desktop integration (.desktop):** On first launch
  `~/.local/share/applications/radiotr.desktop` and the hicolor app icon are
  created automatically, so it shows up in the app menu.
- **Station export (RadioAndroid):** Export your stations from the Settings menu
  to RadioAndroid's JSON format (`[{"Nazwa","Sciezka"}]`) and import them on your
  phone.
- **User data moved to XDG:** The database is now stored under
  `~/.local/share/RadioTR/playlist.db`; an old `playlist.db` in the repo folder is
  migrated automatically on first launch.
- **Multilingual interface (Turkish / English):** pick the language from
  Settings → Language (Auto / Turkish / English). "Auto" uses the system
  language and falls back to English for unsupported languages. The choice is
  saved in the `ayarlar.dil` setting and restored on launch.
- **`lang/` translation files:** All translations live in `lang/tr.json` and
  `lang/en.json`; `dil.py` reads them and falls back to English for missing
  keys. Genre names stay Turkish in the database and are shown via `genre.*`
  keys.

### Changed
- **All UI text is translatable:** window title, menus, buttons, message boxes,
  tray menu/tooltip and VU-meter error texts use dynamic translation and update
  instantly on language change.
- **VU meter translation support:** error texts (`vu.*` keys) follow the
  selected language; `set_language()` reflects changes immediately.

### Technical / Infrastructure
- New module `dil.py`: `I18n(db_path)`, `t()` (value/translation), `g()` (genre
  translation), `system_language()` system-language detection.

## [0.2.0] - 2026-08-05

### Added
- **Tray station menu:** right-click the system tray icon for a "Stations"
  submenu and switch stations from there. The playing station is checked (✓)
  and the tray tooltip shows the station name. The menu refreshes automatically
  after adding/editing/deleting a station.
- **Automatic source selection for the VU meter:** the default speaker's
  `.monitor` source is selected automatically at startup; if the default speaker
  changes (Bluetooth connect/disconnect, cable change) it switches to the new
  source automatically by polling every 3 seconds.
- **Volume slider:** added to the UI; the value is written to the `ses_seviyesi`
  setting and restored on launch.
- **Settings-schema repair:** the old `ayarlar(anahtar, deger)` schema is
  migrated to the new `ayarlar(ayar_adi, deger)` automatically
  (`ayarlar_tablosunu_onar`).
- **Settings menu:** the "VU Meter Capture Source" picker lists PulseAudio
  monitor sources via `pactl` and offers "Automatic (default speaker)".

### Changed
- **VU meter now uses real audio:** the fake/random data logic (`update_visualizer`
  timer) was removed; the level is computed from actually captured PCM by
  converting RMS to a dB scale.
- **Capture method:** because PortAudio's ALSA backend cannot see the PulseAudio
  monitor, capture is done with `parecord` + named FIFO (`parecord` does not
  write to stdout on this system). Falls back to PortAudio if `parecord` is
  missing.
- **Absolute file paths:** `playlist.db`, `style.qss` and `icons/` are resolved
  to absolute paths relative to the script location, so the app works from any
  working directory.
- **Unified playback logic:** double-click and the tray menu share the same
  `play_station(isim, url)` function.
- **Consistent icon/stop-only button state:** the wrong icon/tooltip mapping in
  `stop_station` was fixed; the currently playing station is cleared on stop.
- **Resource cleanup:** VLC player and VU-meter resources (parecord process,
  FIFO, streams) are released on exit; no process/FIFO leaks.

### Fixed
- Database schema mismatch (code used `ayar_adi` while the creator generated
  `anahtar`).
- Missing `veritabani_olustur()` function (previously imported but undefined).
- The VU capture-device picker failing with a `Device unavailable` error.
- `load_stations` being called before the tray menu was built, opening an error
  box at startup.
- DB/QSS not being found when launched from another directory due to relative
  paths.
- Dead code (`get_device_channels`, unnecessary `pyaudio` import).

### Technical / Infrastructure
- `vumetre.py` and `veritabani_olustur.py` were refactored for readability;
  setting helpers (`get_setting`/`save_setting`) were centralized.

## [0.1.0] - 2025-08-25

- Initial release: PyQt6 + VLC internet radio player. Add, edit and delete
  stations; SQLite storage; system tray; dark theme.

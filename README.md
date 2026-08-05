<p dir="auto" align="center">
  <img src="radio.jpg" alt="RadioTR Logo" style="max-width: 100%;margin: 0 auto">
</p>

<div align="center">

**[Türkçe](README.tr.md)**

</div>

# RadioTR Player

RadioTR Player is a modern desktop application for listening to internet radio stations, adding and editing stations, controlling the volume and monitoring it with a real-time VU meter.

## Features

- Add, edit and delete radio stations
- Store stations in a SQLite database
- VLC-based radio streaming
- **Real-time VU meter** (actual audio level read from the PulseAudio monitor source)
- **Automatic device selection** for the VU meter (tracks the default speaker; automatically switches on Bluetooth connect/disconnect)
- **Volume slider** (the value is remembered)
- **System tray support** — pick/switch stations and hide the window from the tray menu
- **Multilingual interface** (Turkish / English) — Settings → Language; automatic system-language detection, selection is remembered
- **Export stations for RadioAndroid** — export your station list to RadioAndroid's JSON format (`[{"Nazwa","Sciezka"}]`) from Settings and import it on Android
- Single play/stop button with icon support
- Modern, clean dark theme (PyQt6 + QSS)
- Tooltips on the station list

## Installation

### Requirements

- Python 3.9+
- [VLC](https://www.videolan.org/vlc/) (must be installed on the system)
- PulseAudio (`pactl`/`parecord`) — for the VU meter (default on most Linux distros)
- Python packages:
  - PyQt6
  - python-vlc
  - numpy
  - PyAudio (optional — VU-meter fallback only on systems without `parecord`)

### Installing dependencies

First install the system packages (Linux):
```bash
vlc
pulseaudio-utils   # pactl + parecord (VU meter)
```

Then install the app (installs dependencies automatically):
```bash
pip install .
```

For development, an editable install in a virtual environment:
```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -e .
```

After installation the app starts with the `radiotr` command. On first launch
`~/.local/share/applications/radiotr.desktop` and the app icon are created
automatically, so you can start it from your application menu. The database is
stored under `~/.local/share/RadioTR/playlist.db` (an old `playlist.db` in the
repo folder is migrated automatically on first launch).

### Icons

The `radiotr/icons/` folder contains:
- `radio-icon.png` — window and tray icon
- `play-green.png` / `stop-green.png` — play/stop buttons

You can use your own icons as well.

## Usage

```bash
radiotr                 # after installation
# or from the source tree:
./player-v3.py
```

- To add a station, use "Add Station" from the settings gear in the top-right corner.
- Double-click a station (or use the play/stop button) to start streaming.
- Right-click a station to edit or delete it.
- Use the slider to set the volume; the value is remembered automatically.
- Watch the volume in real time on the VU meter. If the speaker changes
  (e.g. Bluetooth), it automatically switches to the new source; you can also
  pick a source manually from the settings menu.
- Click the tray icon to minimize to the tray instead of closing the window.
- **Right-click** the tray icon to switch stations from the "Stations" menu;
  the currently playing station is checked.
- Change the UI language from **Settings → Language** (Auto / Turkish / English).
  "Auto" uses the system language; the selection is remembered and restored on launch.
- Export your stations for Android from **Settings → Export Stations (RadioAndroid)**.
  Choose a location; the resulting JSON file can be imported into the RadioAndroid app
  (`[{"Nazwa","Sciezka"}]`).

## Database

Stations are stored in `playlist.db` (under `~/.local/share/RadioTR/`).
The database is created automatically on first run; settings tables from older
versions are migrated to the new schema automatically.

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for release notes.

## Contributing & License

This project is released under the GNU General Public License v3.0.
You can open a pull request to contribute. Report issues and suggestions via <a href='https://github.com/erkanisik1/RadioTR/issues' target='_blank'><b>issues</b></a>.

---

**Developer:** Erkan Işık
GitHub: [github.com/erkanisik1](https://github.com/erkanisik1)

# ✦ ASMR Player with Subtitle Display

A minimal, portable audio player with real-time subtitle display — designed for ASMR content, guided meditations, audiobooks, or any audio where you want on-screen text sync.

---

## Requirements

- **Python 3.8+** — https://python.org (check "Add Python to PATH")
- **pygame** and **mutagen** (auto-installed by the launcher)

---

## Quick Start

**Double-click `Launch ASMR Player.bat`**

This installs dependencies and opens the player automatically.

Or manually:
```
pip install pygame mutagen
python asmr_player.py
```

---

## Supported Formats

### Audio
| Format | Extension |
|--------|-----------|
| MP3    | `.mp3`    |
| WAV    | `.wav`    |
| OGG    | `.ogg`    |
| FLAC   | `.flac`   |

### Subtitles
| Format   | Extension | Notes                              |
|----------|-----------|------------------------------------|
| SRT      | `.srt`    | Standard subtitle format           |
| WebVTT   | `.vtt`    | Web video text tracks              |
| Plain TXT| `.txt`    | With timestamps like `[00:01:23]` or `00:01:23` |

---

## Subtitle Auto-Load

If your audio and subtitle file share the same base name, the subtitle loads automatically:

```
my_audio.mp3
my_audio.srt   ← auto-loaded!
```

---

## TXT Timestamp Format

Plain `.txt` files are supported as long as each line starts with a timestamp:

```
[00:00:00] Welcome, take a deep breath...
[00:00:05] Let the sound wash over you.
[00:00:12] Close your eyes slowly.
0:00:20 Focus on the gentle rhythm.
```

---

## Controls

| Control         | Action                  |
|----------------|-------------------------|
| `▶ / ⏸`        | Play / Pause            |
| `⏮ / ⏭`        | Skip back/forward 10s   |
| Progress bar    | Click or drag to seek   |
| Volume slider   | Adjust playback volume  |

---

## Portable Usage

Copy the entire folder to any Windows machine with Python. Run the `.bat` file — no install needed beyond Python itself.

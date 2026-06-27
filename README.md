# ✦ ASMR Player with Subtitle Display

A minimal, portable ASMR audio player with real-time subtitle display and image gallery support.

Designed for ASMR recordings, guided meditation, audiobooks, voice content, or any audio where you want synchronized text and visual content displayed together.

Features:

* 🎵 Audio playback with subtitle synchronization
* 💬 Real-time SRT / VTT / TXT subtitle display
* 🖼️ Built-in image gallery viewer
* 📂 Folder-based auto loading of audio, subtitles, and images
* 🎚️ Seek bar, volume control, skip controls
* ✨ Customizable subtitle size, bold mode, and position

---

## Requirements

* **Python 3.8+** — https://python.org (enable "Add Python to PATH")
* Required Python packages:

  * `pygame` — audio playback
  * `mutagen` — audio duration detection
  * `Pillow` — image gallery support

---

## Quick Start

### Windows

Double-click:

			
```
Launch ASMR Player.bat
```

The launcher installs required dependencies and starts the player automatically.

### Manual

Install dependencies:

```
pip install pygame mutagen Pillow
```

Run:

```
python asmr_player.py
```

---

# Supported Formats

## Audio

| Format | Extension |
| ------ | --------- |
| MP3    | `.mp3`    |
| WAV    | `.wav`    |
| OGG    | `.ogg`    |
| FLAC   | `.flac`   |
| M4A    | `.m4a`    |
| AAC    | `.aac`    |
| OGA    | `.oga`    |

---

## Subtitles

| Format | Extension | Notes                           |
| ------ | --------- | ------------------------------- |
| SRT    | `.srt`    | Standard subtitle format        |
| WebVTT | `.vtt`    | Web subtitle format             |
| TXT    | `.txt`    | Timestamp-based subtitle format |

Example TXT:

```
[00:00:00] Welcome, take a deep breath...
[00:00:05] Let the sound wash over you.
[00:00:12] Close your eyes slowly.
```

---

## Images / Gallery

The player supports displaying images together with audio playback.

Supported image formats:

| Format | Extension       |
| ------ | --------------- |
| PNG    | `.png`          |
| JPEG   | `.jpg`, `.jpeg` |
| BMP    | `.bmp`          |
| GIF    | `.gif`          |
| WebP   | `.webp`         |
| TIFF   | `.tiff`         |

Images are displayed in the main viewing area and can be browsed using:

```
❮ Previous Image
❯ Next Image
```

The current image number is displayed in the top-right corner.

---

# Folder Auto-Load Feature

Selecting a folder automatically scans the entire directory and loads:

* Audio files → added into the playlist
* Image files → loaded into the image gallery
* Subtitle files → automatically matched with audio tracks

Example folder:

```
ASMR Session/
│
├── 01_Relaxing_ASMR.wav
├── 01_Relaxing_ASMR.srt
│
├── 02_Soft_Whispers.mp3
├── 02_Soft_Whispers.vtt
│
├── cover.png
├── scene_01.jpg
└── scene_02.jpg
```

After selecting this folder:

* Audio files become the playback playlist
* Images become the visual gallery
* Matching subtitles are loaded automatically when each track starts

---

# Subtitle Auto-Load Rules

When an audio file is loaded, the player searches the same folder for matching subtitle files.

Supported matching examples:

```
my_audio.mp3
my_audio.srt
```

or:

```
my_audio.wav
my_audio.wav.vtt
```

The player also supports subtitle files where the filename starts with the audio filename, useful for files containing extra naming characters.

Example:

```
01_Prologue.wav
01_Prologue - English Subtitle.txt
```

---

# Controls

| Control                  | Action                             |
| ------------------------ | ---------------------------------- |
| ▶ / ⏸                    | Play / Pause                       |
| ⏮ / ⏭                    | Previous / Next audio track        |
| ⏪ / ⏩                    | Skip backward / forward 10 seconds |
| Progress bar             | Click or drag to seek              |
| Volume slider            | Adjust playback volume             |
| A+                       | Increase subtitle size             |
| A−                       | Decrease subtitle size             |
| B                        | Toggle bold subtitles              |
| Subtitle position button | Switch subtitle position           |
| ❮ / ❯                    | Browse image gallery               |

---

# Portable Usage

Copy the entire project folder to another Windows machine.

Requirements:

* Python installed
* Run `Launch ASMR Player.bat`

No additional installation is required.

---

# Project Structure

Example:

```
ASMR Player/
│
├── asmr_player.py
├── requirements.txt
├── Launch ASMR Player.bat
└── README.md
```

Place your ASMR audio folders anywhere. The player will discover related audio, subtitle, and image files when you select a folder.

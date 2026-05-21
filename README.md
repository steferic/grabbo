# grabbo

Download audio, video, or transcripts from YouTube and 1800+ sites — from the command line.

## Installation

Requires Python 3.10+ and ffmpeg.

```bash
# Install ffmpeg (if not already installed)
brew install ffmpeg

# Clone and install
git clone https://github.com/steferic/grabbo.git
cd grabbo
pip install -e .
```

## Usage

### Clipboard watcher

The easiest way to use grabbo - just copy any YouTube URL and it downloads automatically:

```bash
# Auto-download mode - copies trigger downloads
grabbo watch -y

# Interactive mode - prompts before each download
grabbo watch

# With quality option
grabbo watch -y -q 320
```

Keep a terminal running with `grabbo watch -y`, then copy any YouTube URL from your browser.

### Download audio, video, or transcript

Pick what you want — each command auto-detects playlist URLs:

```bash
grabbo audio "URL"        # MP3 (also: grabbo d "URL", grabbo download "URL")
grabbo video "URL"        # video file (also: grabbo v "URL")
grabbo transcript "URL"   # captions (also: grabbo t "URL")
```

### Time clipping (audio + video)

Extract a specific portion. The clip flags work the same for `audio` and `video`:

```bash
# 20 seconds starting at 0:12
grabbo audio "URL" -s 12 -d 20
grabbo video "URL" -s 12 -d 20

# From 1:30 to 2:00
grabbo audio "URL" -s 1:30 -e 2:00

# Various time formats work
grabbo audio "URL" -s 1m30s -d 30s
grabbo audio "URL" -s 1:02:30 -e 1:05:00
```

### Audio options

```bash
-o, --output PATH    Output directory
-q, --quality        Audio quality: 128, 192 (default), or 320 kbps
-n, --name           Custom filename (without extension)
-s, --start          Start time (e.g., 12, 1:30, 1m30s)
-d, --duration       Duration (e.g., 20, 20s, 1:00)
-e, --end            End time (alternative to duration)
-N, --max            Max videos when URL is a playlist
```

### Video options

```bash
-o, --output PATH       Output directory
-r, --resolution        Cap on height: 480, 720, 1080, 1440, 2160 (4K), 4320 (8K) (default: best)
-c, --container         mp4 (default) or webm
-n, --name              Custom filename
-s, --start             Start time
-d, --duration          Duration
-e, --end               End time
-N, --max               Max videos when URL is a playlist
```

### Search and download

Search YouTube without needing a URL:

```bash
# Search and show results
grabbo search "lofi hip hop"

# Download the first result directly
grabbo search "song name" -d 1

# Show more results
grabbo search "query" -n 20
```

### Playlist downloads

Download entire YouTube playlists:

```bash
# Download all videos in a playlist
grabbo playlist "https://youtube.com/playlist?list=..."

# Download first 5 videos only
grabbo playlist "URL" -n 5

# Preview playlist contents without downloading
grabbo playlist "URL" --info
```

### Batch downloads

Download multiple videos at once:

```bash
# Multiple URLs as arguments
grabbo batch "url1" "url2" "url3"

# From a file (one URL per line)
grabbo batch -f urls.txt

# Combine both
grabbo batch "url1" -f more_urls.txt -q 320
```

### Trim silence

Remove silence from the beginning and end of tracks:

```bash
# Trim a specific file
grabbo trim "song.mp3"

# Trim all files in output directory
grabbo trim --all

# Only trim start (keep ending)
grabbo trim song.mp3 --no-end

# More aggressive threshold (-40dB instead of -50dB)
grabbo trim song.mp3 -t -40
```

### Download transcripts

Download captions/transcripts only (no audio):

```bash
# Download transcript as plain text
grabbo transcript "https://youtube.com/watch?v=..."

# Or use the shortcut
grabbo t "https://youtube.com/watch?v=..."

# Different formats
grabbo t "URL" -f txt   # Plain text (default)
grabbo t "URL" -f srt   # SRT subtitles with timestamps
grabbo t "URL" -f json  # JSON with timestamps

# Download transcripts for entire playlist
grabbo t "PLAYLIST_URL"

# First 10 videos only
grabbo t "PLAYLIST_URL" -n 10

# Preview playlist without downloading
grabbo t "PLAYLIST_URL" --info

# Different language
grabbo t "URL" -l es    # Spanish
```

Transcripts are organized by creator and playlist under the base dir:
```
~/grabbo/transcripts/
├── Huberman Lab/
│   └── Huberman Lab Podcast/
│       ├── Episode 1.txt
│       └── Episode 2.txt
└── Lex Fridman/
    └── Lex Fridman Podcast/
        └── Interview.txt
```

### Default folder layout

Everything lives under one base directory (default: `~/grabbo`), with one subfolder per kind:

```
~/grabbo/
├── audio/         # MP3s from `grabbo audio` / `download` / `batch` / `playlist` / `watch`
├── video/         # videos from `grabbo video`
└── transcripts/   # captions from `grabbo transcript`, nested by creator/playlist
```

`grabbo set-dir` changes the base, not a single kind's dir.

### Manage downloads

```bash
# List downloaded files (audio by default)
grabbo list
grabbo list -k video         # List video files instead

# Show current config (counts per kind)
grabbo config

# Change base output directory (default: ~/grabbo)
grabbo set-dir ~/Media

# Open base folder in Finder
grabbo open
```

## All Commands

| Command | Description |
|---------|-------------|
| `audio` / `download` / `d` | Download as MP3 (auto-detects playlists) |
| `video` / `v` | Download as video file (auto-detects playlists) |
| `transcript` / `t` | Download captions/transcripts only |
| `watch` | Watch clipboard for YouTube URLs |
| `search` | Search YouTube and download results |
| `playlist` | Download entire playlists as MP3 |
| `batch` | Download multiple videos as MP3 |
| `trim` | Remove silence from start/end of files |
| `list` | List downloaded files (`-k audio` default, `-k video`) |
| `config` | Show current configuration |
| `set-dir` | Set the base output directory |
| `open` | Open output directory in Finder |

# grabbo

Download YouTube videos as MP3 files from the command line.

## Installation

Requires Python 3.10+ and ffmpeg.

```bash
# Install ffmpeg (if not already installed)
brew install ffmpeg

# Clone and install
git clone https://github.com/stefanlenoach/grabbo.git
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

### Download a single video

```bash
grabbo download "https://youtube.com/watch?v=..."

# Or use the shortcut
grabbo d "URL"
```

### Options

```bash
-o, --output PATH    Output directory for this download
-q, --quality        Audio quality: 128, 192 (default), or 320 kbps
-n, --name           Custom filename (without extension)
-s, --start          Start time (e.g., 12, 1:30, 1m30s)
-d, --duration       Duration to capture (e.g., 20, 20s, 1:00)
-e, --end            End time (alternative to duration)
```

### Time clipping

Extract a specific portion of the audio:

```bash
# 20 seconds starting at 0:12
grabbo d "URL" -s 12 -d 20

# From 1:30 to 2:00
grabbo d "URL" -s 1:30 -e 2:00

# Various time formats work
grabbo d "URL" -s 1m30s -d 30s
grabbo d "URL" -s 1:02:30 -e 1:05:00
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

Transcripts are organized by creator and playlist:
```
~/grabbo-transcripts/
├── Huberman Lab/
│   └── Huberman Lab Podcast/
│       ├── Episode 1.txt
│       └── Episode 2.txt
└── Lex Fridman/
    └── Lex Fridman Podcast/
        └── Interview.txt
```

### Manage downloads

```bash
# List downloaded files
grabbo list

# Show current config
grabbo config

# Change default output directory (default: ~/grabbo)
grabbo set-dir ~/Music/Downloads

# Open output folder in Finder
grabbo open
```

## All Commands

| Command | Description |
|---------|-------------|
| `watch` | Watch clipboard for YouTube URLs |
| `download` / `d` | Download a YouTube video as MP3 |
| `search` | Search YouTube and download results |
| `playlist` | Download entire playlists |
| `batch` | Download multiple videos |
| `trim` | Remove silence from start/end of files |
| `transcript` / `t` | Download captions/transcripts only |
| `list` | List downloaded MP3 files |
| `config` | Show current configuration |
| `set-dir` | Set default output directory |
| `open` | Open output directory in Finder |

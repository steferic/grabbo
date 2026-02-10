"""Core download and conversion logic."""
import json
from pathlib import Path

import yt_dlp

CONFIG_FILE = Path.home() / ".grabbo_config.json"
DEFAULT_OUTPUT_DIR = Path.home() / "grabbo"


def get_output_dir() -> Path:
    """Get the configured output directory."""
    if CONFIG_FILE.exists():
        config = json.loads(CONFIG_FILE.read_text())
        return Path(config.get("output_dir", DEFAULT_OUTPUT_DIR))
    return DEFAULT_OUTPUT_DIR


def set_output_dir(path: Path) -> None:
    """Set the output directory."""
    path = path.expanduser().resolve()
    path.mkdir(parents=True, exist_ok=True)
    config = {"output_dir": str(path)}
    CONFIG_FILE.write_text(json.dumps(config, indent=2))


def list_downloads() -> list[dict]:
    """List all MP3 files in the output directory."""
    output_dir = get_output_dir()
    if not output_dir.exists():
        return []

    files = []
    for f in sorted(output_dir.glob("*.mp3"), key=lambda x: x.stat().st_mtime, reverse=True):
        stat = f.stat()
        files.append({
            "name": f.name,
            "size_mb": round(stat.st_size / (1024 * 1024), 2),
            "path": str(f),
        })
    return files


def parse_time(time_str: str) -> float:
    """Parse time string to seconds.

    Supports formats:
    - "12" or "12s" -> 12 seconds
    - "1:30" or "1m30s" -> 90 seconds
    - "1:02:30" or "1h2m30s" -> 3750 seconds
    """
    if not time_str:
        return 0.0

    time_str = time_str.strip().lower()

    # Handle HH:MM:SS or MM:SS format
    if ":" in time_str:
        parts = time_str.split(":")
        if len(parts) == 2:
            mins, secs = parts
            return float(mins) * 60 + float(secs)
        elif len(parts) == 3:
            hours, mins, secs = parts
            return float(hours) * 3600 + float(mins) * 60 + float(secs)

    # Handle 1h2m30s format
    import re
    match = re.match(r"(?:(\d+)h)?(?:(\d+)m)?(?:(\d+(?:\.\d+)?)s?)?$", time_str)
    if match:
        hours = float(match.group(1) or 0)
        mins = float(match.group(2) or 0)
        secs = float(match.group(3) or 0)
        return hours * 3600 + mins * 60 + secs

    # Plain number (seconds)
    return float(time_str.rstrip("s"))


def download_as_mp3(
    url: str,
    output_dir: Path | None = None,
    quality: int = 192,
    filename: str | None = None,
    progress_callback=None,
    start_time: str | None = None,
    duration: str | None = None,
    end_time: str | None = None,
) -> Path:
    """Download a YouTube video and convert to MP3.

    Time clipping:
    - start_time: Where to start (e.g., "12", "1:30", "1m30s")
    - duration: How long to capture (e.g., "20", "20s", "1:00")
    - end_time: Where to end (alternative to duration)
    """
    if output_dir is None:
        output_dir = get_output_dir()

    output_dir = Path(output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    if filename:
        output_template = str(output_dir / f"{filename}.%(ext)s")
    else:
        output_template = str(output_dir / "%(title)s.%(ext)s")

    def progress_hook(d):
        if progress_callback and d["status"] == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate", 0)
            downloaded = d.get("downloaded_bytes", 0)
            if total > 0:
                progress_callback(downloaded, total)
        elif progress_callback and d["status"] == "finished":
            progress_callback(1, 1, finished=True)

    # Build clip timing.
    clip_info = None
    if start_time or duration or end_time:
        start_secs = parse_time(start_time) if start_time else 0
        if duration:
            end_secs = start_secs + parse_time(duration)
        elif end_time:
            end_secs = parse_time(end_time)
        else:
            end_secs = None
        if end_secs is not None and end_secs < start_secs:
            raise ValueError("end_time must be greater than or equal to start_time")
        clip_info = (start_secs, end_secs)

    ydl_opts = {
        "format": "bestaudio/best",
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": str(quality),
        }],
        "outtmpl": output_template,
        "quiet": True,
        "no_warnings": True,
        "progress_hooks": [progress_hook],
    }

    # Apply clipping at audio extraction time so output MP3 length is correct.
    if clip_info:
        start_secs, end_secs = clip_info
        ffmpeg_args: list[str] = []
        if start_secs > 0:
            ffmpeg_args.extend(["-ss", str(start_secs)])
        if end_secs is not None:
            ffmpeg_args.extend(["-t", str(end_secs - start_secs)])
        if ffmpeg_args:
            ydl_opts["postprocessor_args"] = {"extractaudio+ffmpeg_i": ffmpeg_args}

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        title = info.get("title", "download")

        if filename:
            final_path = output_dir / f"{filename}.mp3"
        else:
            safe_title = ydl.prepare_filename(info)
            final_path = Path(safe_title).with_suffix(".mp3")

    return final_path


def trim_silence(
    input_path: Path,
    output_path: Path | None = None,
    threshold_db: float = -50,
    min_silence_duration: float = 0.1,
    trim_start: bool = True,
    trim_end: bool = True,
) -> Path:
    """Remove silence from the beginning and/or end of an audio file.

    Args:
        input_path: Path to the input audio file
        output_path: Path for output file (defaults to overwriting input)
        threshold_db: Volume threshold in dB below which is considered silence (default -50dB)
        min_silence_duration: Minimum duration of silence to detect (default 0.1s)
        trim_start: Whether to trim silence from the start
        trim_end: Whether to trim silence from the end

    Returns:
        Path to the output file
    """
    import subprocess
    import tempfile

    input_path = Path(input_path).resolve()
    if output_path is None:
        output_path = input_path
    else:
        output_path = Path(output_path).resolve()

    # Build the silenceremove filter
    filters = []

    if trim_start:
        # Remove silence from start: stop after first non-silence
        filters.append(
            f"silenceremove=start_periods=1:start_duration={min_silence_duration}:start_threshold={threshold_db}dB"
        )

    if trim_end:
        # Remove silence from end: reverse, remove from "start", reverse back
        filters.append(
            f"areverse,silenceremove=start_periods=1:start_duration={min_silence_duration}:start_threshold={threshold_db}dB,areverse"
        )

    if not filters:
        return input_path

    filter_chain = ",".join(filters)

    # Use temp file if overwriting
    if output_path == input_path:
        temp_fd, temp_path = tempfile.mkstemp(suffix=".mp3")
        temp_path = Path(temp_path)
    else:
        temp_path = output_path
        output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        cmd = [
            "ffmpeg",
            "-y",
            "-i", str(input_path),
            "-af", filter_chain,
            "-acodec", "libmp3lame",
            "-q:a", "2",
            str(temp_path),
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg failed: {result.stderr}")

        # If overwriting, replace the original
        if output_path == input_path:
            import shutil
            shutil.move(str(temp_path), str(output_path))

    finally:
        # Clean up temp file if it still exists
        if output_path == input_path and temp_path.exists():
            temp_path.unlink()

    return output_path


def get_audio_duration(path: Path) -> float:
    """Get the duration of an audio file in seconds."""
    import subprocess

    result = subprocess.run(
        [
            "ffprobe",
            "-v", "quiet",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {result.stderr}")

    return float(result.stdout.strip())


def search_youtube(query: str, max_results: int = 10) -> list[dict]:
    """Search YouTube and return video info.

    Returns list of dicts with: id, title, duration, channel, url
    """
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        search_url = f"ytsearch{max_results}:{query}"
        info = ydl.extract_info(search_url, download=False)

        results = []
        for entry in info.get("entries", []):
            duration = entry.get("duration", 0)
            if duration:
                mins, secs = divmod(int(duration), 60)
                duration_str = f"{mins}:{secs:02d}"
            else:
                duration_str = "?"

            results.append({
                "id": entry.get("id"),
                "title": entry.get("title", "Unknown"),
                "duration": duration_str,
                "duration_secs": duration,
                "channel": entry.get("channel") or entry.get("uploader", "Unknown"),
                "url": entry.get("url") or f"https://youtube.com/watch?v={entry.get('id')}",
            })

        return results


def get_playlist_info(url: str) -> dict:
    """Get info about a playlist without downloading.

    Returns dict with: title, channel, count, entries (list of video info)
    """
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

        entries = []
        for entry in info.get("entries", []):
            if entry is None:
                continue
            duration = entry.get("duration", 0)
            if duration:
                mins, secs = divmod(int(duration), 60)
                duration_str = f"{mins}:{secs:02d}"
            else:
                duration_str = "?"

            entries.append({
                "id": entry.get("id"),
                "title": entry.get("title", "Unknown"),
                "duration": duration_str,
                "duration_secs": duration or 0,
                "url": entry.get("url") or f"https://youtube.com/watch?v={entry.get('id')}",
            })

        return {
            "title": info.get("title", "Unknown Playlist"),
            "channel": info.get("channel") or info.get("uploader", "Unknown"),
            "count": len(entries),
            "entries": entries,
        }


def download_playlist(
    url: str,
    output_dir: Path | None = None,
    quality: int = 192,
    max_downloads: int | None = None,
    progress_callback=None,
) -> list[Path]:
    """Download all videos from a playlist as MP3.

    Args:
        url: Playlist URL
        output_dir: Output directory
        quality: Audio quality in kbps
        max_downloads: Max number of videos to download (None = all)
        progress_callback: Called with (index, total, title, path_or_error)

    Returns:
        List of successfully downloaded file paths
    """
    if output_dir is None:
        output_dir = get_output_dir()

    output_dir = Path(output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    # First get playlist info
    playlist_info = get_playlist_info(url)
    entries = playlist_info["entries"]

    if max_downloads:
        entries = entries[:max_downloads]

    downloaded = []
    total = len(entries)

    for i, entry in enumerate(entries, 1):
        video_url = entry["url"]
        title = entry["title"]

        try:
            path = download_as_mp3(
                url=video_url,
                output_dir=output_dir,
                quality=quality,
            )
            downloaded.append(path)
            if progress_callback:
                progress_callback(i, total, title, path)
        except Exception as e:
            if progress_callback:
                progress_callback(i, total, title, e)

    return downloaded


def get_transcript_dir() -> Path:
    """Get the transcripts output directory."""
    return get_output_dir().parent / "grabbo-transcripts"


def _sanitize_path_component(name: str, max_length: int = 100) -> str:
    """Sanitize a string for use in file/directory names."""
    import re
    # Remove invalid characters
    safe = re.sub(r'[<>:"/\\|?*]', '', name)
    # Replace multiple spaces with single space
    safe = re.sub(r'\s+', ' ', safe).strip()
    # Limit length
    return safe[:max_length] if safe else "Unknown"


def download_transcript(
    url: str,
    output_dir: Path | None = None,
    language: str = "en",
    include_auto: bool = True,
    format: str = "txt",
    creator_name: str | None = None,
) -> Path | None:
    """Download transcript/captions for a YouTube video.

    Args:
        url: YouTube video URL
        output_dir: Output directory (defaults to ~/grabbo-transcripts/{creator})
        language: Preferred language code (default: en)
        include_auto: Include auto-generated captions if manual not available
        format: Output format - "txt" (plain text), "srt" (subtitles), or "json" (with timestamps)
        creator_name: Override creator name for folder organization

    Returns:
        Path to the transcript file, or None if no captions available
    """
    import tempfile
    import re

    # First, extract video info to get the title and channel
    with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True}) as ydl:
        info = ydl.extract_info(url, download=False)
        video_title = info.get("title", "transcript")
        channel = creator_name or info.get("channel") or info.get("uploader", "Unknown")

        # Sanitize for filesystem
        safe_title = _sanitize_path_component(video_title)
        safe_channel = _sanitize_path_component(channel)

    # Build output directory: base/creator/
    if output_dir is None:
        output_dir = get_transcript_dir() / safe_channel

    output_dir = Path(output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    # Download subtitles to temp dir first
    with tempfile.TemporaryDirectory() as temp_dir:
        sub_opts = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "writesubtitles": True,
            "writeautomaticsub": include_auto,
            "subtitleslangs": [language, f"{language}.*"],
            "subtitlesformat": "vtt",
            "outtmpl": f"{temp_dir}/%(id)s.%(ext)s",
        }

        with yt_dlp.YoutubeDL(sub_opts) as ydl:
            ydl.download([url])

        # Find the downloaded subtitle file
        temp_path = Path(temp_dir)
        vtt_files = list(temp_path.glob("*.vtt"))

        if not vtt_files:
            return None

        vtt_file = vtt_files[0]
        vtt_content = vtt_file.read_text(encoding="utf-8")

        # Parse and convert based on format
        if format == "txt":
            # Extract plain text, removing timestamps and formatting
            lines = []
            for line in vtt_content.split("\n"):
                # Skip WebVTT header, timestamps, and empty lines
                if line.startswith("WEBVTT") or line.startswith("Kind:") or line.startswith("Language:"):
                    continue
                if "-->" in line:
                    continue
                if line.strip() == "":
                    continue
                if re.match(r"^\d+$", line.strip()):
                    continue
                # Remove HTML-like tags
                clean_line = re.sub(r"<[^>]+>", "", line)
                if clean_line.strip():
                    lines.append(clean_line.strip())

            # Remove duplicate consecutive lines (common in auto-captions)
            deduped = []
            for line in lines:
                if not deduped or line != deduped[-1]:
                    deduped.append(line)

            content = "\n".join(deduped)
            ext = "txt"

        elif format == "srt":
            # Convert VTT to SRT format
            content = vtt_to_srt(vtt_content)
            ext = "srt"

        elif format == "json":
            # Parse into JSON with timestamps
            segments = parse_vtt_to_segments(vtt_content)
            content = json.dumps(segments, indent=2)
            ext = "json"

        else:
            raise ValueError(f"Unknown format: {format}")

        # Write to output
        output_path = output_dir / f"{safe_title}.{ext}"
        output_path.write_text(content, encoding="utf-8")

        return output_path


def vtt_to_srt(vtt_content: str) -> str:
    """Convert VTT subtitle format to SRT."""
    import re

    lines = vtt_content.split("\n")
    srt_lines = []
    counter = 1

    i = 0
    while i < len(lines):
        line = lines[i]

        # Look for timestamp lines
        if "-->" in line:
            # Convert VTT timestamp format to SRT (. -> ,)
            timestamp = line.replace(".", ",")
            # Remove any positioning info after the timestamp
            timestamp = re.sub(r" .*$", "", timestamp)

            srt_lines.append(str(counter))
            srt_lines.append(timestamp)
            counter += 1

            # Collect text lines until empty line
            i += 1
            text_lines = []
            while i < len(lines) and lines[i].strip():
                text_lines.append(re.sub(r"<[^>]+>", "", lines[i]))
                i += 1
            srt_lines.extend(text_lines)
            srt_lines.append("")
        i += 1

    return "\n".join(srt_lines)


def parse_vtt_to_segments(vtt_content: str) -> list[dict]:
    """Parse VTT content into list of segments with timestamps."""
    import re

    segments = []
    lines = vtt_content.split("\n")

    i = 0
    while i < len(lines):
        line = lines[i]

        if "-->" in line:
            # Parse timestamp
            match = re.match(r"(\d+:\d+:\d+\.\d+|\d+:\d+\.\d+)\s*-->\s*(\d+:\d+:\d+\.\d+|\d+:\d+\.\d+)", line)
            if match:
                start_str, end_str = match.groups()

                # Collect text
                i += 1
                text_lines = []
                while i < len(lines) and lines[i].strip():
                    clean = re.sub(r"<[^>]+>", "", lines[i])
                    if clean.strip():
                        text_lines.append(clean.strip())
                    i += 1

                if text_lines:
                    segments.append({
                        "start": start_str,
                        "end": end_str,
                        "text": " ".join(text_lines),
                    })
        i += 1

    return segments


def download_playlist_transcripts(
    url: str,
    output_dir: Path | None = None,
    language: str = "en",
    include_auto: bool = True,
    format: str = "txt",
    max_downloads: int | None = None,
    progress_callback=None,
) -> tuple[list[Path], Path]:
    """Download transcripts for all videos in a playlist.

    Args:
        url: Playlist URL
        output_dir: Output directory (defaults to ~/grabbo-transcripts/{creator}/{playlist})
        language: Preferred language code
        include_auto: Include auto-generated captions
        format: Output format (txt, srt, json)
        max_downloads: Max number of videos (None = all)
        progress_callback: Called with (index, total, title, path_or_error)

    Returns:
        Tuple of (list of successfully downloaded transcript paths, output directory used)
    """
    # Get playlist info first to determine folder structure
    playlist_info = get_playlist_info(url)

    # Sanitize creator and playlist names for filesystem
    creator = _sanitize_path_component(playlist_info["channel"])
    playlist_name = _sanitize_path_component(playlist_info["title"])

    # Build output directory: base/creator/playlist/
    if output_dir is None:
        output_dir = get_transcript_dir() / creator / playlist_name

    output_dir = Path(output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    entries = playlist_info["entries"]

    if max_downloads:
        entries = entries[:max_downloads]

    downloaded = []
    total = len(entries)

    for i, entry in enumerate(entries, 1):
        video_url = entry["url"]
        title = entry["title"]

        try:
            path = download_transcript(
                url=video_url,
                output_dir=output_dir,
                language=language,
                include_auto=include_auto,
                format=format,
                creator_name=playlist_info["channel"],  # Pass creator to avoid re-fetching
            )
            if path:
                downloaded.append(path)
                if progress_callback:
                    progress_callback(i, total, title, path)
            else:
                if progress_callback:
                    progress_callback(i, total, title, Exception("No captions available"))
        except Exception as e:
            if progress_callback:
                progress_callback(i, total, title, e)

    return downloaded, output_dir

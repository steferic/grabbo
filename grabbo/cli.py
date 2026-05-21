"""CLI interface for grabbo."""
import click
from pathlib import Path

from . import downloader


@click.group()
def cli():
    """Download audio, video, or transcripts from YouTube and 1800+ sites.

    \b
    Usage:
      grabbo audio <url>        # Download as MP3
      grabbo video <url>        # Download as video file
      grabbo transcript <url>   # Download captions

    Each command auto-detects playlist URLs.
    """
    pass


def _is_playlist_url(url: str) -> bool:
    return "playlist" in url.lower() or "list=" in url


@cli.command("download")
@click.argument("url")
@click.option("-o", "--output", type=click.Path(), help="Output directory for this download")
@click.option("-q", "--quality", type=click.Choice(["128", "192", "320"]), default="192", help="Audio quality in kbps")
@click.option("-n", "--name", help="Custom filename (without extension)")
@click.option("-s", "--start", "start_time", help="Start time (e.g., 12, 1:30, 1m30s)")
@click.option("-d", "--duration", help="Duration to capture (e.g., 20, 20s, 1:00)")
@click.option("-e", "--end", "end_time", help="End time (alternative to duration)")
def download(url, output, quality, name, start_time, duration, end_time):
    """Download a YouTube video as MP3 (alias for `grabbo audio`).

    \b
    Examples:
      grabbo download "URL"                    # Full video
      grabbo download "URL" -s 12 -d 20        # 20 sec starting at 0:12
      grabbo download "URL" -s 1:30 -e 2:00    # From 1:30 to 2:00
      grabbo download "URL" -s 1m30s -d 30s    # Same as above
    """
    output_dir = Path(output) if output else None
    quality_int = int(quality)

    click.echo(f"Downloading: {url}")
    click.echo(f"Quality: {quality_int} kbps")
    if start_time or duration or end_time:
        time_info = f"Clip: start={start_time or '0'}"
        if duration:
            time_info += f", duration={duration}"
        elif end_time:
            time_info += f", end={end_time}"
        click.echo(time_info)
    click.echo(f"Output: {output_dir or downloader.get_audio_dir()}")
    click.echo()

    with click.progressbar(length=100, label="Downloading") as bar:
        last_percent = [0]

        def progress_callback(downloaded, total, finished=False):
            if finished:
                bar.update(100 - last_percent[0])
            elif total > 0:
                percent = int((downloaded / total) * 100)
                delta = percent - last_percent[0]
                if delta > 0:
                    bar.update(delta)
                    last_percent[0] = percent

        try:
            result_path = downloader.download_as_mp3(
                url=url,
                output_dir=output_dir,
                quality=quality_int,
                filename=name,
                progress_callback=progress_callback,
                start_time=start_time,
                duration=duration,
                end_time=end_time,
            )
            click.echo()
            click.secho(f"Saved: {result_path}", fg="green")
        except Exception as e:
            click.echo()
            click.secho(f"Error: {e}", fg="red")
            raise SystemExit(1)


# Alias 'd' for download
@cli.command("d")
@click.argument("url")
@click.option("-o", "--output", type=click.Path(), help="Output directory for this download")
@click.option("-q", "--quality", type=click.Choice(["128", "192", "320"]), default="192", help="Audio quality in kbps")
@click.option("-n", "--name", help="Custom filename (without extension)")
@click.option("-s", "--start", "start_time", help="Start time (e.g., 12, 1:30, 1m30s)")
@click.option("-d", "--duration", help="Duration to capture (e.g., 20, 20s, 1:00)")
@click.option("-e", "--end", "end_time", help="End time (alternative to duration)")
@click.pass_context
def download_alias(ctx, url, output, quality, name, start_time, duration, end_time):
    """Shortcut for 'download' command."""
    ctx.invoke(download, url=url, output=output, quality=quality, name=name,
               start_time=start_time, duration=duration, end_time=end_time)


def _download_with_progress(label, fn, **kwargs):
    """Run a single-video download with a progress bar."""
    with click.progressbar(length=100, label=label) as bar:
        last_percent = [0]

        def progress_callback(downloaded, total, finished=False):
            if finished:
                bar.update(100 - last_percent[0])
            elif total > 0:
                percent = int((downloaded / total) * 100)
                delta = percent - last_percent[0]
                if delta > 0:
                    bar.update(delta)
                    last_percent[0] = percent

        return fn(progress_callback=progress_callback, **kwargs)


def _run_playlist(url, label, downloader_fn, **kwargs):
    """Shared playlist runner. downloader_fn is a download_playlist* function."""
    click.echo("Fetching playlist info...")
    try:
        info = downloader.get_playlist_info(url)
    except Exception as e:
        click.secho(f"Error: {e}", fg="red")
        raise SystemExit(1)

    click.echo(f"\nPlaylist: {info['title']}")
    click.echo(f"Channel: {info['channel']}")
    click.echo(f"Videos: {info['count']}")

    max_downloads = kwargs.get("max_downloads")
    entries = info["entries"]
    if max_downloads:
        entries = entries[:max_downloads]
        click.echo(f"Downloading first {max_downloads} {label}...")
    else:
        click.echo(f"Downloading {len(entries)} {label}...")

    click.echo()

    succeeded = 0
    failed = 0

    def on_progress(idx, total, title, result):
        nonlocal succeeded, failed
        if isinstance(result, Exception):
            click.echo(f"[{idx}/{total}] {title}")
            click.secho(f"  Error: {result}", fg="red")
            failed += 1
        else:
            click.echo(f"[{idx}/{total}] {title}")
            click.secho(f"  -> {result.name}", fg="green")
            succeeded += 1

    downloader_fn(url=url, progress_callback=on_progress, **kwargs)

    click.echo()
    click.echo(f"Completed: {succeeded}/{succeeded + failed} succeeded")


@cli.command("audio")
@click.argument("url")
@click.option("-o", "--output", type=click.Path(), help="Output directory")
@click.option("-q", "--quality", type=click.Choice(["128", "192", "320"]), default="192", help="Audio quality in kbps")
@click.option("-n", "--name", help="Custom filename (single video only)")
@click.option("-s", "--start", "start_time", help="Start time (e.g., 12, 1:30, 1m30s)")
@click.option("-d", "--duration", help="Duration to capture (e.g., 20, 20s, 1:00)")
@click.option("-e", "--end", "end_time", help="End time (alternative to duration)")
@click.option("-N", "--max", "max_downloads", type=int, help="Max videos when URL is a playlist")
def audio(url, output, quality, name, start_time, duration, end_time, max_downloads):
    """Download as audio (MP3). Auto-detects playlist URLs.

    \b
    Examples:
      grabbo audio "URL"                    # Single video
      grabbo audio "URL" -s 12 -d 20        # Clip 20s starting at 0:12
      grabbo audio "PLAYLIST_URL"           # Entire playlist
      grabbo audio "PLAYLIST_URL" -N 5      # First 5 of playlist
    """
    output_dir = Path(output) if output else None
    quality_int = int(quality)

    if _is_playlist_url(url):
        if start_time or duration or end_time:
            click.secho("Clip flags (-s/-d/-e) are not supported for playlists.", fg="red")
            raise SystemExit(1)
        _run_playlist(
            url,
            "videos",
            downloader.download_playlist,
            output_dir=output_dir,
            quality=quality_int,
            max_downloads=max_downloads,
        )
        return

    click.echo(f"Downloading: {url}")
    click.echo(f"Quality: {quality_int} kbps")
    if start_time or duration or end_time:
        time_info = f"Clip: start={start_time or '0'}"
        if duration:
            time_info += f", duration={duration}"
        elif end_time:
            time_info += f", end={end_time}"
        click.echo(time_info)
    click.echo(f"Output: {output_dir or downloader.get_audio_dir()}")
    click.echo()

    try:
        result_path = _download_with_progress(
            "Downloading",
            downloader.download_as_mp3,
            url=url,
            output_dir=output_dir,
            quality=quality_int,
            filename=name,
            start_time=start_time,
            duration=duration,
            end_time=end_time,
        )
        click.echo()
        click.secho(f"Saved: {result_path}", fg="green")
    except Exception as e:
        click.echo()
        click.secho(f"Error: {e}", fg="red")
        raise SystemExit(1)


@cli.command("video")
@click.argument("url")
@click.option("-o", "--output", type=click.Path(), help="Output directory")
@click.option("-r", "--resolution", type=click.Choice(["480", "720", "1080", "1440", "2160", "4320"]), help="Max vertical resolution (default: best)")
@click.option("-c", "--container", type=click.Choice(["mp4", "webm"]), default="mp4", help="Output container")
@click.option("-n", "--name", help="Custom filename (single video only)")
@click.option("-s", "--start", "start_time", help="Start time (e.g., 12, 1:30, 1m30s)")
@click.option("-d", "--duration", help="Duration to capture (e.g., 20, 20s, 1:00)")
@click.option("-e", "--end", "end_time", help="End time (alternative to duration)")
@click.option("-N", "--max", "max_downloads", type=int, help="Max videos when URL is a playlist")
def video(url, output, resolution, container, name, start_time, duration, end_time, max_downloads):
    """Download as a video file. Auto-detects playlist URLs.

    \b
    Examples:
      grabbo video "URL"                    # Best available
      grabbo video "URL" -r 720             # Cap at 720p
      grabbo video "URL" -s 1:30 -e 2:00    # Clip from 1:30 to 2:00
      grabbo video "PLAYLIST_URL" -N 5      # First 5 of playlist
    """
    output_dir = Path(output) if output else None
    resolution_int = int(resolution) if resolution else None

    if _is_playlist_url(url):
        if start_time or duration or end_time:
            click.secho("Clip flags (-s/-d/-e) are not supported for playlists.", fg="red")
            raise SystemExit(1)
        _run_playlist(
            url,
            "videos",
            downloader.download_playlist_videos,
            output_dir=output_dir,
            resolution=resolution_int,
            container=container,
            max_downloads=max_downloads,
        )
        return

    click.echo(f"Downloading: {url}")
    click.echo(f"Resolution: {resolution_int or 'best'}")
    click.echo(f"Container: {container}")
    if start_time or duration or end_time:
        time_info = f"Clip: start={start_time or '0'}"
        if duration:
            time_info += f", duration={duration}"
        elif end_time:
            time_info += f", end={end_time}"
        click.echo(time_info)
    click.echo(f"Output: {output_dir or downloader.get_video_dir()}")
    click.echo()

    try:
        result_path = _download_with_progress(
            "Downloading",
            downloader.download_as_video,
            url=url,
            output_dir=output_dir,
            resolution=resolution_int,
            container=container,
            filename=name,
            start_time=start_time,
            duration=duration,
            end_time=end_time,
        )
        click.echo()
        click.secho(f"Saved: {result_path}", fg="green")
    except Exception as e:
        click.echo()
        click.secho(f"Error: {e}", fg="red")
        raise SystemExit(1)


# Short alias 'v' for video
@cli.command("v")
@click.argument("url")
@click.option("-o", "--output", type=click.Path())
@click.option("-r", "--resolution", type=click.Choice(["480", "720", "1080", "1440", "2160", "4320"]))
@click.option("-c", "--container", type=click.Choice(["mp4", "webm"]), default="mp4")
@click.option("-n", "--name")
@click.option("-s", "--start", "start_time")
@click.option("-d", "--duration")
@click.option("-e", "--end", "end_time")
@click.option("-N", "--max", "max_downloads", type=int)
@click.pass_context
def video_alias(ctx, url, output, resolution, container, name, start_time, duration, end_time, max_downloads):
    """Shortcut for 'video' command."""
    ctx.invoke(video, url=url, output=output, resolution=resolution, container=container,
               name=name, start_time=start_time, duration=duration, end_time=end_time,
               max_downloads=max_downloads)


@cli.command("batch")
@click.argument("urls", nargs=-1)
@click.option("-f", "--file", "file_path", type=click.Path(exists=True), help="File containing URLs (one per line)")
@click.option("-o", "--output", type=click.Path(), help="Output directory for downloads")
@click.option("-q", "--quality", type=click.Choice(["128", "192", "320"]), default="192", help="Audio quality in kbps")
def batch(urls, file_path, output, quality):
    """Download multiple YouTube videos as MP3.

    Pass URLs directly or use a file:

    \b
    grabbo batch "url1" "url2" "url3"
    grabbo batch -f urls.txt
    """
    url_list = list(urls)

    if file_path:
        with open(file_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    url_list.append(line)

    if not url_list:
        click.echo("No URLs provided. Pass URLs as arguments or use -f/--file.")
        raise SystemExit(1)

    output_dir = Path(output) if output else None
    quality_int = int(quality)
    total = len(url_list)
    succeeded = []
    failed = []

    click.echo(f"Downloading {total} videos...")
    click.echo(f"Quality: {quality_int} kbps")
    click.echo(f"Output: {output_dir or downloader.get_audio_dir()}")
    click.echo()

    for i, url in enumerate(url_list, 1):
        click.echo(f"[{i}/{total}] {url}")

        try:
            result_path = downloader.download_as_mp3(
                url=url,
                output_dir=output_dir,
                quality=quality_int,
            )
            click.secho(f"  -> {result_path.name}", fg="green")
            succeeded.append(url)
        except Exception as e:
            click.secho(f"  Error: {e}", fg="red")
            failed.append((url, str(e)))

    click.echo()
    click.echo(f"Completed: {len(succeeded)}/{total} succeeded")
    if failed:
        click.secho(f"Failed ({len(failed)}):", fg="red")
        for url, err in failed:
            click.echo(f"  {url}")


@cli.command("list")
@click.option("-n", "--count", default=20, help="Number of files to show")
@click.option("-k", "--kind", type=click.Choice(["audio", "video"]), default="audio", help="Which media kind to list")
def list_files(count, kind):
    """List downloaded files for a given kind (default: audio)."""
    files = downloader.list_downloads(kind=kind)
    dir_path = downloader.get_audio_dir() if kind == "audio" else downloader.get_video_dir()

    if not files:
        click.echo(f"No {kind} files in {dir_path}")
        return

    click.echo(f"{kind.capitalize()} files in {dir_path}:\n")
    for f in files[:count]:
        click.echo(f"  {f['size_mb']:>6.1f} MB  {f['name']}")

    if len(files) > count:
        click.echo(f"\n  ... and {len(files) - count} more files")


@cli.command("set-dir")
@click.argument("path", type=click.Path())
def set_dir(path):
    """Set the default output directory."""
    path = Path(path).expanduser().resolve()
    downloader.set_output_dir(path)
    click.secho(f"Output directory set to: {path}", fg="green")


@cli.command("config")
def show_config():
    """Show current configuration."""
    base_dir = downloader.get_output_dir()
    click.echo(f"Base directory: {base_dir}")
    click.echo()

    for kind in ("audio", "video"):
        files = downloader.list_downloads(kind=kind)
        total_size = sum(f["size_mb"] for f in files)
        sub = base_dir / kind
        click.echo(f"  {kind:<11} {len(files):>4} files  {total_size:>7.1f} MB  ({sub})")

    transcripts_dir = downloader.get_transcript_dir()
    if transcripts_dir.exists():
        transcript_count = sum(1 for _ in transcripts_dir.rglob("*.*"))
    else:
        transcript_count = 0
    click.echo(f"  {'transcripts':<11} {transcript_count:>4} files            ({transcripts_dir})")


@cli.command("open")
def open_dir():
    """Open the output directory in Finder."""
    import subprocess
    output_dir = downloader.get_output_dir()
    subprocess.run(["open", str(output_dir)])
    click.echo(f"Opened: {output_dir}")


@cli.command("watch")
@click.option("-q", "--quality", type=click.Choice(["128", "192", "320"]), default="192", help="Audio quality in kbps")
@click.option("-o", "--output", type=click.Path(), help="Output directory")
@click.option("-y", "--yes", is_flag=True, help="Auto-download without prompting")
@click.option("-i", "--interval", default=1.0, help="Clipboard check interval in seconds")
def watch(quality, output, yes, interval):
    """Watch clipboard for YouTube URLs and auto-download.

    \b
    Run this in a terminal, then copy any YouTube URL.
    The tool will detect it and prompt you to download.

    \b
    Examples:
      grabbo watch              # Interactive mode
      grabbo watch -y           # Auto-download without prompts
      grabbo watch -q 320 -y    # Auto-download at 320kbps
    """
    from . import watcher

    output_dir = Path(output) if output else None
    quality_int = int(quality)

    click.echo("Watching clipboard for YouTube URLs...")
    click.echo(f"Quality: {quality_int} kbps")
    click.echo(f"Output: {output_dir or downloader.get_audio_dir()}")
    if yes:
        click.echo("Auto-download: ON")
    click.echo("Press Ctrl+C to stop.\n")

    def on_url_detected(url):
        click.echo(f"\nDetected: {url}")

        if not yes:
            if not click.confirm("Download?", default=True):
                click.echo("Skipped.")
                return

        click.echo("Downloading...")
        try:
            result_path = downloader.download_as_mp3(
                url=url,
                output_dir=output_dir,
                quality=quality_int,
            )
            click.secho(f"Saved: {result_path}", fg="green")
        except Exception as e:
            click.secho(f"Error: {e}", fg="red")

        click.echo("\nWatching...")

    try:
        watcher.watch_clipboard(on_url_detected, interval=interval)
    except KeyboardInterrupt:
        click.echo("\nStopped watching.")


@cli.command("search")
@click.argument("query", nargs=-1, required=True)
@click.option("-n", "--count", default=10, help="Number of results (default: 10)")
@click.option("-d", "--download", "download_idx", type=int, help="Download result by number")
@click.option("-q", "--quality", type=click.Choice(["128", "192", "320"]), default="192", help="Audio quality")
def search(query, count, download_idx, quality):
    """Search YouTube and optionally download.

    \b
    Examples:
      grabbo search "lofi hip hop"           # Search and show results
      grabbo search "song name" -d 1         # Download first result
      grabbo search "artist song" -d 1 -q 320
    """
    query_str = " ".join(query)
    click.echo(f"Searching: {query_str}...")

    try:
        results = downloader.search_youtube(query_str, max_results=count)
    except Exception as e:
        click.secho(f"Error: {e}", fg="red")
        raise SystemExit(1)

    if not results:
        click.echo("No results found.")
        return

    click.echo()
    for i, r in enumerate(results, 1):
        click.echo(f"  {i:2}. [{r['duration']:>5}] {r['title']}")
        click.echo(f"      {r['channel']}")

    if download_idx:
        if download_idx < 1 or download_idx > len(results):
            click.secho(f"Invalid selection: {download_idx}", fg="red")
            raise SystemExit(1)

        selected = results[download_idx - 1]
        click.echo()
        click.echo(f"Downloading: {selected['title']}")

        try:
            result_path = downloader.download_as_mp3(
                url=selected["url"],
                quality=int(quality),
            )
            click.secho(f"Saved: {result_path}", fg="green")
        except Exception as e:
            click.secho(f"Error: {e}", fg="red")
            raise SystemExit(1)
    else:
        click.echo()
        click.echo("Use -d N to download a result, e.g.: grabbo search \"query\" -d 1")


@cli.command("playlist")
@click.argument("url")
@click.option("-o", "--output", type=click.Path(), help="Output directory")
@click.option("-q", "--quality", type=click.Choice(["128", "192", "320"]), default="192", help="Audio quality")
@click.option("-n", "--max", "max_downloads", type=int, help="Max videos to download")
@click.option("--info", "info_only", is_flag=True, help="Show playlist info without downloading")
def playlist(url, output, quality, max_downloads, info_only):
    """Download an entire YouTube playlist as MP3.

    \b
    Note: `grabbo audio PLAYLIST_URL` and `grabbo video PLAYLIST_URL`
    now auto-detect playlists too. This command stays for back-compat
    and the --info preview.

    \b
    Examples:
      grabbo playlist "URL"              # Download entire playlist
      grabbo playlist "URL" -n 5         # Download first 5 videos
      grabbo playlist "URL" --info       # Just show playlist contents
    """
    click.echo("Fetching playlist info...")

    try:
        info = downloader.get_playlist_info(url)
    except Exception as e:
        click.secho(f"Error: {e}", fg="red")
        raise SystemExit(1)

    click.echo(f"\nPlaylist: {info['title']}")
    click.echo(f"Channel: {info['channel']}")
    click.echo(f"Videos: {info['count']}")

    if info_only:
        click.echo()
        for i, entry in enumerate(info["entries"], 1):
            click.echo(f"  {i:3}. [{entry['duration']:>5}] {entry['title']}")
        return

    entries = info["entries"]
    if max_downloads:
        entries = entries[:max_downloads]
        click.echo(f"Downloading first {max_downloads} videos...")
    else:
        click.echo(f"Downloading {len(entries)} videos...")

    click.echo()

    output_dir = Path(output) if output else None
    quality_int = int(quality)
    succeeded = 0
    failed = 0

    def on_progress(idx, total, title, result):
        nonlocal succeeded, failed
        if isinstance(result, Exception):
            click.echo(f"[{idx}/{total}] {title}")
            click.secho(f"  Error: {result}", fg="red")
            failed += 1
        else:
            click.echo(f"[{idx}/{total}] {title}")
            click.secho(f"  -> {result.name}", fg="green")
            succeeded += 1

    downloader.download_playlist(
        url=url,
        output_dir=output_dir,
        quality=quality_int,
        max_downloads=max_downloads,
        progress_callback=on_progress,
    )

    click.echo()
    click.echo(f"Completed: {succeeded}/{succeeded + failed} succeeded")


@cli.command("trim")
@click.argument("file", type=click.Path(exists=True), required=False)
@click.option("--all", "trim_all", is_flag=True, help="Trim all files in the output directory")
@click.option("--start/--no-start", default=True, help="Trim silence from start (default: yes)")
@click.option("--end/--no-end", default=True, help="Trim silence from end (default: yes)")
@click.option("-t", "--threshold", default=-50, help="Silence threshold in dB (default: -50)")
def trim(file, trim_all, start, end, threshold):
    """Remove silence from the beginning/end of MP3 files.

    \b
    Examples:
      grabbo trim "song.mp3"           # Trim a specific file
      grabbo trim --all                # Trim all files in output dir
      grabbo trim song.mp3 --no-end    # Only trim start
      grabbo trim song.mp3 -t -40      # More aggressive threshold
    """
    if not file and not trim_all:
        click.echo("Specify a file or use --all to trim all files.")
        raise SystemExit(1)

    files_to_trim = []

    if trim_all:
        output_dir = downloader.get_audio_dir()
        files_to_trim = list(output_dir.glob("*.mp3"))
        if not files_to_trim:
            click.echo(f"No MP3 files found in {output_dir}")
            return
        click.echo(f"Trimming {len(files_to_trim)} files in {output_dir}...")
    else:
        files_to_trim = [Path(file)]

    for mp3_path in files_to_trim:
        try:
            before_duration = downloader.get_audio_duration(mp3_path)

            click.echo(f"Trimming: {mp3_path.name}...", nl=False)
            downloader.trim_silence(
                mp3_path,
                threshold_db=threshold,
                trim_start=start,
                trim_end=end,
            )

            after_duration = downloader.get_audio_duration(mp3_path)
            saved = before_duration - after_duration

            if saved > 0.1:
                click.secho(f" removed {saved:.1f}s", fg="green")
            else:
                click.echo(" no silence found")

        except Exception as e:
            click.secho(f" error: {e}", fg="red")


@cli.command("transcript")
@click.argument("url")
@click.option("-o", "--output", type=click.Path(), help="Output directory")
@click.option("-l", "--lang", default="en", help="Language code (default: en)")
@click.option("-f", "--format", "fmt", type=click.Choice(["txt", "srt", "json"]), default="txt", help="Output format")
@click.option("--no-auto", is_flag=True, help="Skip auto-generated captions")
@click.option("-n", "--max", "max_downloads", type=int, help="Max videos for playlist")
@click.option("--info", "info_only", is_flag=True, help="Show playlist info without downloading")
def transcript(url, output, lang, fmt, no_auto, max_downloads, info_only):
    """Download transcript/captions for a video or playlist.

    \b
    Downloads captions only (no audio).
    Saves to ~/grabbo/transcripts/{creator}/{playlist}/ by default.

    \b
    Examples:
      grabbo transcript "URL"                    # Download as plain text
      grabbo transcript "URL" -f srt             # Download as SRT subtitles
      grabbo transcript "URL" -f json            # Download with timestamps
      grabbo transcript "PLAYLIST_URL" -n 10    # First 10 videos from playlist
    """
    output_dir = Path(output) if output else None
    include_auto = not no_auto

    # Check if it's a playlist
    is_playlist = "playlist" in url.lower() or "list=" in url

    if is_playlist:
        click.echo("Fetching playlist info...")
        try:
            info = downloader.get_playlist_info(url)
        except Exception as e:
            click.secho(f"Error: {e}", fg="red")
            raise SystemExit(1)

        click.echo(f"\nPlaylist: {info['title']}")
        click.echo(f"Channel: {info['channel']}")
        click.echo(f"Videos: {info['count']}")

        if info_only:
            click.echo()
            for i, entry in enumerate(info["entries"], 1):
                click.echo(f"  {i:3}. [{entry['duration']:>5}] {entry['title']}")
            return

        entries = info["entries"]
        if max_downloads:
            entries = entries[:max_downloads]
            click.echo(f"Downloading first {max_downloads} transcripts...")
        else:
            click.echo(f"Downloading {len(entries)} transcripts...")

        click.echo(f"Format: {fmt}")
        click.echo()

        succeeded = 0
        failed = 0

        def on_progress(idx, total, title, result):
            nonlocal succeeded, failed
            if isinstance(result, Exception):
                click.echo(f"[{idx}/{total}] {title}")
                click.secho(f"  Error: {result}", fg="red")
                failed += 1
            else:
                click.echo(f"[{idx}/{total}] {title}")
                click.secho(f"  -> {result.name}", fg="green")
                succeeded += 1

        _, actual_output_dir = downloader.download_playlist_transcripts(
            url=url,
            output_dir=output_dir,
            language=lang,
            include_auto=include_auto,
            format=fmt,
            max_downloads=max_downloads,
            progress_callback=on_progress,
        )

        click.echo()
        click.echo(f"Completed: {succeeded}/{succeeded + failed} succeeded")
        click.echo(f"Output: {actual_output_dir}")

    else:
        # Single video
        click.echo(f"Downloading transcript: {url}")
        click.echo(f"Format: {fmt}")
        click.echo()

        try:
            result_path = downloader.download_transcript(
                url=url,
                output_dir=output_dir,
                language=lang,
                include_auto=include_auto,
                format=fmt,
            )
            if result_path:
                click.secho(f"Saved: {result_path}", fg="green")
            else:
                click.secho("No captions available for this video.", fg="yellow")
        except Exception as e:
            click.secho(f"Error: {e}", fg="red")
            raise SystemExit(1)


# Alias 't' for transcript
@cli.command("t")
@click.argument("url")
@click.option("-o", "--output", type=click.Path(), help="Output directory")
@click.option("-l", "--lang", default="en", help="Language code (default: en)")
@click.option("-f", "--format", "fmt", type=click.Choice(["txt", "srt", "json"]), default="txt", help="Output format")
@click.option("--no-auto", is_flag=True, help="Skip auto-generated captions")
@click.option("-n", "--max", "max_downloads", type=int, help="Max videos for playlist")
@click.option("--info", "info_only", is_flag=True, help="Show playlist info without downloading")
@click.pass_context
def transcript_alias(ctx, url, output, lang, fmt, no_auto, max_downloads, info_only):
    """Shortcut for 'transcript' command."""
    ctx.invoke(transcript, url=url, output=output, lang=lang, fmt=fmt,
               no_auto=no_auto, max_downloads=max_downloads, info_only=info_only)


if __name__ == "__main__":
    cli()

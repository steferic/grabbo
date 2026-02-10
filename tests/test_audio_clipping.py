from pathlib import Path
import shutil
import subprocess

import pytest
import yt_dlp

import grabbo.downloader as downloader


def _make_sine_video(path: Path, duration_secs: int = 8) -> None:
    subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency=1000:duration={duration_secs}",
            "-c:a",
            "aac",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )


@pytest.mark.skipif(
    shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None,
    reason="ffmpeg/ffprobe required for audio clipping integration test",
)
def test_download_as_mp3_respects_start_and_duration(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source_video = tmp_path / "input.mp4"
    _make_sine_video(source_video, duration_secs=8)

    class LocalFileYoutubeDL(yt_dlp.YoutubeDL):
        def __init__(self, params=None, *args, **kwargs):
            params = dict(params or {})
            params["enable_file_urls"] = True
            super().__init__(params, *args, **kwargs)

    monkeypatch.setattr(downloader.yt_dlp, "YoutubeDL", LocalFileYoutubeDL)

    output_path = downloader.download_as_mp3(
        url=source_video.as_uri(),
        output_dir=tmp_path,
        filename="clipped",
        start_time="2",
        duration="3",
    )

    assert output_path.exists()
    clipped_duration = downloader.get_audio_duration(output_path)
    assert clipped_duration == pytest.approx(3.0, abs=0.35)

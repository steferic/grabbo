import grabbo.downloader as downloader


def _track(lang: str, tlang: str | None = None) -> list[dict]:
    url = f"https://www.youtube.com/api/timedtext?v=x&lang={lang}&fmt=vtt"
    if tlang:
        url += f"&tlang={tlang}"
    return [{"ext": "vtt", "url": url}]


def test_dubbed_video_prefers_original_over_translated_auto_captions() -> None:
    info = {
        "subtitles": {},
        "automatic_captions": {
            "en": _track("es-US", tlang="en"),
            "en-orig": _track("en"),
            "es-US": _track("es-US"),
            "en-GB": _track("en"),
        },
    }

    assert downloader._caption_candidates(info, "en", include_auto=True) == [
        ("en-orig", True),
        ("en-GB", True),
        ("en", True),
    ]


def test_manual_captions_come_first_and_no_auto_skips_auto() -> None:
    info = {
        "subtitles": {"en-US": _track("en"), "en": _track("en"), "live_chat": []},
        "automatic_captions": {"en-orig": _track("en")},
    }

    assert downloader._caption_candidates(info, "en", include_auto=False) == [
        ("en", False),
        ("en-US", False),
    ]
    assert downloader._caption_candidates(info, "en", include_auto=True)[-1] == ("en-orig", True)

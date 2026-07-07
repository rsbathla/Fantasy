#!/usr/bin/env python3
"""brain_video.py — download a YouTube/podcast link, transcribe it with Whisper, and write a
source note into the Obsidian vault with the transcript, timestamps, and detected player/team links.

Runs on the user's Mac (needs network + ffmpeg + yt-dlp + faster-whisper — see setup_brain_mac.sh).
Idempotent: a URL already in the vault manifest is skipped.

  python3 brain_video.py <url> --vault ~/Downloads/NFL-Brain [--model small.en]

Only YouTube / podcast (public) links to start — no X-native video (that needs login).
"""
import argparse
import glob
import html
import json
import os
import sys
import tempfile

import brain_common as bc


class BotFlag(Exception):
    """YouTube flagged the IP as a bot. youtube-transcript discipline: STOP, never retry in a loop."""


def _is_bot_flag(err):
    m = str(err).lower()
    return ("sign in to confirm you're not a bot" in m
            or "http error 429" in m or "too many requests" in m)


class Seg:
    """Lightweight transcript segment (mirrors faster-whisper's .start/.text) for the captions path."""
    __slots__ = ("start", "text")

    def __init__(self, start, text):
        self.start = start
        self.text = text


def fmt_ts(sec):
    m, s = divmod(int(sec), 60)
    h, m = divmod(m, 60)
    return f"{h:d}:{m:02d}:{s:02d}" if h else f"{m:d}:{s:02d}"


def fetch_captions(url, workdir):
    """Captions-first: grab the video's OWN subtitles as json3 so we skip the slow audio+whisper path.
    json3 ONLY (never VTT/SRT — auto VTT double-prints every line as rolling captions). Returns
    (segments, info); segments is None when there are no usable captions. Raises BotFlag on IP flag."""
    import yt_dlp
    opts = {
        "skip_download": True,
        "writesubtitles": True, "writeautomaticsub": True,
        "subtitlesformat": "json3", "subtitleslangs": ["en.*"],
        "outtmpl": os.path.join(workdir, "%(id)s.%(ext)s"),
        "quiet": True, "no_warnings": True, "noplaylist": True,
        "extractor_args": {"youtube": {"player_client": ["tv", "web_safari", "ios", "android"]}},
    }
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
    except Exception as e:
        if _is_bot_flag(e):
            raise BotFlag(str(e))
        return None, None
    files = sorted(glob.glob(os.path.join(workdir, f"{info['id']}*.json3")))
    if not files:
        return None, info
    return (_parse_json3(files[0]) or None), info


def _parse_json3(path):
    """Flatten a YouTube json3 caption file into timed segments (keeps start times for the notes)."""
    try:
        data = json.load(open(path, encoding="utf-8"))
    except Exception:
        return []
    segs = []
    for e in data.get("events", []):
        txt = "".join(s.get("utf8", "") for s in (e.get("segs") or [])).strip()
        if txt:
            segs.append(Seg((e.get("tStartMs") or 0) / 1000.0, html.unescape(txt)))
    return segs


def download_audio(url, workdir):
    import yt_dlp
    base = {
        "format": "bestaudio/best",
        "outtmpl": os.path.join(workdir, "%(id)s.%(ext)s"),
        "quiet": True, "no_warnings": True, "noplaylist": True,
        "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "m4a"}],
        # alternative player clients bypass most of YouTube's "page needs to be reloaded" bot-wall
        "extractor_args": {"youtube": {"player_client": ["tv", "web_safari", "ios", "android"]}},
    }
    # try clean first; then reuse the browser's YouTube login as a fallback
    configs = [base, {**base, "cookiesfrombrowser": ("chrome",)}]
    last = None
    for cfg in configs:
        try:
            with yt_dlp.YoutubeDL(cfg) as ydl:
                info = ydl.extract_info(url, download=True)
            audio = glob.glob(os.path.join(workdir, f"{info['id']}.*"))
            audio = [a for a in audio if a.rsplit(".", 1)[-1] in ("m4a", "mp3", "webm", "opus", "wav")]
            if audio:
                return audio[0], info
        except Exception as e:
            last = e
            if _is_bot_flag(e):
                raise BotFlag(str(e))      # STOP on a bot flag — do not try more configs / loop
    raise last or RuntimeError("yt-dlp produced no audio")


def transcribe(audio_path, model_name):
    from faster_whisper import WhisperModel
    model = WhisperModel(model_name, device="cpu", compute_type="int8")
    segments, info = model.transcribe(audio_path, vad_filter=True, beam_size=1)
    return list(segments), info


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("--vault", required=True)
    ap.add_argument("--repo", default=None)
    ap.add_argument("--model", default="small.en", help="faster-whisper model (tiny/base/small.en/medium)")
    ap.add_argument("--source", default=None, help="analyst/show name for provenance (defaults to the channel)")
    ap.add_argument("--star", action="store_true", help="mark as a curated hand-pick (#curated)")
    ap.add_argument("--force", action="store_true", help="re-ingest even if already in the manifest")
    a = ap.parse_args()
    vault = os.path.expanduser(a.vault)
    repo = bc.repo_root(a.repo)

    if bc.already_done(vault, a.url) and not a.force:
        bc.log(f"SKIP (already ingested): {a.url}")
        return 0
    if a.force and bc.already_done(vault, a.url):
        bc.log(f"re-ingesting (forced): {a.url}")

    src_kind = "captions"
    try:
        with tempfile.TemporaryDirectory() as wd:
            bc.log(f"fetching captions … {a.url}")
            segs, info = fetch_captions(a.url, wd)
            if not segs:                                   # no captions -> fall back to audio + whisper
                bc.log("no captions — falling back to audio + whisper (slow)")
                audio, info2 = download_audio(a.url, wd)
                info = info or info2
                dur0 = (info.get("duration") if info else 0) or 0
                bc.log(f"transcribing ({fmt_ts(dur0)}) with {a.model} … this is the slow step")
                segs, _ = transcribe(audio, a.model)
                src_kind = f"whisper:{a.model}"
            info = info or {}
    except BotFlag as e:
        bc.log(f"BOT-FLAG on {a.url}: {e}\n  STOP — not retrying (retrying only deepens the IP flag). "
               f"Try later or from another network.")
        return 2
    except Exception as e:
        bc.log(f"ERROR on {a.url}: {e}")
        return 1

    title = info.get("title") or "Untitled video"
    channel = info.get("uploader") or info.get("channel") or info.get("uploader_id") or ""
    dur = info.get("duration") or 0
    up = info.get("upload_date") or ""
    date = f"{up[:4]}-{up[4:6]}-{up[6:8]}" if len(up) == 8 else bc.now_utc().strftime("%Y-%m-%d")

    full_text = " ".join(s.text.strip() for s in segs)
    players, teams, coaches = bc.detect_entities(title + " " + full_text, repo)
    mentions = players + coaches + teams

    body = [f"[{fmt_ts(s.start)}] {s.text.strip()}" for s in segs]
    fname = f"{date} {bc.slug(title)} (video).md"
    content = f"""---
type: video
title: "{title.replace('"', "'")}"
channel: "{channel}"
analyst: "{(a.source or channel).replace('"', "'")}"
url: {a.url}
date: {date}
duration_min: {round(dur/60, 1)}
asr_model: {a.model}
transcript_source: {src_kind}
curated: {str(a.star).lower()}
mentions: [{bc.wikilinks(mentions)}]
tags: [source/video{', curated' if a.star else ', auto'}]
status: {'starred' if a.star else 'analyst-take'}
ingested: {bc.now_utc().isoformat(timespec='seconds')}
---

# {title}{'  ⭐' if a.star else ''}

> [!info] Source video · {channel} · {fmt_ts(dur)} · {'captions (json3)' if src_kind == 'captions' else f'Whisper ({a.model})'}{'  · ⭐ curated pick' if a.star else ''}
> {a.url}

**Mentions:** {', '.join(f'[[{m}]]' for m in mentions) if mentions else '_none detected_'}

## Claims → (review queue)
_Auto-extraction (injury / role / usage / scheme dims) runs in `brain_link.py`. Until then, skim the
transcript below and promote anything worth keeping into the mentioned players' `## Intel log`._

## Transcript
{os.linesep.join(body)}
"""
    rel = bc.write_note(vault, "Sources", fname, content)
    bc.mark_done(vault, a.url, rel)
    bc.log(f"OK → {rel}  ({len(segs)} segments, mentions: {', '.join(mentions) or 'none'})")
    return 0


if __name__ == "__main__":
    sys.exit(main())

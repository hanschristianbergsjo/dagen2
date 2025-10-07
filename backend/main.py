from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from pathlib import Path
import os
import tempfile

from .dagen_video_simple import (
    fetch_article_text,
    summarise_text,
    generate_audio_elevenlabs,
    generate_srt,
    create_video,
    BrandConfig,
    Scene,
)

app = FastAPI(title="Dagen Reels API", description="Convert Dagen articles into video reels")

class ConvertResponse(BaseModel):
    """
    Backwards compatibility response model.  When the API is called with
    ``format=json``, the endpoint will return a JSON object containing
    the original URL and the summarised scene texts.  Otherwise, it
    returns a video file.
    """

    url: str
    scenes: list[str]


@app.get('/convert')
async def convert(url: str, format: str = "mp4"):
    """
    Convert a Dagen article to a reel video or return summarised scenes.

    By default this endpoint downloads the article, summarises it into
    scenes, synthesises speech via ElevenLabs, generates subtitles, and
    composes a vertical video with Dagen branding.  The resulting MP4
    is returned as a file attachment.

    If the ``format`` query parameter is set to ``json``, the
    endpoint will instead return a JSON object containing the input
    URL and the scene texts without generating audio or video.  This
    is useful for debugging or when the environment lacks moviepy
    support.
    """
    try:
        article = fetch_article_text(url)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch article: {e}")

    scene_texts = summarise_text(article, max_scenes=5)
    # If JSON requested, return early without generating media
    if format.lower() == "json":
        return ConvertResponse(url=url, scenes=scene_texts)

    # Otherwise generate audio, subtitles and video in a temporary directory
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            scenes: list[Scene] = []
            audio_dir = os.path.join(tmpdir, "audio")
            os.makedirs(audio_dir, exist_ok=True)
            for idx, text in enumerate(scene_texts, 1):
                audio_path, duration = generate_audio_elevenlabs(text, idx, audio_dir)
                scenes.append(Scene(text=text, audio_path=audio_path, duration=duration))
            # Create subtitles
            srt_path = os.path.join(tmpdir, "subs.srt")
            generate_srt(scenes, srt_path)
            # Assemble video
            brand = BrandConfig()
            video_path = os.path.join(tmpdir, "reel.mp4")
            create_video(scenes, brand, video_path)
            return FileResponse(video_path, media_type="video/mp4", filename="reel.mp4")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate video: {e}")

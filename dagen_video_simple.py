from dataclasses import dataclass
from typing import List
import requests
from bs4 import BeautifulSoup
import textwrap, tempfile, os
from moviepy.editor import AudioFileClip, AudioClip, concatenate_audioclips, ColorClip
import numpy as np
import pysrt

@dataclass
class Scene:
    text: str
    audio_path: str
    duration: float

@dataclass
class BrandConfig:
    primary_color: str = "#005BB7"
    secondary_color: str = "#E5E5E5"
    accent_color: str = "#FF6600"
    font: str = "Merriweather"

def fetch_article_text(url: str) -> str:
    resp = requests.get(url)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    paragraphs = soup.find_all(["p"])
    return "\n".join(p.get_text().strip() for p in paragraphs)

def summarise_text(article: str, max_scenes: int = 5) -> List[str]:
    paragraphs = [p.strip() for p in article.split("\n") if p.strip()]
    if not paragraphs:
        return []
    n = min(max_scenes, len(paragraphs))
    step = len(paragraphs) / n
    return [paragraphs[int(i * step)] for i in range(n)]

def generate_audio_elevenlabs(text: str, api_key: str, voice_id="21m00Tcm4TlvDq8ikWAM", model_id="eleven_multilingual_v2"):
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {"xi-api-key": api_key, "Content-Type": "application/json"}
    payload = {"text": text, "model_id": model_id}
    try:
        r = requests.post(url, headers=headers, json=payload)
        r.raise_for_status()
        audio_bytes = r.content
        suffix = ".mp3"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as f:
            f.write(audio_bytes)
            audio_path = f.name
        clip = AudioFileClip(audio_path)
        duration = clip.duration
        clip.close()
        return audio_path, duration
    except Exception:
        # fallback to silence if API fails
        duration = max(2.0, len(text) / 15.0)
        silence = AudioClip(lambda t: 0, duration=duration, fps=44100)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
            silence.write_audiofile(f.name, fps=44100)
            audio_path = f.name
        silence.close()
        return audio_path, duration

def generate_srt(scene_texts: List[str], audio_paths: List[str]) -> str:
    subs = pysrt.SubRipFile()
    t0 = 0.0
    for idx, (txt, audio_path) in enumerate(zip(scene_texts, audio_paths), start=1):
        clip = AudioFileClip(audio_path)
        duration = clip.duration
        clip.close()
        line_text = "\n".join(textwrap.wrap(txt, width=30))
        subs.append(pysrt.SubRipItem(index=idx, start=pysrt.SubRipTime(seconds=t0),
                                     end=pysrt.SubRipTime(seconds=t0 + duration), text=line_text))
        t0 += duration
    srt_path = os.path.join(tempfile.gettempdir(), "subtitles.srt")
    subs.save(srt_path, encoding="utf-8")
    return srt_path

def hex_to_rgb(color: str):
    color = color.lstrip("#")
    return tuple(int(color[i:i+2], 16) for i in (0, 2, 4))

def create_video(scene_texts: List[str], audio_paths: List[str], srt_path: str, brand: BrandConfig, output_path: str) -> str:
    audio_clips = [AudioFileClip(p) for p in audio_paths]
    composite_audio = concatenate_audioclips(audio_clips)
    total_duration = composite_audio.duration
    bg_color = hex_to_rgb(brand.secondary_color)
    video = ColorClip(size=(1080, 1920), color=bg_color, duration=total_duration)
    video = video.set_audio(composite_audio)
    video.write_videofile(output_path, fps=30, codec="libx264", audio_codec="aac")
    composite_audio.close()
    for clip in audio_clips:
        clip.close()
    return output_path

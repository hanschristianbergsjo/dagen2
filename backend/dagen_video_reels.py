from dataclasses import dataclass
from typing import List
from bs4 import BeautifulSoup
import requests
import textwrap
from moviepy.editor import AudioFileClip, ColorClip, TextClip, CompositeVideoClip, CompositeAudioClip, AudioClip
import numpy as np
import pysrt
import os
import tempfile

@dataclass
class Scene:
    title: str
    bullet_points: List[str]
    audio_filename: str = ""
    duration: float = 0.0

@dataclass
class BrandConfig:
    font_family: str = "Merriweather"
    bg_color: str = "#005bb7"  # primary color
    text_color: str = "#ffffff"
    bullet_color: str = "#f06292"

def fetch_article_text(url: str) -> str:
    """
    Fetch the article text from a given URL.
    """
    resp = requests.get(url)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    return soup.get_text(separator="\n")

def summarise_text(text: str) -> List[Scene]:
    """
    Very simple summariser: split the article into paragraphs and create scenes.
    """
    paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
    scenes: List[Scene] = []
    for i, para in enumerate(paragraphs[:4]):
        title = para[:80]
        bullets = textwrap.wrap(para, width=60)
        scenes.append(Scene(title=title, bullet_points=bullets))
    return scenes

def generate_audio_elevenlabs(scene: Scene, api_key: str, voice_id: str = "21m00Tcm4TlvDq8ikWAM") -> Scene:
    """
    Generate speech audio for a scene using ElevenLabs.
    If the API key is not provided, generate silent audio as fallback.
    """
    # fallback to silent audio if no key
    if not api_key:
        duration = max(3.0, sum(len(bp.split()) for bp in scene.bullet_points) / 2.0)
        fps = 44100
        silent = AudioClip(lambda t: 0*t, duration=duration, fps=fps)
        fd, tmp_wav = tempfile.mkstemp(suffix=".wav")
        os.close(fd)
        silent.write_audiofile(tmp_wav, fps=fps, nbytes=2, codec="pcm_s16le")
        scene.audio_filename = tmp_wav
        scene.duration = duration
        return scene
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json"
    }
    text_to_speak = " ".join(scene.bullet_points)
    body = {"text": text_to_speak, "model_id": "eleven_multilingual_v2"}
    response = requests.post(url, headers=headers, json=body)
    response.raise_for_status()
    fd, tmp_mp3 = tempfile.mkstemp(suffix=".mp3")
    os.close(fd)
    with open(tmp_mp3, "wb") as f:
        f.write(response.content)
    audio_clip = AudioFileClip(tmp_mp3)
    scene.audio_filename = tmp_mp3
    scene.duration = audio_clip.duration
    audio_clip.close()
    return scene

def generate_srt(scenes: List[Scene], srt_path: str) -> None:
    """
    Generate an SRT subtitle file for the list of scenes.
    """
    subs = pysrt.SubRipFile()
    current = 0.0
    for i, scene in enumerate(scenes, 1):
        start = current
        end = current + scene.duration
        text = "\n".join(scene.bullet_points)
        subs.append(pysrt.SubRipItem(
            index=i,
            start=pysrt.SubRipTime(seconds=start),
            end=pysrt.SubRipTime(seconds=end),
            text=text
        ))
        current = end
    subs.save(srt_path, encoding="utf-8")

def hex_to_rgb(hex_color: str):
    """
    Convert a hex color code to an RGB tuple.
    """
    hex_color = hex_color.lstrip("#")
    lv = len(hex_color)
    return tuple(int(hex_color[i:i+lv//3], 16) for i in range(0, lv, lv//3))

def create_video(scenes: List[Scene], output_path: str, brand: BrandConfig, fps: int = 30):
    """
    Create a vertical video combining scenes with text overlays and audio.
    """
    width, height = 1080, 1920
    total_duration = sum(scene.duration for scene in scenes)
    bg_color = hex_to_rgb(brand.bg_color)
    video = ColorClip(size=(width, height), color=bg_color, duration=total_duration)

    # build the audio track by concatenating scene audios
    audio_clips = [AudioFileClip(scene.audio_filename) for scene in scenes]
    audio = CompositeAudioClip(audio_clips)
    video = video.set_audio(audio)

    # overlay text for each scene
    clips = [video]
    current = 0.0
    for scene in scenes:
        text_content = "\n".join(scene.bullet_points)
        txt_clip = TextClip(
            text_content,
            fontsize=48,
            font=brand.font_family,
            color=brand.text_color,
            size=(int(width*0.8), None),
            method="caption"
        )
        txt_clip = txt_clip.set_position(("center", "center")).set_start(current).set_duration(scene.duration)
        clips.append(txt_clip)
        current += scene.duration

    final_clip = CompositeVideoClip(clips)
    final_clip.write_videofile(output_path, fps=fps, codec="libx264", audio_codec="aac")

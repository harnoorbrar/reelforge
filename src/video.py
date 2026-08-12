"""Video assembly with moviepy (v2 API) + ffmpeg.

Pipeline: one ImageClip per scene -> Ken-Burns zoom/pan -> caption overlay
(bold, with soft shadow) -> hard-cut -> set to the generated voiceover audio
-> fade in/out music bed. Output is a 1080x1920 (9:16) .mp4 ready for
TikTok / Reels / Shorts.
"""
from pathlib import Path

from moviepy import (
    ImageClip, AudioFileClip, TextClip, CompositeVideoClip,
    ColorClip, concatenate_videoclips, vfx,
)
from .config import VIDEO_W, VIDEO_H, STATIC_DIR

ASSETS = Path(__file__).resolve().parent / "assets"
FONT_BOLD = str(ASSETS / "Roboto-Bold.ttf")
FONT_REGULAR = str(ASSETS / "Roboto-Regular.ttf")
# 100% royalty-free, no attribution. Replace with your own for branding.
MUSIC_URL = (
    "https://cdn.pixabay.com/download/audio/2022/03/15/"
    "audio_8cb749d484.mp3?filename=energetic-upbeat-112195.mp3"
)


def _ken_burns(clip, duration, zoom_from=1.0, zoom_to=1.14, pan="down"):
    """Slow centered zoom for a cinematic, non-static feel (robust moviepy v2)."""
    def zoom(t):
        return zoom_from + (zoom_to - zoom_from) * (t / duration)

    bigger = clip.resized(lambda t: zoom(t))
    return bigger.cropped(
        width=VIDEO_W, height=VIDEO_H,
        x_center=VIDEO_W / 2, y_center=VIDEO_H / 2,
    )


def _make_caption(text, duration, start):
    # NOTE: moviepy v2 uses ImageMagick to rasterize TextClip. With
    # method="caption" the per-glyph rasterizer mangles certain letters
    # (notably "U" -> two bars). Switching to method="label" renders the
    # full string as one image, sidestepping the bug while keeping bold +
    # stroke. Position is anchored manually to keep it centered, lower-third.
    txt = TextClip(
        text=text.upper(),
        font_size=80,
        font=FONT_BOLD,
        color="white",
        stroke_color="black",
        stroke_width=8,
        method="label",
        text_align="center",
        size=(VIDEO_W - 120, None),
    )
    txt = (
        txt.with_position(("center", 0.70), relative=True)
        .with_duration(duration)
        .with_start(start)
    )
    return txt


def build_video(script: dict, image_paths: list, audio_path: Path,
                out_path, music_path=None) -> Path:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    audio = AudioFileClip(str(audio_path))
    total = audio.duration

    n = len(script["scenes"])
    seg = total / n
    clips = []
    captions = []

    for i, scene in enumerate(script["scenes"]):
        img = Path(image_paths[i])
        ic = ImageClip(str(img)).resized((VIDEO_W, VIDEO_H))
        ic = _ken_burns(ic, duration=seg, zoom_from=1.0, zoom_to=1.14)
        ic = ic.with_duration(seg)
        # subtle 0.25s fade between scenes
        ic = ic.with_effects([vfx.CrossFadeIn(0.25)]) if i > 0 else ic
        clips.append(ic)
        captions.append(_make_caption(scene["caption"], seg, i * seg))

    base = concatenate_videoclips(clips, method="compose")
    caption_layer = [base] + captions
    final = CompositeVideoClip(caption_layer, size=(VIDEO_W, VIDEO_H))

    # Music bed at low volume, mixed under the voiceover.
    from moviepy import CompositeAudioClip
    from moviepy.audio.fx import AudioNormalize, MultiplyVolume

    if music_path and Path(music_path).exists():
        try:
            music = AudioFileClip(str(music_path)).subclipped(0, total)
            music = music.with_effects([MultiplyVolume(0.15)])
            voice = audio.with_effects([AudioNormalize()]).with_effects(
                [MultiplyVolume(1.3)]
            )
            final = final.with_audio(CompositeAudioClip([voice, music]))
        except Exception as e:
            print(f"[video] music bed skipped: {e}")
            final = final.with_audio(audio)
    else:
        final = final.with_audio(audio)

    final = final.with_duration(total)
    final.write_videofile(
        str(out_path),
        codec="libx264",
        audio_codec="aac",
        fps=30,
        preset="medium",
        threads=2,
        ffmpeg_params=["-pix_fmt", "yuv420p"],
    )
    return out_path


if __name__ == "__main__":
    # smoke test with generated assets
    from .scripts import generate_script
    from .voice import generate_voice
    from .images import generate_image
    import tempfile, os
    d = Path(tempfile.mkdtemp())
    sc = generate_script("why your phone drains battery", 3, "cinematic")
    imgs, aud = [], d / "voice.mp3"
    for i, s in enumerate(sc["scenes"]):
        imgs.append(str(generate_image(s["image_prompt"], d / f"img{i}.png")))
    generate_voice(sc["total_voice"], aud)
    out = build_video(sc, imgs, aud, d / "out.mp4")
    print("wrote", out)

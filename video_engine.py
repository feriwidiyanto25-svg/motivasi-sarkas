import os
import gc
import glob
import random
import uuid
import requests
from dotenv import load_dotenv

# ==========================================
# KONFIGURASI PROYEK
# ==========================================
import config
from tts_engine import generate_voiceover_for_scenes

# ==========================================
# PILLOW COMPATIBILITY
# ==========================================
from PIL import Image

if not hasattr(Image, "ANTIALIAS"):
    Image.ANTIALIAS = Image.Resampling.LANCZOS

# ==========================================
# IMAGEMAGICK
# ==========================================
from moviepy.config import change_settings

if config.IMAGEMAGICK_BINARY:
    change_settings({"IMAGEMAGICK_BINARY": config.IMAGEMAGICK_BINARY})

# ==========================================
# MOVIEPY
# ==========================================
from moviepy.editor import (
    VideoFileClip,
    TextClip,
    CompositeVideoClip,
    CompositeAudioClip,
    concatenate_videoclips,
    AudioFileClip,
    ColorClip,
    vfx
)
from moviepy.audio.fx.all import audio_loop

# ==========================================
# KONSTANTA TAMPILAN
# ==========================================
VIDEO_WIDTH = config.VIDEO_WIDTH
VIDEO_HEIGHT = config.VIDEO_HEIGHT
TARGET_ASPECT_RATIO = VIDEO_WIDTH / VIDEO_HEIGHT

TEXT_WIDTH = 620
TITLE_FONT_SIZE = 38
SCENE_FONT_SIZE = 38

# ==========================================
# PILIH VIDEO LATAR LOKAL (assets/videos)
# ==========================================
def get_local_background_video(target_duration):
    """
    Mengambil video dari folder lokal assets/videos/ secara acak.
    Jika folder belum memiliki video, membuat background fallback warna gelap
    agar sistem tetap bisa merender tanpa crash.
    """
    video_extensions = ("*.mp4", "*.mov", "*.webm", "*.mkv")
    candidates = []

    for ext in video_extensions:
        candidates.extend(glob.glob(os.path.join(config.VIDEOS_DIR, ext)))

    if not candidates:
        print(f"⚠️ Tidak ada video di '{config.VIDEOS_DIR}'. Menggunakan background kanvas fallback.")
        return None

    chosen_video = random.choice(candidates)
    print(f"🎬 Video Latar Terpilih: {os.path.basename(chosen_video)}")
    return chosen_video

# ==========================================
# SESUAIKAN VIDEO KE FULLSCREEN (9:16)
# ==========================================
def fit_video_to_fullscreen(video, target_duration):
    """
    Memastikan video mengisi penuh layar vertikal (720x1280) tanpa distorsi,
    dan melakukan loop jika durasi video lebih pendek dari target.
    """
    current_width = video.w
    current_height = video.h
    current_ratio = current_width / current_height

    if current_ratio > TARGET_ASPECT_RATIO:
        # Video lebih lebar -> sesuaikan tinggi lalu crop lebarnya
        video = video.resize(height=VIDEO_HEIGHT)
        x1 = (video.w - VIDEO_WIDTH) / 2
        video = video.crop(x1=x1, y1=0, x2=x1 + VIDEO_WIDTH, y2=VIDEO_HEIGHT)
    else:
        # Video lebih ramping/pas -> sesuaikan lebar lalu crop tingginya
        video = video.resize(width=VIDEO_WIDTH)
        y1 = (video.h - VIDEO_HEIGHT) / 2
        video = video.crop(x1=0, y1=y1, x2=VIDEO_WIDTH, y2=y1 + VIDEO_HEIGHT)

    # Loop video jika lebih pendek dari total durasi narasi
    if video.duration < target_duration:
        video = video.fx(vfx.loop, duration=target_duration)
    else:
        video = video.subclip(0, target_duration)

    return video.set_position(("center", "center"))

# ==========================================
# PEMBUATAN TEXT CLIP (TEKNIK 1: BLACK STROKE)
# ==========================================
def create_text_clip(text, fontsize, color, start, duration, position, stroke_color="black", stroke_width=4, align="center"):
    font_path = os.path.abspath(os.path.join(config.BASE_DIR, "assets", "Poppins-Bold.ttf"))
    if not os.path.exists(font_path):
        font_path = "DejaVu-Sans-Bold"

    return (
        TextClip(
            text,
            fontsize=fontsize,
            color=color,
            stroke_color=stroke_color,
            stroke_width=stroke_width,
            method="caption",
            size=(TEXT_WIDTH, None),
            font=font_path,
            align=align
        )
        .set_position(position)
        .set_start(start)
        .set_duration(duration)
    )

# ==========================================
# ELEMEN TATA LETAK (LAYOUT ELEMENT)
# ==========================================
def generate_layout_elements(naskah, timings):
    clips = []
    total_dur = timings["total_duration"]

    font_path = os.path.abspath(os.path.join(config.BASE_DIR, "assets", "Poppins-Bold.ttf"))
    if not os.path.exists(font_path):
        font_path = "DejaVu-Sans-Bold"

    # 1. BADGE "KENAPA YA?" (Bagian Atas Tengah)
    BADGE_WIDTH = 180
    BADGE_HEIGHT = 42
    BADGE_Y = 130

    badge_bg = (
        ColorClip(size=(BADGE_WIDTH, BADGE_HEIGHT), color=(250, 204, 21))
        .set_position(("center", BADGE_Y))
        .set_start(0)
        .set_duration(total_dur)
    )

    badge_text = (
        TextClip("KENAPA YA?", fontsize=20, color="black", font=font_path)
        .set_position(("center", BADGE_Y + 9))
        .set_start(0)
        .set_duration(total_dur)
    )
    clips.extend([("badge_bg", badge_bg), ("badge_text", badge_text)])

    # 2. JUDUL PERMANEN (Atas, Rata Tengah, Stroke Hitam Tebal)
    title_text = naskah.get("title", "").strip()
    TITLE_Y = BADGE_Y + BADGE_HEIGHT + 20  # Y = 192

    txt_title = create_text_clip(
        title_text,
        fontsize=TITLE_FONT_SIZE,
        color="white",
        start=0,
        duration=total_dur,
        position=("center", TITLE_Y),
        stroke_color="black",
        stroke_width=4,
        align="center"
    )
    clips.append(("title", txt_title))

    # 3. SUBTITLE SCENES (Tengah Layar - Tepat di Safe Zone)
    # Penonton fokus ke sini, dan bebas dari tombol-tombol UI YouTube di bawah
    SCENE_Y = 570

    for sc in timings["scene_timings"]:
        txt_scene = create_text_clip(
            sc["text"],
            fontsize=SCENE_FONT_SIZE,
            color="white",
            start=sc["start"],
            duration=sc["duration"],
            position=("center", SCENE_Y),
            stroke_color="black",
            stroke_width=5,
            align="center"
        )
        clips.append((sc["name"], txt_scene))

    return clips

# ==========================================
# AUDIO MIXING (VOICEOVER + BGM PELAN)
# ==========================================
def create_composite_audio(voiceover_path, total_duration):
    """
    Menggabungkan audio narasi Voiceover (100%) dengan BGM latar (15%).
    """
    try:
        voiceover_clip = AudioFileClip(voiceover_path).volumex(config.VOICEOVER_VOLUME)
        audio_elements = [voiceover_clip]

        # Ambil BGM dari folder assets/audio/setup
        bgm_pool = glob.glob(os.path.join(config.AUDIO_DIR, "setup", "*.mp3"))
        if bgm_pool:
            bgm_file = random.choice(bgm_pool)
            print(f"🎵 BGM Terpilih: {os.path.basename(bgm_file)} (Volume {int(config.BGM_VOLUME * 100)}%)")
            bgm_clip = AudioFileClip(bgm_file)

            if bgm_clip.duration >= total_duration:
                bgm_clip = bgm_clip.subclip(0, total_duration)
            else:
                bgm_clip = audio_loop(bgm_clip, duration=total_duration)

            bgm_clip = bgm_clip.volumex(config.BGM_VOLUME)
            audio_elements.insert(0, bgm_clip)

        final_audio = CompositeAudioClip(audio_elements).set_duration(total_duration)
        return final_audio
    except Exception as e:
        print(f"⚠️ Audio mixing warning: {e}")
        try:
            return AudioFileClip(voiceover_path).set_duration(total_duration)
        except Exception:
            return None

# ==========================================
# CLEANUP
# ==========================================
def safe_close(clip):
    try:
        if clip:
            clip.close()
    except Exception:
        pass

# ==========================================
# RENDER FINAL VIDEO
# ==========================================
def render_final_video(naskah):
    print("\n====================================")
    print("      MULAI RENDER VIDEO SHORTS     ")
    print("====================================")

    # 1. GENERATE VOICEOVER & HITUNG PRESISI TIMING
    scenes = naskah.get("scenes", [])
    if not scenes:
        raise ValueError("Naskah tidak memiliki scenes untuk di-render.")

    scene_timings, master_voiceover_path, total_duration = generate_voiceover_for_scenes(scenes)

    timings = {
        "scene_timings": scene_timings,
        "voiceover_path": master_voiceover_path,
        "total_duration": total_duration
    }

    source_video = None
    bg_video = None
    final_video = None
    final_audio = None

    try:
        # 2. SIAPKAN VIDEO LATAR BELAKANG LOKAL
        bg_local_path = get_local_background_video(total_duration)

        if bg_local_path and os.path.exists(bg_local_path):
            print("Membuka video latar lokal...")
            source_video = VideoFileClip(bg_local_path, audio=False)
            bg_video = fit_video_to_fullscreen(source_video, total_duration)
        else:
            print("Menggunakan latar kanvas fallback...")
            bg_video = ColorClip(
                size=(VIDEO_WIDTH, VIDEO_HEIGHT),
                color=(24, 28, 36),
                duration=total_duration
            ).set_position(("center", "center"))

        # 3. SUSUN ELEMEN TEKS DENGAN BLACK STROKE
        layout_elements = generate_layout_elements(naskah, timings)
        composed_segments = []

        print("Menggabungkan layer teks dan video...")
        current_time = 0.0
        while current_time < total_duration:
            segment_dur = min(1.0, total_duration - current_time)

            active_clips = [
                bg_video.subclip(current_time, current_time + segment_dur).set_start(0)
            ]

            for name, clip in layout_elements:
                clip_start = clip.start
                clip_end = clip.start + clip.duration

                if current_time < clip_end and (current_time + segment_dur) > clip_start:
                    rel_start = max(0.0, clip_start - current_time)
                    rel_end = min(segment_dur, clip_end - current_time)
                    rel_dur = rel_end - rel_start

                    if rel_dur > 0:
                        active_clips.append(clip.set_start(rel_start).set_duration(rel_dur))

            segment = CompositeVideoClip(active_clips, size=(VIDEO_WIDTH, VIDEO_HEIGHT)).set_duration(segment_dur)
            composed_segments.append(segment)

            # Ekstrak thumbnail dari detik ke-0.5
            if current_time == 0.0:
                os.makedirs(config.TEMP_DIR, exist_ok=True)
                thumbnail_path = os.path.join(config.TEMP_DIR, "thumbnail.jpg")
                try:
                    frame = segment.get_frame(0.5)
                    thumb_img = Image.fromarray(frame).convert("RGB")
                    thumb_img.save(thumbnail_path, format="JPEG", quality=90, optimize=True)
                    print("✅ Thumbnail berhasil disimpan.")
                except Exception as e:
                    print(f"Peringatan thumbnail: {e}")

            current_time += segment_dur

        final_video = concatenate_videoclips(composed_segments, method="chain")
        final_video = final_video.set_duration(total_duration)

        # 4. PASANG AUDIO (VOICEOVER + BGM)
        final_audio = create_composite_audio(master_voiceover_path, total_duration)
        if final_audio:
            final_video = final_video.set_audio(final_audio)

        # 5. EKSPOR FILE MP4
        os.makedirs(config.TEMP_DIR, exist_ok=True)
        unique_id = uuid.uuid4().hex[:8]
        output_path = os.path.join(config.TEMP_DIR, f"final_{unique_id}.mp4")

        print(f"\nMengekspor video Shorts ({total_duration:.2f}s)...")
        final_video.write_videofile(
            output_path,
            fps=config.VIDEO_FPS,
            codec="libx264",
            bitrate="2500k",
            audio_codec="aac",
            audio_bitrate="128k",
            preset="fast",
            threads=2,
            logger=None
        )

        print("\n====================================")
        print("       VIDEO BERHASIL DIBUAT        ")
        print("====================================")
        print(f"Durasi : {total_duration:.2f}s")
        print(f"File   : {output_path}")

        return output_path

    except Exception as e:
        print("\n❌ ERROR SAAT RENDER VIDEO:")
        print(f"{type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return None

    finally:
        safe_close(final_audio)
        safe_close(final_video)
        safe_close(bg_video)
        safe_close(source_video)

        if 'layout_elements' in locals():
            for name, clip in layout_elements:
                safe_close(clip)

        gc.collect()

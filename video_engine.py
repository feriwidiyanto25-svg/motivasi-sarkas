import os
import gc
import glob
import random
import uuid
import requests

from dotenv import load_dotenv
from PIL import Image

if not hasattr(Image, "ANTIALIAS"):
    Image.ANTIALIAS = Image.Resampling.LANCZOS

from moviepy.config import change_settings
if os.name == "nt":
    # Sesuaikan path ImageMagick jika berbeda di komputermu
    change_settings({"IMAGEMAGICK_BINARY": r"C:\Program Files\ImageMagick-7.1.1-Q16-HDRI\magick.exe"})

from moviepy.editor import (
    VideoFileClip, TextClip, CompositeVideoClip, concatenate_videoclips,
    AudioFileClip, ColorClip, vfx
)
from moviepy.audio.fx.all import audio_loop

load_dotenv()
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")

VIDEO_WIDTH = 720
VIDEO_HEIGHT = 1280
TARGET_ASPECT_RATIO = VIDEO_WIDTH / VIDEO_HEIGHT

# ==========================================
# TIMING & READING SETTINGS (RELAXED)
# ==========================================
# Kecepatan baca diperlambat agar audiens lebih mudah mencerna teks panjang
WORDS_PER_SECOND = 1.8 
TITLE_DURATION = 3.0 # Judul ditahan lebih lama

MIN_SCENE_DURATION = 3.0
MAX_SCENE_DURATION = 15.0 # Batas maksimal di layar diperbesar untuk teks panjang
MIN_TOTAL_DURATION = 10.0 # Durasi minimal video

# ==========================================
# TEXT SETTINGS
# ==========================================
TEXT_WIDTH = 620 # Diperlebar sedikit agar muat teks panjang
TITLE_FONT_SIZE = 70
SCENE_FONT_SIZE = 50 # Diperkecil dari 60 agar kalimat panjang tidak menutupi layar

def count_words(text):
    return len((text or "").strip().split())

def calculate_reading_duration(text, min_dur, max_dur):
    # Diberi tambahan waktu +1.0 detik untuk jeda nafas/mencerna informasi
    duration = (count_words(text) / WORDS_PER_SECOND) + 1.0
    return min(max(min_dur, duration), max_dur)

def calculate_timings(naskah):
    title = naskah.get("title", "")
    scenes = naskah.get("scenes", [])
    
    start_time = 0.0
    durasi_title = TITLE_DURATION
    
    scene_timings = []
    current_start = durasi_title
    
    for scene in scenes:
        durasi = calculate_reading_duration(scene, MIN_SCENE_DURATION, MAX_SCENE_DURATION)
        scene_timings.append({
            "text": scene,
            "start": current_start,
            "duration": durasi
        })
        current_start += durasi

    total_duration = max(current_start, MIN_TOTAL_DURATION)
    
    print("\n========== DYNAMIC TIMING ==========")
    print(f"Title: {durasi_title:.2f}s")
    for i, st in enumerate(scene_timings):
        print(f"Scene {i+1} ({count_words(st['text'])} kata): {st['duration']:.2f}s")
    print(f"TOTAL DURASI ESTIMASI: {total_duration:.2f}s")
    print("====================================\n")

    return {
        "dur_title": durasi_title,
        "scene_timings": scene_timings,
        "total_duration": total_duration
    }

def search_pexels(keyword, per_page=4):
    if not PEXELS_API_KEY: return []
    url = f"[https://api.pexels.com/videos/search?query=](https://api.pexels.com/videos/search?query=){keyword}&orientation=portrait&per_page={per_page}"
    try:
        response = requests.get(url, headers={"Authorization": PEXELS_API_KEY}, timeout=15)
        if response.status_code == 200: return response.json().get("videos", [])
    except Exception: pass
    return []

def fetch_background_video(naskah, target_duration):
    keywords = naskah.get("bg_keywords", [])
    if not keywords and naskah.get("bg_keyword"):
        keywords = [naskah.get("bg_keyword")]
        
    for keyword in keywords[:4]:
        videos = search_pexels(keyword)
        for video in videos:
            files = video.get("video_files", [])
            for vf in files:
                if vf.get("width", 0) > 0 and vf.get("height", 0) >= 720:
                    link = vf.get("link")
                    if link:
                        os.makedirs("temp", exist_ok=True)
                        output_path = os.path.join("temp", f"bg_{uuid.uuid4().hex[:8]}.mp4")
                        try:
                            req = requests.get(link, timeout=40) # Timeout diperbesar untuk donwload video yg mungkin agak panjang
                            if req.status_code == 200 and len(req.content) > 10000:
                                with open(output_path, "wb") as f: f.write(req.content)
                                return output_path
                        except: pass
    return None

def fit_video_to_vertical(video):
    current_ratio = video.w / video.h
    if current_ratio > TARGET_ASPECT_RATIO:
        video = video.resize(height=VIDEO_HEIGHT)
        x1 = (video.w - VIDEO_WIDTH) / 2
        video = video.crop(x1=x1, y1=0, x2=x1+VIDEO_WIDTH, y2=VIDEO_HEIGHT)
    else:
        video = video.resize(width=VIDEO_WIDTH)
        y1 = (video.h - VIDEO_HEIGHT) / 2
        video = video.crop(x1=0, y1=y1, x2=VIDEO_WIDTH, y2=y1+VIDEO_HEIGHT)
    return video

def create_text_clip(text, fontsize, color, duration, stroke_width):
    return (TextClip(text, fontsize=fontsize, color=color, method="caption", 
                     size=(TEXT_WIDTH, None), font="Arial-Bold", align="center",
                     stroke_color="black", stroke_width=stroke_width)
            .set_position(("center", "center"))
            .set_duration(duration))

def render_final_video(naskah):
    print("\n======== MULAI RENDER VIDEO EDUKASI ========")
    timings = calculate_timings(naskah)
    bg_path = None
    composed_segments = []
    
    try:
        bg_path = fetch_background_video(naskah, timings["total_duration"])
        
        if bg_path and os.path.exists(bg_path):
            source_video = VideoFileClip(bg_path, audio=False)
            source_video = fit_video_to_vertical(source_video)
            
            # Jika video Pexels lebih pendek dari teks kita yang panjang, otomatis loop!
            if source_video.duration >= timings["total_duration"]:
                video_bg = source_video.subclip(0, timings["total_duration"])
            else:
                print("Melakukan looping background video...")
                video_bg = source_video.fx(vfx.loop, duration=timings["total_duration"])
        else:
            video_bg = ColorClip(size=(VIDEO_WIDTH, VIDEO_HEIGHT), color=(0,0,0), duration=timings["total_duration"])
            
        # Gelapkan background agar teks tidak tenggelam
        video_bg = video_bg.fx(vfx.colorx, 0.4)

        # 1. RENDER TITLE
        title_bg = video_bg.subclip(0, timings["dur_title"])
        txt_title = create_text_clip(naskah.get("title", "").upper(), TITLE_FONT_SIZE, "yellow", timings["dur_title"], 3)
        segment_title = CompositeVideoClip([title_bg, txt_title.set_start(0)])
        composed_segments.append(segment_title)
        
        # 2. RENDER SCENES
        for scene_info in timings["scene_timings"]:
            start = scene_info["start"]
            dur = scene_info["duration"]
            
            scene_bg = video_bg.subclip(start, start + dur)
            txt_scene = create_text_clip(scene_info["text"], SCENE_FONT_SIZE, "white", dur, 2)
            segment_scene = CompositeVideoClip([scene_bg, txt_scene.set_start(0)])
            composed_segments.append(segment_scene)

        # GABUNGKAN SEMUA SEGMENT
        final_video = concatenate_videoclips(composed_segments, method="chain")
        
        # AUDIO
        try:
            audio_pool = glob.glob("assets/audio/setup/*.mp3")
            if audio_pool:
                bgm = AudioFileClip(random.choice(audio_pool))
                if bgm.duration < timings["total_duration"]:
                    bgm = audio_loop(bgm, duration=timings["total_duration"])
                else:
                    bgm = bgm.subclip(0, timings["total_duration"])
                final_video = final_video.set_audio(bgm)
        except Exception as e:
            print(f"Peringatan Audio: {e}")

        # EXPORT
        os.makedirs("temp", exist_ok=True)
        output_path = os.path.join("temp", f"final_{uuid.uuid4().hex[:12]}.mp4")
        
        print(f"\nMengekspor video (Estimasi durasi: {timings['total_duration']:.2f} detik)...")
        final_video.write_videofile(output_path, fps=24, codec="libx264", audio_codec="aac", preset="ultrafast", threads=2, logger=None)
        print(f"VIDEO SELESAI: {output_path}")
        
        return output_path

    except Exception as e:
        print(f"ERROR RENDER: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        gc.collect()
        if bg_path and os.path.exists(bg_path):
            try: os.remove(bg_path)
            except: pass

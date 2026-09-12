import os
import gc
import glob
import random
import uuid
import requests

from dotenv import load_dotenv

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

if os.name == "nt":
    change_settings({
        "IMAGEMAGICK_BINARY": (
            r"E:\motivasi\ImageMagick"
            r"\ImageMagick-7.1.2-Q16-HDRI\magick.exe"
        )
    })

# ==========================================
# MOVIEPY
# ==========================================
from moviepy.editor import (
    VideoFileClip,
    TextClip,
    CompositeVideoClip,
    concatenate_videoclips,
    AudioFileClip,
    ColorClip,
    vfx
)
from moviepy.audio.fx.all import audio_loop

# ==========================================
# ENVIRONMENT
# ==========================================
load_dotenv()
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")

# ==========================================
# VIDEO CONFIG (SPLIT-SCREEN)
# ==========================================
VIDEO_WIDTH = 720
VIDEO_HEIGHT = 1280

# Video akan menempati sekitar 60% layar atas (760px)
TOP_VIDEO_HEIGHT = 760
TARGET_ASPECT_RATIO = VIDEO_WIDTH / TOP_VIDEO_HEIGHT

# ==========================================
# DYNAMIC TIMING (EDUKASI)
# ==========================================
WORDS_PER_SECOND = 1.8 
MIN_SCENE_DURATION = 3.0
MAX_SCENE_DURATION = 15.0

MIN_TOTAL_DURATION = 10.0
MAX_TOTAL_DURATION = 150.0 # BATES MAKSIMAL 2.5 MENIT AGAR TELEGRAM AMAN

# ==========================================
# TEXT CONFIG (EDUKASI)
# ==========================================
TEXT_WIDTH = 620
TITLE_FONT_SIZE = 55 
SCENE_FONT_SIZE = 35

# ==========================================
# UTIL
# ==========================================
def count_words(text):
    if not text: return 0
    return len(text.strip().split())

# ==========================================
# READING DURATION
# ==========================================
def calculate_reading_duration(text, min_duration, max_duration):
    word_count = count_words(text)
    duration = (word_count / WORDS_PER_SECOND) + 1.0
    duration = max(min_duration, duration)
    duration = min(max_duration, duration)
    return duration

# ==========================================
# DYNAMIC TIMING (AUTO SCALING & CUTTER)
# ==========================================
def calculate_timings(naskah):
    title = naskah.get("title", "")
    raw_scenes = naskah.get("scenes", [])

    # Memotong teks yang kepanjangan (Maks 12 Kata per layar)
    scenes = []
    for text in raw_scenes:
        words = text.split()
        if len(words) > 12:
            for i in range(0, len(words), 12):
                chunk = " ".join(words[i:i+12])
                scenes.append(chunk)
        else:
            scenes.append(text)

    scene_timings = []
    current_start = 0.0
    
    for index, scene in enumerate(scenes):
        dur = calculate_reading_duration(scene, MIN_SCENE_DURATION, MAX_SCENE_DURATION)
        scene_timings.append({
            "name": f"scene_{index+1}",
            "text": scene,
            "start": current_start,
            "duration": dur
        })
        current_start += dur
        
    total_duration = max(current_start, MIN_TOTAL_DURATION)

    # Auto-scaling agar tidak melebihi 2.5 menit (untuk Telegram)
    if total_duration > MAX_TOTAL_DURATION:
        print(f"\n⚠️ Peringatan: Durasi mentah ({total_duration:.1f}s) melebihi batas {MAX_TOTAL_DURATION}s.")
        print("Melakukan auto-scaling agar aman untuk Telegram...")
        
        scale_factor = MAX_TOTAL_DURATION / total_duration
        current_start = 0.0
        
        for sc in scene_timings:
            sc["duration"] *= scale_factor
            sc["start"] = current_start
            current_start += sc["duration"]
            
        total_duration = MAX_TOTAL_DURATION

    print("")
    print("========== DYNAMIC TIMING ==========")
    print(f"Title      : {count_words(title)} kata → Tampil Sepanjang Video")
    for sc in scene_timings:
        print(f"{sc['name'].capitalize()}    : {count_words(sc['text'])} kata → {sc['duration']:.2f}s")
    print(f"TOTAL      : {total_duration:.2f}s")
    print("====================================")
    print("")

    return {
        "start_title": 0.0,
        "dur_title": total_duration, # Judul tayang sepanjang video
        "scene_timings": scene_timings,
        "total_duration": total_duration
    }

# ==========================================
# PEXELS SEARCH (BERSIH)
# ==========================================
def search_pexels(keyword, per_page=4):
    if not PEXELS_API_KEY: return []
    
    url = f"https://api.pexels.com/videos/search?query={keyword}&orientation=portrait&per_page={per_page}"
    headers = {"Authorization": PEXELS_API_KEY}
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code != 200:
            print(f"Pexels error {response.status_code} untuk keyword '{keyword}'")
            return []
            
        data = response.json()
        return data.get("videos", [])
        
    except requests.RequestException as e:
        print(f"Pexels request error: {e}")
        return []
    except Exception as e:
        print(f"Pexels parsing error: {e}")
        return []

# ==========================================
# CHOOSE VIDEO FILE
# ==========================================
def choose_video_file(video, target_duration):
    files = video.get("video_files", [])
    candidates = []

    for vf in files:
        link = vf.get("link")
        width = vf.get("width", 0)
        height = vf.get("height", 0)

        if not link or width <= 0 or height <= 0:
            continue

        ratio = width / height
        portrait_penalty = abs(ratio - TARGET_ASPECT_RATIO)
        duration = video.get("duration", 0)

        score = 0
        if height >= 1080: score += 5
        elif height >= 720: score += 3
        elif height >= 480: score += 1

        score -= (portrait_penalty * 10)
        if duration >= target_duration: score += 4

        candidates.append((score, vf))

    if not candidates: return None
    candidates.sort(key=lambda item: item[0], reverse=True)
    return candidates[0][1]

# ==========================================
# FETCH BACKGROUND
# ==========================================
def fetch_background_video(naskah, target_duration):
    visual_context = naskah.get("visual_context", "")
    keywords = naskah.get("bg_keywords", [])

    if not keywords:
        fallback = naskah.get("bg_keyword")
        if fallback: keywords = [fallback]

    print("")
    print("========== VISUAL SEARCH ==========")
    print(f"Visual context: {visual_context}")
    print(f"Keywords: {keywords}")
    print("===================================")

    if not PEXELS_API_KEY:
        print("PEXELS_API_KEY tidak ditemukan.")
        return None

    all_candidates = []
    for keyword in keywords[:4]:
        print(f"Mencari Pexels: '{keyword}'")
        videos = search_pexels(keyword, per_page=4)
        for video in videos:
            video["_search_keyword"] = keyword
            all_candidates.append(video)

    if not all_candidates:
        print("Tidak ada kandidat Pexels.")
        return None

    ranked = []
    for video in all_candidates:
        selected_file = choose_video_file(video, target_duration)
        if not selected_file: continue

        width = selected_file.get("width", 0)
        height = selected_file.get("height", 0)
        ratio = (width / height if height else 0)
        aspect_penalty = abs(ratio - TARGET_ASPECT_RATIO)
        duration = video.get("duration", 0)

        score = 0
        score -= (aspect_penalty * 20)
        if height > width: score += 10
        if duration >= target_duration: score += 8
        else: score -= (target_duration - duration)

        if height >= 1080: score += 6
        elif height >= 720: score += 4
        elif height >= 480: score += 2

        ranked.append({"score": score, "video": video, "file": selected_file})

    if not ranked:
        print("Tidak ada kandidat video yang valid.")
        return None

    ranked.sort(key=lambda item: item["score"], reverse=True)
    best = ranked[0]

    selected_video = best["video"]
    selected_file = best["file"]
    keyword_used = selected_video.get("_search_keyword", "")

    print(f"Video terpilih dari keyword: {keyword_used}")
    print(f"Resolution: {selected_file.get('width')}x{selected_file.get('height')}")

    os.makedirs("temp", exist_ok=True)

    for candidate_index, candidate in enumerate(ranked[:4], start=1):
        selected_file = candidate["file"]
        video_url = selected_file.get("link")
        if not video_url: continue

        unique_id = uuid.uuid4().hex[:12]
        output_path = os.path.join("temp", f"bg_{unique_id}.mp4")

        try:
            print(f"Download kandidat background #{candidate_index}...")
            response = requests.get(video_url, timeout=60)
            if response.status_code != 200:
                print(f"Download gagal. HTTP {response.status_code}.")
                continue

            content = response.content
            if len(content) < 10000:
                print(f"File background terlalu kecil.")
                continue

            with open(output_path, "wb") as file:
                file.write(content)
            
            test_clip = None
            try:
                test_clip = VideoFileClip(output_path, audio=False)
                if not test_clip.w or not test_clip.h or not test_clip.duration:
                    raise ValueError("Metadata video tidak valid.")
                print(f"Background valid dan tersimpan di: {output_path}")
                return output_path
            except Exception as validation_error:
                print(f"Background rusak: {validation_error}")
                try:
                    if test_clip: test_clip.close()
                    if os.path.exists(output_path): os.remove(output_path)
                except: pass
                continue
            finally:
                try: 
                    if test_clip: test_clip.close()
                except: pass

        except Exception as e:
            print(f"Background error: {e}")

    print("Semua kandidat background gagal di-download.")
    return None

# ==========================================
# FIT VIDEO TO TOP HALF (Memotong bagian atas)
# ==========================================
def fit_video_to_top_half(video):
    current_width = video.w
    current_height = video.h
    if not current_width or not current_height: return video
    
    current_ratio = current_width / current_height

    if current_ratio > TARGET_ASPECT_RATIO:
        video = video.resize(height=TOP_VIDEO_HEIGHT)
        x1 = (video.w - VIDEO_WIDTH) / 2
        video = video.crop(x1=x1, y1=0, x2=x1+VIDEO_WIDTH, y2=TOP_VIDEO_HEIGHT)
    else:
        video = video.resize(width=VIDEO_WIDTH)
        y1 = (video.h - TOP_VIDEO_HEIGHT) / 2
        video = video.crop(x1=0, y1=y1, x2=VIDEO_WIDTH, y2=y1+TOP_VIDEO_HEIGHT)

    return video

# ==========================================
# TEXT CREATION ALIGNED LEFT
# ==========================================
def create_text_clip(text, fontsize, color, start, duration, position, align="West"):
    font_path = os.path.abspath(os.path.join("assets", "Poppins-Bold.ttf"))
    if not os.path.exists(font_path):
        font_path = "DejaVu-Sans-Bold"

    return (
        TextClip(
            text,
            fontsize=fontsize,
            color=color,
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
# GENERATE SPLIT-SCREEN LAYOUT
# ==========================================
def generate_layout_elements(naskah, timings):
    clips = []
    
    # Koordinat Y Pasti (Mencegah error txt_title.h)
    BADGE_Y = TOP_VIDEO_HEIGHT + 35    # Y = 795
    TITLE_Y = BADGE_Y + 45 + 15        # Y = 855
    SCENE_Y = TITLE_Y + 140            # Y = 995 (Spasi cukup untuk 2-3 baris judul)

    # 1. BADGE "KENAPA YA?" KUNING (Permanen)
    badge_bg = ColorClip(size=(180, 45), color=(242, 201, 76)).set_position((50, BADGE_Y)).set_start(0).set_duration(timings["total_duration"])
    
    font_path = os.path.abspath(os.path.join("assets", "Poppins-Bold.ttf"))
    if not os.path.exists(font_path): font_path = "DejaVu-Sans-Bold"
    
    badge_text = TextClip("KENAPA YA?", fontsize=22, color="black", font=font_path).set_position((62, BADGE_Y + 8)).set_start(0).set_duration(timings["total_duration"])
    clips.extend([("badge_bg", badge_bg), ("badge_text", badge_text)])

    # 2. JUDUL PERMANEN (Putih Tebal, Rata Kiri)
    title_text = naskah.get("title", "").strip()
    txt_title = create_text_clip(title_text, TITLE_FONT_SIZE, "white", 0, timings["total_duration"], (50, TITLE_Y), align="West")
    clips.append(("title", txt_title))

    # 3. TEKS SCENE (Abu-abu terang, Rata Kiri)
    for sc in timings["scene_timings"]:
        txt_scene = create_text_clip(sc["text"], SCENE_FONT_SIZE, "#d1d5db", sc["start"], sc["duration"], (50, SCENE_Y), align="West")
        clips.append((sc["name"], txt_scene))

    return clips

# ==========================================
# AUDIO (BGM LOOP)
# ==========================================
def create_audio(timings):
    try:
        setup_pool = glob.glob("assets/audio/setup/*.mp3")
        if not setup_pool:
            return None

        bgm_source = AudioFileClip(random.choice(setup_pool))
        total_dur = timings["total_duration"]

        if bgm_source.duration >= total_dur:
            final_audio = bgm_source.subclip(0, total_dur)
        else:
            final_audio = audio_loop(bgm_source, duration=total_dur)

        return final_audio.set_duration(total_dur)
    except Exception as e:
        return None

# ==========================================
# CLEANUP
# ==========================================
def safe_close(clip):
    try:
        if clip: clip.close()
    except: pass

# ==========================================
# RENDER FINAL VIDEO (SPLIT-SCREEN MODE)
# ==========================================
def render_final_video(naskah):
    print("")
    print("====================================")
    print("      MULAI RENDER SPLIT-SCREEN")
    print("====================================")

    timings = calculate_timings(naskah)

    bg_path = None
    source_video = None
    video = None
    final_video = None
    final_audio = None
    all_clips_ref = []

    try:
        # BASE CANVAS: Warna Background Abu-abu sangat gelap untuk panel bawah (TIDAK HITAM PEKAT)
        base_canvas = ColorClip(size=(VIDEO_WIDTH, VIDEO_HEIGHT), color=(20, 22, 28), duration=timings["total_duration"])
        
        bg_path = fetch_background_video(naskah, timings["total_duration"])

        if bg_path and os.path.exists(bg_path):
            print("Membuka background video...")
            source_video = VideoFileClip(bg_path, audio=False)
            
            # FIT HANYA SETENGAH ATAS LAYAR
            video = fit_video_to_top_half(source_video)

            if video.duration >= timings["total_duration"]:
                video = video.subclip(0, timings["total_duration"])
            else:
                print("Background lebih pendek dari kebutuhan. Loop...")
                video = video.fx(vfx.loop, duration=timings["total_duration"])
            
            # VIDEO TIDAK DIGELAPKAN SAMA SEKALI, TAPI DIPOSISIKAN DI ATAS
            video = video.set_position(("center", "top"))
        else:
            print("Background gagal. Menggunakan warna abu-abu untuk area video.")
            video = ColorClip(size=(VIDEO_WIDTH, TOP_VIDEO_HEIGHT), color=(40,40,40), duration=timings["total_duration"]).set_position(("center", "top"))

        layout_elements = generate_layout_elements(naskah, timings)
        composed_segments = []

        # RENDER CHUNKING (MEMORY OPTIMIZED)
        print("Menggabungkan layer video...")
        current_time = 0.0
        while current_time < timings["total_duration"]:
            segment_dur = min(1.0, timings["total_duration"] - current_time)
            
            active_clips = [
                base_canvas.subclip(current_time, current_time + segment_dur).set_start(0),
                video.subclip(current_time, current_time + segment_dur).set_start(0)
            ]
            
            for name, clip in layout_elements:
                if current_time < (clip.start + clip.duration) and (current_time + segment_dur) > clip.start:
                    active_clips.append(clip.set_start(0).set_duration(segment_dur))
                    all_clips_ref.append(clip)

            segment = CompositeVideoClip(active_clips, size=(VIDEO_WIDTH, VIDEO_HEIGHT)).set_duration(segment_dur)
            composed_segments.append(segment)
            
            # GENERATE THUMBNAIL PADA DETIK 0.5
            if current_time == 0.0:
                thumbnail_path = os.path.join("temp", "thumbnail.jpg")
                try:
                    segment.save_frame(thumbnail_path, t=0.5) 
                    with Image.open(thumbnail_path) as thumbnail_image:
                        thumbnail_image = thumbnail_image.convert("RGB")
                        thumbnail_image.save(thumbnail_path, format="JPEG", quality=90, optimize=True)
                except Exception:
                    pass

            current_time += segment_dur

        final_video = concatenate_videoclips(composed_segments, method="chain")
        final_video = final_video.set_duration(timings["total_duration"])

        final_audio = create_audio(timings)
        if final_audio:
            final_video = final_video.set_audio(final_audio)

        os.makedirs("temp", exist_ok=True)
        unique_id = uuid.uuid4().hex[:12]
        
        output_path = os.path.join("temp", f"final_{unique_id}.mp4")

        # PENGATURAN KOMPRESI
        print("\nMengekspor video Split-Screen...")
        final_video.write_videofile(
            output_path,
            fps=24,
            codec="libx264",
            bitrate="2000k",
            audio_codec="aac",
            audio_bitrate="128k",
            preset="fast",
            threads=2,
            logger=None
        )

        print("")
        print("====================================")
        print("       VIDEO SELESAI DIBUAT")
        print("====================================")
        print(f"Durasi: {timings['total_duration']:.2f}s")
        print(f"Output: {output_path}")

        return output_path

    except Exception as e:
        print("\nERROR SAAT RENDER VIDEO:")
        print(f"{type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return None

    finally:
        safe_close(final_audio)
        safe_close(final_video)
        safe_close(video)
        safe_close(source_video)
        for clip in all_clips_ref:
            safe_close(clip)

        if bg_path and os.path.exists(bg_path):
            try:
                os.remove(bg_path)
            except: pass
        gc.collect()

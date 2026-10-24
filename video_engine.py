import os
import gc
import glob
import random
import uuid
import requests
import numpy as np
from dotenv import load_dotenv

# ==========================================
# KONFIGURASI PROYEK
# ==========================================
import config
from tts_engine import generate_voiceover_for_scenes

# ==========================================
# PILLOW COMPATIBILITY
# ==========================================
from PIL import Image, ImageDraw, ImageFont

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
    ImageClip,
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

MAX_TEXT_WIDTH = 620
HOOK_FONT_SIZE = 48
BODY_FONT_SIZE = 44
OPTICAL_CENTER_Y = 620

def get_font_path():
    """Mengambil path font Poppins-Black dengan forward slashes untuk kompatibilitas multi-platform."""
    font_path = os.path.abspath(os.path.join(config.BASE_DIR, "assets", "Poppins-Black.ttf")).replace('\\', '/')
    if not os.path.exists(font_path):
        font_path = os.path.abspath(os.path.join(config.BASE_DIR, "assets", "Poppins-Bold.ttf")).replace('\\', '/')
    if not os.path.exists(font_path):
        font_path = "DejaVu-Sans-Bold"
    return font_path

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
# TEKNIK B: TRUE GAUSSIAN BLUR MASK (DEFOCUS BOKEH)
# ==========================================
def apply_top_bottom_blur_mask(bg_video, total_duration):
    """
    Menerapkan efek blur bokeh defocus sinematik di bagian atas (0-220px) dan bawah (1060-1280px),
    sementara zona tengah (340-940px) tetap 100% tajam dan jernih kristal.
    Zona transisi di-feather halus menggunakan kurva smoothstep agar tidak ada garis kaku.
    """
    try:
        # 1. Layer Defocus Bokeh: downsample 10x lalu upsample ke 720x1280 + pencahayaan 85%
        blurred_layer = (
            bg_video
            .resize(0.10)
            .resize((VIDEO_WIDTH, VIDEO_HEIGHT))
            .fx(vfx.colorx, 0.85)
        )

        # 2. Mask Feathering 2D (Smoothstep fade-in di atas, fade-out di bawah)
        y_indices = np.arange(VIDEO_HEIGHT, dtype=np.float32)
        t_top = np.clip((y_indices - 220.0) / (340.0 - 220.0), 0.0, 1.0)
        mask_top = t_top * t_top * (3.0 - 2.0 * t_top)

        t_bot = np.clip((1060.0 - y_indices) / (1060.0 - 940.0), 0.0, 1.0)
        mask_bot = t_bot * t_bot * (3.0 - 2.0 * t_bot)

        mask_1d = np.minimum(mask_top, mask_bot)
        mask_2d = np.tile(mask_1d[:, np.newaxis], (1, VIDEO_WIDTH))

        mask_clip = ImageClip(mask_2d, ismask=True).set_duration(total_duration)
        sharp_layer = bg_video.set_mask(mask_clip)

        return CompositeVideoClip([blurred_layer, sharp_layer], size=(VIDEO_WIDTH, VIDEO_HEIGHT)).set_duration(total_duration)
    except Exception as e:
        print(f"⚠️ Warning blur mask fallback: {e}")
        return bg_video

# ==========================================
# PIL-BASED MULTI-COLOR SUBTITLE RENDERER
# ==========================================
def render_scene_text_clip(text, font_size, font_path, start, duration, center_y=620, max_width=620, is_hook=False):
    """
    Merender teks subtitle ke ImageClip menggunakan Pillow dengan fitur:
    - Multi-color keyword highlighting: #FACC15 (Kuning Menyala) untuk kata penegas (*KATA*, angka, atau kata pemicu emosi),
      dan #FFFFFF (Putih Solid) untuk kata narasi biasa.
    - Outline / stroke hitam 2px yang rapi tanpa menyumbat rongga huruf font.
    - 3D drop shadow di (x+3, y+4) untuk keterbacaan tinggi di atas latar terang maupun gelap.
    - Auto word wrapping presisi dan posisi tepat di Optical Center (Y = 620).
    """
    try:
        font = ImageFont.truetype(font_path, font_size)
    except Exception:
        font = ImageFont.load_default()

    # Predefined keyword highlight jika AI tidak memberikan tanda bintang (*)
    HIGHLIGHT_KEYWORDS = {
        "KENAPA", "TERNYATA", "RAHASIA", "OTAK", "BAHAYA", "PENTING",
        "ALASANNYA", "FAKTANYA", "SISTEM", "KUNCI", "UNIK", "MENIT",
        "DETIK", "TAHUN", "HARI", "TUBUH", "MANUSIA", "SADAR", "WASPADA",
        "BUKAN", "KEBETULAN", "ALASAN", "PUNYA", "SANGAT", "MUDAH"
    }

    raw_words = text.strip().split()
    tokens = []
    has_explicit_stars = any("*" in w for w in raw_words)

    for w in raw_words:
        is_highlight = False
        if has_explicit_stars:
            if "*" in w:
                is_highlight = True
        else:
            clean_check = w.strip(".,!?:;\"'()[]")
            if clean_check.upper() in HIGHLIGHT_KEYWORDS or any(char.isdigit() for char in clean_check):
                is_highlight = True

        display_word = w.replace("*", "")
        tokens.append((display_word, is_highlight))

    # Auto word wrap
    lines = []
    curr_line = []
    curr_w = 0
    space_w = font.getbbox(" ")[2] - font.getbbox(" ")[0]

    for word, hl in tokens:
        bbox = font.getbbox(word)
        w_len = bbox[2] - bbox[0]

        if curr_line and (curr_w + space_w + w_len > max_width):
            lines.append(curr_line)
            curr_line = [(word, hl, w_len)]
            curr_w = w_len
        else:
            if curr_line:
                curr_w += space_w
            curr_line.append((word, hl, w_len))
            curr_w += w_len

    if curr_line:
        lines.append(curr_line)

    line_height = int(font_size * 1.30)
    padding_y = 20
    canvas_h = len(lines) * line_height + padding_y * 2
    canvas_w = VIDEO_WIDTH

    img = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    y = padding_y
    for line in lines:
        total_line_w = sum(w[2] for w in line) + space_w * (len(line) - 1)
        x = (canvas_w - total_line_w) / 2

        for word, hl, w_len in line:
            fill_color = (250, 204, 21, 255) if hl else (255, 255, 255, 255)

            # 3D Drop Shadow di layer belakang (offset +3, +4)
            draw.text((x + 3, y + 4), word, font=font, fill=(0, 0, 0, 220), stroke_width=2, stroke_fill=(0, 0, 0, 220))
            # Teks utama dengan outline hitam tajam
            draw.text((x, y), word, font=font, fill=fill_color, stroke_width=2, stroke_fill=(0, 0, 0, 255))

            x += w_len + space_w

        y += line_height

    rgb_np = np.array(img.convert("RGB"))
    alpha_np = np.array(img.split()[-1]) / 255.0

    actual_y = int(center_y - canvas_h / 2)

    mask_clip = ImageClip(alpha_np, ismask=True).set_start(start).set_duration(duration)
    text_clip = (
        ImageClip(rgb_np)
        .set_mask(mask_clip)
        .set_position((0, actual_y))
        .set_start(start)
        .set_duration(duration)
    )

    return text_clip

# ==========================================
# ELEMEN TATA LETAK DINAMIS (LAYOUT ELEMENTS)
# ==========================================
def generate_layout_elements(naskah, timings):
    """
    Menghasilkan elemen teks untuk video Shorts:
    1. Badge 'Kenapa ya?' dan judul statis di atas ditiadakan (tampilan bersih & cinematic).
    2. Hook (Scene 1) tampil besar dan mencolok di Optical Center (Y = 620) di awal video.
    3. Setelah Scene 1 selesai, hook hilang dan digantikan oleh scene penjelasan secara berurutan di tengah.
    4. Menggunakan multi-color keyword highlighting dengan transisi yang mulus.
    """
    clips = []
    font_path = get_font_path()

    scene_timings = timings.get("scene_timings", [])
    for idx, sc in enumerate(scene_timings):
        sc_text = sc["text"].strip().upper()
        if not sc_text:
            continue

        is_hook = (idx == 0)
        fontsize = HOOK_FONT_SIZE if is_hook else BODY_FONT_SIZE

        text_clip = render_scene_text_clip(
            text=sc_text,
            font_size=fontsize,
            font_path=font_path,
            start=sc["start"],
            duration=sc["duration"],
            center_y=OPTICAL_CENTER_Y,
            max_width=MAX_TEXT_WIDTH,
            is_hook=is_hook
        )
        if text_clip:
            clips.append((f"{sc['name']}_text", text_clip))

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
    composite_bg = None
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

        # 3. TERAPKAN TEKNIK B: TRUE GAUSSIAN BLUR MASK PADA LATAR BELAKANG
        print("Menerapkan efek Defocus Bokeh Blur Mask pada bagian atas dan bawah latar...")
        composite_bg = apply_top_bottom_blur_mask(bg_video, total_duration)

        # 4. SUSUN ELEMEN SUBTITLE DINAMIS (HOOK DI AWAL & PENJELASAN BERURUTAN DI TENGAH)
        layout_elements = generate_layout_elements(naskah, timings)

        print("Menggabungkan layer teks dan video latar...")
        all_layers = [composite_bg]
        for name, clip in layout_elements:
            all_layers.append(clip)

        final_video = CompositeVideoClip(all_layers, size=(VIDEO_WIDTH, VIDEO_HEIGHT)).set_duration(total_duration)

        # Ekstrak thumbnail dari detik ke-0.5
        os.makedirs(config.TEMP_DIR, exist_ok=True)
        thumbnail_path = os.path.join(config.TEMP_DIR, "thumbnail.jpg")
        try:
            frame = final_video.get_frame(min(0.5, total_duration / 2))
            thumb_img = Image.fromarray(frame).convert("RGB")
            thumb_img.save(thumbnail_path, format="JPEG", quality=90, optimize=True)
            print("✅ Thumbnail berhasil disimpan.")
        except Exception as e:
            print(f"Peringatan thumbnail: {e}")

        # 5. PASANG AUDIO (VOICEOVER + BGM)
        final_audio = create_composite_audio(master_voiceover_path, total_duration)
        if final_audio:
            final_video = final_video.set_audio(final_audio)

        # 6. EKSPOR FILE MP4 KILAT (ULTRAFAST + 4 THREADS)
        os.makedirs(config.TEMP_DIR, exist_ok=True)
        unique_id = uuid.uuid4().hex[:8]
        output_path = os.path.join(config.TEMP_DIR, f"final_{unique_id}.mp4")

        print(f"\nMengekspor video Shorts ({total_duration:.2f}s) dengan preset ultrafast...")
        final_video.write_videofile(
            output_path,
            fps=config.VIDEO_FPS,
            codec="libx264",
            bitrate="2500k",
            audio_codec="aac",
            audio_bitrate="128k",
            preset="ultrafast",
            threads=4,
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
        safe_close(composite_bg)
        safe_close(bg_video)
        safe_close(source_video)

        if 'layout_elements' in locals():
            for name, clip in layout_elements:
                safe_close(clip)

        gc.collect()

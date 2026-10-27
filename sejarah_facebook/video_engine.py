import os
import sys
import gc
import glob
import random
import uuid
import numpy as np

try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

from PIL import Image, ImageDraw, ImageFont

if not hasattr(Image, "ANTIALIAS"):
    Image.ANTIALIAS = Image.Resampling.LANCZOS

from moviepy.editor import (
    VideoFileClip,
    ImageClip,
    CompositeVideoClip,
    CompositeAudioClip,
    concatenate_videoclips,
    AudioFileClip,
    ColorClip,
    vfx
)
from moviepy.audio.fx.all import audio_loop

from . import config
from .tts_engine import generate_voiceover_for_scenes

# ==============================================================================
# PEMBUATAN LATAR BELAKANG SEJARAH (SLIDESHOW SINEMATIK)
# ==============================================================================
def fit_image_to_fullscreen_np(image_path):
    """Center-crop gambar ke resolusi 720x1280 vertikal 9:16."""
    with Image.open(image_path) as img:
        img = img.convert("RGB")
        w, h = img.size
        img_ratio = w / h
        target_ratio = config.VIDEO_WIDTH / config.VIDEO_HEIGHT

        if img_ratio > target_ratio:
            new_h = config.VIDEO_HEIGHT
            new_w = int(w * (new_h / h))
            img_resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            x1 = (new_w - config.VIDEO_WIDTH) // 2
            img_cropped = img_resized.crop((x1, 0, x1 + config.VIDEO_WIDTH, config.VIDEO_HEIGHT))
        else:
            new_w = config.VIDEO_WIDTH
            new_h = int(h * (new_w / w))
            img_resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            y1 = (new_h - config.VIDEO_HEIGHT) // 2
            img_cropped = img_resized.crop((0, y1, config.VIDEO_WIDTH, y1 + config.VIDEO_HEIGHT))

        return np.array(img_cropped)

def get_history_background_clip(total_duration):
    """
    Menghasilkan video latar bertema sejarah:
    - Mengambil gambar dari sejarah_facebook/assets/images/ (atau fallback ke aset root).
    - Rata-rata setiap gambar tampil 3.5 - 4.5 detik untuk menciptakan interupsi visual dokumenter.
    """
    image_extensions = ("*.jpg", "*.jpeg", "*.png", "*.webp")
    candidates = []

    # 1. Cek folder lokal sejarah_facebook/assets/images
    if os.path.exists(config.IMAGES_DIR):
        for ext in image_extensions:
            candidates.extend(glob.glob(os.path.join(config.IMAGES_DIR, ext)))

    if not candidates:
        print("⚠️ Folder 'sejarah_facebook/assets/images' masih kosong.")
        print("   Menunggu gambar khusus sejarah dari Flow dimasukkan...")

    if candidates:
        target_per_image = 4.0
        num_images = max(3, int(round(total_duration / target_per_image)))
        clip_duration = total_duration / num_images

        if len(candidates) >= num_images:
            chosen = random.sample(candidates, num_images)
        else:
            chosen = random.choices(candidates, k=num_images)

        print(f"🖼️ [Sejarah FB] Menggunakan {num_images} visual arsip (ganti tiap {clip_duration:.1f}s)")
        image_clips = []
        for p in chosen:
            try:
                np_frame = fit_image_to_fullscreen_np(p)
                clip = ImageClip(np_frame).set_duration(clip_duration)
                image_clips.append(clip)
            except Exception as e:
                print(f"⚠️ Peringatan gambar sejarah: {e}")

        if image_clips:
            return concatenate_videoclips(image_clips, method="compose").set_duration(total_duration)

    # 3. Fallback jika belum ada gambar sama sekali: kanvas temaram klasik
    return ColorClip(
        size=(config.VIDEO_WIDTH, config.VIDEO_HEIGHT),
        color=(18, 14, 12),  # Nuansa cokelat tua temaram kuno
        duration=total_duration
    ).set_position(("center", "center"))

# ==============================================================================
# DEFOCUS BOKEH BLUR MASK (ATAS & BAWAH)
# ==============================================================================
def apply_history_blur_mask(bg_video, total_duration):
    """Menerapkan defocus bokeh blur lembut di atas dan bawah latar belakang."""
    try:
        blurred_layer = (
            bg_video
            .resize(0.10)
            .resize((config.VIDEO_WIDTH, config.VIDEO_HEIGHT))
            .fx(vfx.colorx, 0.80)  # Sedikit lebih temaram (80%) agar nuansa sejarah lebih misterius
        )

        y_indices = np.arange(config.VIDEO_HEIGHT, dtype=np.float32)
        t_top = np.clip((y_indices - 220.0) / (340.0 - 220.0), 0.0, 1.0)
        mask_top = t_top * t_top * (3.0 - 2.0 * t_top)

        t_bot = np.clip((1060.0 - y_indices) / (1060.0 - 940.0), 0.0, 1.0)
        mask_bot = t_bot * t_bot * (3.0 - 2.0 * t_bot)

        mask_1d = np.minimum(mask_top, mask_bot)
        mask_2d = np.tile(mask_1d[:, np.newaxis], (1, config.VIDEO_WIDTH))

        mask_clip = ImageClip(mask_2d, ismask=True).set_duration(total_duration)
        sharp_layer = bg_video.set_mask(mask_clip)

        return CompositeVideoClip([blurred_layer, sharp_layer], size=(config.VIDEO_WIDTH, config.VIDEO_HEIGHT)).set_duration(total_duration)
    except Exception as e:
        print(f"⚠️ Blur mask fallback: {e}")
        return bg_video

# ==============================================================================
# WATERMARK BRANDING: "ARSIP SEJARAH"
# ==============================================================================
def create_brand_watermark(total_duration):
    """Membuat badge brand elegan di zona aman atas."""
    badge_w, badge_h = 210, 36
    img = Image.new("RGBA", (badge_w, badge_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Kotak pil temaram dengan garis batas emas halus
    draw.rounded_rectangle([(0, 0), (badge_w, badge_h)], radius=18, fill=(15, 23, 42, 210), outline=(245, 158, 11, 230), width=1)

    try:
        font = ImageFont.truetype(config.FONT_PATH, 16)
    except Exception:
        font = ImageFont.load_default()

    text = config.BRAND_WATERMARK
    bbox = font.getbbox(text)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    tx = (badge_w - tw) / 2
    ty = (badge_h - th) / 2 - 2

    draw.text((tx, ty), text, font=font, fill=(245, 158, 11, 255))

    rgb = np.array(img.convert("RGB"))
    alpha = np.array(img.split()[-1]) / 255.0

    mask = ImageClip(alpha, ismask=True).set_duration(total_duration)
    return ImageClip(rgb).set_mask(mask).set_position(("center", 240)).set_duration(total_duration)

# ==============================================================================
# SUBTITLE ENGINE KHUSUS SEJARAH (DI BAGIAN BAWAH ALA CAPCUT / VIRAL REELS)
# ==============================================================================
# Teks diposisikan di Lower-Third bawah, berlabuh rapi di atas area caption FB
BOTTOM_ANCHOR_Y = 1080  # Titik batas bawah teks

def render_history_text_clip(text, font_size, start, duration, max_width=640):
    try:
        font = ImageFont.truetype(config.FONT_PATH, font_size)
    except Exception:
        font = ImageFont.load_default()

    KEYWORDS_SEJARAH = {
        "SEJARAH", "MISTERI", "PERANG", "KERAJAAN", "MAJAPAHIT", "ROMAWI",
        "PIRAMIDA", "RAHASIA", "TAKTIK", "PASUKAN", "JENDERAL", "RAJA",
        "KAISAR", "HANCUR", "LENYAP", "BUNUH", "DARAH", "ARSIP", "KOMENTAR"
    }

    raw_words = text.strip().split()
    tokens = []
    has_stars = any("*" in w for w in raw_words)

    for w in raw_words:
        is_highlight = False
        if has_stars:
            if "*" in w:
                is_highlight = True
        else:
            clean = w.strip(".,!?:;\"'()[]")
            if clean.upper() in KEYWORDS_SEJARAH or any(c.isdigit() for c in clean):
                is_highlight = True
        display_w = w.replace("*", "")
        tokens.append((display_w, is_highlight))

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

    line_height = int(font_size * 1.25)
    padding_y = 14
    canvas_h = len(lines) * line_height + padding_y * 2
    canvas_w = config.VIDEO_WIDTH

    img = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    y = padding_y
    for line in lines:
        tot_w = sum(w[2] for w in line) + space_w * (len(line) - 1)
        x = (canvas_w - tot_w) / 2
        for word, hl, w_len in line:
            # Warna teks: Kuning Menyala (#FACC15) khas subtitle viral,
            # dengan kata penegas berwarna Putih Solid (#FFFFFF) yang sangat kontras
            fill_color = (255, 255, 255, 255) if hl else (250, 204, 21, 255)

            # 3D Drop Shadow halus di belakang (+2, +3)
            draw.text((x + 2, y + 3), word, font=font, fill=(0, 0, 0, 230), stroke_width=3, stroke_fill=(0, 0, 0, 230))
            # Teks utama dengan stroke hitam tebal 3.5px yang sangat tegas
            draw.text((x, y), word, font=font, fill=fill_color, stroke_width=3, stroke_fill=(0, 0, 0, 255))

            x += w_len + space_w
        y += line_height

    rgb = np.array(img.convert("RGB"))
    alpha = np.array(img.split()[-1]) / 255.0
    actual_y = int(BOTTOM_ANCHOR_Y - canvas_h)

    mask = ImageClip(alpha, ismask=True).set_start(start).set_duration(duration)
    return ImageClip(rgb).set_mask(mask).set_position((0, actual_y)).set_start(start).set_duration(duration)

# ==============================================================================
# AUDIO MIXING: DOKUMENTER BGM + SUARA ARDI
# ==============================================================================
def create_history_audio(voiceover_path, total_duration):
    try:
        vo = AudioFileClip(voiceover_path).volumex(config.VOICEOVER_VOLUME)
        elements = [vo]

        # Cari BGM di folder sejarah_facebook/assets/audio atau fallback ke root
        bgm_pool = glob.glob(os.path.join(config.AUDIO_DIR, "*.mp3"))
        if not bgm_pool:
            bgm_pool = glob.glob(os.path.join(config.ROOT_DIR, "assets", "audio", "setup", "*.mp3"))

        if bgm_pool:
            bgm_file = random.choice(bgm_pool)
            print(f"🎵 [Sejarah FB] BGM Dokumenter: {os.path.basename(bgm_file)}")
            bgm = AudioFileClip(bgm_file)
            if bgm.duration >= total_duration:
                bgm = bgm.subclip(0, total_duration)
            else:
                bgm = audio_loop(bgm, duration=total_duration)
            bgm = bgm.volumex(config.BGM_VOLUME)
            elements.insert(0, bgm)

        return CompositeAudioClip(elements).set_duration(total_duration)
    except Exception as e:
        print(f"⚠️ Audio mixing warning: {e}")
        return AudioFileClip(voiceover_path).set_duration(total_duration)

# ==============================================================================
# RENDER FINAL VIDEO SEJARAH FACEBOOK
# ==============================================================================
def render_history_video(naskah):
    print("\n============================================")
    print("   MEMULAI RENDER VIDEO SEJARAH FACEBOOK    ")
    print("============================================")

    scenes = naskah.get("scenes", [])
    if not scenes:
        raise ValueError("Naskah sejarah tidak memiliki scene.")

    # 1. Narasi Suara Dokumenter
    scene_timings, master_vo_path, total_duration = generate_voiceover_for_scenes(scenes)

    raw_bg = None
    composite_bg = None
    final_video = None
    final_audio = None
    brand_clip = None

    try:
        # 2. Latar Belakang Gambar Arsip Dinamis
        raw_bg = get_history_background_clip(total_duration)

        # 3. Defocus Bokeh Blur Mask
        composite_bg = apply_history_blur_mask(raw_bg, total_duration)

        # 4. Watermark Brand Dokumenter
        brand_clip = create_brand_watermark(total_duration)

        # 5. Susun Subtitle di Bagian Bawah Layar (Lower Third)
        all_layers = [composite_bg, brand_clip]

        for idx, sc in enumerate(scene_timings):
            txt = sc["text"].strip().upper()
            if not txt:
                continue
            # Font 38px rapi dan padat di bawah layar
            f_size = 40 if idx == 0 else 38
            clip = render_history_text_clip(txt, f_size, sc["start"], sc["duration"], max_width=640)
            all_layers.append(clip)

        final_video = CompositeVideoClip(all_layers, size=(config.VIDEO_WIDTH, config.VIDEO_HEIGHT)).set_duration(total_duration)

        # 6. Pasang Audio
        final_audio = create_history_audio(master_vo_path, total_duration)
        if final_audio:
            final_video = final_video.set_audio(final_audio)

        # 7. Ekspor MP4
        unique_id = uuid.uuid4().hex[:8]
        output_filename = f"sejarah_{unique_id}.mp4"
        output_path = os.path.join(config.OUTPUT_DIR, output_filename)

        print(f"\n🚀 Mengekspor Video Sejarah Facebook ({total_duration:.2f}s)...")
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

        print("\n============================================")
        print("     VIDEO SEJARAH FACEBOOK BERHASIL        ")
        print("============================================")
        print(f"File Output : {output_path}")
        print(f"Durasi      : {total_duration:.2f}s\n")

        return output_path

    finally:
        for c in [final_audio, final_video, composite_bg, raw_bg, brand_clip]:
            try:
                if c:
                    c.close()
            except Exception:
                pass
        gc.collect()

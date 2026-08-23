import os
import gc
import glob
import random
import uuid
import requests

from dotenv import load_dotenv

# ==========================================
# PILLOW COMPATIBILITY
# MoviePy 1.0.3 + Pillow terbaru
# ==========================================
from PIL import Image

if not hasattr(
    Image,
    "ANTIALIAS"
):
    Image.ANTIALIAS = (
        Image.Resampling.LANCZOS
    )


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
    AudioFileClip,
    CompositeAudioClip,
    ColorClip,
    vfx
)

from moviepy.audio.fx.all import (
    audio_loop
)


# ==========================================
# ENVIRONMENT
# ==========================================
load_dotenv()

PEXELS_API_KEY = os.getenv(
    "PEXELS_API_KEY"
)


# ==========================================
# VIDEO CONFIG
# ==========================================
VIDEO_WIDTH = 720
VIDEO_HEIGHT = 1280

TARGET_ASPECT_RATIO = (
    VIDEO_WIDTH / VIDEO_HEIGHT
)

# ==========================================
# DYNAMIC TIMING
# ==========================================
WORDS_PER_SECOND = 2.7

# Slide pembuka / title
TITLE_DURATION = 2.2

MIN_SETUP_DURATION = 2.5
MAX_SETUP_DURATION = 5.0

MIN_PUNCHLINE_DURATION = 1.8
MAX_PUNCHLINE_DURATION = 3.0

PUNCHLINE_PAUSE = 0.5

# Video tidak lagi dipaksa sekitar 10 detik.
# Durasi mengikuti kebutuhan joke, dengan batas yang lebih longgar.
MIN_TOTAL_DURATION = 9.0
MAX_TOTAL_DURATION = 18.0

# ==========================================
# TEXT
# ==========================================
TEXT_WIDTH = 580

TITLE_FONT_SIZE = 82
SETUP_FONT_SIZE = 60
PUNCHLINE_FONT_SIZE = 75


# ==========================================
# UTIL
# ==========================================
def count_words(text):

    if not text:
        return 0

    return len(
        text.strip().split()
    )


# ==========================================
# READING DURATION
# ==========================================
def calculate_reading_duration(
    text,
    min_duration,
    max_duration
):

    word_count = count_words(
        text
    )

    duration = (
        word_count
        / WORDS_PER_SECOND
    )

    duration = max(
        min_duration,
        duration
    )

    duration = min(
        max_duration,
        duration
    )

    return duration + 0.3


# ==========================================
# DYNAMIC TIMING
# ==========================================
def calculate_timings(naskah):

    title = naskah.get(
        "title",
        ""
    )

    setup1 = naskah.get(
        "setup_1",
        ""
    )

    setup2 = naskah.get(
        "setup_2",
        ""
    )

    punchline = naskah.get(
        "punchline",
        ""
    )

    # --------------------------------------
    # TITLE SLIDE
    # --------------------------------------
    durasi_title = TITLE_DURATION
    start_title = 0.0

    # --------------------------------------
    # CONTENT DURATIONS
    # --------------------------------------
    durasi_setup1 = (
        calculate_reading_duration(
            setup1,
            MIN_SETUP_DURATION,
            MAX_SETUP_DURATION
        )
    )

    durasi_setup2 = (
        calculate_reading_duration(
            setup2,
            MIN_SETUP_DURATION,
            MAX_SETUP_DURATION
        )
    )

    durasi_punchline = (
        calculate_reading_duration(
            punchline,
            MIN_PUNCHLINE_DURATION,
            MAX_PUNCHLINE_DURATION
        )
    )

    # Setup 1 dimulai setelah title slide.
    start_setup1 = (
        start_title
        + durasi_title
    )

    start_setup2 = (
        start_setup1
        + durasi_setup1
    )

    start_punchline = (
        start_setup2
        + durasi_setup2
        + PUNCHLINE_PAUSE
    )

    total_duration = (
        start_punchline
        + durasi_punchline
    )

    # --------------------------------------
    # MINIMUM TOTAL
    # --------------------------------------
    if total_duration < MIN_TOTAL_DURATION:

        tambahan = (
            MIN_TOTAL_DURATION
            - total_duration
        )

        durasi_setup2 += tambahan

        start_punchline = (
            start_setup2
            + durasi_setup2
            + PUNCHLINE_PAUSE
        )

        total_duration = (
            start_punchline
            + durasi_punchline
        )

    # --------------------------------------
    # MAXIMUM TOTAL
    # --------------------------------------
    if total_duration > MAX_TOTAL_DURATION:

        kelebihan = (
            total_duration
            - MAX_TOTAL_DURATION
        )

        # Kurangi setup 2 terlebih dahulu
        pengurangan = min(
            kelebihan,
            max(
                0,
                durasi_setup2
                - MIN_SETUP_DURATION
            )
        )

        durasi_setup2 -= pengurangan
        kelebihan -= pengurangan

        # Jika masih terlalu panjang, kurangi setup 1
        if kelebihan > 0:

            pengurangan = min(
                kelebihan,
                max(
                    0,
                    durasi_setup1
                    - MIN_SETUP_DURATION
                )
            )

            durasi_setup1 -= pengurangan
            kelebihan -= pengurangan

        # Recalculate positions
        start_setup2 = (
            start_setup1
            + durasi_setup1
        )

        start_punchline = (
            start_setup2
            + durasi_setup2
            + PUNCHLINE_PAUSE
        )

        total_duration = (
            start_punchline
            + durasi_punchline
        )

    print("")
    print(
        "========== DYNAMIC TIMING =========="
    )

    print(
        f"Title      : "
        f"{count_words(title)} kata "
        f"→ {durasi_title:.2f}s"
    )

    print(
        f"Setup 1    : "
        f"{count_words(setup1)} kata "
        f"→ {durasi_setup1:.2f}s"
    )

    print(
        f"Setup 2    : "
        f"{count_words(setup2)} kata "
        f"→ {durasi_setup2:.2f}s"
    )

    print(
        f"Pause      : "
        f"{PUNCHLINE_PAUSE:.2f}s"
    )

    print(
        f"Punchline  : "
        f"{count_words(punchline)} kata "
        f"→ {durasi_punchline:.2f}s"
    )

    print(
        f"TOTAL      : "
        f"{total_duration:.2f}s"
    )

    print(
        "===================================="
    )
    print("")

    return {
        "start_title": start_title,
        "dur_title": durasi_title,

        "start_setup1": start_setup1,
        "dur_setup1": durasi_setup1,

        "start_setup2": start_setup2,
        "dur_setup2": durasi_setup2,

        "start_punchline": start_punchline,
        "dur_punchline": durasi_punchline,

        "total_duration": total_duration
    }


# ==========================================
# PEXELS SEARCH
# ==========================================
def search_pexels(
    keyword,
    per_page=4
):

    if not PEXELS_API_KEY:
        return []

    url = (
        "https://api.pexels.com/videos/search"
        f"?query={keyword}"
        f"&orientation=portrait"
        f"&per_page={per_page}"
    )

    headers = {
        "Authorization": PEXELS_API_KEY
    }

    try:

        response = requests.get(
            url,
            headers=headers,
            timeout=30
        )

        if response.status_code != 200:

            print(
                f"Pexels error {response.status_code} "
                f"untuk keyword '{keyword}'"
            )

            return []

        data = response.json()

        return (
            data.get(
                "videos",
                []
            )
        )

    except requests.RequestException as e:

        print(
            f"Pexels request error: {e}"
        )

        return []

    except Exception as e:

        print(
            f"Pexels parsing error: {e}"
        )

        return []


# ==========================================
# CHOOSE VIDEO FILE
# ==========================================
def choose_video_file(
    video,
    target_duration
):

    files = video.get(
        "video_files",
        []
    )

    candidates = []

    for vf in files:

        link = vf.get(
            "link"
        )

        width = vf.get(
            "width",
            0
        )

        height = vf.get(
            "height",
            0
        )

        if not link:
            continue

        if width <= 0 or height <= 0:
            continue

        ratio = (
            width / height
        )

        portrait_penalty = abs(
            ratio
            - TARGET_ASPECT_RATIO
        )

        duration = video.get(
            "duration",
            0
        )

        # Score:
        # - portrait lebih baik
        # - resolusi cukup
        # - target duration lebih baik
        score = 0

        if height >= 1080:
            score += 5

        elif height >= 720:
            score += 3

        elif height >= 480:
            score += 1

        score -= (
            portrait_penalty * 10
        )

        if duration >= target_duration:
            score += 4

        candidates.append(
            (
                score,
                vf
            )
        )

    if not candidates:
        return None

    candidates.sort(
        key=lambda item: item[0],
        reverse=True
    )

    return candidates[0][1]


# ==========================================
# DOWNLOAD BACKGROUND
# ==========================================
def fetch_background_video(
    naskah,
    target_duration
):

    visual_context = naskah.get(
        "visual_context",
        ""
    )

    keywords = naskah.get(
        "bg_keywords",
        []
    )

    # Compatibility
    if not keywords:

        fallback = naskah.get(
            "bg_keyword"
        )

        if fallback:
            keywords = [
                fallback
            ]

    print("")
    print(
        "========== VISUAL SEARCH =========="
    )

    print(
        f"Visual context: "
        f"{visual_context}"
    )

    print(
        f"Keywords: "
        f"{keywords}"
    )

    print(
        "==================================="
    )

    if not PEXELS_API_KEY:

        print(
            "PEXELS_API_KEY tidak ditemukan."
        )

        return None

    all_candidates = []

    # --------------------------------------
    # Cari dari beberapa keyword
    # --------------------------------------
    for keyword in keywords[:4]:

        print(
            f"Mencari Pexels: '{keyword}'"
        )

        videos = search_pexels(
            keyword,
            per_page=4
        )

        for video in videos:

            video["_search_keyword"] = (
                keyword
            )

            all_candidates.append(
                video
            )

    if not all_candidates:

        print(
            "Tidak ada kandidat Pexels."
        )

        return None

    # --------------------------------------
    # Evaluasi kandidat
    # --------------------------------------
    ranked = []

    for video in all_candidates:

        selected_file = (
            choose_video_file(
                video,
                target_duration
            )
        )

        if not selected_file:
            continue

        width = selected_file.get(
            "width",
            0
        )

        height = selected_file.get(
            "height",
            0
        )

        ratio = (
            width / height
            if height
            else 0
        )

        aspect_penalty = abs(
            ratio
            - TARGET_ASPECT_RATIO
        )

        duration = video.get(
            "duration",
            0
        )

        score = 0

        # ----------------------------------
        # Aspect ratio
        # ----------------------------------
        score -= (
            aspect_penalty * 20
        )

        # ----------------------------------
        # Portrait
        # ----------------------------------
        if height > width:
            score += 10

        # ----------------------------------
        # Duration
        # ----------------------------------
        if duration >= target_duration:
            score += 8
        else:
            score -= (
                target_duration
                - duration
            )

        # ----------------------------------
        # Resolution
        # ----------------------------------
        if height >= 1080:
            score += 6

        elif height >= 720:
            score += 4

        elif height >= 480:
            score += 2

        ranked.append(
            {
                "score": score,
                "video": video,
                "file": selected_file
            }
        )

    if not ranked:

        print(
            "Tidak ada kandidat video yang valid."
        )

        return None

    ranked.sort(
        key=lambda item: item["score"],
        reverse=True
    )

    best = ranked[0]

    selected_video = best["video"]
    selected_file = best["file"]

    keyword_used = selected_video.get(
        "_search_keyword",
        ""
    )

    print(
        f"Video terpilih dari keyword: "
        f"{keyword_used}"
    )

    print(
        f"Video score: "
        f"{best['score']:.2f}"
    )

    print(
        f"Resolution: "
        f"{selected_file.get('width')}x"
        f"{selected_file.get('height')}"
    )

    # ======================================
    # DOWNLOAD + VALIDATE BACKGROUND
    # ======================================
    os.makedirs(
        "temp",
        exist_ok=True
    )

    # Coba beberapa kandidat terbaik sampai menemukan
    # file yang benar-benar bisa dibaca MoviePy/FFmpeg.
    for candidate_index, candidate in enumerate(ranked[:4], start=1):

        selected_video = candidate["video"]
        selected_file = candidate["file"]

        video_url = selected_file.get(
            "link"
        )

        if not video_url:
            print(
                f"Kandidat #{candidate_index}: link video kosong."
            )
            continue

        unique_id = uuid.uuid4().hex[:12]

        output_path = os.path.join(
            "temp",
            f"bg_{unique_id}.mp4"
        )

        try:

            print(
                f"Download kandidat background #{candidate_index}..."
            )

            response = requests.get(
                video_url,
                timeout=60
            )

            if response.status_code != 200:

                print(
                    f"Download gagal. HTTP {response.status_code}."
                )
                continue

            content = response.content

            # File yang sangat kecil hampir pasti bukan video valid.
            if len(content) < 10000:

                print(
                    f"File background terlalu kecil: {len(content)} bytes."
                )
                continue

            with open(
                output_path,
                "wb"
            ) as file:

                file.write(content)

            print(
                f"Background tersimpan: {output_path}"
            )

            # Validasi langsung dengan MoviePy. Konstruktor VideoFileClip
            # membaca frame pertama sehingga file yang rusak/tidak kompatibel
            # akan terdeteksi sebelum masuk ke proses render utama.
            test_clip = None

            try:
                test_clip = VideoFileClip(
                    output_path,
                    audio=False
                )

                if (
                    not test_clip.w
                    or not test_clip.h
                    or not test_clip.duration
                ):
                    raise ValueError(
                        "Metadata video tidak valid."
                    )

                print(
                    f"Background valid: {test_clip.w}x{test_clip.h}, "
                    f"{test_clip.duration:.2f}s"
                )

                return output_path

            except Exception as validation_error:

                print(
                    "Background tidak dapat dibaca MoviePy/FFmpeg: "
                    f"{type(validation_error).__name__}: {validation_error}"
                )

                try:
                    if test_clip:
                        test_clip.close()
                except Exception:
                    pass

                try:
                    if os.path.exists(output_path):
                        os.remove(output_path)
                except Exception:
                    pass

                continue

            finally:
                try:
                    if test_clip:
                        test_clip.close()
                except Exception:
                    pass

        except requests.RequestException as e:

            print(
                f"Download Pexels error: {e}"
            )

            try:
                if os.path.exists(output_path):
                    os.remove(output_path)
            except Exception:
                pass

        except Exception as e:

            print(
                f"Background download/validation error: {type(e).__name__}: {e}"
            )

            try:
                if os.path.exists(output_path):
                    os.remove(output_path)
            except Exception:
                pass

    print(
        "Semua kandidat background gagal di-download atau divalidasi."
    )

    return None


# ==========================================
# FIT 9:16
# ==========================================
def fit_video_to_vertical(
    video
):

    current_width = video.w
    current_height = video.h

    if not current_width or not current_height:

        return video

    current_ratio = (
        current_width
        / current_height
    )

    print(
        f"Background asli: "
        f"{current_width}x"
        f"{current_height}"
    )

    # ======================================
    # TERLALU LEBAR
    # ======================================
    if (
        current_ratio
        > TARGET_ASPECT_RATIO
    ):

        video = video.resize(
            height=VIDEO_HEIGHT
        )

        new_width = video.w

        x1 = (
            new_width
            - VIDEO_WIDTH
        ) / 2

        x2 = (
            x1
            + VIDEO_WIDTH
        )

        video = video.crop(
            x1=x1,
            y1=0,
            x2=x2,
            y2=VIDEO_HEIGHT
        )

    # ======================================
    # TERLALU TINGGI
    # ======================================
    else:

        video = video.resize(
            width=VIDEO_WIDTH
        )

        new_height = video.h

        y1 = (
            new_height
            - VIDEO_HEIGHT
        ) / 2

        y2 = (
            y1
            + VIDEO_HEIGHT
        )

        video = video.crop(
            x1=0,
            y1=y1,
            x2=VIDEO_WIDTH,
            y2=y2
        )

    print(
        f"Background final: "
        f"{video.w}x{video.h}"
    )

    return video


# ==========================================
# TEXT
# ==========================================
def create_text_clip(
    text,
    fontsize,
    color,
    start,
    duration,
    stroke_width
):
    return (
        TextClip(
            text,
            fontsize=fontsize,
            color=color,
            method="caption",
            size=(
                TEXT_WIDTH,
                None
            ),
            font="DejaVu-Sans-Bold",
            align="center",
            stroke_color="black",
            stroke_width=stroke_width
        )
        .set_position(
            ("center", "center")
        )
        .set_start(
            start
        )
        .set_duration(
            duration
        )
    )


# ==========================================
# TEXT OVERLAY
# ==========================================
def generate_text_overlay(
    naskah,
    timings
):

    print(
        "Membuat tata letak teks..."
    )

    # --------------------------------------
    # TITLE / OPENING HOOK
    # --------------------------------------
    title_text = (
        naskah.get(
            "title",
            ""
        )
        .strip()
        .upper()
    )

    txt_title = create_text_clip(
        title_text,
        TITLE_FONT_SIZE,
        "yellow",
        timings["start_title"],
        timings["dur_title"],
        4
    )

    # --------------------------------------
    # SETUP 1
    # --------------------------------------
    txt_setup1 = create_text_clip(
        naskah["setup_1"],
        SETUP_FONT_SIZE,
        "white",
        timings["start_setup1"],
        timings["dur_setup1"],
        2
    )

    # --------------------------------------
    # SETUP 2
    # --------------------------------------
    txt_setup2 = create_text_clip(
        naskah["setup_2"],
        SETUP_FONT_SIZE,
        "white",
        timings["start_setup2"],
        timings["dur_setup2"],
        2
    )

    # --------------------------------------
    # PUNCHLINE
    # --------------------------------------
    txt_punchline = create_text_clip(
        naskah["punchline"],
        PUNCHLINE_FONT_SIZE,
        "yellow",
        timings["start_punchline"],
        timings["dur_punchline"],
        3
    )

    return [
        txt_title,
        txt_setup1,
        txt_setup2,
        txt_punchline
    ]


# ==========================================
# AUDIO
# ==========================================
def create_audio(
    timings
):

    final_audio = None
    audio_setup = None
    audio_punchline = None

    try:

        setup_pool = glob.glob(
            "assets/audio/setup/*.mp3"
        )

        punchline_pool = glob.glob(
            "assets/audio/punchline/*.mp3"
        )

        if not setup_pool:

            print(
                "Audio setup tidak tersedia."
            )

            return None

        if not punchline_pool:

            print(
                "Audio punchline tidak tersedia."
            )

            return None

        # ==================================
        # SETUP
        # ==================================
        setup_source = AudioFileClip(
            random.choice(
                setup_pool
            )
        )

        setup_duration = (
            timings["start_punchline"]
        )

        if (
            setup_source.duration
            >= setup_duration
        ):

            audio_setup = (
                setup_source
                .subclip(
                    0,
                    setup_duration
                )
            )

        else:

            audio_setup = audio_loop(
                setup_source,
                duration=setup_duration
            )

        # ==================================
        # PUNCHLINE
        # ==================================
        punchline_source = (
            AudioFileClip(
                random.choice(
                    punchline_pool
                )
            )
        )

        punchline_duration = (
            timings["dur_punchline"]
        )

        if (
            punchline_source.duration
            >= punchline_duration
        ):

            audio_punchline = (
                punchline_source
                .subclip(
                    0,
                    punchline_duration
                )
                .set_start(
                    timings["start_punchline"]
                )
            )

        else:

            audio_punchline = (
                audio_loop(
                    punchline_source,
                    duration=punchline_duration
                )
                .set_start(
                    timings["start_punchline"]
                )
            )

        final_audio = (
            CompositeAudioClip(
                [
                    audio_setup,
                    audio_punchline
                ]
            )
            .set_duration(
                timings["total_duration"]
            )
        )

        return final_audio

    except Exception as e:

        print(
            f"Peringatan Audio: {e}"
        )

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
def render_final_video(
    naskah
):

    print("")
    print(
        "===================================="
    )
    print(
        "         MULAI RENDER VIDEO"
    )
    print(
        "===================================="
    )

    timings = calculate_timings(
        naskah
    )

    bg_path = None
    source_video = None
    video = None
    final_video = None
    final_audio = None
    text_clips = []

    try:

        # ==================================
        # GET BACKGROUND
        # ==================================
        bg_path = (
            fetch_background_video(
                naskah,
                timings["total_duration"]
            )
        )

        # ==================================
        # BACKGROUND
        # ==================================
        if (
            bg_path
            and os.path.exists(
                bg_path
            )
        ):

            print(
                "Membuka background video..."
            )

            source_video = (
                VideoFileClip(
                    bg_path
                )
            )

            source_video = (
                fit_video_to_vertical(
                    source_video
                )
            )

            # ==================================
            # DURASI
            # ==================================
            if (
                source_video.duration
                >= timings["total_duration"]
            ):

                video = (
                    source_video
                    .subclip(
                        0,
                        timings["total_duration"]
                    )
                )

            else:

                print(
                    "Background lebih pendek "
                    "dari kebutuhan. Loop..."
                )

                video = (
                    source_video
                    .fx(
                        vfx.loop,
                        duration=timings[
                            "total_duration"
                        ]
                    )
                )

            video = (
                video
                .set_duration(
                    timings["total_duration"]
                )
            )

        else:

            print(
                "Background gagal. "
                "Menggunakan warna hitam."
            )

            video = ColorClip(
                size=(
                    VIDEO_WIDTH,
                    VIDEO_HEIGHT
                ),
                color=(
                    0,
                    0,
                    0
                ),
                duration=timings[
                    "total_duration"
                ]
            )

        # ==================================
        # DARKEN BACKGROUND
        # ==================================
        video = video.fx(
            vfx.colorx,
            0.5
        )

        # ==================================
        # TEXT
        # ==================================
        text_clips = (
            generate_text_overlay(
                naskah,
                timings
            )
        )

        # ==================================
        # COMPOSITE
        # ==================================
        final_video = (
            CompositeVideoClip(
                [video] + text_clips,
                size=(
                    VIDEO_WIDTH,
                    VIDEO_HEIGHT
                )
            )
            .set_duration(
                timings["total_duration"]
            )
        )

        # ==================================
        # AUDIO
        # ==================================
        final_audio = create_audio(
            timings
        )

        if final_audio:

            final_video = (
                final_video
                .set_audio(
                    final_audio
                )
            )

        # ==================================
        # OUTPUT UNIQUE
        # ==================================
        os.makedirs(
            "temp",
            exist_ok=True
        )

        unique_id = uuid.uuid4().hex[:12]

        output_path = os.path.join(
            "temp",
            f"final_{unique_id}.mp4"
        )

        # ==================================
        # EXPORT
        # ==================================
        print("")
        print(
            "Mengekspor video..."
        )

        final_video.write_videofile(
            output_path,
            fps=24,
            codec="libx264",
            audio_codec="aac",
            preset="ultrafast",
            logger=None
        )

        print("")
        print(
            "===================================="
        )

        print(
            "       VIDEO SELESAI DIBUAT"
        )

        print(
            "===================================="
        )

        print(
            f"Durasi: "
            f"{timings['total_duration']:.2f}s"
        )

        print(
            f"Output: "
            f"{output_path}"
        )

        return output_path

    except Exception as e:

        print("")
        print(
            "ERROR SAAT RENDER VIDEO:"
        )

        print(
            f"{type(e).__name__}: {e}"
        )

        import traceback
        traceback.print_exc()

        return None

    finally:

        # ==================================
        # CLOSE RESOURCES
        # ==================================
        safe_close(
            final_audio
        )

        safe_close(
            final_video
        )

        safe_close(
            video
        )

        safe_close(
            source_video
        )

        for clip in text_clips:

            safe_close(
                clip
            )

        # ==================================
        # DELETE RAW BACKGROUND
        # ==================================
        if (
            bg_path
            and os.path.exists(
                bg_path
            )
        ):

            try:

                os.remove(
                    bg_path
                )

                print(
                    f"Temporary background "
                    f"dihapus: {bg_path}"
                )

            except Exception:

                pass

        gc.collect()
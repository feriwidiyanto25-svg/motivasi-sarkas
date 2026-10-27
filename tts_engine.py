import os
import time
import asyncio
import uuid
import random
from pathlib import Path
import edge_tts
import config

# Pilihan suara 2 mode: Pria & Wanita (acak / bergantian per video)
VOICE_CHOICES = ["id-ID-ArdiNeural", "id-ID-GadisNeural"]

async def _generate_single_audio_async(text: str, output_path: str, voice: str = None, rate: str = None) -> str:
    voice = voice or config.TTS_VOICE
    rate = rate or config.TTS_RATE
    last_error = None

    # Retry loop hingga 3 kali dengan jeda singkat untuk mengatasi fluktuasi koneksi Edge TTS
    for attempt in range(1, 4):
        try:
            communicate = edge_tts.Communicate(text, voice, rate=rate)
            await communicate.save(output_path)
            if os.path.exists(output_path) and os.path.getsize(output_path) > 500:
                return output_path
        except Exception as e:
            last_error = e
            await asyncio.sleep(0.5 * attempt)

    # Jika 3x percobaan gagal, fallback ke suara alternatif
    fallback_voice = "id-ID-GadisNeural" if voice != "id-ID-GadisNeural" else "id-ID-ArdiNeural"
    try:
        communicate = edge_tts.Communicate(text, fallback_voice, rate=rate)
        await communicate.save(output_path)
        if os.path.exists(output_path) and os.path.getsize(output_path) > 500:
            return output_path
    except Exception as e:
        last_error = e

    if last_error:
        raise last_error
    return output_path

def generate_single_audio(text: str, output_path: str, voice: str = None, rate: str = None) -> str:
    """Menghasilkan file audio MP3 dari teks tunggal dengan proteksi retry."""
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    asyncio.run(_generate_single_audio_async(text, output_path, voice, rate))
    return output_path

def generate_voiceover_for_scenes(scenes: list, output_dir: str = None, voice: str = None) -> tuple:
    """
    Menghasilkan file audio untuk setiap scene naskah secara individual.
    Mendukung 2 mode suara: Pria (Ardi) dan Wanita (Gadis) secara acak per video.
    Mengembalikan:
      - scene_timings: list dict berisi 'name', 'text', 'start', 'duration', 'audio_path'
      - master_voiceover_path: path file MP3 gabungan seluruh narasi
      - total_duration: float durasi total
    """
    from moviepy.editor import AudioFileClip, concatenate_audioclips

    if not output_dir:
        output_dir = os.path.join(config.TEMP_DIR, f"tts_{uuid.uuid4().hex[:8]}")
    os.makedirs(output_dir, exist_ok=True)

    # Pilih suara: jika tidak ditentukan secara manual, acak antara Pria dan Wanita
    if not voice:
        voice = random.choice(VOICE_CHOICES)

    gender_label = "Pria (Ardi)" if "Ardi" in voice else "Wanita (Gadis)"

    scene_timings = []
    audio_clips = []
    current_time = 0.0

    print(f"\n🎙️ Meng-generate Voiceover ({voice} - {gender_label})...")

    for i, scene_text in enumerate(scenes, start=1):
        clean_text = scene_text.strip()
        if not clean_text:
            continue

        # Hilangkan simbol format penegas (*) khusus saat dikirim ke TTS agar suara terdengar mulus dan natural
        spoken_text = clean_text.replace("*", "")
        audio_file = os.path.join(output_dir, f"scene_{i:02d}.mp3")
        generate_single_audio(spoken_text, audio_file, voice=voice)

        # Jeda sangat singkat (0.2s) untuk stabilitas socket koneksi Edge TTS
        time.sleep(0.2)

        # Ukur durasi audio yang dihasilkan
        clip = AudioFileClip(audio_file)
        dur = clip.duration

        # Durasi tampilan teks persis 1:1 dengan durasi audio (menghindari audio drift)
        scene_duration = dur

        scene_timings.append({
            "name": f"scene_{i}",
            "text": clean_text.upper(),
            "start": current_time,
            "duration": scene_duration,
            "audio_duration": dur,
            "audio_path": audio_file
        })

        audio_clips.append(clip)
        current_time += scene_duration
        print(f"  [{i}/{len(scenes)}] {dur:.2f}s -> {spoken_text[:35]}...")

    if not audio_clips:
        raise ValueError("Tidak ada scene teks yang valid untuk di-generate suaranya.")

    # Gabungkan seluruh potongan audio menjadi satu file master audio
    master_audio = concatenate_audioclips(audio_clips)
    master_path = os.path.join(output_dir, "master_voiceover.mp3")
    master_audio.write_audiofile(master_path, fps=44100, nbytes=2, codec="libmp3lame", verbose=False, logger=None)

    total_duration = current_time

    # Tutup temporary audio clips
    for c in audio_clips:
        try:
            c.close()
        except Exception:
            pass
    try:
        master_audio.close()
    except Exception:
        pass

    print(f"✅ Voiceover selesai ({gender_label}): {total_duration:.2f}s ({len(scene_timings)} scenes)")
    return scene_timings, master_path, total_duration

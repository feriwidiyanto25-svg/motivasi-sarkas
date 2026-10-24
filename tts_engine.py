import os
import asyncio
import uuid
from pathlib import Path
import edge_tts
import config

async def _generate_single_audio_async(text: str, output_path: str, voice: str = None, rate: str = None) -> str:
    voice = voice or config.TTS_VOICE
    rate = rate or config.TTS_RATE
    communicate = edge_tts.Communicate(text, voice, rate=rate)
    await communicate.save(output_path)
    return output_path

def generate_single_audio(text: str, output_path: str, voice: str = None, rate: str = None) -> str:
    """Menghasilkan file audio MP3 dari teks tunggal."""
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    asyncio.run(_generate_single_audio_async(text, output_path, voice, rate))
    return output_path

def generate_voiceover_for_scenes(scenes: list, output_dir: str = None, voice: str = None) -> tuple:
    """
    Menghasilkan file audio untuk setiap scene naskah secara individual.
    Mengembalikan:
      - scene_timings: list dict berisi 'name', 'text', 'start', 'duration', 'audio_path'
      - master_voiceover_path: path file MP3 gabungan seluruh narasi
      - total_duration: float durasi total
    """
    from moviepy.editor import AudioFileClip, concatenate_audioclips

    if not output_dir:
        output_dir = os.path.join(config.TEMP_DIR, f"tts_{uuid.uuid4().hex[:8]}")
    os.makedirs(output_dir, exist_ok=True)

    voice = voice or config.TTS_VOICE
    scene_timings = []
    audio_clips = []
    current_time = 0.0

    print(f"\n🎙️ Meng-generate Voiceover ({voice})...")

    for i, scene_text in enumerate(scenes, start=1):
        clean_text = scene_text.strip()
        if not clean_text:
            continue

        # Hilangkan simbol format penegas (*) khusus saat dikirim ke TTS agar suara terdengar mulus dan natural
        spoken_text = clean_text.replace("*", "")
        audio_file = os.path.join(output_dir, f"scene_{i:02d}.mp3")
        generate_single_audio(spoken_text, audio_file, voice=voice)

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

    print(f"✅ Voiceover selesai: {total_duration:.2f}s ({len(scene_timings)} scenes)")
    return scene_timings, master_path, total_duration

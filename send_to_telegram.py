import json
import os
from pathlib import Path

import requests


def main() -> None:
    bot_token = os.environ.get(
        "TELEGRAM_BOT_TOKEN",
        ""
    ).strip()

    chat_id = os.environ.get(
        "CHAT_ID",
        ""
    ).strip()

    run_id = os.environ.get(
        "GITHUB_RUN_ID",
        ""
    ).strip()

    if not bot_token:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN belum tersedia."
        )

    if not chat_id:
        raise RuntimeError(
            "CHAT_ID belum tersedia."
        )

    if not run_id:
        raise RuntimeError(
            "GITHUB_RUN_ID belum tersedia."
        )

    temp_dir = Path("temp")

    # ==================================================
    # CARI VIDEO
    # ==================================================

    videos = sorted(
        temp_dir.glob("*.mp4"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    if not videos:
        raise RuntimeError(
            "File MP4 hasil render tidak ditemukan."
        )

    video_path = videos[0]

    # ==================================================
    # BACA YOUTUBE.JSON
    # ==================================================

    youtube_path = (
        temp_dir / "youtube.json"
    )

    if not youtube_path.exists():
        raise RuntimeError(
            "youtube.json tidak ditemukan."
        )

    with youtube_path.open(
        "r",
        encoding="utf-8"
    ) as file:
        metadata = json.load(file)

    title = str(
        metadata.get(
            "title",
            ""
        )
    ).strip()

    description = str(
        metadata.get(
            "description",
            ""
        )
    ).strip()

    hashtags = metadata.get(
        "hashtags",
        []
    )

    if not isinstance(
        hashtags,
        list
    ):
        hashtags = []

    hashtags_text = " ".join(
        str(item).strip()
        for item in hashtags
        if str(item).strip()
    )

    # ==================================================
    # KIRIM VIDEO
    # ==================================================

    caption = (
        "🎬 VIDEO SELESAI\n\n"
        f"Title:\n{title}"
    )

    response = requests.post(
        f"https://api.telegram.org/"
        f"bot{bot_token}/sendVideo",
        data={
            "chat_id": chat_id,
            "caption": caption[:1024],
        },
        files={
            "video": (
                video_path.name,
                video_path.open("rb"),
                "video/mp4",
            )
        },
        timeout=600,
    )

    response.raise_for_status()

    print(
        "✅ Video berhasil dikirim ke Telegram."
    )

    # ==================================================
    # METADATA + TOMBOL UPLOAD
    # ==================================================

    metadata_text = (
        "📝 YOUTUBE METADATA\n\n"
        f"Title:\n{title}\n\n"
        f"Description:\n{description}\n\n"
        f"Hashtags:\n{hashtags_text}"
    )

    # run_id disimpan di callback_data.
    # Contoh:
    # upload:32814639663
    reply_markup = {
        "inline_keyboard": [
            [
                {
                    "text": "📺 Upload YouTube",
                    "callback_data": f"upload:{run_id}",
                }
            ]
        ]
    }

    response = requests.post(
        f"https://api.telegram.org/"
        f"bot{bot_token}/sendMessage",
        json={
            "chat_id": chat_id,
            "text": metadata_text,
            "reply_markup": reply_markup,
        },
        timeout=60,
    )

    response.raise_for_status()

    print(
        "✅ Metadata berhasil dikirim ke Telegram."
    )

    print(
        f"✅ Upload button menggunakan run_id: {run_id}"
    )


if __name__ == "__main__":
    main()

import json
import os
from pathlib import Path

import requests

from youtube_uploader import YouTubeUploader


def send_telegram(bot_token: str, chat_id: str, text: str) -> None:
    response = requests.post(
        f"https://api.telegram.org/bot{bot_token}/sendMessage",
        json={"chat_id": chat_id, "text": text},
        timeout=60,
    )
    response.raise_for_status()


def main() -> None:
    bot_token = os.environ["TELEGRAM_BOT_TOKEN"].strip()
    chat_id = os.environ["CHAT_ID"].strip()
    video_path = Path(os.environ["VIDEO_PATH"])
    metadata_path = Path(os.environ["YOUTUBE_JSON"])

    with metadata_path.open("r", encoding="utf-8") as file:
        metadata = json.load(file)

    title = str(metadata.get("title", "")).strip()
    description = str(metadata.get("description", "")).strip()
    hashtags = metadata.get("hashtags", [])

    if not title:
        raise RuntimeError("Title YouTube kosong.")
    if not video_path.exists():
        raise RuntimeError(f"Video tidak ditemukan: {video_path}")
    if not isinstance(hashtags, list):
        hashtags = []

    hashtag_text = " ".join(
        str(item).strip() for item in hashtags if str(item).strip()
    )
    if hashtag_text:
        description = description.rstrip() + "\n\n" + hashtag_text

    try:
        uploader = YouTubeUploader()
        result = uploader.upload_video(
            video_path=str(video_path),
            title=title,
            description=description,
            privacy_status="public",
        )

        if not isinstance(result, dict) or not result.get("id"):
            raise RuntimeError(f"Response YouTube tidak valid: {result}")

        video_id = result["id"]
        youtube_url = f"https://www.youtube.com/watch?v={video_id}"

        send_telegram(
            bot_token,
            chat_id,
            "✅ UPLOAD YOUTUBE BERHASIL\n\n"
            f"Title:\n{title}\n\n"
            f"YouTube:\n{youtube_url}",
        )

        print(f"✅ YouTube upload berhasil: {youtube_url}")
    except Exception as exc:
        try:
            send_telegram(
                bot_token,
                chat_id,
                "❌ UPLOAD YOUTUBE GAGAL\n\n"
                f"{type(exc).__name__}: {exc}",
            )
        finally:
            raise


if __name__ == "__main__":
    main()

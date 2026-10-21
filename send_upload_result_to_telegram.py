import json
import os
from pathlib import Path

import requests


def main() -> None:
    bot_token = os.environ.get(
        "TELEGRAM_BOT_TOKEN",
        "",
    ).strip()

    chat_id = os.environ.get(
        "CHAT_ID",
        "",
    ).strip()

    outcome = os.environ.get(
        "UPLOAD_OUTCOME",
        "",
    ).strip().lower()

    run_url = os.environ.get(
        "GITHUB_RUN_URL",
        "",
    ).strip()

    if not bot_token:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN belum tersedia."
        )

    if not chat_id:
        raise RuntimeError(
            "CHAT_ID belum tersedia."
        )

    if outcome == "success":
        result_path = Path(
            "youtube_upload_result.json"
        )

        if result_path.exists():
            with result_path.open(
                "r",
                encoding="utf-8",
            ) as file:
                result = json.load(file)

            title = str(
                result.get("title", "")
            ).strip()

            youtube_url = str(
                result.get("youtube_url", "")
            ).strip()

            message = (
                "✅ UPLOAD YOUTUBE BERHASIL\n\n"
                f"Title:\n{title}\n\n"
                f"YouTube:\n{youtube_url}"
            )

        else:
            message = (
                "✅ UPLOAD YOUTUBE BERHASIL.\n\n"
                "Video sudah selesai di-upload ke YouTube."
            )

    else:
        message = (
            "❌ UPLOAD YOUTUBE GAGAL\n\n"
            "Proses upload berhenti di GitHub Actions.\n"
        )

        if run_url:
            message += (
                f"\nLihat detail proses:\n{run_url}"
            )

    response = requests.post(
        f"https://api.telegram.org/bot{bot_token}/sendMessage",
        json={
            "chat_id": chat_id,
            "text": message,
        },
        timeout=60,
    )

    if not response.ok:
        raise RuntimeError(
            "Gagal mengirim response upload ke Telegram: "
            f"{response.text}"
        )

    print(
        f"✅ Response upload ({outcome or 'unknown'}) "
        "berhasil dikirim ke Telegram."
    )


if __name__ == "__main__":
    main()

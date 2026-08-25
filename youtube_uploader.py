import json
import os
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload


class YouTubeUploader:

    SCOPES = [
        "https://www.googleapis.com/auth/youtube.upload"
    ]

    def __init__(self):

        self.secrets_dir = Path("secrets")

        self.credentials_file = (
            self.secrets_dir / "credentials.json"
        )

        self.token_file = (
            self.secrets_dir / "token.json"
        )

    def authenticate(self):

        creds = None

        if self.token_file.exists():

            creds = Credentials.from_authorized_user_file(
                str(self.token_file),
                self.SCOPES,
            )

        if not creds or not creds.valid:

            if (
                creds
                and creds.expired
                and creds.refresh_token
            ):

                creds.refresh(
                    Request()
                )

            else:

                flow = (
                    InstalledAppFlow
                    .from_client_secrets_file(
                        str(self.credentials_file),
                        self.SCOPES,
                    )
                )

                creds = (
                    flow.run_local_server(
                        port=0
                    )
                )

            with open(
                self.token_file,
                "w"
            ) as token:

                token.write(
                    creds.to_json()
                )

        return creds

    def get_service(self):

        creds = self.authenticate()

        return build(
            "youtube",
            "v3",
            credentials=creds,
        )

    def upload_video(
        self,
        video_path,
        title,
        description,
        tags=None,
        category_id="25",
        privacy_status="public",
    ):

        youtube = self.get_service()

        body = {
            "snippet": {
                "title": title,
                "description": description,
                "tags": tags or [],
                "categoryId": category_id,
            },
            "status": {
                "privacyStatus": privacy_status,
            },
        }

        media = MediaFileUpload(
            video_path,
            resumable=True,
        )

        request = youtube.videos().insert(
            part="snippet,status",
            body=body,
            media_body=media,
        )

        print("Uploading video...")

        response = None

        while response is None:

            status, response = (
                request.next_chunk()
            )

            if status:

                print(
                    f"Progress : "
                    f"{int(status.progress() * 100)}%"
                )

        print("Upload selesai.")

        return response

    def set_thumbnail(
        self,
        video_id,
        thumbnail_path,
    ):
        """
        Set custom thumbnail untuk video YouTube.

        Fungsi ini sengaja berdiri sendiri agar proses upload video
        yang sudah berjalan tetap sama. Bila thumbnail gagal, caller
        dapat menangani error tanpa membatalkan video yang sudah
        berhasil di-upload.
        """

        thumbnail_file = Path(thumbnail_path)

        if not thumbnail_file.exists():
            raise RuntimeError(
                f"Thumbnail tidak ditemukan: {thumbnail_file}"
            )

        if thumbnail_file.stat().st_size <= 0:
            raise RuntimeError(
                f"Thumbnail kosong: {thumbnail_file}"
            )

        suffix = thumbnail_file.suffix.lower()

        if suffix in (".jpg", ".jpeg"):
            mimetype = "image/jpeg"
        elif suffix == ".png":
            mimetype = "image/png"
        else:
            raise RuntimeError(
                "Format thumbnail tidak didukung. "
                "Gunakan JPG/JPEG atau PNG."
            )

        youtube = self.get_service()

        media = MediaFileUpload(
            str(thumbnail_file),
            mimetype=mimetype,
            resumable=False,
        )

        print(
            "Mengatur custom thumbnail..."
        )

        request = (
            youtube
            .thumbnails()
            .set(
                videoId=video_id,
                media_body=media,
            )
        )

        response = request.execute()

        print(
            "✅ Custom thumbnail berhasil diset."
        )

        return response


# ==========================================================
# GITHUB ACTIONS DIRECT EXECUTION
# ==========================================================

if __name__ == "__main__":

    video_path = os.environ.get(
        "VIDEO_PATH",
        ""
    ).strip()

    youtube_json = os.environ.get(
        "YOUTUBE_JSON",
        ""
    ).strip()

    # Optional. Bila tidak ada, proses upload video tetap berjalan
    # seperti sebelumnya tanpa custom thumbnail.
    thumbnail_path = os.environ.get(
        "THUMBNAIL_PATH",
        ""
    ).strip()

    if not video_path:
        raise RuntimeError(
            "VIDEO_PATH belum diset."
        )

    if not youtube_json:
        raise RuntimeError(
            "YOUTUBE_JSON belum diset."
        )

    video_file = Path(
        video_path
    )

    metadata_file = Path(
        youtube_json
    )

    if not video_file.exists():
        raise RuntimeError(
            f"Video tidak ditemukan: "
            f"{video_file}"
        )

    if not metadata_file.exists():
        raise RuntimeError(
            f"youtube.json tidak ditemukan: "
            f"{metadata_file}"
        )

    with open(
        metadata_file,
        "r",
        encoding="utf-8"
    ) as file:

        metadata = json.load(
            file
        )

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

    if not title:
        raise RuntimeError(
            "Title YouTube kosong."
        )

    if not isinstance(
        hashtags,
        list
    ):
        hashtags = []

    # Masukkan hashtag ke description.
    hashtag_text = " ".join(
        str(item).strip()
        for item in hashtags
        if str(item).strip()
    )

    if hashtag_text:

        description = (
            description.rstrip()
            + "\n\n"
            + hashtag_text
        )

    print("")
    print(
        "===================================="
    )
    print(
        "       YOUTUBE UPLOAD"
    )
    print(
        "===================================="
    )

    print("")
    print(
        f"Video : {video_file}"
    )

    print(
        f"Title : {title}"
    )

    if thumbnail_path:
        print(
            f"Thumbnail : {thumbnail_path}"
        )
    else:
        print(
            "Thumbnail : [NONE]"
        )

    print("")
    print(
        "Mulai upload..."
    )

    uploader = YouTubeUploader()

    # ======================================================
    # 1. UPLOAD VIDEO
    # ======================================================

    result = uploader.upload_video(
        video_path=str(
            video_file
        ),
        title=title,
        description=description,
        privacy_status="public",
    )

    if not isinstance(
        result,
        dict
    ):

        raise RuntimeError(
            "Response YouTube tidak valid."
        )

    video_id = result.get(
        "id"
    )

    if not video_id:

        raise RuntimeError(
            "Upload selesai tetapi "
            "video ID tidak ditemukan."
        )

    # ======================================================
    # 2. SET CUSTOM THUMBNAIL (OPTIONAL)
    # ======================================================
    # Jangan biarkan kegagalan thumbnail membatalkan upload
    # video yang sudah berhasil. Ini menjaga fungsi lama tetap aman.

    thumbnail_status = "not_requested"

    if thumbnail_path:

        thumbnail_file = Path(
            thumbnail_path
        )

        if not thumbnail_file.exists():

            print(
                "⚠️ Thumbnail tidak ditemukan. "
                "Video tetap dianggap berhasil di-upload."
            )

            thumbnail_status = "not_found"

        else:

            try:

                uploader.set_thumbnail(
                    video_id=video_id,
                    thumbnail_path=str(
                        thumbnail_file
                    ),
                )

                thumbnail_status = "success"

            except Exception as thumbnail_error:

                thumbnail_status = "failed"

                print("")
                print(
                    "⚠️ CUSTOM THUMBNAIL GAGAL"
                )
                print(
                    f"{type(thumbnail_error).__name__}: "
                    f"{thumbnail_error}"
                )
                print(
                    "Video YouTube tetap berhasil di-upload."
                )

    youtube_url = (
        "https://www.youtube.com/watch?v="
        + video_id
    )

    result_path = Path(
        "youtube_upload_result.json"
    )

    with open(
        result_path,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            {
                "video_id": video_id,
                "youtube_url": youtube_url,
                "title": title,
                "thumbnail_status": thumbnail_status,
            },
            file,
            ensure_ascii=False,
            indent=2,
        )

    print("")
    print(
        "✅ UPLOAD YOUTUBE BERHASIL"
    )

    print(
        f"YouTube URL: "
        f"{youtube_url}"
    )

    print(
        f"Thumbnail status: {thumbnail_status}"
    )

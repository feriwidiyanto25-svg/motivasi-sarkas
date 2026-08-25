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

            if creds and creds.expired and creds.refresh_token:

                creds.refresh(Request())

            else:

                flow = InstalledAppFlow.from_client_secrets_file(
                    str(self.credentials_file),
                    self.SCOPES,
                )

                creds = flow.run_local_server(port=0)

            with open(self.token_file, "w") as token:

                token.write(creds.to_json())

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

            status, response = request.next_chunk()

            if status:
                print(
                    f"Progress : {int(status.progress() * 100)}%"
                )

        print("Upload selesai.")

        return response
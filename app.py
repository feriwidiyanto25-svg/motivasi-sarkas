import os
import base64
import json
import os
import time
import tempfile
import zipfile
from datetime import datetime, timezone

import gradio as gr
import requests


def github_headers():
    token = os.environ.get("GITHUB_TOKEN", "").strip()

    if not token:
        raise RuntimeError(
            "GITHUB_TOKEN belum diset di Railway Variables."
        )

    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def trigger_github_render(topik, api_key, model_pilihan):
    url = (
        "https://api.github.com/repos/"
        "feriwidiyanto25-svg/motivasi-sarkas/dispatches"
    )

    payload = {
        "event_type": "render_video",
        "client_payload": {
            "topik": topik,
            "api_key": api_key,
            "model_pilihan": model_pilihan,
        },
    }

    response = requests.post(
        url,
        headers=github_headers(),
        json=payload,
        timeout=30,
    )

    if response.status_code != 204:
        raise RuntimeError(
            "Gagal memicu GitHub Actions. "
            f"HTTP {response.status_code}: "
            f"{response.text[:500]}"
        )

    return datetime.now(timezone.utc)


def wait_for_github_run(dispatch_time, timeout_seconds=300):
    deadline = time.monotonic() + timeout_seconds

    url = (
        "https://api.github.com/repos/"
        "feriwidiyanto25-svg/motivasi-sarkas/"
        "actions/runs"
    )

    while time.monotonic() < deadline:
        response = requests.get(
            url,
            headers=github_headers(),
            params={
                "event": "repository_dispatch",
                "branch": "main",
                "per_page": 10,
            },
            timeout=30,
        )

        if response.status_code != 200:
            raise RuntimeError(
                "Gagal membaca GitHub Actions. "
                f"HTTP {response.status_code}: "
                f"{response.text[:500]}"
            )

        runs = response.json().get("workflow_runs", [])

        candidates = []

        for run in runs:
            if run.get("name") != "Motivasi Sarkas Render":
                continue

            created_at = run.get("created_at")
            if not created_at:
                continue

            try:
                created_at_dt = datetime.fromisoformat(
                    created_at.replace("Z", "+00:00")
                )
            except ValueError:
                continue

            if created_at_dt >= dispatch_time:
                candidates.append(run)

        if candidates:
            candidates.sort(
                key=lambda item: item.get("created_at", ""),
                reverse=True,
            )

            run = candidates[0]
            status = run.get("status")

            print(
                f"GitHub run #{run.get('id')} "
                f"status={status} "
                f"conclusion={run.get('conclusion')}"
            )

            if status == "completed":
                return run

        time.sleep(3)

    raise TimeoutError(
        "GitHub Actions belum selesai dalam "
        f"{timeout_seconds} detik."
    )


def download_render_artifact(run_id):
    artifacts_url = (
        "https://api.github.com/repos/"
        "feriwidiyanto25-svg/motivasi-sarkas/"
        f"actions/runs/{run_id}/artifacts"
    )

    response = requests.get(
        artifacts_url,
        headers=github_headers(),
        params={"per_page": 20},
        timeout=30,
    )

    if response.status_code != 200:
        raise RuntimeError(
            "Gagal mengambil daftar artifact. "
            f"HTTP {response.status_code}: "
            f"{response.text[:500]}"
        )

    artifacts = response.json().get("artifacts", [])

    valid = [
        item
        for item in artifacts
        if not item.get("expired", False)
        and str(item.get("name", "")).startswith(
            "motivasi-sarkas-video-"
        )
    ]

    if not valid:
        raise RuntimeError(
            "Artifact video tidak ditemukan."
        )

    valid.sort(
        key=lambda item: item.get("created_at", ""),
        reverse=True,
    )

    artifact = valid[0]
    artifact_id = artifact["id"]

    zip_url = (
        "https://api.github.com/repos/"
        "feriwidiyanto25-svg/motivasi-sarkas/"
        f"actions/artifacts/{artifact_id}/zip"
    )

    zip_response = requests.get(
        zip_url,
        headers=github_headers(),
        timeout=120,
        allow_redirects=True,
    )

    if zip_response.status_code != 200:
        raise RuntimeError(
            "Gagal mengunduh artifact. "
            f"HTTP {zip_response.status_code}: "
            f"{zip_response.text[:500]}"
        )

    os.makedirs("temp", exist_ok=True)

    extract_dir = os.path.abspath(
        os.path.join("temp", f"render_{run_id}")
    )
    os.makedirs(extract_dir, exist_ok=True)

    zip_path = os.path.join(
        extract_dir,
        "artifact.zip",
    )

    with open(zip_path, "wb") as file:
        file.write(zip_response.content)

    with zipfile.ZipFile(zip_path, "r") as archive:
        members = archive.namelist()

        video_member = next(
            (
                item
                for item in members
                if item.lower().endswith(".mp4")
            ),
            None,
        )

        result_member = next(
            (
                item
                for item in members
                if item.lower().endswith("render_result.json")
            ),
            None,
        )

        if not video_member:
            raise RuntimeError(
                "Artifact tidak berisi file MP4."
            )

        archive.extract(video_member, extract_dir)

        result_data = {}

        if result_member:
            archive.extract(result_member, extract_dir)

            result_path = os.path.join(
                extract_dir,
                result_member,
            )

            with open(
                result_path,
                "r",
                encoding="utf-8",
            ) as file:
                result_data = json.load(file)

    video_path = os.path.abspath(
        os.path.join(
            extract_dir,
            video_member,
        )
    )

    if not os.path.exists(video_path):
        raise RuntimeError(
            "File video hasil render tidak ditemukan."
        )

    if os.path.getsize(video_path) < 1000:
        raise RuntimeError(
            "File video hasil render terlalu kecil."
        )

    return video_path, result_data


def buat_video_motivasi(topik, api_key, model_pilihan):
    err_topik_html = ""
    err_key_html = ""
    is_invalid = False

    if not api_key or api_key.strip() == "":
        err_key_html = (
            "<span style='color: red; font-size: 13px; "
            "font-weight: bold;'>Gemini API Key wajib diisi</span>"
        )
        is_invalid = True

    if not topik or topik.strip() == "":
        err_topik_html = (
            "<span style='color: red; font-size: 13px; "
            "font-weight: bold;'>Topik / keresahan wajib diisi</span>"
        )
        is_invalid = True

    if is_invalid:
        return (
            err_topik_html,
            err_key_html,
            "",
            "",
            "⚠️ Mohon lengkapi kolom yang masih kosong di atas.",
            None,
            gr.update(
                interactive=True,
                value="🚀 Bikin Video Sekarang",
            ),
        )

    try:
        print(
            f"\n--- Memulai Proses Baru: {topik} "
            f"(Model: {model_pilihan}) ---"
        )

        print(
            "1. Mengirim request render ke GitHub Actions..."
        )

        dispatch_time = trigger_github_render(
            topik,
            api_key,
            model_pilihan,
        )

        print(
            "✅ GitHub Actions berhasil dipicu."
        )

        print(
            "2. Menunggu GitHub menyelesaikan render..."
        )

        run = wait_for_github_run(
            dispatch_time,
            timeout_seconds=int(
                os.environ.get(
                    "GITHUB_RENDER_TIMEOUT",
                    "300",
                )
            ),
        )

        if run.get("conclusion") != "success":
            raise RuntimeError(
                "GitHub Actions gagal. "
                f"Run #{run.get('id')} "
                f"conclusion={run.get('conclusion')}"
            )

        run_id = run["id"]

        print(
            f"✅ GitHub Run #{run_id} berhasil."
        )

        print(
            "3. Mengambil artifact hasil render..."
        )

        video_path, result_data = download_render_artifact(
            run_id
        )

        naskah = result_data.get("naskah", result_data)

        formatted_naskah = f"""
### 📝 Hasil Naskah:
* **Judul:** {naskah.get('title', '')}
* **Setup 1:** {naskah.get('setup_1', '')}
* **Setup 2:** {naskah.get('setup_2', '')}
* **Punchline:** {naskah.get('punchline', '')}
* **Keyword Pexels:** `{naskah.get('bg_keyword', '')}`
""".strip()

        print(
            "4. Video siap ditampilkan."
        )

        print(
            f"Video: {video_path}"
        )

        return (
            err_topik_html,
            err_key_html,
            "",
            "",
            formatted_naskah,
            video_path,
            gr.update(
                interactive=True,
                value="🚀 Bikin Video Sekarang",
            ),
        )

    except Exception as e:
        print(
            "ERROR SAAT REQUEST RENDER GITHUB:"
        )
        print(
            f"{type(e).__name__}: {e}"
        )

        return (
            err_topik_html,
            err_key_html,
            "",
            "",
            f"❌ Error: {str(e)}",
            None,
            gr.update(
                interactive=True,
                value="🚀 Bikin Video Sekarang",
            ),
        )


# ==========================================
# FAVICON
# ==========================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FAVICON_PATH = os.path.join(
    BASE_DIR,
    "assets",
    "favicon.png"
)

# Embed favicon directly in the page head so the browser does not fall
# back to the default Gradio icon when the favicon file is cached/served late.
FAVICON_HEAD = ""
try:
    with open(FAVICON_PATH, "rb") as favicon_file:
        favicon_b64 = base64.b64encode(
            favicon_file.read()
        ).decode("ascii")

    FAVICON_HEAD = (
        '<link rel="icon" type="image/png" '
        f'href="data:image/png;base64,{favicon_b64}">'
    )
except Exception as e:
    print(f"Favicon tidak dapat dimuat: {e}")


with gr.Blocks(
    title="Motivasi Sarkas",
    theme=gr.themes.Soft(),
    css="footer {display: none !important;}",
    head=FAVICON_HEAD
) as ui:

    gr.Markdown("# 🎬 Motivasi Sarkas Generator")
    gr.Markdown("Ketik keresahanmu, masukkan API Key, dan hasilkan video pendek otomatis.")

    with gr.Row():
        with gr.Column():

            # =========================
            # TOPIK
            # =========================
            with gr.Row():
                input_topik = gr.Textbox(
                    label="Topik / Keresahan Hari Ini",
                    placeholder="Contoh: Gaji numpang lewat di awal bulan...",
                    scale=4
                )

                status_topik = gr.Markdown(
                    "",
                    scale=1
                )

            output_err_topik = gr.HTML("")

            # =========================
            # API KEY
            # =========================
            with gr.Row():
                input_apikey = gr.Textbox(
                    label="Gemini API Key",
                    placeholder="Masukkan API Key Gemini...",
                    type="password",
                    scale=4
                )

                status_key = gr.Markdown(
                    "",
                    scale=4
                )

            output_err_key = gr.HTML("")

            # =========================
            # MODEL GEMINI
            # =========================
            with gr.Row():
                input_model = gr.Dropdown(
                    label="Pilih Versi Model Gemini",
                    choices=[
                        "gemini-2.5-flash",
                        "gemini-2.5-pro",
                        "gemini-3.0-flash",
                        "gemini-3.0-pro",
                        "gemini-3.5-flash",
                        "gemini-3.5-pro",
                        "gemini-3.6-flash"
                    ],
                    value="gemini-2.5-flash",
                    scale=4
                )

            # =========================
            # BUTTON
            # =========================
            btn_generate = gr.Button(
                "🚀 Bikin Video Sekarang",
                variant="primary"
            )

    # =========================
    # OUTPUT
    # =========================
    with gr.Row():

        with gr.Column():
            gr.Markdown("### 🤖 Naskah dari AI")
            output_naskah = gr.Markdown(label="Tampilan Naskah")

        with gr.Column():
            gr.Markdown("### 🎥 Hasil Video")
            output_video = gr.Video(label="Preview & Download")

    # =========================
    # PROCESSING STATE
    # =========================
    btn_generate.click(
        fn=lambda t, k, m: (
            "⏳ Processing...",
            "⏳ Processing...",
            gr.update(
                interactive=False,
                value="⏳ Sedang Merakit Video..."
            )
        ),
        inputs=[
            input_topik,
            input_apikey,
            input_model
        ],
        outputs=[
            status_topik,
            status_key,
            btn_generate
        ],
        queue=False
    ).then(
        fn=buat_video_motivasi,
        inputs=[
            input_topik,
            input_apikey,
            input_model
        ],
        outputs=[
            output_err_topik,
            output_err_key,
            status_topik,
            status_key,
            output_naskah,
            output_video,
            btn_generate
        ]
    )


if __name__ == "__main__":
    ui.launch(
        server_name="0.0.0.0",
        server_port=int(os.environ.get("PORT", 7860)),
        favicon_path=FAVICON_PATH
    )

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


def get_recent_github_run_ids():
    """
    Ambil ID workflow run yang sudah ada sebelum dispatch.
    Kita pakai ID ini untuk membedakan run baru dari run lama,
    sehingga tidak bergantung pada perbedaan waktu server.
    """
    url = (
        "https://api.github.com/repos/"
        "feriwidiyanto25-svg/motivasi-sarkas/"
        "actions/runs"
    )

    response = requests.get(
        url,
        headers=github_headers(),
        params={
            "event": "repository_dispatch",
            "branch": "main",
            "per_page": 20,
        },
        timeout=30,
    )

    if response.status_code != 200:
        raise RuntimeError(
            "Gagal membaca workflow runs sebelum dispatch. "
            f"HTTP {response.status_code}: "
            f"{response.text[:500]}"
        )

    runs = response.json().get("workflow_runs", [])

    return {
        run.get("id")
        for run in runs
        if run.get("id")
    }


def trigger_github_render(topik, api_key, model_pilihan):
    """
    Trigger GitHub Actions dan kembalikan snapshot ID run
    sebelum dispatch + waktu lokal sebagai informasi tambahan.
    """
    previous_run_ids = get_recent_github_run_ids()

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

    print(
        f"Dispatch berhasil. Run lama yang diabaikan: "
        f"{len(previous_run_ids)}"
    )

    return previous_run_ids, datetime.now(timezone.utc)


def wait_for_github_run(
    dispatch_info,
    timeout_seconds=600,
):
    previous_run_ids, dispatch_time = dispatch_info
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
                "per_page": 20,
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
            run_id = run.get("id")

            if not run_id:
                continue

            if run_id in previous_run_ids:
                continue

            if run.get("name") != "Motivasi Sarkas Render":
                continue

            candidates.append(run)

        if candidates:
            candidates.sort(
                key=lambda item: (
                    item.get("created_at", ""),
                    item.get("id", 0),
                ),
                reverse=True,
            )

            run = candidates[0]

            status = run.get("status")
            conclusion = run.get("conclusion")

            print(
                f"GitHub run #{run.get('id')} "
                f"status={status} "
                f"conclusion={conclusion}"
            )

            if status == "completed":
                return run

        # Jika GitHub butuh sedikit waktu untuk membuat run,
        # terus polling sampai deadline.
        elapsed = int(
            time.monotonic()
            - (deadline - timeout_seconds)
        )

        print(
            f"Menunggu GitHub run... "
            f"{elapsed}s"
        )

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
            "⚠️ Mohon lengkapi kolom yang masih kosong di atas.",
            None,
            gr.update(
                interactive=True,
                value="🚀 Bikin Video Sekarang",
            ),
            gr.update(visible=False),
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
            formatted_naskah,
            video_path,
            gr.update(
                interactive=True,
                value="🚀 Bikin Video Sekarang",
            ),
            gr.update(visible=False),
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
            f"❌ Error: {str(e)}",
            None,
            gr.update(
                interactive=True,
                value="🚀 Bikin Video Sekarang",
            ),
            gr.update(visible=False),
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


# ==========================================
# LOADING OVERLAY
# ==========================================
LOADING_OVERLAY = r"""
<div style="
    position: fixed;
    inset: 0;
    z-index: 999999;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(0, 0, 0, 0.72);
    backdrop-filter: blur(4px);
    pointer-events: all;
">
    <div style="
        min-width: 260px;
        max-width: 88vw;
        padding: 28px 30px;
        border-radius: 18px;
        text-align: center;
        background: rgba(30, 35, 50, 0.97);
        box-shadow: 0 18px 50px rgba(0, 0, 0, 0.35);
    ">
        <div style="
            width: 42px;
            height: 42px;
            margin: 0 auto;
            border: 4px solid rgba(255, 255, 255, 0.22);
            border-top-color: #6c63ff;
            border-radius: 50%;
            animation: motivasi-spin 0.9s linear infinite;
        "></div>

        <div style="
            margin-top: 16px;
            font-size: 21px;
            font-weight: 700;
            color: #ffffff !important;
        ">
            🎬 Sedang Merakit Video
        </div>

        <div style="
            margin-top: 8px;
            font-size: 14px;
            color: #d8dce8 !important;
            opacity: 1 !important;
        ">
            Mohon tunggu sebentar...
        </div>
    </div>
</div>

<style>
@keyframes motivasi-spin {
    to { transform: rotate(360deg); }
}
</style>
"""


with gr.Blocks(
    title="Motivasi Sarkas",
    theme=gr.themes.Soft(),
    css="footer {display: none !important;}",
    head=FAVICON_HEAD
) as ui:

    loading_overlay = gr.HTML(
        LOADING_OVERLAY,
        visible=False
    )

    gr.Markdown("# 🎬 Motivasi Sarkas Generator")
    gr.Markdown("Ketik keresahanmu, masukkan API Key, dan hasilkan video pendek otomatis.")

    with gr.Row():
        with gr.Column():

            # =========================
            # TOPIK
            # =========================
            input_topik = gr.Textbox(
                label="Topik / Keresahan Hari Ini",
                placeholder="Contoh: Gaji numpang lewat di awal bulan..."
            )

            output_err_topik = gr.HTML("")

            # =========================
            # API KEY
            # =========================
            input_apikey = gr.Textbox(
                label="Gemini API Key",
                placeholder="Masukkan API Key Gemini...",
                type="password"
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
            gr.update(
                interactive=False,
                value="⏳ Sedang Merakit Video..."
            ),
            gr.update(visible=True)
        ),
        inputs=[
            input_topik,
            input_apikey,
            input_model
        ],
        outputs=[
            btn_generate,
            loading_overlay
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
            output_naskah,
            output_video,
            btn_generate,
            loading_overlay
        ]
    )



if __name__ == "__main__":
    ui.launch(
        server_name="0.0.0.0",
        server_port=int(os.environ.get("PORT", 7860)),
        favicon_path=FAVICON_PATH
    )

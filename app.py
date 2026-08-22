import os
import gradio as gr
from ai_generator import generate_naskah
from video_engine import render_final_video


def buat_video_motivasi(topik, api_key, model_pilihan):
    err_topik_html = ""
    err_key_html = ""
    is_invalid = False

    # Validasi API Key
    if not api_key or api_key.strip() == "":
        err_key_html = "<span style='color: red; font-size: 13px; font-weight: bold;'>Gemini API Key wajib diisi</span>"
        is_invalid = True

    # Validasi Topik
    if not topik or topik.strip() == "":
        err_topik_html = "<span style='color: red; font-size: 13px; font-weight: bold;'>Topik / keresahan wajib diisi</span>"
        is_invalid = True

    # Jika validasi gagal
    if is_invalid:
        return (
            err_topik_html,
            err_key_html,
            "",
            "",
            "⚠️ Mohon lengkapi kolom yang masih kosong di atas.",
            None,
            gr.update(interactive=True, value="🚀 Bikin Video Sekarang")
        )

    print(f"\n--- Memulai Proses Baru: {topik} (Model: {model_pilihan}) ---")

    # Generate naskah
    print("1. Menghubungi Gemini AI...")
    naskah_json = generate_naskah(
        topik,
        api_key=api_key,
        model_name=model_pilihan
    )

    # Jika Gemini mengembalikan error
    if "error" in naskah_json:
        return (
            err_topik_html,
            err_key_html,
            "",
            "",
            f"❌ Error: {naskah_json['error']}",
            None,
            gr.update(interactive=True, value="🚀 Bikin Video Sekarang")
        )

    # Format naskah untuk ditampilkan
    formatted_naskah = f"""
### 📝 Hasil Naskah:
* **Setup 1:** {naskah_json.get('setup_1')}
* **Setup 2:** {naskah_json.get('setup_2')}
* **Punchline:** {naskah_json.get('punchline')}
* **Keyword Pexels:** `{naskah_json.get('bg_keyword')}`
""".strip()

    # Render video
    print("2. Menyerahkan naskah ke Mesin Video...")
    path_video = render_final_video(naskah_json)

    # Debug video
    print("=== DEBUG VIDEO ===")
    print("Video path:", path_video)

    if path_video:
        print("File exists:", os.path.exists(path_video))

        if os.path.exists(path_video):
            print("File size:", os.path.getsize(path_video))
        else:
            print("❌ File video tidak ditemukan:", path_video)
    else:
        print("❌ render_final_video() mengembalikan None")

    print("===================")

    # Jika renderer tidak menghasilkan path video
    if not path_video:
        print("❌ Video gagal dibuat karena path_video kosong.")

        return (
            err_topik_html,
            err_key_html,
            "",
            "",
            formatted_naskah,
            None,
            gr.update(interactive=True, value="🚀 Bikin Video Sekarang")
        )

    # Jika path ada tetapi file tidak ditemukan
    if not os.path.exists(path_video):
        print(f"❌ File video tidak ditemukan: {path_video}")

        return (
            err_topik_html,
            err_key_html,
            "",
            "",
            formatted_naskah,
            None,
            gr.update(interactive=True, value="🚀 Bikin Video Sekarang")
        )

    print("--- Proses Selesai! ---")

    # Kembalikan hasil
    return (
        err_topik_html,
        err_key_html,
        "",
        "",
        formatted_naskah,
        path_video,
        gr.update(interactive=True, value="🚀 Bikin Video Sekarang")
    )


with gr.Blocks(
    title="Motivasi Sarkas",
    theme=gr.themes.Soft(),
    css="footer {display: none !important;}"
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
        favicon_path="assets/favicon.png"
    )
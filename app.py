import gradio as gr
from ai_generator import generate_naskah
from video_engine import render_final_video

def buat_video_motivasi(topik, api_key, model_pilihan):
    err_topik_html = ""
    err_key_html = ""
    is_invalid = False
    
    if not api_key or api_key.strip() == "":
        err_key_html = "<span style='color: red; font-size: 13px; font-weight: bold;'>Gemini API Key wajib diisi</span>"
        is_invalid = True
        
    if not topik or topik.strip() == "":
        err_topik_html = "<span style='color: red; font-size: 13px; font-weight: bold;'>Topik / keresahan wajib diisi</span>"
        is_invalid = True
        
    if is_invalid:
        # Kembalikan tombol ke kondisi aktif semula jika validasi gagal
        return (
            err_topik_html, err_key_html, "", "", 
            "⚠️ Mohon lengkapi kolom yang masih kosong di atas.", None, 
            gr.update(interactive=True, value="🚀 Bikin Video Sekarang")
        )
        
    print(f"\n--- Memulai Proses Baru: {topik} (Model: {model_pilihan}) ---")
    
    print("1. Menghubungi Gemini AI...")
    naskah_json = generate_naskah(topik, api_key=api_key, model_name=model_pilihan)
    
    if "error" in naskah_json:
        return (
            err_topik_html, err_key_html, "", "", 
            f"❌ Error: {naskah_json['error']}", None, 
            gr.update(interactive=True, value="🚀 Bikin Video Sekarang")
        )
        
    formatted_naskah = f"""
### 📝 Hasil Naskah:
* **Setup 1:** {naskah_json.get('setup_1')}
* **Setup 2:** {naskah_json.get('setup_2')}
* **Punchline:** {naskah_json.get('punchline')}
* **Keyword Pexels:** `{naskah_json.get('bg_keyword')}`
    """.strip()
    
    print("2. Menyerahkan naskah ke Mesin Video...")
    path_video = render_final_video(naskah_json)
    
    print("--- Proses Selesai! ---")
    # Kembalikan tombol ke kondisi aktif setelah selesai
    return (
        err_topik_html, err_key_html, "", "", 
        formatted_naskah, path_video, 
        gr.update(interactive=True, value="🚀 Bikin Video Sekarang")
    )

with gr.Blocks(theme=gr.themes.Soft(), css="footer {display: none !important;}") as ui:
    gr.Markdown("# 🎬 Auto-Motivasi Sarkas Generator")
    gr.Markdown("Ketik keresahanmu, masukkan API Key, dan hasilkan video pendek otomatis.")
    
    with gr.Row():
        with gr.Column():
            with gr.Row():
                input_topik = gr.Textbox(
                    label="Topik / Keresahan Hari Ini", 
                    placeholder="Contoh: Gaji numpang lewat di awal bulan...",
                    scale=4
                )
                status_topik = gr.Markdown("", scale=1) # Indikator processing di kanan input
            output_err_topik = gr.HTML("")
            
            with gr.Row():
                input_apikey = gr.Textbox(
                    label="Gemini API Key", 
                    placeholder="Masukkan API Key Gemini...", 
                    type="password",
                    scale=4
                )
                status_key = gr.Markdown("", scale=1) # Indikator processing di kanan input
            output_err_key = gr.HTML("")
            
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
                value="gemini-2.5-flash"
            )
            
            btn_generate = gr.Button("🚀 Bikin Video Sekarang", variant="primary")
        
    with gr.Row():
        with gr.Column():
            gr.Markdown("### 🤖 Naskah dari AI")
            output_naskah = gr.Markdown(label="Tampilan Naskah")
        with gr.Column():
            gr.Markdown("### 🎥 Hasil Video")
            output_video = gr.Video(label="Preview & Download")
            
    # Mengaktifkan efek loading, mengunci tombol saat proses, dan memunculkan teks "Processing..." di kanan input
    btn_generate.click(
        fn=lambda t, k, m: ("⏳ Processing...", "⏳ Processing...", gr.update(interactive=False, value="⏳ Sedang Merakit Video...")),
        inputs=[input_topik, input_apikey, input_model],
        outputs=[status_topik, status_key, btn_generate],
        queue=False
    ).then(
        fn=buat_video_motivasi,
        inputs=[input_topik, input_apikey, input_model],
        outputs=[output_err_topik, output_err_key, status_topik, status_key, output_naskah, output_video, btn_generate]
    )

if __name__ == "__main__":
    ui.launch(share=False)
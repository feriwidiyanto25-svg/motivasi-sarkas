import os
import json
import random
import google.generativeai as genai
from . import config

# ==============================================================================
# KATEGORI TOPIK SEJARAH & MISTERI BERPUTAR
# ==============================================================================
KATEGORI_SEJARAH = [
    "Misteri Peradaban Kuno Dunia (Piramida Mesir, Suku Maya, Rahasia Kuil Romawi, Atlantis, Peninggalan Sumeria, Catacomb)",
    "Fakta Menggegerkan Sejarah Nusantara (Kerajaan Majapahit, Armada Laut Sriwijaya, Rahasia Candi, Senjata Pusaka, Taktik Perang Lokal)",
    "Taktik Perang Gila & Strategi Jenius (Pasukan Berkuda Mongol, Trik Pasukan Gajah Hannibal, Strategi Pasukan 300 Sparta, Perang Salib)",
    "Sisi Gelap & Rahasia Tokoh Terkenal (Kekayaan Genghis Khan yang Lenyap, Kematian Misterius Tokoh Dunia, Konspirasi Istana Kuno)",
    "Benda Terkutuk & Artefak Legendaris yang Hilang (Peti Emas, Pedang Legendaris, Harta Karun Laut Dalam, Naskah Terlarang)"
]

def load_history():
    """Membaca riwayat topik sejarah agar tidak membuat video yang sama."""
    if not os.path.exists(config.TOPICS_HISTORY_FILE):
        return []
    try:
        with open(config.TOPICS_HISTORY_FILE, "r", encoding="utf-8") as f:
            return [line.strip() for line in f if line.strip() and not line.startswith("#")]
    except Exception:
        return []

def save_history(topic):
    """Menyimpan topik sejarah ke riwayat."""
    try:
        with open(config.TOPICS_HISTORY_FILE, "a", encoding="utf-8") as f:
            f.write(f"{topic}\n")
    except Exception as e:
        print(f"Peringatan riwayat sejarah: {e}")

def get_history_topic(api_key=None, model_name="gemini-2.5-flash"):
    """Menghasilkan ide topik sejarah yang paling memikat audiens Facebook."""
    api_key = api_key or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return "Misteri Pasukan Romawi yang Hilang di Hutan Teutoburg"

    try:
        genai.configure(api_key=api_key.strip())
        model = genai.GenerativeModel(model_name)

        chosen_cat = random.choice(KATEGORI_SEJARAH)
        history = load_history()[-25:]
        history_text = "\n".join([f"- {h}" for h in history]) if history else "Belum ada."

        prompt = f"""
Kamu adalah produser konten dokumenter sejarah viral di Facebook Reels bernama "Arsip Sejarah".
Buatkan 1 (SATU) topik misteri sejarah yang sangat memicu rasa takjub, perdebatan, atau membagikan (share) ke teman.

FOKUS KATEGORI:
{chosen_cat}

DILARANG MEMBUAT TOPIK YANG SUDAH PERNAH DIBIKIN:
{history_text}

ATURAN TOPIK:
- Singkat, padat, dan sangat mengundang klik (Contoh: "Taktik Gila Pasukan Gajah Hannibal yang Menghancurkan Romawi" atau "Rahasia Mengerikan di Balik Runtuhnya Majapahit").
- Jangan ada penomoran atau tanda kutip.
- Hanya kembalikan 1 baris judul topik saja.
"""
        res = model.generate_content(prompt, generation_config={"temperature": 1.0})
        topic = (getattr(res, "text", "") or "").strip().strip('"').strip("'")
        if topic:
            save_history(topic)
            return topic
    except Exception as e:
        print(f"Gagal generate topik sejarah: {e}")

    return "Taktik Pasukan Kuda Mongol yang Menaklukkan Setengah Dunia"

def generate_history_script(topic=None, api_key=None, model_name="gemini-2.5-flash"):
    """
    Menghasilkan Naskah Storytelling Sejarah 45 Detik untuk Facebook Reels
    lengkap dengan 5 prompt gambar bergaya lukisan klasik/oil painting untuk Flow/MCP.
    """
    api_key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("ℹ️ GEMINI_API_KEY belum diset di .env. Menggunakan naskah sejarah percontohan (Demo Mode)...")
        chosen_title = topic or "Taktik Pasukan Kuda Mongol yang Menaklukkan Setengah Dunia"
        return {
            "title": chosen_title,
            "series_tag": "Misteri Peradaban Dunia: Bagian 1",
            "scenes": [
                "Buku sekolah mencatat pasukan Mongol menang karena jumlah.",
                "Tapi *ARSIP RAHASIA* membuktikan alasan lain!",
                "Tahun 1221, mereka memakai *TAKTIK PSIKOLOGIS* gila.",
                "Setiap prajurit menunggangi *LIMA KUDA BERBEDA*.",
                "Kuda sengaja menyeret semak untuk membuat *DEBU TEBAL*.",
                "Musuh mengira jumlah mereka mencapai *RATUSAN RIBU*!",
                "Benteng terkuat akhirnya hancur *HANYA DALAM 3 HARI*.",
                "Menurutmu, ini taktik jenius atau kejam? *TULIS DI KOMENTAR*!"
            ],
            "image_prompts": [
                "Cinematic oil painting of Mongol horse archers riding into foggy plains, dramatic sunset, 8k --ar 9:16",
                "Ancient rolled war map of Eurasia on dark table, candlelight, bronze coins, moody --ar 9:16",
                "Epic portrait of a Mongol general silhouette holding a recurve bow, stormy dark sky --ar 9:16",
                "Dust storm rising from thousands of horses galloping, dramatic cinematic lighting --ar 9:16",
                "Ancient Asian fortress walls crumbling, smoke rising, photorealistic documentary --ar 9:16"
            ],
            "caption": f"{chosen_title}\n\nMenurutmu, apakah taktik ini jenius atau kejam? Tulis pendapatmu di kolom komentar!\n\n#SejarahDunia #MisteriKuno #FaktaSejarah #ArsipSejarah"
        }

    genai.configure(api_key=api_key.strip())
    model = genai.GenerativeModel(model_name)

    if not topic:
        topic = get_history_topic(api_key, model_name)

    prompt = f"""
Kamu adalah penulis naskah dokumenter sejarah profesional untuk akun Facebook Reels bernama "Arsip Sejarah".
Buatkan naskah storytelling sejarah yang intens, dramatis, dan sangat memikat penonton dewasa di Facebook.

TOPIK:
"{topic}"

TARGET DURASI:
Sekitar 40 sampai 50 detik (terdiri dari 6 sampai 8 scene micro-narasi).

ATURAN STRUKTUR CERITA:
1. SCENE 1 (HOOK ANTI-SKIP):
   - Wajib dimulai dengan format serial: misal "Misteri Arsip Dunia: Bagian 1" atau menyentil fakta rahasia.
   - Contoh: "Di buku sekolah kita diajarkan kerajaan ini kalah perang, tapi *ARSIP RAHASIA* membuktikan sebaliknya!"
2. SCENE 2-3 (LATAR & TEGANGAN):
   - Ungkap peristiwa, tahun kejadian, atau taktik mengejutkan yang terjadi.
3. SCENE 4-5 (KLIMAKS):
   - Momen pertempuran, kehancuran, atau penemuan artefak penting.
4. SCENE AKHIR (TRIGGER KOMENTAR & FOLLOW):
   - Akhiri dengan pertanyaan diskusi yang memancing penonton berdebat di komentar + ajakan ikuti episode selanjutnya.
   - Contoh: "Menurutmu, apakah keputusan raja saat itu tepat? *TULIS DI KOMENTAR*, dan ikuti kisah berikutnya!"

ATURAN TEKS:
- Tandai kata penegas, tahun, nama tokoh penting, atau fakta mencengangkan dengan bintang (*KATA*).
- Setiap scene WAJIB sangat pendek (4 sampai 8 kata per scene, maksimal 10 kata) agar teks tampil bersih 1-2 baris saja di bagian bawah layar (lower-third).
- Jika sebuah kalimat panjang, PECAH menjadi dua atau tiga scene terpisah.

ATURAN PROMPT GAMBAR (IMAGE_PROMPTS):
- Buatkan 5 prompt gambar bahasa Inggris untuk masing-masing babak cerita.
- Gaya visual: Cinematic historical oil painting, dark chiaroscuro lighting, ancient parchment map, moody documentary aesthetic, 8k --ar 9:16 --no text watermark.

OUTPUT HARUS BERUPA JSON MURNI:
{{
    "title": "Judul Menarik",
    "series_tag": "Misteri Arsip: Bagian 1",
    "scenes": [
        "Scene 1...",
        "Scene 2...",
        "Scene 3..."
    ],
    "image_prompts": [
        "Cinematic oil painting prompt 1...",
        "Ancient map candlelit prompt 2...",
        "Warrior silhouette prompt 3...",
        "Battlefield relic prompt 4...",
        "Macro artifact gold prompt 5..."
    ],
    "caption": "Teks caption Facebook lengkap dengan pertanyaan diskusi dan hashtag #SejarahDunia #MisteriKuno #FaktaSejarah #ArsipSejarah"
}}
"""
    res = model.generate_content(prompt, generation_config={"temperature": 0.85})
    raw_text = (getattr(res, "text", "") or "").strip()

    # Ekstrak JSON
    if "```json" in raw_text:
        raw_text = raw_text.split("```json")[1].split("```")[0].strip()
    elif "```" in raw_text:
        raw_text = raw_text.split("```")[1].split("```")[0].strip()

    start_idx = raw_text.find("{")
    end_idx = raw_text.rfind("}")
    if start_idx != -1 and end_idx != -1:
        raw_text = raw_text[start_idx:end_idx+1]

    data = json.loads(raw_text)
    return data

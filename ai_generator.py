import json
import google.generativeai as genai

# ==========================================
# UTILITAS JSON
# ==========================================
def extract_json(text):
    text = (text or "").strip()
    if "```json" in text:
        text = text.replace("```json", "")
    text = text.replace("```", "").strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    start = text.find("{")
    if start == -1:
        raise json.JSONDecodeError("JSON object tidak ditemukan.", text, 0)
    decoder = json.JSONDecoder()
    result, _ = decoder.raw_decode(text[start:])
    return result

# ==========================================
# VALIDASI HASIL AI
# ==========================================
def validate_result(hasil):
    required_fields = ["title", "scenes", "visual_context", "bg_keywords"]

    for field in required_fields:
        if field not in hasil:
            return None, f"AI tidak menghasilkan field: {field}"

    if not isinstance(hasil["title"], str) or not hasil["title"].strip():
        return None, "Field title harus berupa teks dan tidak boleh kosong."
    
    if not isinstance(hasil["visual_context"], str) or len(hasil["visual_context"]) < 5:
        return None, "Field visual_context tidak valid atau terlalu pendek."

    # Validasi Scenes untuk penjelasan yang lebih panjang
    if not isinstance(hasil["scenes"], list) or len(hasil["scenes"]) == 0:
        return None, "Field scenes harus berupa array/list kalimat."
    
    hasil["scenes"] = [s.strip() for s in hasil["scenes"] if isinstance(s, str) and s.strip()]

    if not isinstance(hasil["bg_keywords"], list):
        return None, "bg_keywords harus berupa array."

    cleaned_keywords = list(dict.fromkeys([k.strip() for k in hasil["bg_keywords"] if isinstance(k, str) and k.strip()]))
    if not cleaned_keywords:
        return None, "bg_keywords tidak boleh kosong."

    hasil["bg_keywords"] = cleaned_keywords[:4]
    hasil["bg_keyword"] = hasil["bg_keywords"][0]

    return hasil, None

# ==========================================
# GENERATE NASKAH EDUKASI MENDALAM
# ==========================================
def generate_naskah(topik, api_key, model_name="gemini-2.5-flash"):
    if not api_key or api_key.strip() == "":
        return {"error": "Gemini API Key wajib diisi!"}
    if not topik or not topik.strip():
        return {"error": "Topik wajib diisi!"}

    genai.configure(api_key=api_key.strip())

    try:
        model = genai.GenerativeModel(model_name)

        # Instruksi diubah: Fokus pada kejelasan, kedalaman, dan tanpa batasan durasi ketat
        prompt = f"""
Kamu adalah seorang edukator sains dan pengetahuan umum pembuat konten video.
Fokus utamamu adalah menjelaskan hal kompleks menjadi sangat jelas, komprehensif, dan mudah dimengerti. 
TIDAK ADA BATASAN DURASI, yang penting informasinya utuh.

TOPIK YANG DITANYAKAN:
"{topik}"

ATURAN UTAMA:
1. FAKTUAL & MENDALAM: Jelaskan alasan sebenarnya secara ilmiah dan logis. Jangan mengarang. Jika ada proses sains/sejarah di baliknya, jelaskan proses itu dari A sampai Z.
2. BAHASA MENGALIR: Gunakan bahasa Indonesia sehari-hari yang nyaman didengar/dibaca. 
3. STRUKTUR SCENE: Karena teks akan ditampilkan di video, pecah seluruh penjelasanmu menjadi banyak scene (misalnya 4 hingga 8 scene, atau lebih jika diperlukan). 
4. PANJANG TEKS: Setiap scene boleh berisi 1 hingga 3 kalimat (jangan terlalu panjang sampai menutupi layar penuh, pecah ke scene berikutnya jika kepanjangan).

OUTPUT WAJIB FORMAT JSON MURNI TANPA MARKDOWN:
{{
    "title": "Kenapa Rambut Bisa Berubah Menjadi Putih?",
    "scenes": [
        "Warna rambut kita sebenarnya ditentukan oleh sel khusus bernama melanosit.",
        "Sel melanosit ini bertugas memproduksi pigmen bernama melanin, yang memberikan warna hitam, coklat, atau pirang pada rambut.",
        "Seiring bertambahnya usia, folikel rambut mulai mengalami kelelahan seluler dan produksi melanin menurun secara drastis.",
        "Selain faktor usia, penumpukan hidrogen peroksida alami di folikel juga bisa 'memutihkan' rambut dari dalam.",
        "Akibatnya, helai rambut baru yang tumbuh tidak lagi mendapat pasokan warna. Ia tumbuh dalam keadaan transparan.",
        "Karena pantulan cahaya, rambut transparan ini terlihat putih atau abu-abu di mata kita."
    ],
    "visual_context": "close up shot of someone combing white or gray hair or microscopic hair follicle",
    "bg_keywords": ["white hair", "elderly", "hair root"]
}}
"""

        response = model.generate_content(prompt)
        teks = (getattr(response, "text", "") or "").strip()

        if not teks:
            return {"error": "Gemini tidak menghasilkan teks."}

        try:
            hasil = extract_json(teks)
        except json.JSONDecodeError as e:
            return {"error": f"Format JSON dari AI tidak valid: {str(e)}"}

        hasil, validation_error = validate_result(hasil)
        if validation_error:
            return {"error": validation_error}

        print("\n========== CONTENT ENGINE ==========")
        print(f"Title: {hasil['title']}")
        for i, scene in enumerate(hasil['scenes']):
            print(f"Scene {i+1}: {scene}")
        print(f"Total {len(hasil['scenes'])} Scenes dihasilkan.")
        print("====================================\n")

        return hasil

    except Exception as e:
        return {"error": f"Gagal menghubungi AI: {str(e)}"}

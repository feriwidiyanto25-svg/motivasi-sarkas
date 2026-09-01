import json
import google.generativeai as genai


# ==========================================
# UTILITAS JSON
# ==========================================
def extract_json(text):
    """
    Mencoba mengambil object JSON pertama dari response Gemini.
    Lebih tahan terhadap response seperti:
    "Berikut hasilnya: {...}"
    """

    text = (text or "").strip()

    # Bersihkan markdown fence
    if "```json" in text:
        text = text.replace("```json", "")

    text = text.replace("```", "").strip()

    # Coba langsung
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Cari object JSON pertama
    start = text.find("{")

    if start == -1:
        raise json.JSONDecodeError(
            "JSON object tidak ditemukan.",
            text,
            0
        )

    decoder = json.JSONDecoder()

    result, _ = decoder.raw_decode(
        text[start:]
    )

    return result


# ==========================================
# VALIDASI HASIL AI
# ==========================================
def validate_result(hasil):
    required_fields = [
        "title",
        "setup_1",
        "setup_2",
        "punchline",
        "visual_context",
        "bg_keywords"
    ]

    # ------------------------------------------
    # FIELD WAJIB
    # ------------------------------------------
    for field in required_fields:

        if field not in hasil:
            return (
                None,
                f"AI tidak menghasilkan field: {field}"
            )

    # ------------------------------------------
    # STRING FIELD
    # ------------------------------------------
    string_fields = [
        "title",
        "setup_1",
        "setup_2",
        "punchline",
        "visual_context"
    ]

    for field in string_fields:

        if not isinstance(
            hasil[field],
            str
        ):
            return (
                None,
                f"Field {field} harus berupa teks."
            )

        hasil[field] = hasil[field].strip()

        if not hasil[field]:
            return (
                None,
                f"Field {field} tidak boleh kosong."
            )

    # ------------------------------------------
    # BG KEYWORDS
    # ------------------------------------------
    if not isinstance(
        hasil["bg_keywords"],
        list
    ):
        return (
            None,
            "bg_keywords harus berupa array."
        )

    cleaned_keywords = []

    for keyword in hasil["bg_keywords"]:

        if not isinstance(
            keyword,
            str
        ):
            continue

        keyword = keyword.strip()

        if keyword:
            cleaned_keywords.append(
                keyword
            )

    # Hapus duplicate
    cleaned_keywords = list(
        dict.fromkeys(
            cleaned_keywords
        )
    )

    if not cleaned_keywords:
        return (
            None,
            "bg_keywords tidak boleh kosong."
        )

    # Maksimal 4 keyword
    hasil["bg_keywords"] = (
        cleaned_keywords[:4]
    )

    # Compatibility dengan app.py lama
    hasil["bg_keyword"] = (
        hasil["bg_keywords"][0]
    )

    # ------------------------------------------
    # VALIDASI PANJANG TEKS
    # ------------------------------------------
    title_words = len(
        hasil["title"].split()
    )

    setup1_words = len(
        hasil["setup_1"].split()
    )

    setup2_words = len(
        hasil["setup_2"].split()
    )

    punchline_words = len(
        hasil["punchline"].split()
    )

    if title_words > 9:
        return (
            None,
            (
                "Title terlalu panjang. "
                f"Maksimal 9 kata, "
                f"hasil: {title_words}."
            )
        )

    if setup1_words > 12:
        return (
            None,
            (
                "Setup 1 terlalu panjang. "
                f"Maksimal 12 kata, "
                f"hasil: {setup1_words}."
            )
        )

    if setup2_words > 12:
        return (
            None,
            (
                "Setup 2 terlalu panjang. "
                f"Maksimal 12 kata, "
                f"hasil: {setup2_words}."
            )
        )

    if punchline_words > 10:
        return (
            None,
            (
                "Punchline terlalu panjang. "
                f"Maksimal 10 kata, "
                f"hasil: {punchline_words}."
            )
        )

    # ------------------------------------------
    # VALIDASI VISUAL CONTEXT
    # ------------------------------------------
    if len(hasil["visual_context"]) < 5:
        return (
            None,
            "visual_context terlalu pendek."
        )

    return hasil, None


# ==========================================
# GENERATE NASKAH
# ==========================================
def generate_naskah(
    topik,
    api_key,
    model_name="gemini-2.5-flash"
):

    # ==========================================
    # VALIDASI API KEY
    # ==========================================
    if not api_key or api_key.strip() == "":
        return {
            "error": "Gemini API Key wajib diisi!"
        }

    # ==========================================
    # VALIDASI TOPIK
    # ==========================================
    if not topik or not topik.strip():
        return {
            "error": "Topik / keresahan wajib diisi!"
        }

    # ==========================================
    # GEMINI
    # ==========================================
    genai.configure(
        api_key=api_key.strip()
    )

    try:

        model = genai.GenerativeModel(
            model_name
        )

        # ==========================================
        # CONTENT + VISUAL ENGINE
        # ==========================================
        prompt = f"""
Kamu adalah creative director dan penulis
konten pengetahuan short-form Indonesia.

KARAKTER:

Kamu adalah pembuat konten yang sangat pandai
menjelaskan hal-hal sehari-hari dengan cara
yang sederhana, menarik, mudah dipahami, dan membuat orang penasaran.

Konten harus terasa seperti seseorang sedang
menceritakan fakta menarik kepada temannya,
bukan seperti membaca buku pelajaran.

GAYA:

- conversational
- natural
- cerdas
- sederhana
- curiosity-driven
- relatable
- sedikit surprising
- tidak kaku
- tidak terasa seperti artikel Wikipedia
- tidak terasa seperti tulisan AI

TOPIK:
"{topik}"

==================================================
TUJUAN EMOSI
==================================================

Penonton idealnya mengalami:

1. "Eh, iya juga."
2. "Kenapa bisa begitu?"
3. "Oh, ternyata..."
4. "Serius?"
5. "Baru tahu."

Jangan langsung memberikan jawaban.

Bangun rasa penasaran terlebih dahulu,
kemudian berikan penjelasan yang memuaskan.

==================================================
STRUKTUR KONTEN
==================================================

Gunakan alur:

HOOK
↓
CURIOSITY
↓
EXPLANATION
↓
REVEAL / INSIGHT

Setiap bagian harus memiliki fungsi berbeda.

Jangan mengulang informasi yang sama
dengan kata-kata berbeda.

==================================================
TITLE / KNOWLEDGE HOOK
==================================================

Fungsi:

Menjadi slide pembuka seperti thumbnail yang hidup.

Judul harus membuat orang ingin mengetahui
jawaban dari topik tersebut.

Karakter judul:

- memancing rasa penasaran
- spesifik
- mudah dipahami
- relevan dengan topik
- tidak clickbait kosong
- tidak memberikan seluruh jawaban
- terdengar natural dalam bahasa Indonesia

Judul boleh berbentuk:

- pertanyaan
- fakta yang terasa aneh
- fenomena sehari-hari
- pernyataan yang membuat penasaran
- "ternyata" jika memang cocok

JANGAN selalu menggunakan:

- "Tahukah kamu..."
- "Ternyata..."
- "Kenapa..."
- "Fakta menarik tentang..."

Variasikan bentuk judul.

Maksimal 12 kata.
Ideal 4–8 kata.

==================================================
SETUP 1 = HOOK
==================================================

Fungsi:

Membuat penonton langsung tertarik
pada fenomena yang dibahas.

Hook harus:

- langsung masuk ke topik
- terasa natural
- mudah dipahami
- membuat penonton bertanya-tanya
- menggunakan bahasa percakapan

Hook dapat berupa:

- pertanyaan
- observasi sehari-hari
- fakta yang aneh
- perbandingan
- situasi yang sering dialami
- pernyataan yang bertentangan dengan intuisi

Jangan langsung memberikan jawaban utama.

Maksimal 15 kata.
Ideal 6–12 kata.

==================================================
SETUP 2 = CURIOSITY BUILD
==================================================

Fungsi:

Memberikan informasi awal yang membuat
penonton semakin penasaran.

Setup 2 harus:

- memberikan sedikit konteks
- memberikan petunjuk menuju jawaban
- membuat fenomena terasa semakin menarik
- tetap menyimpan informasi utama untuk reveal

Setup 2 BUKAN:

- jawaban lengkap
- definisi textbook
- pengulangan hook
- fakta random yang tidak berhubungan

Gunakan bahasa sederhana.

Maksimal 14 kata.
Ideal 8–12 kata.

==================================================
REVEAL / INSIGHT
==================================================

Ini adalah BAGIAN TERPENTING.

Reveal harus memberikan jawaban atau fakta utama
yang membuat penonton merasa:

"Oh... ternyata begitu."

Reveal harus:

- informatif
- jelas
- singkat
- mudah dipahami
- benar secara logika
- relevan langsung dengan hook
- memberikan payoff terhadap rasa penasaran

Jangan hanya mengulang setup.

Jika terdapat fakta yang mengejutkan,
prioritaskan fakta tersebut.

Maksimal 18 kata.
Ideal 8–15 kata.

==================================================
KNOWLEDGE QUALITY
==================================================

Informasi harus:

- masuk akal
- tidak mengarang fakta
- tidak membuat klaim berlebihan
- tidak menggunakan jargon jika tidak diperlukan
- menjelaskan "mengapa" atau "bagaimana"
- memberikan insight yang benar-benar bisa dipelajari

Jika topik memiliki beberapa penjelasan,
pilih penjelasan yang paling sederhana
namun tetap akurat.

Jangan membuat fakta hanya agar terdengar menarik.

==================================================
VARIASI PENYAMPAIAN
==================================================

Setiap naskah harus terasa berbeda.

Gunakan teknik yang paling sesuai dengan topik:

1. Pertanyaan
2. Kontras
3. Fakta mengejutkan
4. Perbandingan
5. Analogi sederhana
6. Sebab-akibat
7. Ekspektasi vs kenyataan
8. Fenomena sehari-hari
9. Sejarah singkat
10. Eksperimen sederhana
11. Kesalahpahaman umum
12. "Ternyata" moment

Jangan menggunakan struktur yang sama
pada setiap video.

Jangan terlalu sering menggunakan:

- "Tahukah kamu..."
- "Ternyata..."
- "Pernahkah kamu..."
- "Jadi..."
- "Hal ini karena..."
- "Itulah sebabnya..."

Variasikan pembukaan dan cara menjelaskan.

==================================================
CONVERSATIONAL STYLE
==================================================

Tulislah seperti manusia sedang menjelaskan
sesuatu kepada temannya.

Gunakan:

- bahasa Indonesia natural
- kalimat pendek
- kata yang familiar
- ritme yang nyaman untuk voice-over

Hindari:

- bahasa akademis
- paragraf panjang
- definisi textbook
- terlalu banyak istilah teknis
- kalimat berbelit
- gaya artikel berita

==================================================
VISUAL ENGINE
==================================================

Selain naskah, tentukan konsep visual
yang benar-benar mendukung isi konten.

Visual harus membantu penonton memahami
fenomena yang sedang dijelaskan.

Jangan hanya memberikan keyword umum seperti:

"coffee"
"science"
"interesting"

Buat:

visual_context
=
deskripsi konkret tentang situasi visual
yang paling cocok dengan script.

Contoh:

Topik:
"Kenapa kopi pahit?"

visual_context:
"close-up coffee beans being roasted in a rotating coffee roaster"

BUKAN:

"coffee"

Visual harus mempertimbangkan:

- topik
- hook
- proses yang dijelaskan
- objek utama
- konteks kehidupan
- reveal

==================================================
BG KEYWORDS
==================================================

Buat 2–4 keyword Pexels dalam bahasa Inggris.

Keyword harus:

- konkret
- visual
- mudah dicari di Pexels
- relevan dengan topik
- dapat menghasilkan footage nyata

Contoh:

[
    "coffee roasting",
    "coffee beans close up",
    "pouring coffee"
]

Bukan:

[
    "knowledge",
    "science",
    "interesting"
]

==================================================
ANTI-RANDOM VISUAL
==================================================

Jangan memilih visual hanya karena
keyword terdengar berhubungan.

Visual harus menjelaskan atau memperkuat
apa yang sedang dibicarakan.

Jika topik membahas sebuah proses,
prioritaskan footage yang menunjukkan proses tersebut.

Jika topik membahas sebuah benda,
prioritaskan footage benda tersebut.

Jika topik membahas fenomena alam,
prioritaskan footage fenomena tersebut.

Jika topik membahas sejarah,
gunakan visual yang merepresentasikan
periode atau objek sejarah tersebut.

==================================================
QUALITY CHECK
==================================================

Sebelum menghasilkan JSON, pastikan:

1. Hook membuat penasaran?
2. Topik langsung jelas?
3. Setup 2 menambah rasa ingin tahu?
4. Reveal benar-benar menjawab pertanyaan?
5. Reveal tidak terlalu mudah ditebak?
6. Informasi faktual dan masuk akal?
7. Tidak terasa seperti Wikipedia?
8. Tidak terasa seperti tulisan AI?
9. Bahasa nyaman untuk voice-over?
10. Tidak ada informasi yang berulang?
11. Struktur tidak terlalu mirip video sebelumnya?
12. Visual benar-benar cocok?
13. Keyword Pexels konkret?
14. Visual dapat ditemukan di footage nyata?
15. Ada alasan bagi penonton untuk menonton sampai reveal?

Jika hook lemah,
buat ulang.

Jika reveal terlalu biasa,
cari fakta atau sudut penjelasan yang lebih menarik.

Jika penjelasan terlalu teknis,
sederhanakan.

Jika visual terlalu umum,
buat lebih spesifik.

==================================================
OUTPUT
==================================================

Kembalikan HANYA JSON VALID.

Tidak ada markdown.
Tidak ada ```json.
Tidak ada penjelasan tambahan.

Format:

{{
    "title": "...",
    "setup_1": "...",
    "setup_2": "...",
    "reveal": "...",
    "visual_context": "...",
    "bg_keywords": [
        "...",
        "...",
        "..."
    ]
}}
"""

        # ==========================================
        # GENERATE
        # ==========================================
        response = model.generate_content(
            prompt
        )

        teks = (
            getattr(
                response,
                "text",
                ""
            ) or ""
        ).strip()

        if not teks:
            return {
                "error": "Gemini tidak menghasilkan teks."
            }

        # ==========================================
        # PARSE JSON
        # ==========================================
        try:

            hasil = extract_json(
                teks
            )

        except json.JSONDecodeError as e:

            return {
                "error": (
                    "Format JSON dari AI tidak valid: "
                    f"{str(e)}"
                )
            }

        # ==========================================
        # VALIDASI
        # ==========================================
        hasil, validation_error = (
            validate_result(
                hasil
            )
        )

        if validation_error:
            return {
                "error": validation_error
            }

        # ==========================================
        # LOG
        # ==========================================
        title_words = len(
            hasil["title"].split()
        )

        setup1_words = len(
            hasil["setup_1"].split()
        )

        setup2_words = len(
            hasil["setup_2"].split()
        )

        punchline_words = len(
            hasil["punchline"].split()
        )

        print("")
        print(
            "========== CONTENT ENGINE =========="
        )

        print(
            f"Title     ({title_words} kata): "
            f"{hasil['title']}"
        )

        print(
            f"Setup 1   ({setup1_words} kata): "
            f"{hasil['setup_1']}"
        )

        print(
            f"Setup 2   ({setup2_words} kata): "
            f"{hasil['setup_2']}"
        )

        print(
            f"Punchline ({punchline_words} kata): "
            f"{hasil['punchline']}"
        )

        print(
            f"Visual    : "
            f"{hasil['visual_context']}"
        )

        print(
            "Keywords  : "
            f"{hasil['bg_keywords']}"
        )

        print(
            "===================================="
        )
        print("")

        return hasil

    except Exception as e:

        return {
            "error": (
                "Gagal menghubungi AI: "
                f"{str(e)}"
            )
        }

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
konten short-form Indonesia.

KARAKTER:
"MOTIVATOR YANG SUDAH KEHILANGAN HARAPAN."

Konten terlihat seperti video motivasi,
tetapi perlahan membangun harapan lalu
mematahkannya dengan punchline.

TOPIK / KERESAHAN USER:
"{topik}"

==================================================
TUJUAN EMOSI
==================================================

Penonton harus mengalami:

1. "Ini gue banget."
2. "Oh, ini video motivasi."
3. "Kayaknya masuk akal."
4. "Tunggu..."
5. "Anjir."

Jangan langsung membuat joke.
Bangun setup terlebih dahulu.

==================================================
TITLE / SARCASTIC MOTIVATION HOOK
==================================================

Fungsi:
Menjadi slide pembuka seperti thumbnail yang hidup.
Judul harus menjadi "umpan pertama" sebelum Setup 1.

JUDUL HARUS TERASA SEPERTI DNA "MOTIVASI SARKAS":
- terdengar seperti nasihat, prinsip hidup, motivasi, atau kalimat bijak
- tetapi memiliki ironi atau makna yang bisa dipelintir
- relevan langsung dengan keresahan user
- selaras dengan Setup 1, Setup 2, dan Punchline
- membangun rasa penasaran tanpa membocorkan punchline
- terasa cerdas, santai, relatable, dan deadpan
- bukan sekadar mengulang kata-kata dari Setup 1
- bukan judul berita
- bukan clickbait kosong
- jangan selalu menggunakan "Kamu...", "Jangan...", atau "Ternyata..."
- pilih sudut sarkas yang paling cocok dengan keseluruhan joke

PENTING:
Judul harus terdengar seperti MOTIVASI NORMAL pada pandangan pertama,
lalu setelah penonton melihat isi video, judul tersebut terasa ironis.

Contoh pola (BUKAN template wajib):
- "Kerja Keras Pasti Membawa Hasil."
- "Rezeki Memang Tidak Akan Tertukar."
- "Semua Orang Punya Waktunya Sendiri."
- "Tetap Bersyukur, Itu Kunci Kebahagiaan."

Buat judul baru yang sesuai topik dan joke.
Jangan menyalin contoh di atas jika tidak cocok.

Maksimal 9 kata.
Ideal 4–8 kata.

JANGAN membocorkan punchline di judul.

==================================================
SETUP 1 = HOOK
==================================================

Fungsi:
Membuat penonton langsung merasa relate.

Aturan:
- berdasarkan langsung dari keresahan user
- terasa seperti manusia sedang curhat
- santai
- natural
- tidak formal
- menarik sejak kalimat pertama

Maksimal 12 kata.
Ideal 6–10 kata.

==================================================
SETUP 2 = MOTIVATION BAIT
==================================================

Fungsi:
Membuat penonton percaya bahwa video ini akan memberikan
nasihat atau harapan yang masuk akal.

Setup 2 harus menjadi "umpan motivasi" sebelum punchline.

Karakter:
- terdengar seperti manusia, bukan kutipan motivasi generik
- memberikan sedikit harapan
- bisa berupa nasihat
- bisa berupa optimisme
- bisa berupa pembenaran
- bisa berupa observasi kehidupan
- bisa berupa kalimat bijak sederhana

JANGAN selalu menggunakan pola:
- "Tenang, ..."
- "Setiap orang punya ..."
- "Jangan menyerah, ..."
- "Percayalah pada proses."
- "Semua akan baik-baik saja."

Variasikan cara membangun harapan.

Contoh:

Topik:
"umur 30 belum sukses"

Bisa:
"Tenang, sukses memang nggak punya jadwal yang sama."

Atau:
"Belum terlambat. Banyak orang baru menemukan jalannya setelah gagal."

Atau:
"Yang penting tetap jalan, meskipun arahnya belum jelas."

Atau:
"Nggak semua orang langsung berhasil di percobaan pertama."

PENTING:

Setup 2 TIDAK BOLEH:
- menyelesaikan masalah
- memberikan solusi nyata
- mengalahkan punchline
- sudah menjadi joke
- terlalu lucu
- terlalu gelap
- Maksimal 12 kata.
- Ideal 7–11 kata.

Setup 2 harus meninggalkan "harapan kecil"
yang nantinya bisa dihancurkan oleh punchline.

Tujuannya:

SETUP 1
"Ini gue banget."

↓

SETUP 2
"Oh, mungkin memang masih ada harapan."

↓

PUNCHLINE
"Oh... ternyata nggak."

Setup 2 harus menjadi JEMBATAN menuju punchline,
bukan tujuan akhir dari video.

==================================================
PUNCHLINE = REVERSAL
==================================================

Ini adalah BAGIAN TERPENTING.

Punchline harus menghancurkan harapan
yang baru dibangun.

Harus:
- singkat
- mudah dipahami sekali baca
- relevan dengan topik
- memiliki payoff
- tidak menjelaskan joke
- tidak mengulang setup
- tidak terdengar generik
- membuat orang ingin replay

Maksimal 10 kata.
Ideal 4–9 kata.

Semakin dekat ke punchline,
semakin sedikit kata.

==================================================
VARIASI HUMOR
==================================================


Setiap naskah harus terasa berbeda.

Contoh yang diberikan di prompt hanya menunjukkan
GAYA HUMOR, bukan template yang boleh ditiru terus-menerus.

JANGAN mengulang struktur kalimat yang sama
pada generasi berikutnya.

Jangan terlalu sering menggunakan:

- "Mereka X, kamu Y."
- "Jangan X, karena Y."
- "Tenang, ... ternyata ..."
- "Jalan keluarnya? ..."
- "Iya, ..."

Gunakan variasi teknik:

1. Wordplay
2. Kontras
3. Ironi
4. Realita pahit
5. Logika absurd
6. Self roast
7. Fake wisdom
8. Twist
9. Perbandingan
10. Eskalasi absurd
11. Double meaning
12. Callback terhadap kata dari setup

Pilih teknik yang paling cocok dengan TOPIK.
Jangan memilih teknik secara acak jika membuat joke menjadi tidak natural.

PUNCHLINE HARUS TERASA SEPERTI HASIL ALAMI
DARI TOPIK, BUKAN KUMPULAN TEMPLATE.

Contoh:

TOPIK:
"umur 30 belum sukses"

Boleh:
"Timeline mereka sudah deadline. Kamu masih loading."

Tetapi jangan menganggap struktur
"mereka X, kamu Y" sebagai pola wajib.

Untuk topik lain, gunakan struktur berbeda.

Tujuan akhirnya:
Penonton tidak bisa menebak bentuk punchline
hanya dari melihat dua video sebelumnya.

==================================================
PERSONALITY
==================================================

Dia bukan orang marah.

Dia bukan membenci penonton.

Dia adalah motivator yang masih memberi semangat,
tetapi terlalu sadar dengan kenyataan hidup.

Tone:

- santai
- sarkas
- cerdas
- relatable
- deadpan
- absurd jika cocok
- tidak berlebihan

Hindari:

- penghinaan kelompok
- kebencian
- politik
- vulgar
- ancaman

==================================================
VISUAL ENGINE
==================================================

Selain naskah, tentukan konsep visual
yang benar-benar mendukung isi script.

Jangan hanya memberikan keyword umum seperti:
"stressed"
jika visual bisa dibuat lebih spesifik.

Buat:

visual_context
=
deskripsi singkat tentang situasi visual
yang paling cocok dengan script.

Contoh:

Topik:
"pengen bangun tidur jadi sultan"

visual_context:
"person waking up in a luxurious bedroom"

BUKAN:
"stress"

==================================================
BG KEYWORDS
==================================================

Buat 2–4 keyword Pexels dalam bahasa Inggris.

Keyword harus:

- konkret
- visual
- mudah dicari di Pexels
- relevan dengan situasi
- bukan abstraksi terlalu umum

Contoh:

[
    "luxury bedroom",
    "wealthy lifestyle",
    "expensive house"
]

Bukan:

[
    "success",
    "motivation",
    "dream"
]

Pilih keyword yang paling mungkin menghasilkan
video visual nyata.

==================================================
ANTI-RANDOM VISUAL
==================================================

Visual harus mempertimbangkan:

- topik
- hook
- emosi
- konteks kehidupan
- punchline jika relevan

Jangan memilih visual hanya karena
keyword terdengar mirip.

==================================================
QUALITY CHECK
==================================================

Sebelum menghasilkan JSON, pastikan:

1. Hook relatable?
2. Motivation bait natural?
3. Punchline membalik ekspektasi?
4. Punchline lebih pendek?
5. Punchline relevan?
6. Punchline terlalu mudah ditebak?
7. Terasa seperti tulisan AI?
8. Bisa dibuat lebih tajam?
9. Struktur humor terlalu mirip contoh?
10. Visual benar-benar cocok?
11. Keyword Pexels konkret?
12. Visual tidak terlalu abstrak?
13. Kalimat nyaman untuk video vertical?

Jika punchline generik,
buat ulang.

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
    "punchline": "...",
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

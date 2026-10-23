import os
from pathlib import Path

# Base Path
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "chat_history.db"

# Groq API Anahtarları ve Rotasyon Desteği
def groq_keys_getir():
    key_file = BASE_DIR / ".groq_key"
    env_file = BASE_DIR / ".env"
    
    olasi_konumlar = [
        key_file,
        env_file,
        BASE_DIR.parent / "rag_v15" / ".groq_key",
        BASE_DIR.parent / "rag_v14" / ".groq_key",
        BASE_DIR.parent / "rag_v13" / ".groq_key",
        BASE_DIR.parent / "rag_v12" / ".groq_key",
        BASE_DIR.parent / ".groq_key",
        Path.home() / ".groq_key"
    ]
    
    if not os.getenv("GROQ_API_KEY"):
        for p in olasi_konumlar:
            if p.exists() and p.is_file():
                try:
                    text = p.read_text(encoding="utf-8").strip(' "\'\t\r\n')
                    if text.startswith("GROQ_API_KEY="):
                        text = text.split("=", 1)[1].strip(' "\'\t\r\n')
                    if text and text.startswith("gsk_"):
                        os.environ["GROQ_API_KEY"] = text
                        try:
                            key_file.write_text(text, encoding="utf-8")
                        except Exception:
                            pass
                        break
                except Exception:
                    pass

    env_keys = os.getenv("GROQ_API_KEY", "").strip(' "\'\t\r\n')
    if not env_keys:
        return []
    keys = [k.strip(' "\'\t\r\n') for k in env_keys.split(",") if k.strip(' "\'\t\r\n')]
    
    i = 2
    while True:
        k_extra = os.getenv(f"GROQ_API_KEY_{i}", "").strip(' "\'\t\r\n')
        if k_extra and k_extra not in keys:
            keys.append(k_extra)
            i += 1
        else:
            break
    return keys

GROQ_API_KEYS = groq_keys_getir()
GROQ_API_KEY = GROQ_API_KEYS[0] if GROQ_API_KEYS else ""
GROQ_MODEL = os.getenv("RAG_GROQ_MODEL", "qwen/qwen3.6-27b").strip()

# 🛑 10B - 18B PARÇACIKLI TÜM MODELLER TAMAMEN ELEMİŞTİR!
# Sadece yüksek kaliteli 27B, 32B, 70B ve ultra hızlı 8B modeller yer alır.
HIGH_QUALITY_MODELS = [
    "qwen/qwen3.6-27b",
    "qwen-2.5-32b",
    "llama3-70b-8192",
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "mixtral-8x7b-32768"
]

MODEL_DESCRIPTIONS = {
    "qwen/qwen3.6-27b": {
        "name": "Qwen 2.6 / 3.6 27B Instruct",
        "badge": "🌟 VARSAYILAN / EN İYİ KALİTE",
        "desc": "En üstün Türkçe anlama, yüksek akıl yürütme, derin analiz ve mantıksal doğruluk."
    },
    "qwen-2.5-32b": {
        "name": "Qwen 2.5 32B Instruct",
        "badge": "⚡ POPÜLER & YÜKSEK HIZ",
        "desc": "Yüksek performanslı 32 Milyar parametreli model. Türkçe dil ve teknik alanda usta."
    },
    "deepseek-r1-distill-qwen-32b": {
        "name": "DeepSeek R1 Distill Qwen 32B",
        "badge": "🧠 MANTIK & MUHAKEME",
        "desc": "Derin analitik, adım adım akıl yürütme (Reasoning) ve karmaşık problem çözme."
    },
    "llama3-70b-8192": {
        "name": "Meta Llama 3 70B Instruct",
        "badge": "🛡️ GENİŞ BAĞLAM & DENGELİ",
        "desc": "Meta'nın 70 Milyar parametreli dev modeli. Çok yönlü genel kültür ve dengeli yanıtlar."
    },
    "llama-3.3-70b-versatile": {
        "name": "Meta Llama 3.3 70B Versatile",
        "badge": "🛡️ GENİŞ BAĞLAM & DENGELİ",
        "desc": "Meta'nın 70 Milyar parametreli dev modeli. Çok yönlü genel kültür ve dengeli yanıtlar."
    },
    "llama-3.1-8b-instant": {
        "name": "Meta Llama 3.1 8B Instant",
        "badge": "🚀 ULTRA HIZLI / HAFİF",
        "desc": "Anında yanıt üreten, ultra düşük gecikmeli en hafif model."
    },
    "mixtral-8x7b-32768": {
        "name": "Mistral AI Mixtral 8x7B MoE",
        "badge": "📊 32K UZUN ÖZET",
        "desc": "32.000 token geniş bağlam penceresine sahip Uzmanlar Karışımı (MoE) mimarisi."
    }
}

EMBEDDING_MODEL = "intfloat/multilingual-e5-small"

SEARXNG_URLS = [
    os.getenv("SEARXNG_URL", "https://searx.be").strip(),
    "https://searx.space",
    "https://searx.fyi",
    "https://searx.si"
]

DEBUG_MODE = os.getenv("RAG_DEBUG", "0") == "1"
SHOW_RETRIEVED_CHUNKS = os.getenv("RAG_SHOW_CHUNKS", "1") != "0"

CHUNK_SIZE = 800
CHUNK_OVERLAP = 150

SEMANTIC_TOP_K = 10
BM25_TOP_K = 10
FINAL_TOP_K = 4

SEMANTIC_WEIGHT = 0.65
KEYWORD_WEIGHT = 0.35

MIN_FINAL_SCORE = 0.05
RELEVANCE_THRESHOLD = 0.35
BATCH_SIZE = 32

STOP_WORDS = ["<|im_end|>", "User:", "Assistant:"]

GENEL_BILGI_TETIKLEYICILER = [
    "belgede yer almıyor", "belgede yok", "belgede geçmiyor",
    "kendi bilginle", "genel bilginle", "genel kültürünle",
    "dış bilgi", "genel olarak açıkla", "yine de açıkla", "yine de anlat",
    "belgede olmasa da", "genel yapay zeka", "bağlam dışı", "bağlam dışında",
    "belgeden bağımsız", "belge dışı", "belge dışında", "genel açıkla"
]

OZETLEME_TETIKLEYICILER = [
    "özetle", "ozetle", "özeti nedir", "ozeti nedir",
    "dokümanı özetle", "dokumani ozetle", "pdfi özetle", "pdfi ozetle",
    "pdf'i özetle", "pdf'i ozetle", "konusu nedir", "konusu ne",
    "genel olarak özetle", "detaylı özetle", "bana özetle",
    "kitabı özetle", "kitabi ozetle", "belgeyi özetle"
]

SONRAKI_SAYFA_TETIKLEYICILER = [
    "diğer sayfaya geç", "diger sayfaya gec", "diğer sayfa", "diger sayfa",
    "sonraki sayfa", "sonraki sayfaya geç", "devam et", "ilerle",
    "bir sonraki sayfa", "sonraki sayfayı anlat"
]

SAYI_KELIMELERI = {
    "ilk": 1, "birinci": 1, "1.": 1, "1": 1,
    "ikinci": 2, "2.": 2, "2": 2,
    "üçüncü": 3, "ucuncu": 3, "3.": 3, "3": 3,
    "dördüncü": 4, "dorduncu": 4, "4.": 4, "4": 4,
    "beşinci": 5, "besinci": 5, "5.": 5, "5": 5,
    "altıncı": 6, "altinci": 6, "6.": 6, "6": 6,
    "yedinci": 7, "7.": 7, "7": 7,
    "sekizinci": 8, "8.": 8, "8": 8,
    "dokuzuncu": 9, "9.": 9, "9": 9,
    "onuncu": 10, "10.": 10, "10": 10,
}

LANG_LABELS = {
    "tr": "Türkçe", "en": "İngilizce", "de": "Almanca", "fr": "Fransızca",
    "es": "İspanyolca", "it": "İtalyanca", "ar": "Arapça", "zh-cn": "Çince",
    "ja": "Japonca", "ru": "Rusça",
}

TURKISH_INDICATORS = {
    "nedir", "ne", "açıkla", "özetle", "detaylı", "nasıl", "neden", "mı", "mi", "mu", "mü",
    "acikla", "ozetle", "nelerdir", "kaç", "hangi", "var", "yok", "içeriği", "hakkında", "fiyatlar", "artar"
}

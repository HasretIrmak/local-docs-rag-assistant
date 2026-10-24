"""Central configuration for the RAG assistant.

Secrets and environment-specific settings come from environment variables,
optionally loaded from a local, git-ignored ``.env`` file (see ``.env.example``).
Nothing in this file is secret.
"""
import os
from pathlib import Path
from typing import List

# --------------------------------------------------------------------------- #
# Paths
# --------------------------------------------------------------------------- #
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "chat_history.db"


# --------------------------------------------------------------------------- #
# Environment loading
# --------------------------------------------------------------------------- #
def _clean(value: str) -> str:
    return value.strip(" \"'\t\r\n")


def _load_dotenv(path: Path) -> None:
    """Minimal .env loader (one KEY=VALUE per line). Real environment variables win."""
    if not path.is_file():
        return
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, _, value = line.partition("=")
        name = name.strip().removeprefix("export ").strip()
        if name:
            os.environ.setdefault(name, _clean(value))


def _load_legacy_key_file(path: Path) -> None:
    """Backward compatibility: a ``.groq_key`` file containing just the key."""
    if os.getenv("GROQ_API_KEY") or not path.is_file():
        return
    try:
        text = _clean(path.read_text(encoding="utf-8"))
    except OSError:
        return
    if text.startswith("GROQ_API_KEY="):
        text = _clean(text.split("=", 1)[1])
    if text.startswith("gsk_"):
        os.environ["GROQ_API_KEY"] = text


def groq_keys_getir() -> List[str]:
    """Return the configured Groq API keys (read-only; never writes to disk).

    Lookup order: real environment variable -> ``.env`` -> legacy ``.groq_key``.
    ``GROQ_API_KEY`` may hold several comma-separated keys, and additional keys
    can be supplied as ``GROQ_API_KEY_2``, ``GROQ_API_KEY_3`` ...
    """
    _load_dotenv(BASE_DIR / ".env")
    _load_legacy_key_file(BASE_DIR / ".groq_key")

    raw = _clean(os.getenv("GROQ_API_KEY", ""))
    if not raw:
        return []
    keys = [k for k in (_clean(part) for part in raw.split(",")) if k]

    i = 2
    while True:
        extra = _clean(os.getenv(f"GROQ_API_KEY_{i}", ""))
        if extra and extra not in keys:
            keys.append(extra)
            i += 1
        else:
            break
    return keys


GROQ_API_KEYS = groq_keys_getir()
GROQ_API_KEY = GROQ_API_KEYS[0] if GROQ_API_KEYS else ""


# --------------------------------------------------------------------------- #
# LLM models
#
# Hosted model catalogs change often (models get deprecated and replaced), so
# nothing here is hard-wired: override the primary model and the fallback order
# with RAG_GROQ_MODEL / RAG_FALLBACK_MODELS (comma-separated) in your .env.
# See Groq's list of active models: https://console.groq.com/docs/models
# --------------------------------------------------------------------------- #
DEFAULT_MODEL = "qwen/qwen3.6-27b"
DEFAULT_FALLBACK_MODELS = ["openai/gpt-oss-120b", "openai/gpt-oss-20b"]

GROQ_MODEL = _clean(os.getenv("RAG_GROQ_MODEL", DEFAULT_MODEL)) or DEFAULT_MODEL

_fallback_env = os.getenv("RAG_FALLBACK_MODELS")
if _fallback_env is not None:
    FALLBACK_MODELS = [m for m in (_clean(x) for x in _fallback_env.split(",")) if m]
else:
    FALLBACK_MODELS = list(DEFAULT_FALLBACK_MODELS)

# Primary model first, then fallbacks, without duplicates.
MODEL_CHAIN = list(dict.fromkeys([GROQ_MODEL] + FALLBACK_MODELS))
HIGH_QUALITY_MODELS = MODEL_CHAIN  # backward-compatible alias


class _ModelDescriptions(dict):
    """Known models get a friendly description; unknown ones get a generic one."""

    def __missing__(self, key):
        return {"name": key, "badge": "🔧 ÖZEL MODEL", "desc": "Kullanıcı tarafından yapılandırılmış model."}


MODEL_DESCRIPTIONS = _ModelDescriptions({
    "qwen/qwen3.6-27b": {
        "name": "Qwen 3.6 27B",
        "badge": "🌟 VARSAYILAN / EN İYİ KALİTE",
        "desc": "Güçlü Türkçe anlama, yüksek akıl yürütme, derin analiz ve mantıksal doğruluk."
    },
    "openai/gpt-oss-120b": {
        "name": "OpenAI GPT-OSS 120B",
        "badge": "🧠 MANTIK & MUHAKEME",
        "desc": "Büyük açık ağırlıklı model. Karmaşık sorular ve uzun analizler için güçlü yedek."
    },
    "openai/gpt-oss-20b": {
        "name": "OpenAI GPT-OSS 20B",
        "badge": "🚀 HIZLI / HAFİF",
        "desc": "Düşük gecikmeli, hafif ve hızlı yedek model."
    },
})

EMBEDDING_MODEL = "intfloat/multilingual-e5-small"

SEARXNG_URLS = [
    os.getenv("SEARXNG_URL", "https://searx.be").strip(),
    "https://searx.space",
    "https://searx.fyi",
    "https://searx.si"
]

DEBUG_MODE = os.getenv("RAG_DEBUG", "0") == "1"
SHOW_RETRIEVED_CHUNKS = os.getenv("RAG_SHOW_CHUNKS", "1") != "0"

# --------------------------------------------------------------------------- #
# Retrieval
# --------------------------------------------------------------------------- #
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

# --------------------------------------------------------------------------- #
# Turkish intent triggers
# --------------------------------------------------------------------------- #
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

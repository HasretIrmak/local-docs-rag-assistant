import hashlib
import torch
from pathlib import Path
from typing import List, Optional
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

from config import BASE_DIR, EMBEDDING_MODEL, BATCH_SIZE, DEBUG_MODE
from preprocessing import dokuman_yukle, dokuman_parcala

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

print(f"🧠 Embedding modeli yükleniyor ({EMBEDDING_MODEL} - {DEVICE})...", flush=True)
embedding_model = HuggingFaceEmbeddings(
    model_name=EMBEDDING_MODEL,
    model_kwargs={"device": DEVICE},
    encode_kwargs={"normalize_embeddings": True},
)


def dosya_hash_hesapla(dosya_yolu: Path) -> str:
    hasher = hashlib.md5()
    with open(dosya_yolu, "rb") as f:
        buf = f.read(65536)
        while len(buf) > 0:
            hasher.update(buf)
            buf = f.read(65536)
    model_short = EMBEDDING_MODEL.replace("/", "_").replace("-", "_")
    return f"cache_{dosya_yolu.stem}_{hasher.hexdigest()[:8]}_{model_short}"


def vectordb_hazirla(dosya_yolu: Path) -> Optional[Chroma]:
    if not dosya_yolu.exists():
        print(f"❌ Dosya bulunamadı: {dosya_yolu}")
        return None

    cache_dir = BASE_DIR / "vectordb_cache" / dosya_hash_hesapla(dosya_yolu)
    
    if cache_dir.exists() and any(cache_dir.iterdir()):
        try:
            return Chroma(
                persist_directory=str(cache_dir),
                embedding_function=embedding_model
            )
        except Exception as e:
            if DEBUG_MODE:
                print(f"⚠️ Önbellek yükleme hatası ({e}), yeniden oluşturuluyor...")

    docs = dokuman_yukle(dosya_yolu)
    if not docs:
        return None

    chunks = dokuman_parcala(docs)
    if not chunks:
        return None

    try:
        vectordb = Chroma.from_documents(
            documents=chunks[:BATCH_SIZE],
            embedding=embedding_model,
            persist_directory=str(cache_dir)
        )
        
        for i in range(BATCH_SIZE, len(chunks), BATCH_SIZE):
            batch = chunks[i : i + BATCH_SIZE]
            vectordb.add_documents(batch)
            
        return vectordb
    except Exception as e:
        print(f"❌ Vektör veritabanı oluşturma hatası: {e}")
        return None

import re
from pathlib import Path
from typing import List, Optional
from langchain_core.documents import Document
from langchain_community.document_loaders import (
    PyPDFLoader,
    UnstructuredWordDocumentLoader,
    UnstructuredPowerPointLoader
)
from langchain_text_splitters import RecursiveCharacterTextSplitter
from config import CHUNK_SIZE, CHUNK_OVERLAP, DEBUG_MODE


def metin_temizle(text: str) -> str:
    if text is None:
        return ""
    text = str(text)
    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(
        r"([A-ZÇĞİÖŞÜ])\s+([A-ZÇĞİÖŞÜ])\s+([A-ZÇĞİÖŞÜ])",
        r"\1\2\3",
        text,
    )
    return text.strip()


def dokuman_yukle(dosya_yolu: Path) -> List[Document]:
    uzanti = dosya_yolu.suffix.lower()
    docs = []
    
    try:
        if uzanti == ".pdf":
            loader = PyPDFLoader(str(dosya_yolu))
            docs = loader.load()
        elif uzanti in [".docx", ".doc"]:
            loader = UnstructuredWordDocumentLoader(str(dosya_yolu))
            docs = loader.load()
        elif uzanti in [".pptx", ".ppt"]:
            loader = UnstructuredPowerPointLoader(str(dosya_yolu))
            docs = loader.load()
        else:
            if DEBUG_MODE:
                print(f"⚠️ Desteklenmeyen dosya formatı: {uzanti}")
            return []
    except Exception as e:
        if DEBUG_MODE:
            print(f"❌ Dosya okuma hatası ({dosya_yolu.name}): {e}")
        return []

    temiz_docs = []
    for doc in docs:
        temiz_text = metin_temizle(doc.page_content)
        if temiz_text:
            meta = dict(doc.metadata or {})
            meta["source_name"] = dosya_yolu.name
            temiz_docs.append(Document(page_content=temiz_text, metadata=meta))

    return temiz_docs


def dokuman_parcala(docs: List[Document]) -> List[Document]:
    if not docs:
        return []

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    return splitter.split_documents(docs)

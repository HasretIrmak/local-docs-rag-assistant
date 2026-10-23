import re
from typing import List, Tuple, Dict, Set, Optional
from langchain_core.documents import Document
from langchain_chroma import Chroma
from rank_bm25 import BM25Okapi

from config import (
    SEMANTIC_TOP_K, BM25_TOP_K, FINAL_TOP_K,
    SEMANTIC_WEIGHT, KEYWORD_WEIGHT, MIN_FINAL_SCORE, RELEVANCE_THRESHOLD,
    OZETLEME_TETIKLEYICILER, SONRAKI_SAYFA_TETIKLEYICILER, SAYI_KELIMELERI
)


def bm25_index_olustur(vectordb: Chroma) -> Tuple[BM25Okapi, List[Document]]:
    all_docs_dict = vectordb.get()
    documents = []
    
    if all_docs_dict and "documents" in all_docs_dict and all_docs_dict["documents"]:
        contents = all_docs_dict["documents"]
        metadatas = all_docs_dict.get("metadatas", []) or [{}] * len(contents)
        for text, meta in zip(contents, metadatas):
            documents.append(Document(page_content=text, metadata=meta or {}))

    tokenized_corpus = [doc.page_content.lower().split() for doc in documents]
    bm25 = BM25Okapi(tokenized_corpus) if tokenized_corpus else None
    return bm25, documents


def hibrit_arama(
    vectordb: Chroma,
    bm25: BM25Okapi,
    documents: List[Document],
    soru: str
) -> Tuple[List[Document], bool]:
    if not vectordb or not soru.strip():
        return [], False

    semantiks = vectordb.similarity_search_with_relevance_scores(soru, k=SEMANTIC_TOP_K)
    
    semantic_scores = {}
    doc_map = {}
    for doc, score in semantiks:
        key = doc.page_content[:100]
        semantic_scores[key] = max(0.0, float(score))
        doc_map[key] = doc

    bm25_scores = {}
    if bm25 and documents:
        tokens = soru.lower().split()
        scores = bm25.get_scores(tokens)
        max_b = max(scores) if len(scores) > 0 and max(scores) > 0 else 1.0
        
        for idx, score in enumerate(scores):
            doc = documents[idx]
            key = doc.page_content[:100]
            norm_score = float(score) / max_b
            bm25_scores[key] = norm_score
            if key not in doc_map:
                doc_map[key] = doc

    birlestirilmis = []
    for key, doc in doc_map.items():
        s_score = semantic_scores.get(key, 0.0)
        b_score = bm25_scores.get(key, 0.0)
        hibrit_score = (s_score * SEMANTIC_WEIGHT) + (b_score * KEYWORD_WEIGHT)
        if hibrit_score >= MIN_FINAL_SCORE:
            birlestirilmis.append((doc, hibrit_score))

    birlestirilmis.sort(key=lambda x: x[1], reverse=True)
    en_iyi_docs = [doc for doc, score in birlestirilmis[:FINAL_TOP_K]]
    en_yuksek_skor = birlestirilmis[0][1] if birlestirilmis else 0.0

    gecerli = bool(birlestirilmis and en_yuksek_skor >= RELEVANCE_THRESHOLD)
    return en_iyi_docs, gecerli


def kavram_geciyor_mu(vectordb: Chroma, kavram: str) -> List[int]:
    if not kavram or len(kavram.strip()) < 3:
        return []
    docs = vectordb.similarity_search(kavram, k=8)
    sayfalar = set()
    for doc in docs:
        if kavram.lower() in doc.page_content.lower():
            p = doc.metadata.get("page")
            if p is not None:
                try:
                    sayfalar.add(int(p) + 1)
                except ValueError:
                    pass
    return sorted(list(sayfalar))


def sayfa_numarasi_yakala(soru: str) -> Optional[int]:
    soru_l = soru.lower()
    for kelime, num in SAYI_KELIMELERI.items():
        if f"{kelime} sayfa" in soru_l or f"sayfa {kelime}" in soru_l:
            return num
    match = re.search(r"(\d+)\s*\.?\s*sayfa", soru_l)
    if match:
        return int(match.group(1))
    return None


def sonraki_sayfa_istegi_mi(soru: str) -> bool:
    soru_l = soru.lower()
    return any(t in soru_l for t in SONRAKI_SAYFA_TETIKLEYICILER)


def sayfadan_chunklar_getir(documents: List[Document], sayfa_no: int) -> List[Document]:
    bulunanlar = []
    for doc in documents:
        p = doc.metadata.get("page")
        if p is not None:
            try:
                if int(p) + 1 == sayfa_no:
                    bulunanlar.append(doc)
            except ValueError:
                pass
    return bulunanlar


def ozetleme_istegi_mi(soru: str) -> bool:
    soru_l = soru.lower()
    return any(t in soru_l for t in OZETLEME_TETIKLEYICILER)


def ozet_chunklari_getir(documents: List[Document], limit: int = 5) -> List[Document]:
    if not documents:
        return []
    
    ilk_sayfalar = []
    for doc in documents:
        p = doc.metadata.get("page")
        if p is not None:
            try:
                if int(p) <= 5:
                    ilk_sayfalar.append(doc)
            except ValueError:
                pass
    if ilk_sayfalar:
        return ilk_sayfalar[:limit]
    return documents[:limit]

import os
import uuid
import json
import asyncio
from pathlib import Path
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException, Query, Body
from fastapi.responses import HTMLResponse, StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config import BASE_DIR, GROQ_API_KEY, GROQ_MODEL, MODEL_DESCRIPTIONS, HIGH_QUALITY_MODELS
from database import (
    session_olustur, session_listesi_getir, session_getir,
    session_sil, mesaj_ekle, mesajlari_getir, session_guncelle_model, session_guncelle_baslik
)
from embeddings import vectordb_hazirla
from retrieval import (
    bm25_index_olustur, hibrit_arama, sayfa_numarasi_yakala,
    sonraki_sayfa_istegi_mi, sayfadan_chunklar_getir,
    ozetleme_istegi_mi, ozet_chunklari_getir
)
from memory import sohbet_gecmisi_metin_olustur, sorgu_baglamsallastir, genel_bilgi_istegi_mi
from llm import GroqLLMClient, prompt_olustur, fallback_prompt_olustur, baglam_formatla
from utils import searxng_arama

app = FastAPI(title="RAG v16 — Claude Style Web UI", version="16.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global Cache for Loaded Document VectorDBs & BM25 Indexes
LOADED_DBS: Dict[str, Dict[str, Any]] = {}

# Initialize Groq LLM Client
llm_client = GroqLLMClient(api_key=GROQ_API_KEY, model_name=GROQ_MODEL)

# Static Files Setup
STATIC_DIR = BASE_DIR / "static"
STATIC_DIR.mkdir(exist_ok=True)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


def dosya_listesi_scan() -> List[Dict[str, str]]:
    arama_dizinleri = [
        BASE_DIR,
        Path.home() / "Desktop",
        Path.home() / "Documents",
        Path.home() / "Downloads",
    ]
    uzantilar = [".pdf", ".docx", ".pptx"]
    dosyalar = []
    gorulen = set()

    for dizin in arama_dizinleri:
        if dizin.exists():
            for p in dizin.rglob("*"):
                if p.is_file() and p.suffix.lower() in uzantilar:
                    if p.resolve() not in gorulen:
                        gorulen.add(p.resolve())
                        dosyalar.append({
                            "name": p.name,
                            "path": str(p.resolve()),
                            "folder": str(p.parent.name)
                        })
    return sorted(dosyalar, key=lambda x: x["name"].lower())


class SessionCreateReq(BaseModel):
    doc_path: str
    model_name: Optional[str] = None
    title: Optional[str] = None

class ChatReq(BaseModel):
    session_id: str
    question: str
    model_name: Optional[str] = None
    use_web_search: bool = False


@app.get("/", response_class=HTMLResponse)
async def serve_index():
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return "<h1>RAG v16 — Web UI Hazırlanıyor...</h1>"


@app.get("/api/models")
async def get_models():
    """
    10B-18B arası modeller hariç tutulmuş izin verilen modeller.
    """
    modeller = []
    for m_id, info in MODEL_DESCRIPTIONS.items():
        modeller.append({
            "id": m_id,
            "name": info["name"],
            "badge": info["badge"],
            "desc": info["desc"],
            "is_active": m_id == llm_client.model_name
        })
    return {"models": modeller, "active_model": llm_client.model_name}


@app.get("/api/documents")
async def get_documents():
    return {"documents": dosya_listesi_scan()}


@app.get("/api/sessions")
async def get_sessions():
    return {"sessions": session_listesi_getir()}


@app.get("/api/sessions/{session_id}")
async def get_session_details(session_id: str):
    sess = session_getir(session_id)
    if not sess:
        raise HTTPException(status_code=404, detail="Oturum bulunamadı")
    msgs = mesajlari_getir(session_id)
    return {"session": sess, "messages": msgs}


@app.post("/api/sessions")
async def create_session(req: SessionCreateReq):
    if req.doc_path == "__GENEL_AI__":
        session_id = str(uuid.uuid4())[:8]
        title = req.title or "Genel AI & Web Araması"
        model_name = req.model_name or llm_client.model_name
        session_data = session_olustur(session_id, title, "Genel AI & Web Araması", model_name)
        return session_data

    doc_p = Path(req.doc_path)
    if not doc_p.exists():
        raise HTTPException(status_code=404, detail="Seçilen dosya bulunamadı")

    session_id = str(uuid.uuid4())[:8]
    title = req.title or doc_p.name
    model_name = req.model_name or llm_client.model_name

    session_data = session_olustur(session_id, title, doc_p.name, model_name)
    return session_data


@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str):
    session_sil(session_id)
    return {"status": "success", "message": "Oturum ve sohbet geçmişi silindi."}


@app.post("/api/chat/stream")
async def chat_stream(req: ChatReq):
    session_info = session_getir(req.session_id)
    if not session_info:
        raise HTTPException(status_code=404, detail="Sohbet oturumu bulunamadı.")

    from config import groq_keys_getir
    if not llm_client.api_key or not llm_client.groq_client:
        keys = groq_keys_getir()
        if keys:
            llm_client.api_key = keys[0]
            try:
                from groq import Groq
                llm_client.groq_client = Groq(api_key=keys[0])
                llm_client._aktif_modelleri_kesfet()
            except Exception:
                pass

    doc_name = session_info["doc_name"]
    is_genel_mode = doc_name in ["__GENEL_AI__", "Genel AI & Web Araması"]
    active_model = req.model_name or session_info.get("model_name") or llm_client.model_name
    llm_client.set_model(active_model)
    session_guncelle_model(req.session_id, active_model)

    vectordb = None
    bm25 = None
    all_docs = []

    # 1. Doküman Vektör Veritabanını Hazırla / Önbellekten Al (Dokümanlı Mod için)
    if not is_genel_mode:
        if doc_name not in LOADED_DBS:
            matching_files = [f for f in dosya_listesi_scan() if f["name"] == doc_name]
            if not matching_files:
                raise HTTPException(status_code=404, detail=f"Döküman dosyası sistemde bulunamadı: {doc_name}")
            
            doc_path = Path(matching_files[0]["path"])
            vdb = vectordb_hazirla(doc_path)
            if not vdb:
                raise HTTPException(status_code=500, detail="Vektör veritabanı oluşturulamadı.")
            bm25, docs = bm25_index_olustur(vdb)
            LOADED_DBS[doc_name] = {"vdb": vdb, "bm25": bm25, "docs": docs}

        db_cache = LOADED_DBS[doc_name]
        vectordb = db_cache["vdb"]
        bm25 = db_cache["bm25"]
        all_docs = db_cache["docs"]

    # 2. Geçmiş Sohbetleri Yükle & Zamir Bağlamsallaştır
    past_messages = mesajlari_getir(req.session_id)
    history_tuples = []
    for i in range(0, len(past_messages) - 1, 2):
        if past_messages[i]["role"] == "user" and past_messages[i+1]["role"] == "assistant":
            history_tuples.append((past_messages[i]["content"], past_messages[i+1]["content"]))

    soru = req.question.strip()
    baglamsal_soru = sorgu_baglamsallastir(soru, history_tuples)
    sohbet_str = sohbet_gecmisi_metin_olustur(history_tuples)

    # Kullanıcı Mesajını DB'ye Kaydet
    mesaj_ekle(req.session_id, "user", soru)
    
    # İlk mesajda oturum başlığını güncelle
    if len(past_messages) == 0:
        session_guncelle_baslik(req.session_id, soru[:40])

    # 3. İstem Türünü Belirle & Bağlam Çek
    from utils import otomatik_web_arama_gerekli_mi
    is_web = req.use_web_search or soru.lower().startswith("/web ") or otomatik_web_arama_gerekli_mi(soru)
    is_genel = genel_bilgi_istegi_mi(soru)
    is_ozet = ozetleme_istegi_mi(soru)
    is_next_page = sonraki_sayfa_istegi_mi(soru)
    target_page = sayfa_numarasi_yakala(soru)

    secili_docs = []
    is_fallback = False
    context_data = []

    if is_genel_mode:
        if is_web:
            clean_q = soru.replace("/web ", "").strip()
            web_res = searxng_arama(clean_q)
            sys_p = (
                "Sen dürüst, yetenekli bir Yapay Zeka Asistanısın. Kullanıcının sorusuna CANLI DIŞ WEB ARAMASI SONUÇLARINA dayanarak Türkçe cevap ver.\n"
                "ZORUNLU KURAL: Yanıtında ASLA ve KESİNLİKLE 'Here's a thinking process:', 'Analyze User Input:', 'Draft', 'Rule' gibi KENDİ İÇ DÜŞÜNCE VEYA DEĞERLENDİRME ADIMLARINI YAZMA! "
                "Doğrudan kullanıcıya hitap eden net, düzenli, akıcı Türkçe nihai cevabını ver. "
                "ASLA 'belgede geçmemektedir' UYARISI BASMA!\n"
                f"CANLI WEB ARAMASI SONUÇLARI:\n{web_res}"
            )
            usr_p = f"Soru: {soru}"
        else:
            sys_p = (
                "Sen dürüst, bilgi sahibi ve yardımsever bir Yapay Zeka Asistanısın. "
                "ÖNCEKİ SOHBET GEÇMİŞİ:\n" + (sohbet_str or "Henüz yok.") + "\n\n"
                "Kullanıcının sorusuna genel yapay zeka bilginle detaylı, net ve doğrudan Türkçe yanıt ver. "
                "ZORUNLU KURAL: Kendi iç düşünce adımlarını (Here's a thinking process...) KESİNLİKLE YAZMA. "
                "ASLA '⚠️ Uyarı: Bu bilgi belgede geçmemektedir' GİBİ HİÇBİR UYARI CÜMLESİ KULLANMA!"
            )
            usr_p = f"Soru: {soru}"
    elif is_web:
        clean_q = soru.replace("/web ", "").strip()
        web_res = searxng_arama(clean_q)
        sys_p = (
            "Sen dürüst ve mantıklı bir asistansın. Kullanıcının sorusuna CANLI DIŞ WEB ARAMASI SONUÇLARINA dayanarak Türkçe cevap ver.\n"
            "ZORUNLU KURAL: Kendi iç düşünce adımlarını (Here's a thinking process...) KESİNLİKLE YAZMA. Doğrudan net cevabını dök.\n"
            f"CANLI WEB ARAMASI SONUÇLARI:\n{web_res}"
        )
        usr_p = f"Soru: {soru}"
    elif is_genel:
        sys_p, usr_p = fallback_prompt_olustur(soru, sohbet_str)
        is_fallback = True
    elif is_ozet:
        secili_docs = ozet_chunklari_getir(all_docs, limit=5)
        baglam = baglam_formatla(secili_docs)
        sys_p, usr_p = prompt_olustur(soru, baglam, sohbet_str)
    elif target_page:
        secili_docs = sayfadan_chunklar_getir(all_docs, target_page)
        if not secili_docs:
            secili_docs, gecerli = hibrit_arama(vectordb, bm25, all_docs, baglamsal_soru)
            if not gecerli:
                is_fallback = True
        baglam = baglam_formatla(secili_docs)
        sys_p, usr_p = fallback_prompt_olustur(soru, sohbet_str) if is_fallback else prompt_olustur(soru, baglam, sohbet_str)
    else:
        secili_docs, gecerli = hibrit_arama(vectordb, bm25, all_docs, baglamsal_soru)
        if not gecerli:
            is_fallback = True
            sys_p, usr_p = fallback_prompt_olustur(soru, sohbet_str)
        else:
            baglam = baglam_formatla(secili_docs)
            sys_p, usr_p = prompt_olustur(soru, baglam, sohbet_str)

    if secili_docs:
        for d in secili_docs:
            p = d.metadata.get("page", 0)
            if isinstance(p, int): p += 1
            context_data.append({
                "page": p,
                "content": d.page_content[:300] + "..."
            })

    # Server-Sent Events (SSE) Streaming Response
    async def event_generator():
        full_text = []
        
        # Meta Bilgisi İlet (Context & Fallback status)
        meta_event = {
            "type": "meta",
            "is_fallback": is_fallback,
            "context": context_data,
            "model_name": active_model
        }
        yield f"data: {json.dumps(meta_event, ensure_ascii=False)}\n\n"
        
        # Kelime Kelime Canlı Akış
        generator = llm_client.invoke_stream_generator(sys_p, usr_p)
        for item in generator:
            if isinstance(item, dict):
                if item.get("type") == "text":
                    chunk_text = item.get("content", "")
                    full_text.append(chunk_text)
                    yield f"data: {json.dumps({'type': 'text', 'content': chunk_text}, ensure_ascii=False)}\n\n"
                elif item.get("type") == "model_switched":
                    yield f"data: {json.dumps(item, ensure_ascii=False)}\n\n"
            elif isinstance(item, str):
                full_text.append(item)
                yield f"data: {json.dumps({'type': 'text', 'content': item}, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0.005)

        final_raw = "".join(full_text).strip()
        from utils import dusunce_ve_yaniti_ayir
        thinking_text, answer_text = dusunce_ve_yaniti_ayir(final_raw)
        final_content = answer_text if answer_text else final_raw
        
        # Asistan Cevabını DB'ye Kaydet
        mesaj_ekle(
            session_id=req.session_id,
            role="assistant",
            content=final_content,
            context_json=json.dumps(context_data, ensure_ascii=False) if context_data else None,
            is_fallback=is_fallback
        )
        
        end_event = {
            "type": "end",
            "thinking": thinking_text
        }
        yield f"data: {json.dumps(end_event, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=False)

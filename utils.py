import re
import urllib.parse
from typing import Optional, Tuple

try:
    import requests
    REQUESTS_OK = True
except ImportError:
    REQUESTS_OK = False

from config import SEARXNG_URLS, DEBUG_MODE


def metin_temizle(metin: str) -> str:
    if not metin:
        return ""
    temiz = re.sub(r"\s+", " ", metin)
    return temiz.strip()


def yabanci_karakter_temizle(metin: str) -> str:
    """
    LLM çıktısındaki gereksiz kontrol karakterlerini temizler, Türkçe karakterleri korur.
    """
    if not metin:
        return ""
    return metin


AUTO_WEB_KEYWORDS = [
    "en son", "güncel", "son haber", "en yeni", "fiyatı", "bugün", "kaç tl",
    "kim kazandı", "son durum", "en son keşfedilen", "en son çıkan", "yeni çıkan",
    "güncel haber", "hava durumu", "dolar kaç", "euro kaç", "borsa"
]

def otomatik_web_arama_gerekli_mi(soru: str) -> bool:
    if not soru:
        return False
    s_lower = soru.lower()
    return any(k in s_lower for k in AUTO_WEB_KEYWORDS)


def dusunce_ve_yaniti_ayir(metin: str) -> Tuple[str, str]:
    """
    Model yanıtındaki Düşünce Sürecini (Thinking Process / <think>) ve Nihai Yanıtı iki ayrı metin olarak ayırır.
    """
    if not metin:
        return "", ""
    
    thinking = ""
    answer = metin
    
    # 1. <think> ... </think> etiketleri varsa
    if "<think>" in metin:
        m = re.search(r"<think>(.*?)</think>", metin, flags=re.DOTALL)
        if m:
            thinking = m.group(1).strip()
            answer = re.sub(r"<think>.*?</think>", "", metin, flags=re.DOTALL).strip()
        else:
            parts = metin.split("<think>", 1)
            thinking = parts[1].strip() if len(parts) > 1 else ""
            answer = parts[0].strip()
    
    # 2. "Here's a thinking process:" veya reasoning metin blokları varsa
    elif any(pattern in metin for pattern in ["Here's a thinking process", "Analyze User Input:", "Check Constraints:", "Draft Response"]):
        lines = metin.splitlines()
        thinking_lines = []
        answer_lines = []
        in_thinking = True
        
        for line in lines:
            l_strip = line.strip()
            if any(l_strip.startswith(prefix) for prefix in [
                "Here's a thinking process", "Analyze User Input", "Task:", "Check Constraints",
                "Draft Construction", "Evaluate Context", "Rule ", "Snippet ", "Excerpt ", "Identify Entities",
                "Formulate Answer", "Draft Response", "Final Output"
            ]):
                in_thinking = True
                thinking_lines.append(line)
                continue
            
            # Gerçek Türkçe cevaba geçiş anı
            if in_thinking:
                if (re.search(r"^[A-ZÇĞİÖŞÜa-zçğıöşü]", l_strip) 
                    and not any(k in l_strip for k in ["Draft", "Constraint", "Prompt", "System", "Rule", "Snippet", "Excerpt", "Process", "Analyze"])
                    and not l_strip.endswith(":")):
                    in_thinking = False
                    answer_lines.append(line)
                else:
                    thinking_lines.append(line)
            else:
                answer_lines.append(line)
                
        thinking = "\n".join(thinking_lines).strip()
        answer = "\n".join(answer_lines).strip()
        
    return thinking, answer


def dil_tespit_et(metin: str) -> str:
    if not metin or len(metin.strip()) < 5:
        return "tr"
    
    tr_harfler = set("çğıöşüÇĞİÖŞÜ")
    if any(h in tr_harfler for h in metin):
        return "tr"
        
    try:
        from langdetect import detect
        code = detect(metin)
        return code
    except Exception:
        return "tr"


def searxng_arama(sorgu: str, num_results: int = 5) -> str:
    if not REQUESTS_OK or not sorgu:
        return "Canlı web arama motoru kütüphanesi (requests) kullanılamıyor."

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }
    
    sonuclar = []

    # 1. SearXNG Kamu Sunucuları Taraması
    for base_url in SEARXNG_URLS:
        try:
            url = f"{base_url.rstrip('/')}/search?q={urllib.parse.quote(sorgu)}&format=json&language=tr"
            res = requests.get(url, headers=headers, timeout=3)
            if res.status_code == 200:
                data = res.json()
                results = data.get("results", [])
                if results:
                    for item in results[:num_results]:
                        title = item.get("title", "")
                        snippet = item.get("content", item.get("snippet", ""))
                        link = item.get("url", "")
                        if snippet:
                            sonuclar.append(f"• **[{title}]({link})**\n  {snippet}")
                    if sonuclar:
                        return "\n\n".join(sonuclar)
        except Exception as e:
            if DEBUG_MODE:
                print(f"⚠️ SearXNG Sunucu Hatası ({base_url}): {e}")
            continue

    # 2. Wikipedia Türkçe API Fallback
    try:
        wiki_url = f"https://tr.wikipedia.org/w/api.php?action=query&list=search&srsearch={urllib.parse.quote(sorgu)}&format=json"
        res = requests.get(wiki_url, headers=headers, timeout=3)
        if res.status_code == 200:
            wdata = res.json()
            search_items = wdata.get("query", {}).get("search", [])
            if search_items:
                for item in search_items[:3]:
                    w_title = item.get("title", "")
                    w_snippet = re.sub(r'<[^>]+>', '', item.get("snippet", ""))
                    w_link = f"https://tr.wikipedia.org/wiki/{urllib.parse.quote(w_title)}"
                    sonuclar.append(f"• **[Wikipedia: {w_title}]({w_link})**\n  {w_snippet}...")
                if sonuclar:
                    return "\n\n".join(sonuclar)
    except Exception as e:
        if DEBUG_MODE:
            print(f"⚠️ Wikipedia API Hatası: {e}")

    # 3. DuckDuckGo Instant Answer Fallback
    try:
        ddg_api = f"https://api.duckduckgo.com/?q={urllib.parse.quote(sorgu)}&format=json&no_redirect=1"
        res = requests.get(ddg_api, headers=headers, timeout=4)
        if res.status_code == 200:
            d_json = res.json()
            abstract = d_json.get("AbstractText", "")
            heading = d_json.get("Heading", sorgu)
            abstract_url = d_json.get("AbstractURL", "")
            if abstract:
                return f"• **[{heading}]({abstract_url})**\n  {abstract}"
            
            related = d_json.get("RelatedTopics", [])
            for r in related[:num_results]:
                r_text = r.get("Text", "")
                r_url = r.get("FirstURL", "")
                if r_text:
                    sonuclar.append(f"• **[DuckDuckGo]({r_url})**\n  {r_text}")
            if sonuclar:
                return "\n\n".join(sonuclar)
    except Exception as e:
        if DEBUG_MODE:
            print(f"⚠️ DuckDuckGo API Hatası: {e}")

    return "İnternet aramasında sonuç bulunamadı veya canlı web servislerine ulaşılamadı."

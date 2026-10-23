from typing import List, Tuple
from config import GENEL_BILGI_TETIKLEYICILER


def sohbet_gecmisi_metin_olustur(sohbet_gecmisi: List[Tuple[str, str]], max_tur: int = 3) -> str:
    if not sohbet_gecmisi:
        return ""
    
    son_tur = sohbet_gecmisi[-max_tur:]
    satirlar = []
    for s, c in son_tur:
        c_kisa = c[:250] + "..." if len(c) > 250 else c
        satirlar.append(f"Kullanıcı: {s}")
        satirlar.append(f"Asistan: {c_kisa}")
    return "\n".join(satirlar)


def sorgu_baglamsallastir(soru: str, sohbet_gecmisi: List[Tuple[str, str]]) -> str:
    if not sohbet_gecmisi:
        return soru

    zamirler = ["bu", "bunu", "bunlar", "bunları", "o", "onu", "onlar", "onları", "şunu", "şunlar", "buradaki", "orda"]
    soru_kelimeleri = soru.lower().split()
    
    zamir_var_mi = any(z in soru_kelimeleri for z in zamirler)
    if zamir_var_mi:
        son_soru, _ = sohbet_gecmisi[-1]
        return f"{son_soru} baglaminda: {soru}"
        
    return soru


def genel_bilgi_istegi_mi(soru: str) -> bool:
    soru_l = soru.lower()
    return any(t in soru_l for t in GENEL_BILGI_TETIKLEYICILER)

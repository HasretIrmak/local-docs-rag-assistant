from typing import List, Tuple, Generator, Dict, Any
from langchain_core.documents import Document
from config import GROQ_MODEL, MODEL_CHAIN, MODEL_DESCRIPTIONS, STOP_WORDS, DEBUG_MODE

try:
    from groq import Groq
    GROQ_SDK_OK = True
except ImportError:
    GROQ_SDK_OK = False

from utils import yabanci_karakter_temizle


class GroqLLMClient:
    def __init__(self, api_key: str, model_name: str = GROQ_MODEL):
        self.api_key = api_key.strip(' "\'\t\r\n') if api_key else ""
        self.model_name = model_name
        self.groq_client = None
        self.active_models: List[str] = []
        
        if GROQ_SDK_OK and self.api_key:
            try:
                self.groq_client = Groq(api_key=self.api_key)
                self._aktif_modelleri_kesfet()
            except Exception as e:
                if DEBUG_MODE:
                    print(f"⚠️ Groq SDK başlatma hatası: {e}")
                self.groq_client = None

    def set_model(self, model_name: str):
        if model_name in MODEL_DESCRIPTIONS or model_name in self.active_models:
            self.model_name = model_name

    def _aktif_modelleri_kesfet(self):
        """Ask Groq which models are live and keep only those in our chain."""
        if self.groq_client is None:
            return
        try:
            live_ids = {m.id for m in self.groq_client.models.list().data}
        except Exception as e:
            if DEBUG_MODE:
                print(f"⚠️ Aktif model keşif hatası: {e}")
            self.active_models = list(MODEL_CHAIN)  # cannot verify: try the configured chain
            return
        self.active_models = [m for m in MODEL_CHAIN if m in live_ids]
        if DEBUG_MODE:
            missing = [m for m in MODEL_CHAIN if m not in live_ids]
            if missing:
                print(f"⚠️ Şu an Groq'ta bulunmayan modeller: {missing}")

    def _model_listesi_getir(self) -> List[str]:
        pool = self.active_models or list(MODEL_CHAIN)
        return [self.model_name] + [m for m in pool if m != self.model_name]    

    def invoke_stream_generator(self, system_prompt: str, user_prompt: str) -> Generator[Dict[str, Any], None, None]:
        """
        Web SSE için kelime kelime akış üreteci (Generator).
        Yields dict with 'type', 'content', and 'switched_model' info if model falls back!
        """
        if not self.api_key or self.groq_client is None:
            from config import groq_keys_getir
            keys = groq_keys_getir()
            if keys:
                self.api_key = keys[0]
                if GROQ_SDK_OK:
                    try:
                        self.groq_client = Groq(api_key=self.api_key)
                        self._aktif_modelleri_kesfet()
                    except Exception:
                        pass

        if not self.api_key or self.groq_client is None:
            yield {"type": "text", "content": "❌ HATA: GROQ_API_KEY bulunamadı veya istemci başlatılamadı."}
            return

        denecek_modeller = self._model_listesi_getir()
        
        sys_p_clipped = system_prompt[:8000]
        usr_p_clipped = user_prompt[:4000]

        for idx, m in enumerate(denecek_modeller):
            try:
                response_stream = self.groq_client.chat.completions.create(
                    model=m,
                    messages=[
                        {"role": "system", "content": sys_p_clipped},
                        {"role": "user", "content": usr_p_clipped}
                    ],
                    temperature=0.0,
                    max_tokens=4096,
                    stop=STOP_WORDS[:3],
                    stream=True
                )
                
                if idx > 0:
                    yield {
                        "type": "model_switched",
                        "original_model": self.model_name,
                        "switched_model": m,
                        "reason": "Seçilen model erişilemiyor veya limit aşıldı, otomatik yedek modele geçildi."
                    }
                
                for chunk in response_stream:
                    if chunk.choices and chunk.choices[0].delta.content:
                        text_chunk = chunk.choices[0].delta.content
                        temiz = yabanci_karakter_temizle(text_chunk)
                        if temiz:
                            yield {"type": "text", "content": temiz}
                return
            except Exception as e:
                if DEBUG_MODE:
                    print(f"⚠️ Model {m} çağrısı başarısız ({e}), sonraki modele geçiliyor...")
                if idx == len(denecek_modeller) - 1:
                    yield {"type": "text", "content": f"\n❌ Tüm modeller başarısız oldu. Son hata ({m}): {e}\nRAG_GROQ_MODEL ve RAG_FALLBACK_MODELS değişkenlerini Groq'ta şu an aktif modellerle güncelle (bkz. README)."}
                    return
                continue


SYSTEM_PROMPT = """Sen döküman bazlı çalışan son derece dikkatli, dürüst, bilgili ve mantıklı bir RAG Asistanısın.

ÖNCEKİ SOHBET GEÇMİŞİ:
{history}

SANA VERİLEN BAĞLAM:
{context}

GÖREVİN VE KESİN KESİNLİKLE UYULACAK YANIT KURALLARIN:
1. ROMAN / HİKAYE ÇELİŞKİLERİ KURALI:
   - Roman ve hikaye dökümanlarında olaylar sayfalara veya kurgusal planlara göre değişebilir (örneğin bir sayfada öldüğü söylenirken başka bir sayfada hayatta olduğu veya öldü süsü verildiği ortaya çıkabilir).
   - Eğer sana verilen bağlam parçalarında bir durum hakkında farklı/çelişkili bilgiler varsa (örneğin bir yerde öldü denirken başka bir yerde yaşadığı söyleniyorsa), bu durumu gizleme! Kullanıcıya her iki sayfadaki bilgiyi de parçalarıyla netçe açıkla.

2. EĞER SORULAN KONU VEYA DETAYLAR SANA VERİLEN BAĞLAMDA AÇIKLANIYORSA:
   - Yanıtını tamamen yukarıdaki bağlam içindeki gerçek bilgilere dayandır.
   - ASLA VE KESİNLİKLE "⚠️ Uyarı:" VEYA "belgede geçmemektedir" GİBİ HİÇBİR UYARI VEYA ÇEKİNCELİ İFADE KULLANMA! Doğrudan net, kendinden emin ve detaylı cevabını ver.

3. KENDİ İÇ DÜŞÜNCE ADIMLARINI VEYA SİSTEM KURALLARINI ASLA YAZMA:
   - Yanıtında "Here's a thinking process:", "Rule 1", "Check Constraints" gibi kendi iç değerlendirmelerini KESİNLİKLE YAZMA. Doğrudan kullanıcıya Türkçe nihai cevabını ver.

4. EĞER KULLANICI SORUSUNDA BİLİMSEL, TARİHSEL VEYA KAVRAMSAL BİR BİLGİ HATASI YAPMIŞSA (Örn: 'Marie Curie'nin İzafiyet Teorisi'):
   - Yanıtına KESİNLİKLE öncelikle bu bilgi yanlışını kibarca ve net bir şekilde düzelterek başla (Örn: "💡 **Önemli Düzeltme:** İzafiyet Teorisi Marie Curie'ye değil, Albert Einstein'a aittir...").
   - Ardından konuyu doğru bilimsel bilgilerle açıkla.

5. EĞER SORULAN KONU SANA VERİLEN BAĞLAMDA KESİNLİKLE HİÇ GEÇMİYORSA:
   - Yanıtının tam olarak İLK CÜMLESİNE şu uyarıyı koy:
     "⚠️ **Uyarı:** Bu bilgi yüklediğiniz belgede açıkça geçmemektedir. Ancak genel yapay zeka bilgime dayanarak açıklamam gerekirse: "
   - Bu tek uyarının ardından konuyu genel bilginle tamamla.

6. KESİNTİSİZ TAM YANIT KURALI: Cümlelerini noktayla bitir.
"""

SYSTEM_PROMPT_FALLBACK = """Sen yardımsever, dürüst ve bilgi sahibi bir Yapay Zeka Asistanısın.

ÖNCEKİ SOHBET GEÇMİŞİ:
{history}

GÖREVİN:
Kullanıcının sorduğu soru yüklenen belgede bulunamadı veya genel bilgi sorusudur. Genel yapay zeka bilginle kullanıcıya yardımcı olacaksın.

ZORUNLU KURALLAR:
1. EĞER KULLANICI SORUSUNDA BİLİMSEL, TARİHSEL VEYA KAVRAMSAL BİR BİLGİ HATASI YAPMIŞSA (Örn: 'Marie Curie'nin İzafiyet Teorisi'):
   - Yanıtına KESİNLİKLE öncelikle bu bilgi yanlışını kibarca düzelterek başla!
     Örnek: "💡 **Önemli Düzeltme:** İzafiyet Teorisi Marie Curie'ye değil, Albert Einstein'a aittir. Marie Curie ise radyoaktivite ve kimya alanındaki çalışmalarıyla tanınan iki Nobel ödüllü bilim insanıdır."
   - Bu düzeltmenin ardından sorulan teoriyi/kavramı doğru bilimsel açıklamalarıyla detaylıca tamamla.

2. KENDİ İÇ DÜŞÜNCE ADIMLARINI VEYA SİSTEM KURALLARINI ASLA YAZMA:
   - Yanıtında "Here's a thinking process:", "Rule 1", "Check Constraints" gibi kendi iç değerlendirmelerini KESİNLİKLE YAZMA.

3. EĞER HERHANGİ BİR BİLGİ HATASI YOKSA:
   - Yanıtına KESİNLİKLE tam olarak şu uyarı cümlesi ile başla:
     "⚠️ **Uyarı:** Bu bilgi yüklediğiniz belgede açıkça geçmemektedir. Ancak genel yapay zeka bilgime dayanarak açıklamam gerekirse: "
   - Bu uyarıdan sonra sorulan konuyu detaylı, anlaşılır ve doğru bir şekilde genel bilginle açıklayarak bitir.
"""

USER_PROMPT = """Soru: {question}

Lütfen yukarıdaki kurallara kesinlikle uyarak cevabı açıklayıcı bir şekilde ver:"""


def prompt_olustur(soru: str, baglam: str, sohbet_gecmisi_str: str = "") -> Tuple[str, str]:
    sys_p = SYSTEM_PROMPT.format(context=baglam, history=sohbet_gecmisi_str or "Henüz sohbet geçmişi yok.")
    usr_p = USER_PROMPT.format(question=soru)
    return sys_p, usr_p


def fallback_prompt_olustur(soru: str, sohbet_gecmisi_str: str = "") -> Tuple[str, str]:
    sys_p = SYSTEM_PROMPT_FALLBACK.format(history=sohbet_gecmisi_str or "Henüz sohbet geçmişi yok.")
    usr_p = USER_PROMPT.format(question=soru)
    return sys_p, usr_p


def baglam_formatla(docs: List[Document]) -> str:
    parcalar = []
    for i, doc in enumerate(docs, 1):
        page = doc.metadata.get("page", "Bilinmiyor")
        if isinstance(page, int):
            page += 1
        parcalar.append(f"[Parça {i} - Sayfa {page}]:\n{doc.page_content.strip()}")
    return "\n\n".join(parcalar)

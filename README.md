# 🎨 RAG v16 — Claude-Style Web UI & Kalıcı Sohbet Geçmişi Mimarisi

RAG v16, projedeki gelişmiş metin işleme, hibrit arama (%65 Vektör + %35 BM25), `multilingual-e5-small` embedding yeteneklerini **Claude AI İlhamlı Modern Web Arayüzü (Web UI)**, **10B-18B Model Filtreleme**, **SQLite Tabanlı Kalıcı Sohbet Geçmişi** ve **Server-Sent Events (SSE) Canlı Kelime Akışı** ile taçlandıran yeni nesil web tabanlı RAG mimarisidir.

---

## 🚀 ÖNE ÇIKAN YENİLİKLER VE İYİLEŞTİRMELER

1. **🎨 Claude-Style Modern Web Arayüzü (Dark Mode):**
   * Sol yan menü (Sidebar), açılır kapanır geçmiş sohbetler listesi, Claude renk paleti ve glassmorphism kart tasarımları.
   * Canlı kelime kelime yazma efekti (Streaming output).

2. **🛑 10B - 18B Model Filtreleme:**
   * Kullanıcı direktifi doğrultusunda 10B ile 18B arasındaki tüm modeller listeden ve sistemden tamamen temizlenmiştir.
   * Yalnızca yüksek kaliteli `Qwen 2.6/3.6 27B`, `Qwen 2.5 32B`, `DeepSeek R1 32B`, `Meta Llama 3.3 70B` ve `Llama 3.1 8B` modelleri kullanılabilir.

3. **💾 Kalıcı Sohbet Geçmişi (SQLite Database):**
   * Belgelerle yapılan tüm geçmiş sohbetler SQLite veritabanına (`chat_history.db`) otomatik kaydedilir.
   * Uygulamayı kapatıp açsanız dahi eski sohbetlerinize sol menüden tek tıkla ulaşabilirsiniz.

4. **📂 Yerel Döküman Seçici & Arama:**
   * Bilgisayarınızdaki yerel dökümanlar (PDF, DOCX, PPTX) otomatik taranır. Arayüzden istediğiniz dökümanı seçip anında sohbet başlatabilirsiniz.

---

## 🛠️ ÇALIŞTIRMA REHBERİ

```powershell
cd "C:\Users\Hasret Irmak BARAN\Desktop\RAG_Projects\rag_v16"
pip install -r requirements.txt
python main.py
```

`python main.py` çalıştırıldığında tarayıcınız otomatik olarak `http://127.0.0.1:8000` adresinde açılacaktır.

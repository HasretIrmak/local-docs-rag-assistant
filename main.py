import os
import webbrowser
import threading
import time
import uvicorn
from server import app

def open_browser():
    time.sleep(1.5)
    webbrowser.open("http://127.0.0.1:8000")

def main():
    print("\n" + "=" * 76)
    print("   🚀 RAG ASİSTANI v16 — Claude-Style Web UI & Microservice Architecture")
    print("   • Web Arayüzü: http://127.0.0.1:8000")
    print("   • Local Embedding: intfloat/multilingual-e5-small (384-dim, ~4x Hızlı)")
    print("   • Model Filtresi: 10B - 18B Parçacıklı Modeller Tamamen Elendi")
    print("   • Kalıcı Sohbet Geçmişi: SQLite (Belge Bazlı Oturum Saklama)")
    print("   • Canlı Kelime Akışı: Server-Sent Events (SSE) & Groq Cloud LPU")
    print("=" * 76 + "\n")

    threading.Thread(target=open_browser, daemon=True).start()
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=True)

if __name__ == "__main__":
    main()

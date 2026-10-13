---
title: Darica Belediye Asistan
emoji: 🤖
colorFrom: red
colorTo: red
sdk: streamlit
app_file: app.py
pinned: false
short_description: Darıca Belediyesi Akıllı Vatandaş Asistanı
license: apache-2.0
---

# 🏛️ Darıca Belediyesi Akıllı Vatandaş Asistanı

Bu proje, Darıca Belediyesi hizmetleri, nikah ve tesis ücretleri, idari süreçler ve belediye rehberi hakkında vatandaşların sorularını yanıtlamak üzere geliştirilmiş **RAG (Retrieval-Augmented Generation)** destekli bir yapay zeka asistanıdır.

---

## 🚀 Canlı Demo & Bağlantılar
- **Canlı Uygulama (Space):** [Darıca Belediye Asistanı](https://huggingface.co/spaces/Anil-yilmaz/darica-belediye-asistan)
- **Eğitilmiş Model:** [Anil-yilmaz/Darica-Belediye-3B](https://huggingface.co/Anil-yilmaz/Darica-Belediye-3B)

---

## 🛠️ Teknolojiler ve Özellikler
* **Model:** QLoRA ile Fine-Tune edilmiş LLM (3B)
* **Ajan / Araç Mimarisi (`araclar.py`):** Güncel fiyat ve dinamik sorgular için Python fonksiyon entegrasyonu.
* **RAG Mimarisi (`rehber.pdf`):** Belediye dokümanları üzerinden vektör tabanlı bilgi çekme.
* **Arayüz:** Streamlit

---

## 📁 Proje Dosya Yapısı
```text
├── app.py           # Streamlit arayüzü ve ana uygulama akışı
├── araclar.py       # Dinamik sorgular için fonksiyonlar
├── rehber.pdf       # RAG bilgi bankası dokümanı
├── requirements.txt # Gerekli Python kütüphaneleri
└── README.md        # Proje tanıtım belgesi
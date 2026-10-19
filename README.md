---
title: Darıca Belediye Asistan
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

Bu proje, Darıca Belediyesi hizmetleri, nikah ve otopark tarifeleri, tesis çalışma saatleri ve idari süreçler hakkında vatandaş sorularını yanıtlamak üzere geliştirilmiş **Multi-Agent (Çoklu Ajan) + RAG + Fine-Tuned LLM** mimarisine sahip yapay zekâ asistanıdır.

---

## 🚀 Canlı Demo & Bağlantılar
- **Canlı Uygulama (Space):** [Darıca Belediye Asistanı](https://huggingface.co/spaces/Anil-yilmaz/darica-belediye-asistan)
- **Eğitilmiş Model (Hub):** [Anil-yilmaz/Darica-Belediye-3B](https://huggingface.co/Anil-yilmaz/Darica-Belediye-3B)

---

## ⚙️ Sistem Mimarisi ve Çalışma Mantığı

Uygulama, gelen sorguları **3 kademeli hiyerarşik akış** ile işleyerek doğru yanıta yönlendirir:

1. **1. Aşama (Tarife & İndirim Ajanı - `darica_hizmet_hesapla`):** Nikah, otopark, su aboneliği, atık yağ teşvikleri ve yaşa özel (65+ yaş / öğrenci) indirim sorgularını hesaplar.
2. **2. Aşama (Tesis & Çalışma Saatleri Ajanı - `tesis_bilgisi_sorgula`):** `tesisler.csv` veritabanı üzerinden kütüphane, yüzme havuzu ve spor tesislerinin konum, çalışma saatleri ve kapalı gün bilgilerini getirir.
3. **3. Aşama (RAG & LLM / Güvenlik Koruması):** `rehber.pdf` dokümanından dinamik paragraf/blok arama (Mini-RAG) yapar. Belediye hizmet alanı dışındaki soruları tespit ederek halüsinasyon üretmeden **153 Beyaz Masa** yönlendirmesi sağlar (Guardrail).

---

## 🚀 Fine-Tuning & Model Detayları (V2 Release)

Projede temel model olarak **Qwen2.5-3B-Instruct** kullanılmış ve Darıca Belediyesi veri setiyle **QLoRA (4-Bit Quantization)** tekniğiyle ince ayar (fine-tune) yapılmıştır.

- **Veri Temizliği:** Verasetindeki hatalı ifadeler elenmiş, kurumsal 1. şahıs Türkçe iletişim dili kazandırılmıştır.
- **Eğitim Performansı:** Google Colab T4 GPU üzerinde 3 epoch boyunca eğitilmiş, eğitim hatası (Loss) **2.25 seviyesinden 0.15'e** düşürülmüştür.
- **Model Ağırlıkları:** Fine-tune edilen LoRA adaptör ağırlıkları Hugging Face Hub üzerinde erişime açılmıştır.

---

## 💡 Örnek Test Soruları
- 🏋️ *"Sahil Spor Salonu kaça kadar açık ve hangi gün kapalı?"*
- 💍 *"Hafta sonu otelde nikah kıydırma ücreti ne kadar?"*
- 👴 *"72 yaşındayım, spor salonundan yararlanırken bana bir indirim uygulanıyor mu?"*
- 🛢️ *"5 litre atık yağ getirince ne hediye veriyorsunuz?"*
- ❓ *"Darıca'da en iyi pide nerede yenir?"* *(Güvenlik Koruması / 153 Yönlendirmesi)*

---

## 📁 Proje Dosya Yapısı

```text
├── app.py           # Streamlit arayüzü, 3 aşamalı yönlendirme mantığı ve RAG akışı
├── araclar.py       # Dinamik tarife, yaş indirimi ve tesis sorgu ajanları
├── rehber.pdf       # RAG bilgi bankası dokümanı (Belediye Hizmet Rehberi)
├── tesisler.csv     # Tesis konumları, çalışma saatleri ve ücret veritabanı
├── requirements.txt # Gerekli Python kütüphaneleri
└── README.md        # Proje tanıtım belgesi
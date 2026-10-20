import os
import re
import pypdf
import torch
import streamlit as st
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel
from araclar import darica_hizmet_hesapla, tesis_bilgisi_sorgula

# Sayfa Yapılandırması
st.set_page_config(
    page_title="Darıca Belediyesi Akıllı Vatandaş Asistanı",
    page_icon="🏛️",
    layout="wide"
)

# CSS
st.markdown("""
    <style>
    .main-title { font-size: 2.2rem; color: #1E3A8A; font-weight: 700; }
    .tool-box {
        background-color: #FEF3C7; color: #92400E; padding: 8px 14px;
        border-radius: 6px; font-weight: 600; font-size: 0.85rem;
        border: 1px solid #FCD34D; margin-bottom: 12px; display: inline-block;
    }
    .disclaimer-box {
        background-color: #F3F4F6; padding: 10px; border-radius: 6px;
        font-size: 0.78rem; color: #4B5563; border-left: 4px solid #6B7280;
    }
    </style>
""", unsafe_allow_html=True)

# Ön Bellek Yardımcı Fonksiyonları
@st.cache_data
def get_cjk_token_ids(_tokenizer):
    """Çince ve Doğu Asya karakterlerine ait token ID'lerini önbelleğe alır."""
    cjk_ids = []
    for token, token_id in _tokenizer.get_vocab().items():
        if re.search(r'[\u3400-\u4dbf\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]', token):
            cjk_ids.append(token_id)
    return cjk_ids

# Sidebar
with st.sidebar:
    st.title("🏛️ Darıca-Asistan")
    st.markdown("**Geliştirici:** Anıl Yılmaz")
    st.markdown("**Sürüm:** QLoRA + RAG + Multi-Agent Tooling")
    st.divider()
    
    st.subheader("💡 Deneyebileceğiniz Sorular")
    st.caption("• Sahil Spor Salonu kaça kadar açık?")
    st.caption("• Yüzme havuzu hangi gün kapalı ve ücreti ne kadar?")
    st.caption("• Hafta sonu nikah kıydırma ücreti ne kadar?")
    st.caption("• 70 yaşındaki biri spor tesisinden indirimli faydalanabilir mi?")
    st.caption("• 5 litre atık yağ getirince ne veriliyor?")
    
    st.divider()
    st.markdown("""
    <div class="disclaimer-box">
    📌 <b>Sorumluluk Reddi:</b><br>
    Bu uygulama akademik/portfolyo amaçlı <b>gayriresmî (unofficial)</b> bir konsept projedir. Darıca Belediyesi'nin resmî hizmeti değildir.
    </div>
    """, unsafe_allow_html=True)

st.markdown('<p class="main-title">🏛️ Darıca Belediyesi Akıllı Vatandaş Asistanı</p>', unsafe_allow_html=True)

# Model ve Rehber Yükleme
@st.cache_resource
def kaynaklari_yukle():
    pdf_text = ""
    if os.path.exists("rehber.pdf"):
        try:
            # strict=False parametresi ile bozuk PDF stream hatalarını yok saydık
            reader = pypdf.PdfReader("rehber.pdf", strict=False)
            for page in reader.pages:
                try:
                    extracted = page.extract_text()
                    if extracted:
                        pdf_text += extracted + "\n\n"
                except Exception:
                    continue  # Hatalı sayfayı atlayıp diğerlerine devam eder
        except Exception as e:
            st.error(f"PDF okunurken hata oluştu: {e}")
            
    pdf_text = pdf_text.replace("Martıkent", "Darıca").replace("Martıkent Cebimde", "Darıca Belediyesi Mobil Uygulaması")
        
    repo_id = "Anil-yilmaz/Darica-Belediye-3B"
    base_id = "Qwen/Qwen2.5-3B-Instruct"
    
    tokenizer = AutoTokenizer.from_pretrained(repo_id, trust_remote_code=True)
    
    device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.float16 if torch.cuda.is_available() else torch.float32
    
    base_model = AutoModelForCausalLM.from_pretrained(
        base_id,
        torch_dtype=dtype,
        device_map="auto" if torch.cuda.is_available() else None,
        trust_remote_code=True
    )
    model = PeftModel.from_pretrained(base_model, repo_id)
    model.eval()
    
    return tokenizer, model, pdf_text


def en_ilgili_paragrafi_bul(rehber_metni: str, soru: str) -> str:
    """PDF metni içerisinden kullanıcının sorusuyla en çok eşleşen paragrafları seçer."""
    if not rehber_metni.strip():
        return ""

    raw_paragraflar = rehber_metni.split("\n\n")
    paragraflar = []
    for p in raw_paragraflar:
        clean_p = re.sub(r'\s+', ' ', p).strip()
        if len(clean_p) > 30:
            paragraflar.append(clean_p)
    
    etkisizler = {"ve", "veya", "bir", "bu", "ile", "mi", "mı", "mu", "mü", "için", "da", "de", "ne", "zaman", "nasıl", "kadar"}
    soru_kelimeleri = set(re.findall(r'\w+', soru.lower())) - etkisizler
    
    es_anlamlilar = {
        "depozito": "güvence",
        "sonlandırmak": "kapat",
        "sonlandırdığımda": "kapatıldığında",
        "ücretsiz": "bedava",
        "fiyat": "ücret",
        "ücreti": "ücret",
        "evlilik": "nikah",
        "çöp": "atık"
    }
    
    genisletilmis_kelimeler = set(soru_kelimeleri)
    for k in soru_kelimeleri:
        if k in es_anlamlilar:
            genisletilmis_kelimeler.add(es_anlamlilar[k])
            
    skorlu_paragraflar = []
    for p in paragraflar:
        p_lower = p.lower()
        skor = sum(2 if k in p_lower else 0 for k in genisletilmis_kelimeler)
        if skor > 0:
            skorlu_paragraflar.append((skor, p))
            
    skorlu_paragraflar.sort(key=lambda x: x[0], reverse=True)
    
    if skorlu_paragraflar:
        # En yüksek skorlu ilk 2 paragrafı birleştirir
        en_iyi = [p[1] for p in skorlu_paragraflar[:2]]
        return "\n\n".join(en_iyi)
    
    return "\n\n".join(paragraflar[:2])


with st.spinner("Model ve hizmet rehberi yükleniyor..."):
    tokenizer, model, rehber_metni = kaynaklari_yukle()

# Sohbet Geçmişi
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Merhaba Sayın Vatandaşımız! Darıca Belediyesi hizmetleri, tesislerimiz, çalışma saatleri veya başvuru ücretleri hakkında size nasıl yardımcı olabilirim?"}
    ]

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Kullanıcı Sorgusu İşleme
if prompt := st.chat_input("Sorunuzu yazınız..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        p_lower = prompt.lower()
        
        # 1. Aşama: Kapsam Dışı / Başka Belediye Güvenlik Kontrolü
        baska_kurumlar = ["kadıköy", "kadikoy", "üsküdar", "izmit", "gebze", "istanbul büyükşehir", "ankara"]
        if any(kurum in p_lower for kurum in baska_kurumlar):
            cevap = "Ben yalnızca Darıca Belediyesi hizmetleri için özelleştirilmiş bir AI asistanıyım. Başka belediyeler veya farklı kurumlar hakkında bilgi verememekteyim. Darıca Belediyesi ile ilgili sorularınızı memnuniyetle yanıtlayabilirim."
            st.markdown(cevap)
            st.session_state.messages.append({"role": "assistant", "content": cevap})
            
        else:
            yas_match = re.search(r'(\d+)\s*(yaş|yaşında)', p_lower)
            yas = int(yas_match.group(1)) if yas_match else 0
            
            tesis_anahtarlari = [
                "havuz", "yüzme", "kütüphane", "tenis", "buz pateni", 
                "fitness", "paten", "bakımevi", "barınak", "etüt", "salon", "kültür merkezi"
            ]
            is_tesis_sorgusu = any(k in p_lower for k in tesis_anahtarlari)

            # 2. Aşama: Tarife, İndirim ve Hesaplama Ajanı
            is_hesaplama_sorgusu = any(kw in p_lower for kw in ["hesapla", "indirim", "atık yağ", "deterjan", "karavan", "otopark"]) or (
                any(kw in p_lower for kw in ["ücret", "fiyat", "ne kadar", "kaç tl"]) and 
                any(h in p_lower for h in ["nikah", "otopark", "karavan", "su", "atık"])
            )

            if not is_tesis_sorgusu and (is_hesaplama_sorgusu or yas > 0):
                hizmet_tipi = "genel"
                if "nikah" in p_lower:
                    hizmet_tipi = "nikah"
                elif "otopark" in p_lower or "karavan" in p_lower:
                    hizmet_tipi = "otopark"
                elif "atık" in p_lower or "yağ" in p_lower or "deterjan" in p_lower:
                    hizmet_tipi = "atık"
                elif re.search(r'\bsu(yu|yun|ya|da|dan)?\b', p_lower):
                    hizmet_tipi = "su"
                elif "spor" in p_lower:
                    hizmet_tipi = "spor"
                
                st.markdown(f'<div class="tool-box">🛠️ <b>[Ajan Tetiklendi: darica_hizmet_hesapla]</b> (Hizmet: {hizmet_tipi})</div>', unsafe_allow_html=True)
                hesaplanan = darica_hizmet_hesapla(hizmet_tipi=hizmet_tipi, parametre=prompt, yas=yas)
                cevap = f"Darıca Belediyesi güncel tarifelerine göre:\n\n**{hesaplanan}**"
                
                st.markdown(cevap)
                st.session_state.messages.append({"role": "assistant", "content": cevap})

            # 3. Aşama: Tesis Bilgisi ve Çalışma Saatleri Sorgulama Ajanı (CSV Sorgusu)
            elif is_tesis_sorgusu or any(kw in p_lower for kw in ["çalışma saati", "saat kaç", "kaça kadar", "açılış saati", "kapanış saati", "hangi gün kapalı"]):
                st.markdown('<div class="tool-box">🛠️ <b>[Ajan Tetiklendi: tesis_bilgisi_sorgula]</b></div>', unsafe_allow_html=True)
                hesaplanan = tesis_bilgisi_sorgula(prompt)
                cevap = f"Darıca Belediyesi tesis veritabanı sorgu sonucu:\n\n{hesaplanan}"
                
                st.markdown(cevap)
                st.session_state.messages.append({"role": "assistant", "content": cevap})

            # 4. Aşama: RAG ve LLM Üretimi
            else:
                FALLBACK = "Bu konuda detaylı bilgi almak için 153 Beyaz Masa hattımızı arayabilirsiniz."
                ilgili_baglam = en_ilgili_paragrafi_bul(rehber_metni, prompt)

                messages = [
                    {
                        "role": "system",
                        "content": (
                            "Sen Darıca Belediyesi'nin resmi AI vatandaş asistanısın. "
                            "Aşağıda verilen [REHBER BİLGİSİ] içindeki verilere dayanarak vatandaşın sorusunu "
                            "kısa, net ve resmi bir Türkçe ile yanıtla.\n\n"
                            "KURALLAR:\n"
                            "1. Sadece verilen bilgileri kullan, bilgi dışı kural veya rakam uydurma.\n"
                            "2. Cevap rehberde yoksa 'Bu konuda detaylı bilgi almak için 153 Beyaz Masa hattımız ile iletişime geçebilirsiniz.' de.\n"
                            "3. Türkçe dışında dil kullanma.\n"
                            "4. Yalnızca Darıca Belediyesi hizmetleri ile ilgili soruları yanıtla. Başka belediye veya alakasız sorularda bilgi veremeyeceğini belirt.\n"
                            "5. Kullanıcıya YALNIZCA doğal metin olarak yanıt dön. 'dusunce', 'harcama' veya JSON biçimli ham verileri ekrana yazma."
                        )
                    },
                    {
                        "role": "user",
                        "content": f"[REHBER BİLGİSİ]:\n{ilgili_baglam}\n\n[SORU]: {prompt}"
                    }
                ]

                prompt_str = tokenizer.apply_chat_template(
                    messages, tokenize=False, add_generation_prompt=True
                )

                inputs = tokenizer(
                    prompt_str,
                    return_tensors="pt",
                    truncation=True,
                    max_length=2048
                ).to(model.device)

                with torch.no_grad():
                    outputs = model.generate(
                        **inputs,
                        max_new_tokens=250,
                        do_sample=True,
                        temperature=0.2,
                        top_p=0.9,
                        repetition_penalty=1.15,
                        suppress_tokens=get_cjk_token_ids(tokenizer),
                        pad_token_id=tokenizer.eos_token_id
                    )

                input_length = inputs["input_ids"].shape[1]
                cevap = tokenizer.decode(outputs[0][input_length:], skip_special_tokens=True).strip()

                # METİN TEMİZLEME VE SÜZGEÇ
                cevap = re.sub(r'[\u3400-\u4dbf\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]+', '', cevap)
                cevap = re.sub(r'[{}]', '', cevap)
                cevap = cevap.replace("kapatdığınızda", "kapattığınızda")
                cevap = re.sub(r'\s{2,}', ' ', cevap).strip()

                if cevap and cevap[-1] not in ".!?":
                    son_nokta = max(cevap.rfind("."), cevap.rfind("!"), cevap.rfind("?"))
                    if son_nokta > 20:
                        cevap = cevap[:son_nokta + 1]
                    else:
                        cevap += "."

                bad_words = ["tesis_adi", "almaq", "etməyinizdir", "beled-i mahsusa"]
                if len(cevap) < 8 or any(bad in cevap.lower() for bad in bad_words):
                    cevap = FALLBACK

                st.markdown(cevap)
                st.session_state.messages.append({"role": "assistant", "content": cevap})
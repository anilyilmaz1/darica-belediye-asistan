import os
import re
import pypdf
import torch
import streamlit as st
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel
from araclar import darica_hizmet_hesapla, tesis_bilgisi_sorgula

# --- Sayfa Yapılandırması ---
st.set_page_config(
    page_title="Darıca Belediyesi Akıllı Vatandaş Asistanı",
    page_icon="🏛️",
    layout="wide"
)

# --- Özel Stil (CSS) ---
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

# --- Ön Bellek Yardımcı Fonksiyonları ---
@st.cache_data
def get_cjk_token_ids(_tokenizer):
    """Çince ve Doğu Asya karakterlerine ait token ID'lerini önbelleğe alır (Performans İyileştirmesi)."""
    cjk_ids = []
    for token, token_id in _tokenizer.get_vocab().items():
        if re.search(r'[\u3400-\u4dbf\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]', token):
            cjk_ids.append(token_id)
    return cjk_ids

# --- Yan Menü (Sidebar) ---
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

# --- Model ve Rehber Yükleme ---
@st.cache_resource
def kaynaklari_yukle():
    pdf_text = ""
    if os.path.exists("rehber.pdf"):
        reader = pypdf.PdfReader("rehber.pdf")
        for page in reader.pages:
            extracted = page.extract_text()
            if extracted:
                pdf_text += extracted + "\n"
        pdf_text = pdf_text.replace("Martıkent", "Darıca")
        
    repo_id = "Anil-yilmaz/Darica-Belediye-3B"
    base_id = "Qwen/Qwen2.5-3B-Instruct"
    
    tokenizer = AutoTokenizer.from_pretrained(repo_id)
    
    device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.float16 if torch.cuda.is_available() else torch.float32
    
    base_model = AutoModelForCausalLM.from_pretrained(
        base_id,
        torch_dtype=dtype,
        device_map="auto" if torch.cuda.is_available() else None
    )
    model = PeftModel.from_pretrained(base_model, repo_id)
    
    return tokenizer, model, pdf_text

def en_ilgili_paragrafi_bul(rehber_metni, soru):
    """PDF metni içerisinden kullanıcının sorusuyla en çok eşleşen paragrafı seçer."""
    paragraflar = [p.strip() for p in rehber_metni.split("\n\n") if len(p.strip()) > 20]
    
    # Stop-word (etkisiz kelimeler) temizliği
    etkisizler = {"ve", "veya", "bir", "bu", "ile", "mi", "mı", "mu", "mü", "için", "da", "de", "olduğunu", "miyim", "mıyım"}
    soru_kelimeleri = set(re.findall(r'\w+', soru.lower())) - etkisizler
    
    # Eş anlamlı kelime haritası
    es_anlamlilar = {
        "depozito": "güvence",
        "sonlandırmak": "kapat",
        "sonlandırdığımda": "kapatıldığında",
        "ücretsiz": "bedava",
        "paralı": "ücret"
    }
    
    genisletilmis_kelimeler = set(soru_kelimeleri)
    for k in soru_kelimeleri:
        if k in es_anlamlilar:
            genisletilmis_kelimeler.add(es_anlamlilar[k])
            
    en_iyi_paragraf = ""
    en_yuksek_skor = 0
    
    for p in paragraflar:
        p_lower = p.lower()
        skor = sum(1 for k in genisletilmis_kelimeler if k in p_lower)
        if skor > en_yuksek_skor:
            en_yuksek_skor = skor
            en_iyi_paragraf = p
            
    return en_iyi_paragraf if en_yuksek_skor >= 1 else rehber_metni[:1500]

with st.spinner("Model ve hizmet rehberi yükleniyor..."):
    tokenizer, model, rehber_metni = kaynaklari_yukle()

# --- Sohbet Geçmişi ---
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Merhaba Sayın Vatandaşımız! Darıca Belediyesi hizmetleri, tesislerimiz, çalışma saatleri veya başvuru ücretleri hakkında size nasıl yardımcı olabilirim?"}
    ]

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# --- Kullanıcı Sorgusu İşleme ---
if prompt := st.chat_input("Sorunuzu yazınız..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        p_lower = prompt.lower()
        yas_match = re.search(r'(\d+)\s*(yaş|yaşında)', p_lower)
        yas = int(yas_match.group(1)) if yas_match else 0
        
        # Tesis anahtar kelimeleri SADECE gerçek fiziki tesis isimlerinden oluşmalıdır
        tesis_anahtarlari = [
            "havuz", "yüzme", "kütüphane", "tenis", "buz pateni", 
            "fitness", "paten", "bakımevi", "barınak", "etüt"
        ]
        is_tesis_sorgusu = any(k in p_lower for k in tesis_anahtarlari)

        # 1. Aşama: Tarife, İndirim ve Hesaplama Ajanı (Belirli hizmet tipleri veya yaş hesaplaması)
        is_hesaplama_sorgusu = any(kw in p_lower for kw in ["hesapla", "indirim", "atık yağ", "deterjan"]) or (
            any(kw in p_lower for kw in ["ücret", "fiyat", "ne kadar", "kaç tl"]) and 
            any(h in p_lower for h in ["nikah", "otopark", "karavan", "spor", "su"])
        )

        if not is_tesis_sorgusu and (is_hesaplama_sorgusu or yas > 0):
            hizmet_tipi = "genel"
            if "nikah" in p_lower:
                hizmet_tipi = "nikah"
            elif "otopark" in p_lower or "karavan" in p_lower:
                hizmet_tipi = "otopark"
            elif "atık" in p_lower or "yağ" in p_lower or "deterjan" in p_lower:
                hizmet_tipi = "atık"
            elif any(k in p_lower for k in ["spor", "tesis", "kültür"]) or ("salon" in p_lower and "spor" not in p_lower):
                hizmet_tipi = "spor"
            elif re.search(r'\bsu(yu|yun|ya|da|dan)?\b', p_lower):
                hizmet_tipi = "su"
            
            st.markdown(f'<div class="tool-box">🛠️ <b>[Ajan Tetiklendi: darica_hizmet_hesapla]</b> (Hizmet: {hizmet_tipi})</div>', unsafe_allow_html=True)
            hesaplanan = darica_hizmet_hesapla(hizmet_tipi=hizmet_tipi, parametre=prompt, yas=yas)
            cevap = f"Darıca Belediyesi güncel tarifelerine göre:\n\n**{hesaplanan}**"
            
            st.markdown(cevap)
            st.session_state.messages.append({"role": "assistant", "content": cevap})

        # 2. Aşama: Tesis Bilgisi ve Çalışma Saatleri Sorgulama Ajanı (CSV Sorgusu)
        elif "çöp" not in p_lower and (is_tesis_sorgusu or any(kw in p_lower for kw in [
            "çalışma saati", "saat kaç", "kaça kadar", "açılış saati", "kapanış saati", "hangi gün kapalı"
        ])):
            st.markdown('<div class="tool-box">🛠️ <b>[Ajan Tetiklendi: tesis_bilgisi_sorgula]</b></div>', unsafe_allow_html=True)
            hesaplanan = tesis_bilgisi_sorgula(prompt)
            cevap = f"Darıca Belediyesi tesis veritabanı sorgu sonucu:\n\n{hesaplanan}"
            
            st.markdown(cevap)
            st.session_state.messages.append({"role": "assistant", "content": cevap})

        # 3. Aşama: RAG ve LLM Üretimi (Mini-Retriever Destekli Nokta Atışı RAG)
        else:
            FALLBACK = "Bu konuda detaylı bilgi almak için 153 Beyaz Masa hattımızı arayabilirsiniz."

            # Tüm PDF yerine sadece soruyla ilgili paragrafı seçiyoruz
            ilgili_baglam = en_ilgili_paragrafi_bul(rehber_metni, prompt)

            messages = [
                {
                    "role": "system",
                    "content": (
                        "Sen Darıca Belediyesi'nin resmi AI vatandaş asistanısın. "
                        "Aşağıda verilen bilgiye dayanarak vatandaşın sorusunu "
                        "kısa, net ve kurumsal bir Türkçe ile yanıtla. "
                        "Bilgi dışında rakam veya kural uydurma."
                    )
                },
                {
                    "role": "user",
                    "content": f"[İLGİLİ REHBER BİLGİSİ]\n{ilgili_baglam}\n\n[SORU]\n{prompt}"
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
                    max_new_tokens=100,
                    do_sample=False,
                    repetition_penalty=1.03,
                    suppress_tokens=get_cjk_token_ids(tokenizer),
                    pad_token_id=tokenizer.eos_token_id
                )

            input_length = inputs["input_ids"].shape[1]
            cevap = tokenizer.decode(outputs[0][input_length:], skip_special_tokens=True).strip()

            # --- METİN TEMİZLEME VE SÜZGEÇ ---
            cevap = re.sub(r'[\u3400-\u4dbf\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]+', '', cevap)
            cevap = re.sub(r'[{}]', '', cevap)
            cevap = re.sub(r'\bmutlu\s+hikay[eö]\s*[\w]*\b', '', cevap, flags=re.IGNORECASE)
            cevap = cevap.replace("kapatdığınızda", "kapattığınızda")

            cevap = re.sub(
                r'^(darıca[n]?\s*belediye[siktmnozâa-z]*\s*[\w\s\.\']*(asistanı[ymız]*|oldum)[\.\,\!]?\s*)',
                '', cevap, flags=re.IGNORECASE
            ).strip()

            for kesici in ("Bilmediğiniz", "kullanabilirim"):
                if kesici in cevap:
                    cevap = cevap.split(kesici)[0].strip()

            cevap = re.sub(r'\s{2,}', ' ', cevap).strip()

            if cevap and cevap[-1] not in ".!?":
                son = max(cevap.rfind("."), cevap.rfind("!"), cevap.rfind("?"))
                if son > 15:
                    cevap = cevap[:son + 1]

            bad_words = ["tesis_adi", "almaq", "etməyinizdir", "beled-i mahsusa", "teyzelemektedir"]
            p_check = cevap.lower()
            if len(cevap) < 8 or any(bad in p_check for bad in bad_words):
                cevap = FALLBACK

            if cevap.isupper():
                cevap = cevap.capitalize()

            st.markdown(cevap)
            st.session_state.messages.append({"role": "assistant", "content": cevap})
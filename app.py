import streamlit as st
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel
import pypdf
import os
import re
from araclar import darica_hizmet_hesapla, tesis_bilgisi_sorgula

st.set_page_config(
    page_title="Darıca Belediyesi Akıllı Vatandaş Asistanı",
    page_icon="🏛️",
    layout="wide"
)

# Arayüz Tasarımı (CSS)
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

# Sol Panel (Sidebar)
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

# RAG & Model Yükleyici
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
    base_model = AutoModelForCausalLM.from_pretrained(
        base_id,
        torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
        device_map="auto" if torch.cuda.is_available() else "cpu"
    )
    model = PeftModel.from_pretrained(base_model, repo_id)
    
    return tokenizer, model, pdf_text

with st.spinner("Model ve Darıca Hizmet Rehberi yükleniyor..."):
    tokenizer, model, rehber_metni = kaynaklari_yukle()

if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Merhaba Sayın Vatandaşımız! Darıca Belediyesi hizmetleri, tesislerimiz, çalışma saatleri veya başvuru ücretleri hakkında size nasıl yardımcı olabilirim?"}
    ]

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Sorunuzu yazınız..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        p_lower = prompt.lower()
        yas_match = re.search(r'(\d+)\s*(yaş|yaşında)', p_lower)
        yas = int(yas_match.group(1)) if yas_match else 0
        
        # 🔴 1. ÖNCELİK: AJAN 2 - Tarife, İndirim, Yaş & Atık Yağ Hesaplama
        if any(kw in p_lower for kw in ["ücret", "fiyat", "ne kadar", "kaç tl", "indirim", "hesapla", "atık", "yağ", "deterjan"]) or yas > 0:
            hizmet_tipi = "genel"
            if "nikah" in p_lower: hizmet_tipi = "nikah"
            elif "otopark" in p_lower or "karavan" in p_lower: hizmet_tipi = "otopark"
            elif "spor" in p_lower or "tesis" in p_lower or "kültür" in p_lower or "salon" in p_lower: hizmet_tipi = "spor"
            elif "su" in p_lower: hizmet_tipi = "su"
            elif "atık" in p_lower or "yağ" in p_lower: hizmet_tipi = "atık"
            
            st.markdown(f'<div class="tool-box">🛠️ <b>[Ajan Tetiklendi: darica_hizmet_hesapla]</b> (Hizmet: {hizmet_tipi})</div>', unsafe_allow_html=True)
            hesaplanan = darica_hizmet_hesapla(hizmet_tipi=hizmet_tipi, parametre=prompt, yas=yas)
            cevap = f"Darıca Belediyesi güncel tarifelerine göre:\n\n**{hesaplanan}**"

        # 🔴 2. ÖNCELİK: AJAN 1 - Tesis, Çalışma Saati, Yer & Ders Sorgulama (CSV)
        elif any(kw in p_lower for kw in ["saat", "açık", "kapanıyor", "kapanış", "açılış", "kapalı", "havuz", "kütüphane", "tenis", "buz pateni", "bakımevi", "müze", "salon", "tesis", "spor", "nereler", "nerede", "yerler", "liste", "hangileri", "ders", "kurs", "eğitim"]):
            st.markdown('<div class="tool-box">🛠️ <b>[Ajan Tetiklendi: tesis_bilgisi_sorgula]</b></div>', unsafe_allow_html=True)
            hesaplanan = tesis_bilgisi_sorgula(prompt)
            cevap = f"Darıca Belediyesi tesis veritabanı sorgu sonucu:\n\n{hesaplanan}"

        # 🔵 3. ÖNCELİK: RAG / METİN SORUSU (LLM GENERATION)
        else:
            messages = [
                {
                    "role": "system",
                    "content": (
                        "Sen Darıca Belediyesi'nin resmi akıllı vatandaş asistanısın. "
                        "Aşağıda verilen rehber dökümanındaki bilgilere dayanarak kullanıcının sorusuna kısa, net, düzgün Türkçe ile cevap ver.\n"
                        "Rehberde bulunmayan konular için 'Bu konuda detaylı bilgi almak için 153 Beyaz Masa hattımızı arayabilirsiniz.' de.\n\n"
                        f"[REHBER DÖKÜMANI]\n{rehber_metni}\n[BAĞLAM SONU]"
                    )
                },
                {"role": "user", "content": prompt}
            ]
            
            prompt_str = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
            inputs = tokenizer(prompt_str, return_tensors="pt")
            
            if torch.cuda.is_available():
                inputs = inputs.to("cuda")
                
            with torch.no_grad():
                outputs = model.generate(
                    **inputs,
                    max_new_tokens=150,
                    do_sample=False,               # Greedy Search: Modelin bozuk hece uydurmasını kesin olarak engeller
                    repetition_penalty=1.2,
                    eos_token_id=tokenizer.eos_token_id,
                    pad_token_id=tokenizer.pad_token_id if tokenizer.pad_token_id is not None else tokenizer.eos_token_id
                )
                
            cevap = tokenizer.decode(outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True).strip()
            
            # --- OTOMATİK METİN TEMİZLEME (Post-Processing) ---
            # Model yine de hepsi büyük harf üretirse standart cümle düzenine çevirir
            if cevap.isupper():
                cevap = cevap.capitalize()
                
            if not cevap:
                cevap = "Konu hakkında detaylı bilgi almak için 153 Beyaz Masa hattımızı arayabilirsiniz."

        st.markdown(cevap)
        st.session_state.messages.append({"role": "assistant", "content": cevap})
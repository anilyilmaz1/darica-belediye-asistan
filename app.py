import os
import re
import pypdf
import torch
import streamlit as st
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel
from araclar import darica_hizmet_hesapla, tesis_bilgisi_sorgula

st.set_page_config(
    page_title="Darıca Belediyesi Akıllı Vatandaş Asistanı",
    page_icon="🏛️",
    layout="wide"
)

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

with st.spinner("Model ve hizmet rehberi yükleniyor..."):
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
        
        tesis_anahtarlari = ["havuz", "yüzme", "kütüphane", "tenis", "buz pateni", "fitness", "paten", "bakımevi", "etüt"]
        is_tesis_sorgusu = any(k in p_lower for k in tesis_anahtarlari)

        # 1. Aşama: Tarife, İndirim ve Yaş Hesaplama Ajanı (Spesifik tesis soruları hariç)
        if not is_tesis_sorgusu and (any(kw in p_lower for kw in ["ücret", "fiyat", "ne kadar", "kaç tl", "indirim", "hesapla", "atık", "yağ", "deterjan"]) or yas > 0):
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

        # 2. Aşama: Tesis Bilgisi ve Çalışma Saatleri Sorgulama Ajanı (CSV)
        elif "çöp" not in p_lower and (is_tesis_sorgusu or any(kw in p_lower for kw in [
            "çalışma saati", "saat kaç", "kaça kadar", "açılış saati", "kapanış saati", "hangi gün kapalı"
        ])):
            st.markdown('<div class="tool-box">🛠️ <b>[Ajan Tetiklendi: tesis_bilgisi_sorgula]</b></div>', unsafe_allow_html=True)
            hesaplanan = tesis_bilgisi_sorgula(prompt)
            cevap = f"Darıca Belediyesi tesis veritabanı sorgu sonucu:\n\n{hesaplanan}"
            
            st.markdown(cevap)
            st.session_state.messages.append({"role": "assistant", "content": cevap})

        # 3. Aşama: RAG ve LLM Üretimi (Gelişmiş Chunking & Kök Tabanlı RAG)
        else:
            chunk_size = 800
            overlap = 200
            chunks = []
            for i in range(0, len(rehber_metni), max(1, chunk_size - overlap)):
                chunks.append(rehber_metni[i:i + chunk_size])

            temiz_soru = re.sub(r'[^\w\s]', '', p_lower)
            stop_words = ["için", "nedir", "nelerdir", "nasıl", "veya", "yapılır", "paketinden", "yararlanmak"]
            soru_kelimeleri = [w for w in temiz_soru.split() if len(w) > 2 and w not in stop_words]
            soru_kokleri = [w[:4] for w in soru_kelimeleri]

            eslesmeler = []
            for chunk in chunks:
                chunk_l = chunk.lower()
                puan = sum(1 for kok in soru_kokleri if kok in chunk_l)
                if puan > 0:
                    eslesmeler.append((puan, chunk))

            eslesmeler.sort(key=lambda x: x[0], reverse=True)
            if eslesmeler:
                rehber_ozet = "\n---\n".join([item[1] for item in eslesmeler[:3]])
            else:
                rehber_ozet = rehber_metni[:2500]

            messages = [
                {  
                    "role": "system",
                    "content": (
                        "Sen Darıca Belediyesi'nin resmi AI vatandaş asistanısın. "
                        "Aşağıda verilen rehber bilgilerini kullanarak soruyu kısa, net ve kurumsal bir dille yanıtla.\n\n"
                        "KURALLAR:\n"
                        "1. SADECE DÜZ METİN OLARAK CEVAP VER. Kesinlikle JSON formatı, `{}` parantez veya anahtar-değer çifti KULLANMA.\n"
                        "2. Yanıtına kesinlikle 'Darıca Belediyesi'nin resmi vatandaş asistanı oldum' gibi yapay ifadeler ekleme.\n"
                        "3. Yalnızca rehberde KESİNLİKLE bulunmayan veya belediye dışındaki sorular için SADECE şu cümleyi söyle: "
                        "\"Bu konuda detaylı bilgi almak için 153 Beyaz Masa hattımızı arayabilirsiniz.\"\n\n"
                        f"[REHBER BİLGİLERİ]\n{rehber_ozet}\n[BAĞLAM SONU]"
                    )
                },
                {"role": "user", "content": prompt}
            ]
            
            prompt_str = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
            
            inputs = tokenizer(
                prompt_str, 
                return_tensors="pt", 
                truncation=True, 
                max_length=2048
            ).to(model.device)
            
            with torch.no_grad():
                outputs = model.generate(
                    **inputs,
                    max_new_tokens=256,             
                    repetition_penalty=1.2,         
                    no_repeat_ngram_size=3,         
                    do_sample=True,                 
                    temperature=0.2,               
                    top_p=0.9,
                    pad_token_id=tokenizer.eos_token_id
                )
            
            input_length = inputs["input_ids"].shape[1]
            cevap = tokenizer.decode(outputs[0][input_length:], skip_special_tokens=True).strip()
            
            p_check = cevap.lower()
            bad_words = [
                "darıcakent", "bilmediğin için", "uygolamasını kullan", "uygulamasını kullan",
                "tesis_adi", "daricsi", "beledicisi", "beled-i mahsusa", "borsa", "borsaya", "yardım ister misiniz"
            ]
            
            if cevap.startswith("{") or "{" in cevap or "}" in cevap or any(bad in p_check for bad in bad_words):
                cevap = "Bu konuda detaylı bilgi almak için 153 Beyaz Masa hattımızı arayabilirsiniz."
                
            if cevap.isupper():
                cevap = cevap.capitalize()
                
            if not cevap:
                cevap = "Bu konuda detaylı bilgi almak için 153 Beyaz Masa hattımızı arayabilirsiniz."

            st.markdown(cevap)
            st.session_state.messages.append({"role": "assistant", "content": cevap})
import os
import re
import pypdf
import streamlit as st
import streamlit.components.v1 as components
from groq import Groq
from araclar import darica_hizmet_hesapla, tesis_bilgisi_sorgula
from weather import get_darica_weather

# Dotenv güvenli içe aktarma
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# DuckDuckGo Web Search güvenli içe aktarma
try:
    from duckduckgo_search import DDGS
except ImportError:
    DDGS = None

# Sayfa Yapılandırması
st.set_page_config(
    page_title="Darıca Belediyesi Akıllı Vatandaş Asistanı",
    page_icon="🏛️",
    layout="wide"
)

# Canlı Hava Durumu Gösterimi
weather = get_darica_weather()

if weather:
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(
            label="Darıca Sıcaklık", 
            value=f"{weather['icon']} {weather['temp']} °C", 
            delta=weather['desc']
        )
    with col2:
        st.metric(
            label="Rüzgar Hızı", 
            value=f"{weather['wind']} km/h"
        )
    with col3:
        st.metric(
            label="Konum / Durum", 
            value="Darıca / Kocaeli", 
            delta="Canlı Veri"
        )

st.markdown("---") 

# CSS Stilleri
st.markdown("""
    <style>
    .main-title { font-size: 2.2rem; color: #1E3A8A; font-weight: 700; }
    .disclaimer-box {
        background-color: #F3F4F6; padding: 10px; border-radius: 6px;
        font-size: 0.78rem; color: #4B5563; border-left: 4px solid #6B7280;
    }
    .tool-badge {
        background-color: #FEF3C7; color: #92400E; padding: 6px 12px;
        border-radius: 6px; font-weight: 600; font-size: 0.85rem;
        border: 1px solid #FCD34D; margin-bottom: 8px; display: inline-block;
    }
    </style>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.title("🏛️ Darıca-Asistan")
    st.markdown("**Geliştirici:** Anıl Yılmaz")
    st.markdown("**Sürüm:** Groq Llama-3.3 + RAG + Multi-Agent + Web Search + Ulaşım Portal")
    st.divider()
    
    st.subheader("💡 Deneyebileceğiniz Sorular")
    st.caption("• Sahil Spor Salonu kaça kadar açık?")
    st.caption("• Bayramoğlu'ndaki Kent Müzesi hangi gün kapalı?")
    st.caption("• Hafta sonu nikah kıydırma ücreti ne kadar?")
    st.caption("• 70 yaşındaki biri spor tesisinden indirim alabilir mi?")
    st.caption("• 🌐 *Darıca Millet Bahçesi'nde bu hafta ne var?* (Web Search)")
    st.caption("• 🌐 *Darıca son dakika haberleri neler?* (Web Search)")
    
    st.divider()
    st.markdown("""
    <div class="disclaimer-box">
    📌 <b>Sorumluluk Reddi:</b><br>
    Bu uygulama akademik/portfolyo amaçlı <b>gayriresmî (unofficial)</b> bir konsept projedir. Darıca Belediyesi'nin resmî hizmeti değildir.
    </div>
    """, unsafe_allow_html=True)

st.markdown('<p class="main-title">🏛️ Darıca Belediyesi Akıllı Vatandaş Asistanı</p>', unsafe_allow_html=True)

# Hizmet Rehberi ve Groq İstemcisi Yükleme
@st.cache_resource
def kaynaklari_yukle():
    pdf_text = ""
    if os.path.exists("rehber.pdf"):
        try:
            reader = pypdf.PdfReader("rehber.pdf", strict=False)
            for page in reader.pages:
                try:
                    extracted = page.extract_text()
                    if extracted:
                        pdf_text += extracted + "\n\n"
                except Exception:
                    continue
        except Exception as e:
            st.error(f"PDF okunurken hata oluştu: {e}")
            
    pdf_text = pdf_text.replace("Martıkent", "Darıca").replace("Martıkent Cebimde", "Darıca Belediyesi Mobil Uygulaması")
        
    api_key = os.environ.get("GROQ_API_KEY")
    groq_client = Groq(api_key=api_key) if api_key else None
    
    return groq_client, pdf_text


def web_arama_yap(sorgu: str) -> str:
    """Canlı İnternet Araması Yapar (Geliştirilmiş & Bölge Destekli)"""
    if not DDGS:
        return ""
    try:
        # Soru eklerini temizleme ve 'Darıca' kelimesi tekrarlarını önleme
        temiz_sorgu = re.sub(r'(neler|nedir|var mı|mu|mı|nelerdir|\?)', '', sorgu, flags=re.IGNORECASE).strip()
        if "darıca" not in temiz_sorgu.lower():
            temiz_sorgu = f"Darıca {temiz_sorgu}"
            
        with DDGS() as ddgs:
            results = list(ddgs.text(keywords=temiz_sorgu, region="tr-tr", max_results=4))
            if not results:
                return ""
            ozet = "\n".join([f"- {r.get('title', '')}: {r.get('body', '')}" for r in results])
            return ozet
    except Exception as e:
        print(f"Web Arama Hatası: {e}")
        return ""


def en_ilgili_paragrafi_bul(rehber_metni: str, soru: str) -> str:
    if not rehber_metni.strip():
        return ""

    raw_paragraflar = rehber_metni.split("\n\n")
    paragraflar = [re.sub(r'\s+', ' ', p).strip() for p in raw_paragraflar if len(p.strip()) > 30]
    
    etkisizler = {"ve", "veya", "bir", "bu", "ile", "mi", "mı", "mu", "mü", "için", "da", "de", "ne", "zaman", "nasıl", "kadar"}
    soru_kelimeleri = set(re.findall(r'\w+', soru.lower())) - etkisizler
    
    es_anlamlilar = {
        "depozito": "güvence", "sonlandırmak": "kapat", "sonlandırdığımda": "kapatıldığında",
        "ücretsiz": "bedava", "fiyat": "ücret", "ücreti": "ücret", "evlilik": "nikah", "çöp": "atık"
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
        return "\n\n".join([p[1] for p in skorlu_paragraflar[:2]])
    
    return ""


with st.spinner("Hizmet rehberi ve servisler yükleniyor..."):
    groq_client, rehber_metni = kaynaklari_yukle()

# SEKMELER
tab_asistan, tab_ulasim = st.tabs([
    "💬 Akıllı Vatandaş Asistanı", 
    "🚌 Darıca & Kocaeli Canlı Ulaşım Takip"
])

# -------------------- SEKME 1: AKILLI ASİSTAN --------------------
with tab_asistan:
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": "Merhaba Sayın Vatandaşımız! Darıca Belediyesi hizmetleri, tesislerimiz, çalışma saatleri, başvuru ücretleri veya güncel konular hakkında size nasıl yardımcı olabilirim?"}
        ]

    # Mesaj geçmişini render et (Girdi kutusunun üstünde kalır)
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

# -------------------- SEKME 2: CANLI ULAŞIM PORTAL --------------------
with tab_ulasim:
    st.subheader("🚌 Darıca & Kocaeli Ulaşım Rehberi & Canlı Otobüs Takip")
    st.caption("Aşağıdaki canlı ekran üzerinden Darıca ve Kocaeli genelindeki otobüs hatlarını, canlı otobüs konumlarını ve durak kalkış saatlerini anlık takip edebilirsiniz.")
    
    components.iframe(
        src="https://e-komobil.com/", 
        height=720, 
        scrolling=True
    )

# -------------------- EKRANIN EN ALTINDA SABİT CHAT INPUT --------------------
if prompt := st.chat_input("Sorunuzu yazınız..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    p_lower = prompt.lower()
    
    # 1. Kapsam Dışı / Başka Şehir Kontrolü
    baska_kurumlar = ["kadıköy", "kadikoy", "üsküdar", "izmit", "gebze", "istanbul büyükşehir", "ankara"]
    if any(kurum in p_lower for kurum in baska_kurumlar):
        cevap = "Ben yalnızca Darıca Belediyesi hizmetleri için özelleştirilmiş bir AI asistanıyım. Başka belediyeler veya farklı şehirler hakkında bilgi verememekteyim."

    else:
        yas_match = re.search(r'(\d+)\s*(yaş|yaşında)', p_lower)
        yas = int(yas_match.group(1)) if yas_match else 0
        
        tesis_anahtarlari = [
            "havuz", "yüzme", "kütüphane", "tenis", "buz pateni", 
            "fitness", "paten", "bakımevi", "barınak", "etüt", "salon", "kültür merkezi"
        ]
        is_tesis_sorgusu = any(k in p_lower for k in tesis_anahtarlari)

        is_hesaplama_sorgusu = any(kw in p_lower for kw in ["hesapla", "indirim", "atık yağ", "deterjan", "karavan", "otopark"]) or (
            any(kw in p_lower for kw in ["ücret", "fiyat", "ne kadar", "kaç tl"]) and 
            any(h in p_lower for h in ["nikah", "otopark", "karavan", "su", "atık"])
        )

        # 2. Ajan: Hesaplama & İndirim
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
            
            hesaplanan = darica_hizmet_hesapla(hizmet_tipi=hizmet_tipi, parametre=prompt, yas=yas)
            cevap = f"🛠️ **[Ajan Tetiklendi: darica_hizmet_hesapla]** (Hizmet: {hizmet_tipi})\n\nDarıca Belediyesi güncel tarifelerine göre:\n\n**{hesaplanan}**"

        # 3. Ajan: Tesis Sorgusu
        elif is_tesis_sorgusu or any(kw in p_lower for kw in ["çalışma saati", "saat kaç", "kaça kadar", "açılış saati", "kapanış saati", "hangi gün kapalı"]):
            hesaplanan = tesis_bilgisi_sorgula(prompt)
            cevap = f"🛠️ **[Ajan Tetiklendi: tesis_bilgisi_sorgula]**\n\nDarıca Belediyesi tesis veritabanı sorgu sonucu:\n\n{hesaplanan}"

        # 4. RAG / Web Search / LLM
        else:
            ilgili_baglam = en_ilgili_paragrafi_bul(rehber_metni, prompt)
            web_sonuclari = ""
            ajan_etiketi = ""

            # Rehberde eşleşme zayıfsa veya güncel konu sorgulanıyorsa Web Search çalıştır
            if not ilgili_baglam or any(kw in p_lower for kw in ["haber", "etkinlik", "son dakika", "bugün", "duyuru", "nedir", "son haber"]):
                web_sonuclari = web_arama_yap(prompt)
                if web_sonuclari:
                    ajan_etiketi = "🛠️ **[Ajan Tetiklendi: web_arama_ajani]**\n\n"

            if not groq_client:
                cevap = "⚠️ Sistem şu anda yanıt üretemiyor (Groq API anahtarı ayarlanmamış)."
            else:
                # Dinamik İstemci (System Prompt) Yönetimi
                if web_sonuclari:
                    system_prompt = (
                        "Sen Darıca Belediyesi'nin resmi AI vatandaş asistanısın.\n"
                        "Sana [CANLI WEB ARAMA SONUÇLARI] altında güncel internet haberleri sağlandı.\n\n"
                        "GÖREVİN:\n"
                        "1. Arama sonuçlarındaki bilgileri net, anlaşılır ve öz bir Türkçe ile vatandaşa aktar.\n"
                        "2. Arama sonuçlarında geçen olay, duyuru veya detayları yanıtında kullan.\n"
                        "3. Kullanıcıya doğrudan doğal metin yanıtı ver."
                    )
                else:
                    system_prompt = (
                        "Sen Darıca Belediyesi'nin resmi AI vatandaş asistanısın.\n"
                        "Aşağıda verilen [REHBER BİLGİSİ] içindeki verilere dayanarak vatandaşın sorusunu yanıtla.\n\n"
                        "KURALLAR:\n"
                        "1. Sadece verilen rehber bilgilerini kullan, kural uydurma.\n"
                        "2. Cevap rehberde yoksa 'Bu konuda detaylı bilgi almak için 153 Beyaz Masa hattımız ile iletişime geçebilirsiniz.' de.\n"
                        "3. Yalnızca Darıca Belediyesi ve Darıca ilçesini ilgilendiren soruları yanıtla."
                    )

                baglam_metni = f"[REHBER BİLGİSİ]:\n{ilgili_baglam}\n\n[CANLI WEB ARAMA SONUÇLARI]:\n{web_sonuclari}"
                user_content = f"{baglam_metni}\n\n[SORU]: {prompt}"

                try:
                    completion = groq_client.chat.completions.create(
                        model="qwen/qwen3.8-27b",
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_content}
                        ],
                        temperature=0.2,
                        max_tokens=400
                    )
                    raw_cevap = completion.choices[0].message.content.strip()
                    cevap = f"{ajan_etiketi}{raw_cevap}" if raw_cevap else "Bu konuda detaylı bilgi almak için 153 Beyaz Masa hattımız ile iletişime geçebilirsiniz."

                except Exception as e:
                    cevap = f"Bir hata oluştu: {str(e)}"

    st.session_state.messages.append({"role": "assistant", "content": cevap})
    st.rerun()
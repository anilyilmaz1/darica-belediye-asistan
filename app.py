import os
import re
import pypdf
import streamlit as st
import streamlit.components.v1 as components
from groq import Groq
from weather import get_darica_weather
from araclar import darica_hizmet_hesapla, tesis_bilgisi_sorgula, darica_son_dakika_haberleri, darica_web_arama, piyasa_verileri_getir
from araclar import get_nobetci_eczane
from datetime import datetime


# Dotenv güvenli içe aktarma
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


# Sayfa Yapılandırması
st.set_page_config(
    page_title="Darıca Belediyesi Akıllı Vatandaş Asistanı",
    page_icon="🏛️",
    layout="wide"
)

st.markdown(
    """
    <style>
        .block-container {
            padding-top: 1.2rem !important;
            padding-bottom: 1rem !important;
        }
    </style>
    """,
    unsafe_allow_html=True,
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


# --- CANLI PİYASA VERİLERİ ---
@st.cache_data(ttl=300)
def get_piyasa():
    return piyasa_verileri_getir()

piyasa = get_piyasa()

p_col1, p_col2, p_col3 = st.columns(3)

with p_col1:
    st.metric(label="Dolar (USD/TL)", value=f"{piyasa['usd']} TL")

with p_col2:
    st.metric(label="Euro (EUR/TL)", value=f"{piyasa['eur']} TL")

with p_col3:
    st.metric(label="🪙 Gram Altın", value=f"{piyasa['altin']} TL")


# --- NÖBETÇİ ECZANELER (YAN YANA KARTLAR) ---
eczaneler = get_nobetci_eczane()

if eczaneler:
    e_cols = st.columns(len(eczaneler))

    for idx, eczane in enumerate(eczaneler):
        with e_cols[idx]:
            st.markdown(
                f"""
                <div style="
                    background-color: #FFF5F5;
                    border-left: 5px solid #E53935;
                    padding: 12px 16px;
                    border-radius: 8px;
                    margin-top: 10px;
                    margin-bottom: 15px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.05);
                    min-height: 140px;
                ">
                    <div style="display: flex; align-items: center; margin-bottom: 4px;">
                        <span style="font-size: 18px; margin-right: 8px;">🏥</span>
                        <strong style="color: #C62828; font-size: 14px;">Darıca Nöbetçi Eczane #{idx+1}</strong>
                    </div>
                    <div style="font-size: 15px; font-weight: bold; color: #2C3E50; margin-top: 4px;">
                        {eczane['isim']}
                    </div>
                    <div style="font-size: 13px; color: #555555; margin-top: 2px;">
                        📍 {eczane['adres']}
                    </div>
                    <div style="font-size: 13px; color: #1E88E5; margin-top: 6px; font-weight: 500;">
                        📞 <a href="tel:{eczane['telefon'].replace(' ', '')}" style="color: #1E88E5; text-decoration: none;">{eczane['telefon']}</a>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

else:
    # Veri çekilemediğinde kullanıcıya gösterilecek güvenli uyarı mesajı
    st.info(
        "🏥 **Nöbetçi Eczane Bilgisi:** Anlık nöbetçi eczane verisi sunucudan"
        " alınamadı. En güncel bilgi için lütfen Kocaeli Eczacı Odası veya 112"
        " hattı üzerinden teyit ediniz."
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
    </style>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.title("🏛️ Darıca-Asistan")
    st.markdown("**Geliştirici:** Anıl Yılmaz")
    st.markdown("**Sürüm:** Groq Qwen 3.8-27b + RAG + Multi-Agent + Web Search + Ulaşım Portal")
    st.divider()
    
    st.subheader("💡 Deneyebileceğiniz Sorular")
    st.caption("• Sahil Spor Salonu kaça kadar açık?")
    st.caption("• Bayramoğlu'ndaki Kent Müzesi hangi gün kapalı?")
    st.caption("• Hafta sonu nikah kıydırma ücreti ne kadar?")
    st.caption("• 70 yaşındaki biri spor tesisinden indirim alabilir mi?")
    st.caption("• 🌐 *Darıca metrosu ne zaman açılacak?* (Web Search)")
    st.caption("• 🌐 *Darıca Millet Bahçesi'nde bu hafta ne var?* (Web Search)")
    
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


def web_arama_yap(sorgu: str):
    """(LLM için bağlam metni, kullanıcıya gösterilecek kaynak listesi) döndürür."""
    return darica_web_arama(sorgu)

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


       # 3.5. Ajan: Yerel Haber Ajanı
        elif any(kw in p_lower for kw in ["son dakika", "yerel haber", "gündem"]):
            haber_metni = darica_son_dakika_haberleri()
            
            if haber_metni:
                cevap = f"🛠️ **[Ajan Tetiklendi: yerel_haber_ajani]**\n\nDarıca yerel basından öne çıkan son başlıklar:\n\n{haber_metni}"
            else:
                # Siteden veri çekilemezse yedek olarak Web Search ajanına yönlendirilir
                web_sonuclari, _ = web_arama_yap(prompt)
                if web_sonuclari and "darıca" in web_sonuclari.lower() and groq_client:
                    system_prompt = (
                        "Sen Darıca Belediyesi'nin resmi AI vatandaş asistanısın.\n"
                        "Aşağıdaki arama sonuçlarından yalnızca Darıca (Kocaeli) ile ilgili güncel haberleri kısaca özetle.\n"
                        "Darıca ile ilgili haber yoksa uydurma, bunu açıkça söyle.\n"
                        "Yanıtta 'CANLI WEB ARAMA SONUÇLARI' gibi iç sistem ifadelerini KULLANMA."
                    )
                    user_content = f"[CANLI WEB ARAMA SONUÇLARI]:\n{web_sonuclari}\n\n[SORU]: {prompt}"
                    
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
                        cevap = f"🛠️ **[Ajan Tetiklendi: web_arama_ajani]**\n\n{raw_cevap}"
                    except Exception:
                        cevap = "Şu anda güncel haber servisine ulaşılamıyor. Detaylı bilgi için 153 Beyaz Masa hattımız ile iletişime geçebilirsiniz."
                else:
                    cevap = "Şu anda güncel haber servisine ulaşılamıyor. Detaylı bilgi için 153 Beyaz Masa hattımız ile iletişime geçebilirsiniz."


        # 4. RAG / Web Search / LLM
        else:
            ilgili_baglam = en_ilgili_paragrafi_bul(rehber_metni, prompt)
            web_sonuclari = ""
            ajan_etiketi = ""

            # Darıca, metro, ulaşım, projeler ve güncel aramalarda Web Search'ü çalıştır
            darica_ilgili = any(k in p_lower for k in ["darıca", "belediye", "millet bahçesi", "sahil", "baskan", "başkan", "muhtar", "kaymakam", "kocaeli", "mahalle", "sokak", "metro", "ulaşım", "otobüs", "proje", "parti", "bakan"])
            guncel_kelime = any(kw in p_lower for kw in ["haber", "etkinlik", "son dakika", "bugün", "duyuru", "nedir", "son haber", "ne var", "program", "ne zaman", "açılacak", "açılış", "asfalt", "yol", "çalışma", "bitti mi", "ne durumda"])

            kaynaklar = ""
            arama_yapildi = False

            if (not ilgili_baglam and darica_ilgili) or guncel_kelime:
                arama_yapildi = True
                with st.spinner("Güncel kaynaklar aranıyor..."):
                    web_sonuclari, kaynaklar = web_arama_yap(prompt)
                if web_sonuclari:
                    ajan_etiketi = "🛠️ **[Ajan Tetiklendi: web_arama_ajani]**\n\n"

            if arama_yapildi and not web_sonuclari and not ilgili_baglam:
                # Kaynak yoksa modele cevap uydurtma
                cevap = ("Bu konuda güncel bir kaynak bulamadım. Kesin bilgi için 153 Beyaz Masa "
                         "hattımızı arayabilir veya darica.bel.tr adresini ziyaret edebilirsiniz.")
            elif not groq_client:
                cevap = "⚠️ Sistem şu anda yanıt üretemiyor (Groq API anahtarı ayarlanmamış)."
            else:
                # Esnek ve Doğru Kapsam Belirleyen Sistem İstemcisi
                if web_sonuclari:
                    system_prompt = (
                        "Sen Darıca Belediyesi'nin resmi AI vatandaş asistanısın.\n"
                        f"Bugünün tarihi: {datetime.now().strftime('%d.%m.%Y')}.\n"
                        "KURALLAR:\n"
                        "1. Darıca, Kocaeli iline bağlıdır; İstanbul veya İBB ile ilgisi yoktur. Ulaşım sorularında Kocaeli Büyükşehir Belediyesi veya Ulaştırma ve Altyapı Bakanlığı'nı referans göster.\n"
                        "2. Yalnızca aşağıdaki arama sonuçlarındaki bilgilere dayan. Sonuçlar sorunun cevabını içermiyorsa bunu açıkça söyle, tahmin yürütme.\n"
                        "3. Haberin tarihini belirt. 1 aydan eski bir haberi 'güncel' diye sunma.\n"
                        "4. Sonuçlarda yazmayan telefon numarası, tarih, rakam ve link ASLA uydurma. Gerekirse vatandaşı 153 Beyaz Masa hattına yönlendir.\n"
                        "5. '[CANLI WEB ARAMA SONUÇLARI]' veya '[REHBER BİLGİSİ]' gibi iç sistem ifadelerini KULLANMA; vatandaşa doğal, kısa ve kurumsal bir dille yaz."
                    )
                else:
                    system_prompt = (
                        "Sen Darıca Belediyesi'nin resmi AI vatandaş asistanısın.\n\n"
                        "KESİNLİKLE UYULMASI GEREKEN KURALLAR:\n"
                        "1. Yanıtının içinde 'CANLI WEB ARAMA SONUÇLARI', 'REHBER BİLGİSİ' veya 'Arama sonuçları incelendiğinde' gibi TEKNİK SİSTEM İFADELERİNİ KESİNLİKLE KULLANMA!\n"
                        "2. Sana sağlanan metinde Darıca dışındaki başka şehirler (Hatay, İstanbul vb.) varsa onları tamamen yok say.\n"
                        "3. Eğer Darıca ile ilgili somut bir haber verisi yoksa doğrudan şu cevabı ver: 'Şu anda güncel yerel haber akışına ulaşılamamaktadır. Darıca ile ilgili duyuru ve haberler için darica.bel.tr adresini veya belediyemizin resmi sosyal medya hesaplarını takip edebilirsiniz.'\n"
                        "4. Vatandaşa doğrudan, samimi ve kurumsal bir dille yanıt ver."
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
                    cevap = f"{ajan_etiketi}{raw_cevap}" if raw_cevap else "Darıca Metro projesi ve güncel ulaşım bilgileri için Kocaeli Büyükşehir Belediyesi veya Ulaştırma ve Altyapı Bakanlığı duyurularını takip edebilir, 153 Beyaz Masa hattından detay alabilirsiniz."
                    if kaynaklar:
                        cevap += f"\n\n📎 **Kaynaklar:**\n\n{kaynaklar}"

                except Exception as e:
                    cevap = f"Bir hata oluştu: {str(e)}"

    st.session_state.messages.append({"role": "assistant", "content": cevap})
    st.rerun()
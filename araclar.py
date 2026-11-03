import csv
import os
import re
import time
import requests
from bs4 import BeautifulSoup
import feedparser
from datetime import datetime, timedelta, timezone
from urllib.parse import quote, urlparse
import html
import cloudscraper
import streamlit as st

try:
    from ddgs import DDGS
except ImportError:
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        DDGS = None



def darica_hizmet_hesapla(hizmet_tipi: str, parametre: str = "", yas: int = 0) -> str:
    """Darıca Belediyesi hizmet ve tarife hesaplama ajanı.

    Args:
        hizmet_tipi (str): Nikah, otopark, spor, su, atık vb. hizmet kategorisi.
        parametre (str): Vatandaşın girdiği ham sorgu metni.
        yas (int, optional): Kullanıcı yaş bilgisi (varsayılan: 0).

    Returns:
        str: Hesaplanan güncel tarife ve indirim bilgisi.
    """
    hizmet = hizmet_tipi.lower()
    p_lower = parametre.lower()

    # 1. Nikah Hizmetleri
    if "nikah" in hizmet or "nikah" in p_lower:
        if any(k in p_lower for k in ["dış", "otel", "bahçe", "düğün"]):
            return "Belediye salonları dışındaki mekânlarda (otel, bahçe, düğün salonu vb.) nikah kıyma ücreti 4.500 TL'dir."
        elif "hafta sonu" in p_lower:
            return "Darıca Belediyesi hafta sonu nikah kıyma ücreti 1.600 TL'dir."
        else:
            return "Darıca Belediyesi hafta içi salon nikahı ücreti 900 TL'dir."

    # 2. Otopark ve Karavan Parkı
    elif "otopark" in hizmet or "otopark" in p_lower or "karavan" in p_lower:
        if "karavan" in p_lower:
            if any(k in p_lower for k in ["aylık", "abonelik"]):
                return "Darıca Millet Bahçesi Karavan Parkı aylık abonelik ücreti 6.000 TL'dir."
            else:
                return "Darıca Millet Bahçesi Karavan Parkı ücretleri: 0-1 saat 40 TL, 1-24 saat 300 TL, aylık abonelik ise 6.000 TL'dir."
        elif "engelli" in p_lower:
            return "Engelli araç kartı bulunan araçlar belediye otoparklarından tamamen ücretsiz yararlanır."
        elif any(k in p_lower for k in ["aylık", "abonelik"]):
            return "Belediye otoparklarında aylık otopark aboneliği seçeneği bulunmamaktadır (Yalnızca Karavan Parkı için aylık abonelik 6.000 TL'dir)."
        else:
            return "Belediye otoparklarında ilk 6 saat ücretsizdir. Sonrasında 6-8 saat 20 TL, 8-12 saat 40 TL, 12-24 saat arası için 200 TL'dir."

    # 3. Spor Tesisleri, Kültür Merkezleri ve Kiralama
    elif any(k in hizmet for k in ["spor", "tesis", "kültür"]) or any(k in p_lower for k in ["spor", "kültür", "salon"]):
        is_kultur_veya_kiralama = (
            ("kültür" in hizmet or "kültür" in p_lower or "kiralama" in p_lower)
            or ("salon" in p_lower and "spor" not in p_lower and "spor" not in hizmet)
        )

        if is_kultur_veya_kiralama:
            if any(k in p_lower for k in ["dernek", "okul"]):
                return "Dernekler ve okullara kültür merkezi salon kiralamalarında %70 indirim uygulanır."
            elif any(k in p_lower for k in ["küçük", "400"]):
                return "Darıca Kültür Merkezi küçük salon (400 kişilik) yarım günlük kiralama ücreti 800 TL'dir (Dernek/Okullara %70 indirim uygulanır)."
            else:
                return "Darıca Kültür Merkezi büyük salon (1200 kişilik) yarım günlük kiralama ücreti 2.800 TL, küçük salon (400 kişilik) ise 800 TL'dir. Dernek ve okullara %70 indirim yapılır."
        else:
            if yas >= 65:
                return f"Vatandaşımız {yas} yaşında olduğu için spor tesislerinde %50 Kıdemli Vatandaş indirimi uygulanır."
            elif "öğrenci" in p_lower:
                return "Öğrencilere belediye spor tesislerinde %50 indirim uygulanır."
            else:
                return "Spor tesislerimizde standart tarife geçerlidir. Tesis girişi için Beyaz Masa'dan ücretsiz Darıca Kart alınmalıdır. 65 yaş üzeri vatandaşlara ve öğrencilere %50 indirim uygulanır."

    # 4. Su Aboneliği
    elif "su" in hizmet or "su" in p_lower:
        if any(k in p_lower for k in ["açma", "kesme", "fatura", "borç"]):
            return "Kesilen suyun yeniden açılması için vadesi geçmiş borcun yanı sıra 420 TL su açma ücreti ödenmelidir."
        else:
            return "Konut yeni su aboneliği güvence bedeli 1.154 TL'dir. Kesilen suyun yeniden açma ücreti ise 420 TL'dir."

    # 5. Sıfır Atık ve Geri Dönüşüm
    elif "atık" in hizmet or "yağ" in p_lower or "atık" in p_lower:
        return "5 litre bitkisel atık yağ getiren vatandaşlarımıza muhtarlıklardaki atık getirme merkezlerinde 1 litre deterjan hediye edilmektedir."

    # 6. Genel Yaş / İndirim Sorgusu (Kategori Belirtilmemişse)
    elif yas >= 65:
        return f"65 yaş ve üzeri ({yas} yaş) vatandaşlarımıza belediyemiz spor tesislerinde %50 Kıdemli Vatandaş indirimi uygulanmaktadır. Tesis girişi için Beyaz Masa'dan Darıca Kart alabilirsiniz."

    else:
        return "Belirtilen hizmet kategorisi için belediye çağrı merkezimizi (153) arayabilirsiniz."

    



def tesis_bilgisi_sorgula(sorgu: str, csv_path: str = "tesisler.csv") -> str:
    """CSV veritabanı üzerinden tesis, çalışma saatleri, konum ve kurs sorgulama ajanı.

    Args:
        sorgu (str): Kullanıcı sorgu metni.
        csv_path (str, optional): Tesis verilerinin bulunduğu CSV yolu.

    Returns:
        str: Biçimlendirilmiş tesis ve çalışma saati bilgisi.
    """
    sorgu_lower = sorgu.lower()

    if not os.path.exists(csv_path):
        return f"Tesis bilgi veritabanı ({csv_path}) bulunamadı."

    mahalleler = [
        "yalı", "bağlarbaşı", "kazım karabekir", "yeni", "fevzi çakmak",
        "cami", "piri reis", "emek", "osmangazi", "abdi ipekçi",
        "zincirlikuyu", "bayramoğlu", "sırasöğütler", "nenehatun"
    ]
    aranan_mahalle = next((m for m in mahalleler if m in sorgu_lower), None)

    # CRITICAL FIX: "çalışma" kelimesi "çalışma saatleri" sorgularını bozduğu için kaldırıldı.
    is_kutuphane_sorgu = any(k in sorgu_lower for k in ["ders", "etüt", "kütüphane", "yks", "okuma salonu", "kurs"])
    is_spor_sorgu = any(s in sorgu_lower for s in ["yüzme", "fitness", "tenis", "basketbol", "voleybol", "paten", "spor", "kort", "havuz", "salon"])

    stop_words = {
        "için", "peki", "var", "mı", "mi", "mu", "mü", "nerede", "nereler", 
        "ve", "ile", "ne", "nasıl", "hangi", "gün", "günleri", "saat", 
        "saatleri", "sınırları", "içindeki", "çalışma"
    }
    sorgu_kelimeleri = [w for w in sorgu_lower.split() if len(w) > 2 and w not in stop_words]

    eslesen_tesisler = []

    try:
        # utf-8-sig: Excel CSV kaydetme uyumluluğu için eklendi
        with open(csv_path, mode="r", encoding="utf-8-sig") as file:
            reader = csv.DictReader(file)
            for row in reader:
                tesis_adi = row.get('tesis_adi', '').strip()
                tur = row.get('tur', '').strip()
                mahalle = row.get('mahalle', '').strip()
                acilis = row.get('acilis', '').strip()
                kapanis = row.get('kapanis', '').strip()
                kapali_gun = row.get('kapali_gun', '').strip()
                aylik_ucret = row.get('aylik_ucret_tl', '').strip()

                ucret = "Ücretsiz" if aylik_ucret in ["0", "", "ücretsiz"] else f"{aylik_ucret} TL/ay"
                kapali_str = f" (Kapalı Gün: {kapali_gun})" if kapali_gun and kapali_gun.lower() != "yok" else ""

                bilgi = (
                    f"📍 **{tesis_adi}** ({tur.title()} - {mahalle.title()} Mah.)\n"
                    f"⏰ Çalışma Saatleri: {acilis} - {kapanis}{kapali_str}\n"
                    f"💰 Ücret: {ucret}"
                )

                # Mahalle filtresi
                if aranan_mahalle and (aranan_mahalle not in mahalle.lower() and aranan_mahalle not in tesis_adi.lower()):
                    continue

                is_kutuphane_row = any(k in tur.lower() for k in ["kütüphane", "etüt", "yks", "tiyatro", "enstrüman"])
                is_spor_row = any(s in tur.lower() for s in ["yüzme", "fitness", "tenis", "basketbol", "voleybol", "buz pateni", "pilates", "spor"])

                if is_kutuphane_sorgu and not is_spor_sorgu:
                    if is_kutuphane_row:
                        eslesen_tesisler.append(bilgi)
                elif is_spor_sorgu and not is_kutuphane_sorgu:
                    if is_spor_row:
                        eslesen_tesisler.append(bilgi)
                else:
                    if any(w in tesis_adi.lower() or w in tur.lower() or w in mahalle.lower() for w in sorgu_kelimeleri):
                        eslesen_tesisler.append(bilgi)

        if not eslesen_tesisler:
            if aranan_mahalle:
                kat_str = "kütüphane/ders alanı" if is_kutuphane_sorgu else "tesis"
                return f"**{aranan_mahalle.title()} Mahallesi** sınırları içerisinde aradığınız kriterde {kat_str} bulunmamaktadır."
            return "İlgili ders veya tesis hakkında bilgi bulunamadı."

        if is_kutuphane_sorgu and not is_spor_sorgu:
            return "📚 **Ders Çalışma Alanları ve Kütüphaneler:**\n\n" + "\n\n".join(eslesen_tesisler)
        elif is_spor_sorgu and not is_kutuphane_sorgu:
            return "🏋️ **Spor Tesisleri ve Kursları:**\n\n" + "\n\n".join(eslesen_tesisler)
        else:
            return "\n\n".join(eslesen_tesisler[:5])

    except Exception as e:
        return f"Tesis bilgileri sorgulanırken bir hata oluştu: {str(e)}"

    



# --- HABER & WEB ARAMA AJANI CONFIG ---
_HABER_CACHE = {"zaman": 0.0, "metin": ""}
_HABER_CACHE_SURE = 600  # saniye (10 dk)

_HABER_KAYNAKLARI = [
    (
        "https://news.google.com/rss/search?q="
        + quote("Darıca Kocaeli when:7d")
        + "&hl=tr&gl=TR&ceid=TR:tr",
        False,
    ),
    ("https://www.kocaeligazetesi.com.tr/rss", True),
    ("https://www.ozgurkocaeli.com.tr/rss", True),
]


def _tr_kucult(metin: str) -> str:
    return metin.replace("İ", "i").replace("I", "ı").lower()


def darica_son_dakika_haberleri(adet: int = 5) -> str:
    """Darıca ile ilgili son haber başlıklarını RSS'ten çeker (10 dk önbellekli)."""
    if (
        _HABER_CACHE["metin"]
        and time.time() - _HABER_CACHE["zaman"] < _HABER_CACHE_SURE
    ):
        return _HABER_CACHE["metin"]

    haberler, gorulen = [], set()

    for url, filtrele in _HABER_KAYNAKLARI:
        try:
            r = requests.get(
                url,
                timeout=8,
                headers={
                    "User-Agent": "Mozilla/5.0 (compatible; DaricaAsistan/1.0)"
                },
            )
            r.raise_for_status()
            entries = feedparser.parse(r.content).entries
        except Exception as e:
            print(f"Haber RSS hatası ({url}): {e}")
            continue

        for entry in entries:
            baslik = (entry.get("title") or "").strip()
            link = entry.get("link", "")
            if not baslik:
                continue

            norm = _tr_kucult(baslik)
            if "hava durumu" in norm:
                continue
            if filtrele and "darıca" not in norm and "darica" not in norm:
                continue
            if norm in gorulen:
                continue
            gorulen.add(norm)

            kaynak = ""
            if " - " in baslik:
                baslik, _, kaynak = baslik.rpartition(" - ")

            satir = f"• [{baslik}]({link})" if link else f"• {baslik}"
            if kaynak:
                satir += f" — *{kaynak}*"
            haberler.append(satir)

            if len(haberler) >= adet:
                break
        if len(haberler) >= adet:
            break

    metin = "\n".join(haberler)
    if metin:
        _HABER_CACHE.update(zaman=time.time(), metin=metin)
    return metin


# --- GÜNCEL WEB ARAMA AJANI ---
_UA = {"User-Agent": "Mozilla/5.0 (compatible; DaricaAsistan/1.0)"}
_ARAMA_CACHE = {}  # {sorgu: (zaman, (baglam, kaynaklar))}
_ARAMA_CACHE_SURE = 600  # 10 dk
_ALAKASIZ = ("hatay", "android app", "download")

_SORU_KELIMELERI = {
    "mi",
    "mı",
    "mu",
    "mü",
    "midir",
    "mıdır",
    "bitti",
    "ne",
    "zaman",
    "neler",
    "nedir",
    "nelerdir",
    "var",
    "nasıl",
    "hangi",
    "kaç",
    "kadar",
    "peki",
    "acaba",
    "hala",
    "hâlâ",
    "şu",
    "an",
    "bu",
    "bir",
    "ve",
    "ile",
    "için",
    "da",
    "de",
    "ki",
    "oldu",
    "bana",
    "söyle",
    "lütfen",
    "bugün",
    "hafta",
    "açılacak",
    "başladı",
    "tamamlandı",
}


def _anahtar_kelimeler(sorgu: str) -> list:
    metin = re.sub(r"['’]\w*", "", _tr_kucult(sorgu))
    kelimeler = re.findall(r"\w+", metin)
    return [k for k in kelimeler if k not in _SORU_KELIMELERI and len(k) > 1]


def _arama_sorgulari(sorgu: str) -> list:
    k = _anahtar_kelimeler(sorgu)
    if "darıca" not in k and "darica" not in k:
        k = ["darıca"] + k
    uzun = " ".join(k[:7])
    kisa = " ".join(k[:3])
    return [uzun] if uzun == kisa else [uzun, kisa]


def _tarih_coz(deger):
    try:
        if deger is None or deger == "":
            return None
        if hasattr(deger, "tm_year"):
            return datetime(*deger[:6])
        return datetime.fromisoformat(str(deger).replace("Z", "+00:00")).replace(
            tzinfo=None
        )
    except Exception:
        return None


def _google_haber_ara(sorgu: str, gun: int = 90) -> list:
    url = (
        "https://news.google.com/rss/search?q="
        + quote(f"{sorgu} when:{gun}d")
        + "&hl=tr&gl=TR&ceid=TR:tr"
    )
    try:
        r = requests.get(url, timeout=8, headers=_UA)
        r.raise_for_status()
        entries = feedparser.parse(r.content).entries
    except Exception as e:
        print(f"Google Haberler arama hatası: {e}")
        return []

    sonuc = []
    for e in entries[:10]:
        baslik = (e.get("title") or "").strip()
        if not baslik:
            continue
        kaynak = ""
        if " - " in baslik:
            baslik, _, kaynak = baslik.rpartition(" - ")
        sonuc.append(
            {
                "baslik": baslik,
                "link": e.get("link", ""),
                "kaynak": kaynak,
                "ozet": "",
                "tarih": _tarih_coz(e.get("published_parsed")),
            }
        )
    return sonuc


def _ddg_ara(sorgu: str, adet: int = 5) -> list:
    if not DDGS:
        return []
    try:
        ham = (
            DDGS().text(f"{sorgu} Kocaeli", region="tr-tr", max_results=adet)
            or []
        )
    except Exception as e:
        print(f"DuckDuckGo arama hatası: {e}")
        return []

    sonuc = []
    for r in ham:
        link = r.get("href") or r.get("url") or ""
        sonuc.append(
            {
                "baslik": (r.get("title") or "").strip(),
                "link": link,
                "kaynak": urlparse(link).netloc.replace("www.", ""),
                "ozet": (r.get("body") or "").strip(),
                "tarih": None,
            }
        )
    return sonuc


def darica_web_arama(sorgu: str, adet: int = 5):
    """Darıca odaklı web araması (Google Haberler + DuckDuckGo)."""
    sorgular = _arama_sorgulari(sorgu)
    onbellek_anahtari = sorgular[0]
    kayit = _ARAMA_CACHE.get(onbellek_anahtari)
    if kayit and time.time() - kayit[0] < _ARAMA_CACHE_SURE:
        return kayit[1]

    sonuclar, gorulen = [], set()

    def ekle(liste, darica_sart):
        for s in liste:
            if not s["baslik"]:
                continue
            norm = _tr_kucult(s["baslik"])
            metin = norm + " " + _tr_kucult(s["ozet"])
            if norm in gorulen or any(x in metin for x in _ALAKASIZ):
                continue
            if darica_sart and "darıca" not in metin and "darica" not in metin:
                continue
            gorulen.add(norm)
            sonuclar.append(s)

    for q in sorgular:
        ekle(_google_haber_ara(q), False)
        if len(sonuclar) >= 3:
            break
    del sonuclar[3:]

    ekle(_ddg_ara(sorgular[0]), True)
    del sonuclar[adet:]

    if not sonuclar:
        return "", ""

    sonuclar.sort(key=lambda s: s["tarih"] or datetime.min, reverse=True)

    baglam, kaynaklar = [], []
    for s in sonuclar:
        baslik = s["baslik"].replace("[", "(").replace("]", ")")
        tarih = s["tarih"].strftime("%d.%m.%Y") if s["tarih"] else ""
        kaynak = s["kaynak"] or "web"
        satir = f"- [{tarih or 'tarih yok'}] {baslik} ({kaynak})"
        if s["ozet"]:
            satir += f": {s['ozet'][:300]}"
        baglam.append(satir)
        md = (
            f"• [{baslik}]({s['link']}) — *{kaynak}*"
            if s["link"]
            else f"• {baslik} — *{kaynak}*"
        )
        if tarih:
            md += f" · {tarih}"
        kaynaklar.append(md)

    sonuc = ("\n".join(baglam), "\n".join(kaynaklar))
    _ARAMA_CACHE[onbellek_anahtari] = (time.time(), sonuc)
    return sonuc


def piyasa_verileri_getir() -> dict:
    """Canlı Dolar, Euro ve Gram Altın verilerini çeker."""
    try:
        url = "https://finans.truncgil.com/today.json"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=4)
        
        if response.status_code == 200:
            data = response.json()
            
            usd = data.get("USD", {}).get("Satış", "—")
            eur = data.get("EUR", {}).get("Satış", "—")
            
            # Gram Altın için muhtemel anahtar isimlerinin tamamı kontrol edilir:
            altin_data = (
                data.get("Gram Altın") or 
                data.get("gram-altin") or 
                data.get("GRA") or 
                {}
            )
            
            altin = altin_data.get("Satış", "—") if isinstance(altin_data, dict) else "—"
            
            return {"usd": usd, "eur": eur, "altin": altin}
    except Exception as e:
        print(f"Piyasa verisi çekilemedi: {e}")
        
    return {"usd": "—", "eur": "—", "altin": "—"}





_ECZANE_CACHE = {"zaman": 0.0, "veri": []}
_ECZANE_CACHE_SURE = 14400 # 4 saat cache


def get_nobetci_eczane() -> list:
    """Darıca nöbetçi eczanelerini CollectAPI üzerinden çeker."""
    zaman = time.time()
    c = _ECZANE_CACHE

    # 30 dakikalık cache kontrolü (Kotayı korumak için)
    if c["veri"] and (zaman - c["zaman"] < _ECZANE_CACHE_SURE):
        return c["veri"]

    # Hugging Face Secrets (os.getenv) veya Streamlit Secrets (st.secrets) okuma
    api_key = os.getenv("COLLECTAPI_KEY")
    if not api_key:
        try:
            api_key = st.secrets.get("COLLECTAPI_KEY", "")
        except Exception:
            pass

    if not api_key:
        print("COLLECTAPI_KEY bulunamadı. Lütfen Hugging Face Secrets alanına ekleyin.")
        return []

    headers = {
        "content-type": "application/json",
        "authorization": (
            api_key if api_key.startswith("apikey") else f"apikey {api_key}"
        ),
    }

    url = "https://api.collectapi.com/health/dutyPharmacy?il=Kocaeli&ilce=Darıca"

    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            res_data = r.json()
            if res_data.get("success") and res_data.get("result"):
                eczaneler = []
                for item in res_data["result"]:
                    eczaneler.append(
                        {
                            "isim": html.escape(item.get("name", "")),
                            "adres": html.escape(item.get("address", "")),
                            "telefon": html.escape(item.get("phone", "")),
                            "gecerlilik": "Bugün akşamdan yarın sabaha kadar",
                        }
                    )
                c.update(zaman=zaman, veri=eczaneler)
                return eczaneler
        else:
            print(f"CollectAPI HTTP Hatası {r.status_code}: {r.text}")
    except Exception as e:
        print(f"CollectAPI bağlantı hatası: {e}")

    return []
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

    # Nikah hizmetleri ve salon tarifeleri
    if "nikah" in hizmet:
        if any(k in p_lower for k in ["dış", "otel", "bahçe", "düğün"]):
            return "Belediye salonları dışındaki mekânlarda (otel, bahçe, düğün salonu vb.) nikah kıyma ücreti 4.500 TL'dir."
        elif "hafta sonu" in p_lower:
            return "Darıca Belediyesi hafta sonu nikah kıyma ücreti 1.600 TL'dir."
        else:
            return "Darıca Belediyesi hafta içi salon nikahı ücreti 900 TL'dir."

    # Otopark ve Karavan Parkı tarifeleri
    elif "otopark" in hizmet or "karavan" in p_lower:
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

    # Spor tesisleri, kültür merkezleri ve salon kiralamaları
    elif any(k in hizmet for k in ["spor", "tesis", "kültür"]) or "salon" in p_lower:
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

    # Su aboneliği ve kesinti hizmetleri
    elif "su" in hizmet:
        if any(k in p_lower for k in ["açma", "kesin", "fatura"]):
            return "Kesilen suyun yeniden açılması için vadesi geçmiş borcun yanı sıra 420 TL su açma ücreti ödenmelidir."
        else:
            return "Konut yeni su aboneliği güvence bedeli 1.154 TL'dir. Kesilen suyun yeniden açma ücreti ise 420 TL'dir."

    # Sıfır atık ve geri dönüşüm 
    elif "atık" in hizmet or "yağ" in p_lower:
        return "5 litre bitkisel atık yağ getiren vatandaşlarımıza muhtarlıklardaki atık getirme merkezlerinde 1 litre deterjan hediye edilmektedir."

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

    is_kutuphane_sorgu = any(k in sorgu_lower for k in ["ders", "etüt", "kütüphane", "yks", "okuma", "çalışma", "kurs"])
    is_spor_sorgu = any(s in sorgu_lower for s in ["yüzme", "fitness", "tenis", "basketbol", "voleybol", "paten", "spor", "kort", "havuz", "salon"])

    stop_words = {
        "için", "peki", "var", "mı", "mi", "mu", "mü", "nerede", "nereler", 
        "ve", "ile", "ne", "nasıl", "hangi", "gün", "günleri", "saat", 
        "saatleri", "sınırları", "içindeki"
    }
    sorgu_kelimeleri = [w for w in sorgu_lower.split() if len(w) > 2 and w not in stop_words]

    eslesen_tesisler = []

    try:
        with open(csv_path, mode="r", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            for row in reader:
                tesis_adi = row.get('tesis_adi', '').strip()
                tur = row.get('tur', '').strip()
                mahalle = row.get('mahalle', '').strip()
                acilis = row.get('acilis', '').strip()
                kapanis = row.get('kapanis', '').strip()
                kapali_gun = row.get('kapali_gun', '').strip()
                aylik_ucret = row.get('aylik_ucret_tl', '').strip()

                ucret = "Ücretsiz" if aylik_ucret in ["0", ""] else f"{aylik_ucret} TL/ay"
                kapali_str = f" (Kapalı Gün: {kapali_gun})" if kapali_gun.lower() != "yok" else ""

                bilgi = (
                    f"📍 **{tesis_adi}** ({tur.title()} - {mahalle.title()} Mah.)\n"
                    f"⏰ Çalışma Saatleri: {acilis} - {kapanis}{kapali_str}\n"
                    f"💰 Ücret: {ucret}"
                )

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

        if is_kutuphane_sorgu:
            return "📚 **Ders Çalışma Alanları ve Kütüphaneler:**\n\n" + "\n\n".join(eslesen_tesisler)
        elif is_spor_sorgu:
            return "🏋️ **Spor Tesisleri ve Kursları:**\n\n" + "\n\n".join(eslesen_tesisler)
        else:
            return "\n\n".join(eslesen_tesisler[:5])

    except Exception as e:
        return f"Tesis bilgileri sorgulanırken bir hata oluştu: {str(e)}"


_HABER_CACHE = {"zaman": 0.0, "metin": ""}
_HABER_CACHE_SURE = 600  # saniye (10 dk)

# (adres, başlıkta "Darıca" filtresi uygular mı?)
_HABER_KAYNAKLARI = [
    # Google Haberler araması zaten "Darıca" için süzülmüş geliyor
    ("https://news.google.com/rss/search?q=" + quote("Darıca Kocaeli when:7d")
     + "&hl=tr&gl=TR&ceid=TR:tr", False),
    # Yedek yerel gazete RSS'leri (adresleri tarayıcıda açıp doğrula)
    ("https://www.kocaeligazetesi.com.tr/rss", True),
    ("https://www.ozgurkocaeli.com.tr/rss", True),
]


def _tr_kucult(metin: str) -> str:
    return metin.replace("İ", "i").replace("I", "ı").lower()


def darica_son_dakika_haberleri(adet: int = 5) -> str:
    """Darıca ile ilgili son haber başlıklarını RSS'ten çeker (10 dk önbellekli)."""
    if _HABER_CACHE["metin"] and time.time() - _HABER_CACHE["zaman"] < _HABER_CACHE_SURE:
        return _HABER_CACHE["metin"]

    haberler, gorulen = [], set()

    for url, filtrele in _HABER_KAYNAKLARI:
        try:
            r = requests.get(
                url, timeout=8,
                headers={"User-Agent": "Mozilla/5.0 (compatible; DaricaAsistan/1.0)"}
            )
            r.raise_for_status()
            entries = feedparser.parse(r.content).entries
        except Exception as e:
            print(f"Haber RSS hatası ({url}): {e}")  # HF Space loglarında görünür
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

            # Google Haberler başlıkları "Başlık - Kaynak" biçiminde gelir
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
    if metin:  # boş sonucu önbelleğe alma
        _HABER_CACHE.update(zaman=time.time(), metin=metin)
    return metin


_UA = {"User-Agent": "Mozilla/5.0 (compatible; DaricaAsistan/1.0)"}
_ARAMA_CACHE = {}          # {sorgu: (zaman, (baglam, kaynaklar))}
_ARAMA_CACHE_SURE = 600    # saniye (10 dk)
_ALAKASIZ = ("hatay", "android app", "download")

# Arama sorgusundan atılacak soru kalıpları
_SORU_KELIMELERI = {
    "mi", "mı", "mu", "mü", "midir", "mıdır", "bitti", "ne", "zaman", "neler",
    "nedir", "nelerdir", "var", "nasıl", "hangi", "kaç", "kadar", "peki",
    "acaba", "hala", "hâlâ", "şu", "an", "bu", "bir", "ve", "ile", "için",
    "da", "de", "ki", "oldu", "bana", "söyle", "lütfen", "bugün", "hafta",
    "açılacak", "başladı", "tamamlandı",
}


def _anahtar_kelimeler(sorgu: str) -> list:
    metin = re.sub(r"['’]\w*", "", _tr_kucult(sorgu))   # Darıca'nın -> darıca
    kelimeler = re.findall(r"\w+", metin)
    return [k for k in kelimeler if k not in _SORU_KELIMELERI and len(k) > 1]


def _arama_sorgulari(sorgu: str) -> list:
    """Uzun ve kısa iki arama sorgusu üretir (uzun boş dönerse kısa denenir)."""
    k = _anahtar_kelimeler(sorgu)
    if "darıca" not in k and "darica" not in k:
        k = ["darıca"] + k
    uzun = " ".join(k[:7])
    kisa = " ".join(k[:3])
    return [uzun] if uzun == kisa else [uzun, kisa]


def _tarih_coz(deger):
    """struct_time ya da ISO metni -> datetime (olmazsa None)."""
    try:
        if deger is None or deger == "":
            return None
        if hasattr(deger, "tm_year"):
            return datetime(*deger[:6])
        return datetime.fromisoformat(str(deger).replace("Z", "+00:00")).replace(tzinfo=None)
    except Exception:
        return None


def _google_haber_ara(sorgu: str, gun: int = 90) -> list:
    url = ("https://news.google.com/rss/search?q=" + quote(f"{sorgu} when:{gun}d")
           + "&hl=tr&gl=TR&ceid=TR:tr")
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
        if " - " in baslik:   # "Başlık - Kaynak"
            baslik, _, kaynak = baslik.rpartition(" - ")
        sonuc.append({
            "baslik": baslik, "link": e.get("link", ""), "kaynak": kaynak,
            "ozet": "", "tarih": _tarih_coz(e.get("published_parsed")),
        })
    return sonuc


def _ddg_ara(sorgu: str, adet: int = 5) -> list:
    if not DDGS:
        return []
    try:
        # Parametre adı sürümler arasında değiştiği için sorgu pozisyonel verilir
        ham = DDGS().text(f"{sorgu} Kocaeli", region="tr-tr", max_results=adet) or []
    except Exception as e:
        print(f"DuckDuckGo arama hatası: {e}")
        return []

    sonuc = []
    for r in ham:
        link = r.get("href") or r.get("url") or ""
        sonuc.append({
            "baslik": (r.get("title") or "").strip(), "link": link,
            "kaynak": urlparse(link).netloc.replace("www.", ""),
            "ozet": (r.get("body") or "").strip(), "tarih": None,
        })
    return sonuc


def darica_web_arama(sorgu: str, adet: int = 5):
    """Darıca odaklı web araması (Google Haberler + DuckDuckGo).

    Returns:
        (baglam, kaynaklar): LLM'e verilecek bağlam metni ve kullanıcıya
        gösterilecek tıklanabilir kaynak listesi. Sonuç yoksa ("", "").
    """
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

    # 1) Yerel haberler: önce uzun sorgu, az sonuç varsa kısa sorgu
    for q in sorgular:
        ekle(_google_haber_ara(q), False)
        if len(sonuclar) >= 3:
            break
    del sonuclar[3:]

    # 2) Genel web: resmî sayfalar, duyurular (sadece Darıca geçenler)
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
        md = f"• [{baslik}]({s['link']}) — *{kaynak}*" if s["link"] else f"• {baslik} — *{kaynak}*"
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


_ECZANE_URL = "https://www.eczaneler.gen.tr/nobetci-kocaeli-darica"
_ECZANE_CACHE = {"zaman": 0.0, "bitis": None, "veri": [], "hata_zamani": 0.0}
_ECZANE_CACHE_SURE = 1200      # başarılı sonuç: en fazla 20 dk
_ECZANE_HATA_BEKLEME = 120     # başarısız denemeden sonra 2 dk bekle
_TEL_DESEN = re.compile(r"0\s*\(?\d{3}\)?[\s.-]*\d{3}[\s.-]*\d{2}[\s.-]*\d{2}")
_AY = {"ocak": 1, "şubat": 2, "mart": 3, "nisan": 4, "mayıs": 5, "haziran": 6,
       "temmuz": 7, "ağustos": 8, "eylül": 9, "ekim": 10, "kasım": 11, "aralık": 12}
# "3 Kasım Salı akşamından 4 Kasım Çarşamba sabahına kadar."  (gün adı "P.tesi" gibi noktalı olabilir)
_ARALIK_DESEN = re.compile(
    r"(\d{1,2})\s+([^\W\d_]+)\s+\S+\s+akşamından\s+"
    r"(\d{1,2})\s+([^\W\d_]+)\s+\S+\s+sabahına\s+kadar",
    re.IGNORECASE,
)


def _tr_simdi() -> datetime:
    """Türkiye saati (sunucu UTC olsa bile doğru çalışır)."""
    return datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=3)


def _yakin_tarih(gun: int, ay: int, simdi: datetime):
    adaylar = []
    for y in (simdi.year - 1, simdi.year, simdi.year + 1):
        try:
            adaylar.append(datetime(y, ay, gun))
        except ValueError:
            pass
    return min(adaylar, key=lambda t: abs(t - simdi)) if adaylar else None


def _telefon_bicimle(ham: str) -> str:
    rakam = re.sub(r"\D", "", ham)
    if len(rakam) == 11 and rakam.startswith("0"):
        return f"{rakam[:4]} {rakam[4:7]} {rakam[7:9]} {rakam[9:]}"
    return ham.strip()


def _tablo_satirlari(tablo) -> list:
    """Her eczane: <div class="row"> içinde span.isim (ad), div.col-lg-6 (adres),
    son div.col-lg-3 (telefon)."""
    sonuc = []
    for satir in tablo.find_all("div", class_="row"):
        isim_el = satir.find("span", class_="isim")
        if not isim_el:
            continue                         # başlık satırı ("Eczane Adres Telefon")
        isim = isim_el.get_text(" ", strip=True)

        adres, tarif = "", ""
        adres_div = satir.find("div", class_="col-lg-6")
        if adres_div:
            adres = next((str(s).strip() for s in adres_div.find_all(string=True, recursive=False)
                          if str(s).strip()), "")
            t = adres_div.find("span", class_="font-italic")
            tarif = t.get_text(" ", strip=True) if t else ""

        tel_kolonlari = satir.find_all("div", class_="col-lg-3")
        tel_metni = tel_kolonlari[-1].get_text(" ", strip=True) if tel_kolonlari else satir.get_text(" ", strip=True)
        m = _TEL_DESEN.search(tel_metni)
        telefon = _telefon_bicimle(m.group(0)) if m else ""

        if isim and (adres or telefon):
            sonuc.append({
                "isim": html.escape(isim),
                "adres": html.escape(f"{adres} — {tarif}" if tarif else adres),
                "telefon": html.escape(telefon or "N/A"),
            })
    return sonuc


def _bantlari_bul(soup) -> list:
    """Nöbet aralığı cümlesini içeren en iç etiketleri bulur (cümle etiketlere bölünmüş olabilir)."""
    bantlar = []
    for tag in soup.find_all(True):
        metin = tag.get_text(" ", strip=True)
        if len(metin) > 300:
            continue                        # büyük kapsayıcıları ele
        m = _ARALIK_DESEN.search(metin)
        if not m:
            continue
        if any(_ARALIK_DESEN.search(c.get_text(" ", strip=True)) for c in tag.find_all(True)):
            continue                        # içindeki bir etiket de eşleşiyorsa en içtekini al
        bantlar.append(m)
    return bantlar


def _eczane_sayfasini_coz(html_metni: str, simdi: datetime = None):
    """Sayfada n nöbet bandı ve n eczane tablosu vardır; i. bant i. tabloya aittir
    (bant DOM'da tablosundan sonra gelir). Sayılar tutmazsa yanlış eşleşme riskine
    girmeden boş döner. Şu an geçerli ya da yaklaşan nöbeti seçer.

    Returns: (eczaneler, gecerlilik_metni, bitis_zamani)"""
    simdi = simdi or _tr_simdi()
    soup = BeautifulSoup(html_metni, "html.parser")

    bantlar = _bantlari_bul(soup)
    tablolar = [t for t in soup.find_all("table") if t.find("span", class_="isim")]
    print(f"Eczane ayrıştırma: {len(bantlar)} nöbet bandı, {len(tablolar)} eczane tablosu bulundu.")
    if not bantlar or len(bantlar) != len(tablolar):
        return [], "", None

    paneller = []
    for m, tablo in zip(bantlar, tablolar):
        ay = _AY.get(_tr_kucult(m.group(4)))
        bitis_gun = _yakin_tarih(int(m.group(3)), ay, simdi) if ay else None
        if bitis_gun is None:
            continue
        # Nöbet bitişi: bitiş günü sabah 09:00 (siteler genelde 08:30-09:00'da değiştirir)
        paneller.append((bitis_gun.replace(hour=9), re.sub(r"\s+", " ", m.group(0)).strip(), tablo))

    paneller.sort(key=lambda p: p[0])
    for bitis, metin, tablo in paneller:
        if bitis > simdi:                       # henüz bitmemiş ilk nöbet
            liste = _tablo_satirlari(tablo)
            if liste:
                return liste, metin, bitis
    return [], "", None


def get_nobetci_eczane() -> list:
    """Darıca nöbetçi eczaneleri (eczaneler.gen.tr). Her kayıtta 'gecerlilik' alanı
    nöbet aralığını taşır. Önbellekli; hata olursa bayat veri DÖNMEZ."""
    simdi = _tr_simdi()
    zaman = time.time()

    c = _ECZANE_CACHE
    if c["veri"] and zaman - c["zaman"] < _ECZANE_CACHE_SURE and c["bitis"] and simdi < c["bitis"]:
        return c["veri"]
    if zaman - c["hata_zamani"] < _ECZANE_HATA_BEKLEME:
        return []

    try:
        # requests.get yerine Cloudflare engelini aşan scraper kullanıyoruz
        scraper = cloudscraper.create_scraper(
            browser={
                "browser": "chrome",
                "platform": "windows",
                "desktop": True,
            }
        )
        r = scraper.get(_ECZANE_URL, timeout=10)

        if r.status_code != 200:
            print(f"Eczane kaynağı HTTP {r.status_code}: {_ECZANE_URL}")
        else:
            liste, gecerlilik, bitis = _eczane_sayfasini_coz(r.text, simdi)
            if liste:
                for e in liste:
                    e["gecerlilik"] = html.escape(gecerlilik)
                c.update(zaman=zaman, bitis=bitis, veri=liste)
                return liste
            print("Eczane sayfasında geçerli nöbet aralığı/tablo bulunamadı "
                  "(sayfa yapısı değişmiş ya da liste güncel değil).")
    except Exception as e:
        print(f"Eczane kaynağı hatası: {e}")

    c["hata_zamani"] = zaman
    return []
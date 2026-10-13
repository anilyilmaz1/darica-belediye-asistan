import csv

def darica_hizmet_hesapla(hizmet_tipi: str, parametre: str = "", yas: int = 0) -> str:
    hizmet = hizmet_tipi.lower()

    # 1. Nikah Ücreti Hesaplama
    if "nikah" in hizmet:
        if "hafta sonu" in parametre.lower():
            return "Darıca Belediyesi hafta sonu nikah kıyma ücreti 1.800 TL'dir."
        elif "dış" in parametre.lower() or "otel" in parametre.lower() or "bahçe" in parametre.lower():
            return "Belediye salonları dışındaki mekânlarda (otel, bahçe vb.) nikah kıyma ücreti 4.500 TL'dir."
        else:
            return "Darıca Belediyesi hafta içi salon nikahı ücreti 900 TL'dir."

    # 2. Otopark Ücreti Hesaplama
    elif "otopark" in hizmet:
        if "aylık" in parametre.lower() or "abonelik" in parametre.lower():
            return "Belediye otoparklarında aylık abonelik ücreti 1.500 TL'dir."
        elif "engelli" in parametre.lower():
            return "Engelli araç kartı bulunan araçlar belediye otoparklarından tamamen ücretsiz yararlanır."
        else:
            return "Otoparklarımızda ilk 30 dakika ücretsizdir. Sonrasında saatlik 40 TL uygulanır (Günlük azami 250 TL)."

    # 3. Spor Tesisi & Kültür Merkezi İndirimi
    elif "spor" in hizmet or "tesis" in hizmet or "kültür" in hizmet:
        if yas >= 65:
            return f"Vatandaşımız {yas} yaşında olduğu için tesislerde %50 Kıdemli Vatandaş indirimi uygulanır."
        elif "öğrenci" in parametre.lower() or "okul" in parametre.lower() or "dernek" in parametre.lower():
            return "Öğrencilere spor tesislerinde, dernek ve okullara kültür merkezi salon kiralamalarında %50 indirim uygulanır."
        else:
            return "Tesislerimizde standart tarife geçerlidir. Spor tesisleri için Darıca Kart gereklidir."

    # 4. Su Aboneliği & Açma Ücreti
    elif "su" in hizmet:
        return "Konut su aboneliği güvence bedeli 1.200 TL'dir. Kesilen suyun açılması için 350 TL açma ücreti ve borç ödenmelidir."

    else:
        return "Belirtilen hizmet kategorisi için belediye çağrı merkezimizi (153) arayabilirsiniz."


def tesis_bilgisi_sorgula(sorgu: str) -> str:
    """CSV veritabanından tesislerin çalışma saatlerini, konum, kurs ve ücretlerini getirir."""
    sorgu_lower = sorgu.lower()
    bulunanlar = []

    spor_turleri = ["yüzme", "fitness", "tenis", "basketbol", "voleybol", "buz pateni", "pilates", "spor"]
    kurs_turleri = ["kurs", "ders", "eğitim", "etüt", "okul", "hazırlık"]
    
    # Sorgudan etkisiz kelimeleri ayıkla
    stop_words = {"için", "peki", "var", "mı", "mi", "mu", "mü", "nerede", "nereler", "ve", "ile", "ne", "nasıl"}
    sorgu_kelimeleri = [w for w in sorgu_lower.split() if len(w) > 2 and w not in stop_words]

    try:
        with open("tesisler.csv", mode="r", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            for row in reader:
                tesis_adi = row['tesis_adi'].lower()
                tur = row['tur'].lower()
                mahalle = row['mahalle'].lower()

                # 1. Genel Kategori Eşleşmeleri
                spor_eslesmesi = "spor" in sorgu_lower and any(s in tur for s in spor_turleri)
                kurs_eslesmesi = any(k in sorgu_lower for k in ["kurs", "ders", "eğitim"]) and any(k in tur for k in kurs_turleri)
                
                # 2. Kelime Bazlı Detaylı Eşleşme (Tesis adı, türü veya mahallede arama)
                kelime_eslesmesi = any(w in tesis_adi or w in tur or w in mahalle for w in sorgu_kelimeleri)

                if spor_eslesmesi or kurs_eslesmesi or kelime_eslesmesi:
                    ucret = "Ücretsiz" if row['aylik_ucret_tl'] == "0" else f"{row['aylik_ucret_tl']} TL/ay"
                    kapali = f" (Kapalı Gün: {row['kapali_gun']})" if row['kapali_gun'].lower() != "yok" else ""
                    
                    bilgi = (f"📍 **{row['tesis_adi']}** ({row['tur'].capitalize()} - {row['mahalle']} Mah.)\n"
                             f"⏰ Çalışma Saatleri: {row['acilis']} - {row['kapanis']}{kapali}\n"
                             f"💰 Ücret: {ucret}")
                    bulunanlar.append(bilgi)
        
        if bulunanlar:
            return "\n\n".join(bulunanlar[:5])
        else:
            return "İlgili tesis veya kurs hakkında veritabanında bilgi bulunamadı. 153 Beyaz Masa hattımızdan destek alabilirsiniz."
            
    except FileNotFoundError:
        return "Tesis bilgi veritabanı (tesisler.csv) bulunamadı."
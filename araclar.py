import csv

def darica_hizmet_hesapla(hizmet_tipi: str, parametre: str = "", yas: int = 0) -> str:
    hizmet = hizmet_tipi.lower()
    p_lower = parametre.lower()

    # 1. Nikah Ücreti Hesaplama
    if "nikah" in hizmet:
        if "hafta sonu" in p_lower:
            return "Darıca Belediyesi hafta sonu nikah kıyma ücreti 1.600 TL'dir."
        elif "dış" in p_lower or "otel" in p_lower or "bahçe" in p_lower or "düğün" in p_lower:
            return "Belediye salonları dışındaki mekânlarda (otel, bahçe, düğün salonu vb.) nikah kıyma ücreti 4.500 TL'dir."
        else:
            return "Darıca Belediyesi hafta içi salon nikahı ücreti 900 TL'dir."

    # 2. Otopark Ücreti Hesaplama
    elif "otopark" in hizmet or "karavan" in p_lower:
        if "karavan" in p_lower:
            if "aylık" in p_lower or "abonelik" in p_lower:
                return "Darıca Millet Bahçesi Karavan Parkı aylık abonelik ücreti 6.000 TL'dir."
            else:
                return "Darıca Millet Bahçesi Karavan Parkı ücretleri: 0-1 saat 40 TL, 1-24 saat 300 TL, aylık abonelik ise 6.000 TL'dir."
        elif "engelli" in p_lower:
            return "Engelli araç kartı bulunan araçlar belediye otoparklarından tamamen ücretsiz yararlanır."
        elif "aylık" in p_lower or "abonelik" in p_lower:
            return "Belediye otoparklarında aylık otopark aboneliği seçeneği bulunmamaktadır (Yalnızca Karavan Parkı için aylık abonelik 6.000 TL'dir)."
        else:
            return "Belediye otoparklarında ilk 6 saat ücretsizdir. Sonrasında 6-8 saat 20 TL, 8-12 saat 40 TL, 12-24 saat arası için 200 TL'dir."

    # 3. Spor Tesisi & Kültür Merkezi İndirimi ve Salon Kiralaması
    elif "spor" in hizmet or "tesis" in hizmet or "kültür" in hizmet or "salon" in p_lower:
        if "kültür" in hizmet or "salon" in p_lower or "kiralama" in p_lower:
            if "dernek" in p_lower or "okul" in p_lower:
                return "Dernekler ve okullara kültür merkezi salon kiralamalarında %70 indirim uygulanır."
            elif "küçük" in p_lower or "400" in p_lower:
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

    # 4. Su Aboneliği & Kesinti Açma Ücreti
    elif "su" in hizmet:
        if "açma" in p_lower or "kesin" in p_lower or "fatura" in p_lower:
            return "Kesilen suyun yeniden açılması için vadesi geçmiş borcun yanı sıra 420 TL su açma ücreti ödenmelidir."
        else:
            return "Konut yeni su aboneliği güvence bedeli 1.154 TL'dir. Kesilen suyun yeniden açma ücreti ise 420 TL'dir."

    # 5. Sıfır Atık / Atık Yağ
    elif "atık" in hizmet or "yağ" in p_lower:
        return "5 litre bitkisel atık yağ getiren vatandaşlarımıza muhtarlıklardaki atık getirme merkezlerinde 1 litre deterjan hediye edilmektedir."

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
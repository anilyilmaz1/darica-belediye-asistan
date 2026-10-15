import csv

def darica_hizmet_hesapla(hizmet_tipi: str, parametre: str = "", yas: int = 0) -> str:
    hizmet = hizmet_tipi.lower()
    p_lower = parametre.lower()

    # 1. Nikah Ücreti Hesaplama
    if "nikah" in hizmet:
        if "hafta sonu" in p_lower:
            return "Darıca Belediyesi hafta sonu nikah kıyma ücreti 1.600 TL'dir."
        elif any(k in p_lower for k in ["dış", "otel", "bahçe", "düğün"]):
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
    elif any(k in hizmet for k in ["spor", "tesis", "kültür"]) or "salon" in p_lower:
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
        if any(k in p_lower for k in ["açma", "kesin", "fatura"]):
            return "Kesilen suyun yeniden açılması için vadesi geçmiş borcun yanı sıra 420 TL su açma ücreti ödenmelidir."
        else:
            return "Konut yeni su aboneliği güvence bedeli 1.154 TL'dir. Kesilen suyun yeniden açma ücreti ise 420 TL'dir."

    # 5. Sıfır Atık / Atık Yağ
    elif "atık" in hizmet or "yağ" in p_lower:
        return "5 litre bitkisel atık yağ getiren vatandaşlarımıza muhtarlıklardaki atık getirme merkezlerinde 1 litre deterjan hediye edilmektedir."

    else:
        return "Belirtilen hizmet kategorisi için belediye çağrı merkezimizi (153) arayabilirsiniz."


def tesis_bilgisi_sorgula(sorgu: str) -> str:
    """CSV veritabanından tesislerin çalışma saatlerini, konum, ders/kurs ve ücretlerini getirir."""
    sorgu_lower = sorgu.lower()
    
    # 1. Mahalle Tespiti
    mahalleler = [
        "yalı", "bağlarbaşı", "kazım karabekir", "yeni", "fevzi çakmak",
        "cami", "piri reis", "emek", "osmangazi", "abdi ipekçi",
        "zincirlikuyu", "bayramoğlu", "sırasöğütler", "nenehatun"
    ]
    aranan_mahalle = None
    for m in mahalleler:
        if m in sorgu_lower:
            aranan_mahalle = m
            break

    # 2. Kategori Tespiti
    is_kutuphane_sorgu = any(k in sorgu_lower for k in ["ders", "etüt", "kütüphane", "yks", "okuma", "çalışma", "kurs"])
    is_spor_sorgu = any(s in sorgu_lower for s in ["yüzme", "fitness", "tenis", "basketbol", "voleybol", "paten", "spor", "kort", "havuz", "salon"])

    eslesen_tesisler = []

    stop_words = {"için", "peki", "var", "mı", "mi", "mu", "mü", "nerede", "nereler", "ve", "ile", "ne", "nasıl", "hangi", "gün", "günleri", "saat", "saatleri", "sınırları", "içindeki"}
    sorgu_kelimeleri = [w for w in sorgu_lower.split() if len(w) > 2 and w not in stop_words]

    try:
        with open("tesisler.csv", mode="r", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            for row in reader:
                tesis_adi = row['tesis_adi'].lower()
                tur = row['tur'].lower()
                mahalle = row['mahalle'].lower()

                ucret = "Ücretsiz" if row['aylik_ucret_tl'] == "0" else f"{row['aylik_ucret_tl']} TL/ay"
                kapali = f" (Kapalı Gün: {row['kapali_gun']})" if row['kapali_gun'].lower() != "yok" else ""
                
                bilgi = (f"📍 **{row['tesis_adi']}** ({row['tur'].title()} - {row['mahalle']} Mah.)\n"
                         f"⏰ Çalışma Saatleri: {row['acilis']} - {row['kapanis']}{kapali}\n"
                         f"💰 Ücret: {ucret}")

                # Mahalle Filtrelemesi: Sorguda mahalle adı varsa ve tesiste geçmiyorsa atla
                if aranan_mahalle and (aranan_mahalle not in mahalle and aranan_mahalle not in tesis_adi):
                    continue

                is_kutuphane_row = any(k in tur for k in ["kütüphane", "etüt", "yks", "tiyatro", "enstrüman"])
                is_spor_row = any(s in tur for s in ["yüzme", "fitness", "tenis", "basketbol", "voleybol", "buz pateni", "pilates", "spor"])

                # Kategori İzolasyonu: Kütüphane arandıysa spor tesislerini getirme, spor arandıysa kütüphaneleri getirme
                if is_kutuphane_sorgu and not is_spor_sorgu:
                    if is_kutuphane_row:
                        eslesen_tesisler.append(bilgi)
                elif is_spor_sorgu and not is_kutuphane_sorgu:
                    if is_spor_row:
                        eslesen_tesisler.append(bilgi)
                else:
                    # Genel kelime arama
                    if any(w in tesis_adi or w in tur or w in mahalle for w in sorgu_kelimeleri):
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

    except FileNotFoundError:
        return "Tesis bilgi veritabanı (tesisler.csv) bulunamadı."
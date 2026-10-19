import csv
import os


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
        # Dış mekan/otel önceliği hafta sonuna göre önceliklidir
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
        # Kültür merkezi / salon kiralama kontrolü (Spor salonu aramaları hariç)
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
            # Spor tesisleri ve yaş / öğrenci indirimi
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
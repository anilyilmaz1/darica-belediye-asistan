def darica_hizmet_hesapla(hizmet_tipi: str, parametre: str = "", yas: int = 0) -> str:
    """
    Darıca Belediyesi rehberindeki güncel ücret, indirim ve süre kurallarını hesaplar.
    """
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
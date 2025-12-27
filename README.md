# 📊 2026 Maaş ve İşveren Maliyeti Simülasyon Robotu

Bu uygulama, **2026 yılı** için öngörülen asgari ücret, vergi dilimleri ve SGK parametrelerini temel alarak; işletmelerin **personel maliyetlerini** ve çalışanların **net ele geçen ücretlerini** simüle etmesini sağlayan profesyonel bir hesaplama aracıdır.

🚀 **[Canlı Demo İçin Tıklayın](https://share.streamlit.io)** _(Eğer deploy ettiyseniz linki buraya ekleyin)_

## 🎯 Temel Özellikler

### 1. 2026 Mevzuat Uyumu
*   **Güncel Vergi Dilimleri:** 2026 yılı için öngörülen Gelir Vergisi dilimleri (%15 - %40 artan oranlı) entegre edilmiştir.
*   **Yeni SGK Teşvik Yapısı:** 7566 sayılı Kanun ile değişen işveren teşvik oranları (İmalat %5, Diğer Sektörler %2 veya Teşviksiz) seçilebilir.
*   **Asgari Ücret İstisnası:** Tüm çalışanlar için brüt asgari ücret (Tahmini 33.030 TL) üzerinden vergi istisnaları otomatik uygulanır.

### 2. Esnek Hesaplama Yöntemleri
*   **📁 Excel İle Toplu Hesaplama:** Mevcut personel listenizi (Excel) yükleyerek yüzlerce çalışanın maliyetini saniyeler içinde analiz edin.
*   **✍️ Manuel Tekli Hesaplama:** Excel dosyasına ihtiyaç duymadan, sadece "Ücret" girerek hızlıca tekil hesaplama yapın.
*   **Net veya Brüt Giriş:** Hesaplamayı ister "Brüt Ücret", ister "Net Ücret" üzerinden başlatabilirsiniz.

### 3. Detaylı Raporlama
*   **Aylık Bordro Dökümü:** Her personel için Ocak-Aralık aylarını kapsayan; SGK, İşsizlik, GV, DV, Net Ücret ve İşveren Maliyeti detaylarını içeren tablo.
*   **İşveren Maliyet Analizi:** Toplam yıllık maliyet, Kurumlar Vergisi avantajı ve vergi sonrası net maliyet hesaplamaları.
*   **Excel Çıktısı:** Oluşturulan tüm raporları ve detaylı tabloları tek tıkla Excel formatında indirebilirsiniz.

## 🛠 Kullanım

1.  **Hesaplama Yöntemini Seçin:** "Excel Listesi Yükle" veya "Manuel Hesaplama".
2.  **Parametreleri Ayarlayın:**
    *   Maaş Artış Oranı (Excel modu için)
    *   İşveren Sektörü (İmalat / Diğer / Standart)
    *   Hesaplama Tipi (Brüt / Net)
3.  **Başlatın:** Hesapla butonuna basın.
4.  **Analiz Edin:** Özet metrikleri inceleyin, kişi bazlı detayları görüntüleyin ve raporları indirin.

## 📦 Kurulum (Lokal)

Bu projeyi kendi bilgisayarınızda çalıştırmak için:

```bash
git clone https://github.com/serdartasdoken/maas.git
cd maas
pip install -r requirements.txt
streamlit run maas.py
```

## 📄 Lisans


## 👨‍⚖️ Hazırlayan

**Serdar TAŞDÖKEN**  
*Yeminli Mali Müşavir*  
✉️ serdartasdoken@gmail.com  
[LinkedIn Profili](https://www.linkedin.com/in/serdar-tasdoken/)


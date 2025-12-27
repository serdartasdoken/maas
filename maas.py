import streamlit as st
import pandas as pd
import numpy as np
import io

# --- SABİTLER VE PARAMETRELER (2026 PROJEKSİYONU) ---
CONSTANTS = {
    "ASGARI_UCRET_BRUT": 33030.00,
    "ASGARI_UCRET_NET": 28075.50,
    "SGK_TABAN": 33030.00,
    "SGK_TAVAN": 297270.00,
    "SGK_ISCI_ORANI": 0.14,
    "ISSIZLIK_ISCI_ORANI": 0.01,
    "SGK_ISVEREN_ORANI": 0.2175,  # %21.75 SGK (KVSK Dahil) + %2 İşsizlik = %23.75 Toplam
    "ISSIZLIK_ISVEREN_ORANI": 0.02,
    "DAMGA_VERGISI_ORANI": 0.00759,
    "GELIR_VERGISI_DILIMLERI": [
        {"limit": 190000, "oran": 0.15},
        {"limit": 400000, "oran": 0.20},
        {"limit": 1500000, "oran": 0.27},
        {"limit": 5300000, "oran": 0.35},
        {"limit": float('inf'), "oran": 0.40}
    ]
}

# --- YARDIMCI FONKSİYONLAR ---

def parse_turkish_float(value):
    """Excel'den gelen Türkçe formatlı sayıları (22.104,67) float'a çevirir."""
    if pd.isna(value) or value == '':
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    
    val_str = str(value).strip()
    # Noktaları sil (binlik ayracı), virgülleri noktaya çevir (ondalık)
    val_str = val_str.replace('.', '').replace(',', '.')
    try:
        return float(val_str)
    except ValueError:
        return 0.0

def calculate_income_tax(cumulative_base, current_base):
    """Kümülatif matraha göre gelir vergisini hesaplar."""
    tax = 0.0
    remaining_base = current_base
    current_cum = cumulative_base

    # Dilim mantığı (Basitleştirilmiş kümülatif hesaplama)
    # Önceki kümülatif vergi toplamını bul, sonra (kümülatif + matrah)'ın vergisini bul ve çıkar.
    
    def get_tax_for_value(val):
        t = 0
        prev_limit = 0
        for dilim in CONSTANTS["GELIR_VERGISI_DILIMLERI"]:
            if val > prev_limit:
                taxable_part = min(val, dilim["limit"]) - prev_limit
                t += taxable_part * dilim["oran"]
                prev_limit = dilim["limit"]
            else:
                break
        return t

    tax_before = get_tax_for_value(current_cum)
    tax_after = get_tax_for_value(current_cum + current_base)
    
    return tax_after - tax_before

def get_min_wage_exemption_2026():
    """12 ay için Asgari Ücret GV ve DV istisnalarını hesaplar."""
    exemptions = []
    cum_base = 0
    
    gross_mw = CONSTANTS["ASGARI_UCRET_BRUT"]
    worker_sgk = gross_mw * CONSTANTS["SGK_ISCI_ORANI"]
    worker_unemp = gross_mw * CONSTANTS["ISSIZLIK_ISCI_ORANI"]
    tax_base_mw = gross_mw - (worker_sgk + worker_unemp)
    
    for _ in range(12):
        gv_istisna = calculate_income_tax(cum_base, tax_base_mw)
        dv_istisna = gross_mw * CONSTANTS["DAMGA_VERGISI_ORANI"]
        exemptions.append({"gv": gv_istisna, "dv": dv_istisna})
        cum_base += tax_base_mw
        
    return exemptions

MIN_WAGE_EXEMPTIONS = get_min_wage_exemption_2026()

def calculate_payroll_month(wage, calculation_type, month_idx, cumulative_tax_base):
    """
    Belirli bir ay için bordro hesabı yapar.
    calculation_type: 'Brüt' (Sabit Brüt) veya 'Net' (Sabit Net)
    """
    
    gross_wage = 0.0
    
    # Eğer hesaplama NET üzerinden ise, Brüt'ü bulmak için iterasyon gerekir
    if calculation_type == 'Net':
        target_net = wage
        # Basit Binary Search / Iteration ile Brüt bulma
        low = target_net
        high = target_net * 2.0
        for _ in range(20): # 20 iterasyon yeterli hassasiyet sağlar
            mid = (low + high) / 2
            res = calculate_deductions(mid, month_idx, cumulative_tax_base)
            if abs(res['net_pay'] - target_net) < 0.01:
                gross_wage = mid
                break
            elif res['net_pay'] < target_net:
                low = mid
            else:
                high = mid
        gross_wage = mid
    else:
        gross_wage = wage

    # Hesaplamayı yap
    return calculate_deductions(gross_wage, month_idx, cumulative_tax_base)

def calculate_deductions(gross_wage, month_idx, cumulative_tax_base):
    # Asgari Ücret Kontrolü
    if gross_wage < CONSTANTS["ASGARI_UCRET_BRUT"]:
        gross_wage = CONSTANTS["ASGARI_UCRET_BRUT"]

    # SGK Matrahı (Tavan/Taban)
    sgk_base = min(max(gross_wage, CONSTANTS["SGK_TABAN"]), CONSTANTS["SGK_TAVAN"])
    
    # İşçi Kesintileri
    sgk_worker = sgk_base * CONSTANTS["SGK_ISCI_ORANI"]
    unemp_worker = sgk_base * CONSTANTS["ISSIZLIK_ISCI_ORANI"]
    
    # GV Matrahı
    income_tax_base = gross_wage - (sgk_worker + unemp_worker)
    
    # Gelir Vergisi
    raw_income_tax = calculate_income_tax(cumulative_tax_base, income_tax_base)
    
    # İstisnalar
    exemption = MIN_WAGE_EXEMPTIONS[month_idx]
    payable_income_tax = max(0, raw_income_tax - exemption["gv"])
    
    # Damga Vergisi
    raw_stamp_tax = gross_wage * CONSTANTS["DAMGA_VERGISI_ORANI"]
    payable_stamp_tax = max(0, raw_stamp_tax - exemption["dv"])
    
    # Net Ele Geçen
    net_pay = gross_wage - (sgk_worker + unemp_worker + payable_income_tax + payable_stamp_tax)
    
    # İşveren Maliyeti
    sgk_employer = sgk_base * CONSTANTS["SGK_ISVEREN_ORANI"]
    unemp_employer = sgk_base * CONSTANTS["ISSIZLIK_ISVEREN_ORANI"]
    
    total_employer_cost = gross_wage + sgk_employer + unemp_employer
    
    return {
        "gross_wage": gross_wage,
        "net_pay": net_pay,
        "sgk_worker": sgk_worker,
        "unemp_worker": unemp_worker,
        "income_tax_base": income_tax_base,
        "cumulative_tax_base": cumulative_tax_base, # Kümülatif Matrah
        "raw_income_tax": raw_income_tax, # Hesaplanan GV
        "income_tax": payable_income_tax, # Ödenecek GV
        "gv_exemption": exemption["gv"],  # GV İstisnası
        "raw_stamp_tax": raw_stamp_tax,   # Hesaplanan DV
        "stamp_tax": payable_stamp_tax,   # Ödenecek DV
        "dv_exemption": exemption["dv"],   # DV İstisnası
        "sgk_employer": sgk_employer,
        "unemp_employer": unemp_employer,
        "total_cost": total_employer_cost
    }

# --- STREAMLIT ARAYÜZÜ ---

st.set_page_config(page_title="2026 Maaş Maliyet Simülasyonu", layout="wide")

st.title("📊 2026 Yılı Asgari Ücret ve İşveren Maliyeti Simülasyonu")
st.markdown("""
Bu uygulama, yüklenen personel listesi üzerinden 2026 yılı için tahmini aylık ve yıllık işveren maliyetlerini hesaplar.
Vergi dilimleri, SGK tavanı ve asgari ücret istisnaları **2026 projeksiyonlarına** göre işlenir.
""")

# Sidebar - Girdiler
with st.sidebar:
    st.header("⚙️ Simülasyon Parametreleri")
    
    corporate_tax_rate = st.number_input("Kurumlar Vergisi Oranı (%)", min_value=0.0, max_value=100.0, value=25.0) / 100.0

    st.subheader("SGK Teşvik Oranı (2026/7566 Sayılı Kanun)")
    incentive_choice = st.radio(
        "İşveren SGK ve Teşvik Durumu Seçiniz:",
        ("5510 - İmalat Sektörü (%5 İndirim)", "5510 - İmalat Dışı Sektörler (%2 İndirim)", "Teşviksiz / Standart (%0)")
    )
    
    # 2026 GÜNCELLEMESİ: İşveren Taban Oranı = %23.75 (KVSK Dahil)
    # İşsizlik (%2) Sabit -> SGK Payı = %21.75
    # Çarpanlar sadece SGK Payı üzerinden
    
    if "İmalat Sektörü" in incentive_choice:
        # %5 Puan İndirim
        # Toplam: 18.75% -> SGK Part: 16.75%
        CONSTANTS["SGK_ISVEREN_ORANI"] = 0.1675 
        current_total_rate = 18.75
    elif "İmalat Dışı" in incentive_choice:
        # %2 Puan İndirim (Eski %4 düştü)
        # Toplam: 21.75% -> SGK Part: 19.75%
        CONSTANTS["SGK_ISVEREN_ORANI"] = 0.1975
        current_total_rate = 21.75
    else:
        # Teşviksiz
        # Toplam: 23.75% -> SGK Part: 21.75%
        CONSTANTS["SGK_ISVEREN_ORANI"] = 0.2175
        current_total_rate = 23.75
    
    st.caption(f"Kullanılan Toplam İşveren Prim Oranı (SGK+İşsizlik): **%{current_total_rate:.2f}**")
    
    st.subheader("Maaş Artış Senaryosu")
    
    raise_rate = st.number_input("Maaş Artış Oranı (%)", min_value=0.0, value=30.0, help="Elden ödemelerin resmileştirilmesi veya normal zam dahil toplam artış oranını giriniz.") / 100.0
    
    calc_method = st.radio("Hesaplama Yöntemi", ("Brüt Ücret Üzerinden", "Net Ücret Üzerinden"))
    calc_type_key = 'Brüt' if 'Brüt' in calc_method else 'Net'

    st.info(f"**Bilgi:** Mevcut maaşlara **%{raise_rate*100:.0f}** oranında artış uygulanarak 2026 maliyetleri hesaplanacaktır.")

# --- GİRİŞ YÖNTEMİ SEÇİMİ ---
st.divider()
input_method = st.radio("Hesaplama Yöntemini Seçiniz:", ("📁 Excel Listesi Yükle", "✍️ Manuel Tekli Hesaplama"), horizontal=True)
st.divider()

df = None
col_wage = "Maaş"
col_name = "Personel"
col_dept = "Departman"

if input_method == "📁 Excel Listesi Yükle":
    # Dosya Yükleme
    uploaded_file = st.file_uploader("Personel Listesini Yükleyiniz (Excel .xls/.xlsx)", type=["xls", "xlsx"])

    if uploaded_file is not None:
        try:
            df = pd.read_excel(uploaded_file)

            # Sütun İsimlerini Temizle (Boşlukları kırp)
            df.columns = df.columns.str.strip()
            
            st.subheader("📋 Sütun Eşleştirme")
            st.info("Lütfen Excel dosyanızdaki sütunları aşağıdaki alanlarla eşleştiriniz.")
            
            # Sütun Seçimi
            all_columns = df.columns.tolist()
            
            # Tahmin algoritması (default value için)
            def find_default_col(options, keywords):
                for col in options:
                    for key in keywords:
                        if key.lower() in col.lower():
                            return col
                return options[0] if options else None

            col_wage = st.selectbox(
                "Maaş/Ücret Sütunu (Zorunlu)", 
                all_columns, 
                index=all_columns.index(find_default_col(all_columns, ['ücret', 'maas', 'tutar', 'net', 'brut'])) if find_default_col(all_columns, ['ücret', 'maas', 'tutar', 'net', 'brut']) in all_columns else 0
            )
            
            col_name = st.selectbox(
                "Personel Adı Sütunu (Opsiyonel)", 
                ["Otomatik İsimlendir"] + all_columns, 
                index=all_columns.index(find_default_col(all_columns, ['ad', 'isim', 'personel', 'calisan'])) + 1 if find_default_col(all_columns, ['ad', 'isim', 'personel', 'calisan']) in all_columns else 0
            )
            
            col_dept = st.selectbox(
                "Departman Sütunu (Opsiyonel)", 
                ["Seçiniz"] + all_columns, 
                index=0
            )
        except Exception as e:
            st.error(f"Dosya okunurken hata oluştu: {e}")

else: # Manuel Giriş
    st.subheader("✍️ Personel Bilgileri")
    col1, col2 = st.columns(2)
    with col1:
        manual_wage = st.number_input("Güncel Aylık Maaş (TL)", min_value=0.0, value=30000.0, step=1000.0)
    with col2:
        manual_name = st.text_input("Personel Adı (Opsiyonel)", value="Yeni Personel")
    
    # DataFrame Oluştur
    df = pd.DataFrame({
        "Maaş": [manual_wage],
        "Personel": [manual_name if manual_name else "Personel 1"],
        "Departman": ["Genel"]
    })
    col_wage = "Maaş"
    col_name = "Personel"
    col_dept = "Departman"

if df is not None:
    if st.button("Hesaplamayı Başlat", type="primary"):
        st.success(f"{len(df)} personel kaydı için hesaplama başlıyor...")
        
        try:
            
            # --- HESAPLAMA MOTORU ---
            
            results = []
            detailed_payroll_data = {} # Personel Adı -> [Ay1, Ay2...] listesi
            
            progress_bar = st.progress(0)
            
            for index, row in df.iterrows():
                # İlerleme çubuğu
                progress_bar.progress((index + 1) / len(df))
                
                # 1. Mevcut Maaşı Al
                raw_wage = parse_turkish_float(row.get(col_wage, 0))
                
                # Maaş 0 ise atla veya işlem yapma
                if raw_wage == 0:
                    continue
                
                # 2. 2026 Hedef Maaşı Belirle
                
                multiplier = (1 + raise_rate)
                target_wage_2026 = raw_wage * multiplier
                
                # Departman
                dept_val = row.get(col_dept, '-') if col_dept != "Seçiniz" else '-'
                
                if col_name == "Otomatik İsimlendir":
                    person_name = f"Personel {index + 1}"
                else:
                    person_name = row.get(col_name, f"Personel {index + 1}")

                # 3. Yıllık Simülasyon
                emp_results = {
                    "Personel": person_name,
                    "Departman": dept_val,
                    "Mevcut Ücret": raw_wage,
                    "2026 Hedef Ücret": target_wage_2026,
                    "Ücret Tipi": calc_type_key
                }
                
                yearly_total_cost = 0.0
                cum_tax_base = 0.0
                
                # Yıllık Toplamları Tutacak Değişkenler
                year_net_pay = 0.0
                year_sgk_worker = 0.0
                year_sgk_employer = 0.0
                year_income_tax = 0.0
                year_stamp_tax = 0.0
                
                person_monthly_list = []
                
                for month in range(12):
                    res = calculate_payroll_month(target_wage_2026, calc_type_key, month, cum_tax_base)
                    
                    # Kümülatifi güncelle
                    cum_tax_base += res['income_tax_base']
                    yearly_total_cost += res['total_cost']
                    
                    # Detayları topla
                    year_net_pay += res['net_pay']
                    year_sgk_worker += res['sgk_worker']
                    year_sgk_employer += res['sgk_employer']
                    year_income_tax += res['income_tax']
                    year_stamp_tax += res['stamp_tax']
                    
                    # Aylık verileri kaydet
                    emp_results[f"Ay_{month+1}_Maliyet"] = res['total_cost']
                    emp_results[f"Ay_{month+1}_Net"] = res['net_pay']
                    emp_results[f"Ay_{month+1}_Brut"] = res['gross_wage']
                    
                    # Detaylı liste için kaydet
                    res['month_name'] = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"][month]
                    person_monthly_list.append(res)

                emp_results["Toplam_Yillik_Maliyet"] = yearly_total_cost
                emp_results["Yillik_Net_Ucret"] = year_net_pay
                emp_results["Yillik_SGK_Isci"] = year_sgk_worker
                emp_results["Yillik_SGK_Isveren"] = year_sgk_employer
                emp_results["Yillik_Gelir_Vergisi"] = year_income_tax
                emp_results["Yillik_Damga_Vergisi"] = year_stamp_tax
                
                emp_results["Kurumlar_Vergisi_Tasarrufu"] = yearly_total_cost * corporate_tax_rate
                emp_results["Net_Isveren_Maliyeti"] = yearly_total_cost - emp_results["Kurumlar_Vergisi_Tasarrufu"]
                
                results.append(emp_results)
                detailed_payroll_data[person_name] = person_monthly_list
            
            # Sonuçları Session State'e kaydet (Sonraki etkileşimlerde kaybolmaması için)
            st.session_state['results'] = results
            st.session_state['detailed_payroll_data'] = detailed_payroll_data

        except Exception as e:
            st.error(f"Bir hata oluştu: {e}")
            
        # --- SONUÇLARIN GÖSTERİMİ (Session State'den oku) ---
        
        if 'results' in st.session_state and st.session_state['results']:
            results = st.session_state['results']
            res_df = pd.DataFrame(results)
            detailed_data = st.session_state['detailed_payroll_data']
            
            # 1. Özet Metrikler
            total_cost_all = res_df["Toplam_Yillik_Maliyet"].sum()
            total_tax_saving = res_df["Kurumlar_Vergisi_Tasarrufu"].sum()
            net_cost_all = res_df["Net_Isveren_Maliyeti"].sum()
            
            st.divider()
            col1, col2, col3 = st.columns(3)
            col1.metric("Toplam Yıllık İşveren Maliyeti (2026)", f"{total_cost_all:,.2f} TL")
            col2.metric("Toplam Kurumlar Vergisi Avantajı", f"{total_tax_saving:,.2f} TL")
            col3.metric("Vergi Sonrası Net Maliyet", f"{net_cost_all:,.2f} TL")
            st.divider()
            
            # 2. Detaylı Tablo
            st.subheader("Personel Bazlı Detaylar")
            
            display_cols = [
                "Personel", "Mevcut Ücret", "2026 Hedef Ücret", 
                "Yillik_Net_Ucret", "Yillik_SGK_Isveren", "Toplam_Yillik_Maliyet"
            ]
            
            st.dataframe(res_df[display_cols].style.format({
                "Mevcut Ücret": "{:,.2f}", 
                "2026 Hedef Ücret": "{:,.2f}",
                "Yillik_Net_Ucret": "{:,.2f}",
                "Yillik_SGK_Isveren": "{:,.2f}",
                "Toplam_Yillik_Maliyet": "{:,.2f}"
            }))
            
            # 3. Excel İndirme
            st.subheader("Rapor İndir")
            
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                res_df.to_excel(writer, index=False, sheet_name='2026_Maliyet_Simulasyonu')
            
            st.download_button(
                label="📥 Detaylı Excel Raporunu İndir",
                data=output.getvalue(),
                file_name="2026_Maas_Maliyet_Simulasyonu.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            
            # --- 4. PERSONEL BAZLI DETAYLI BORDRO (YENİ) ---
            st.markdown("---")
            st.header("📄 Personel Bazlı Detaylı Bordro")
            st.info("Aşağıdan bir personel seçerek aylık detaylı brütten nete hesap pusulasını görüntüleyebilirsiniz.")
            
            selected_person = st.selectbox("Personel Seçiniz:", list(detailed_data.keys()))
            
            if selected_person:
                months_data = detailed_data[selected_person]
                
                # Veriyi kullanıcı formatına uygun hale getir
                # İstenen Kolonlar: 
                # Ay | Brüt | SGK İşçi | İşsizlik İşçi | GV Matrahı | Kümülatif Matrah | Hesaplanan GV | GV İstisnası | Asgari GV İstisna?? | DV | DV İstisna | Net | SGK İşveren | İşsizlik İşveren | Toplam Maliyet
                
                payroll_rows = []
                totals = {k: 0.0 for k in ["gross_wage", "sgk_worker", "unemp_worker", "income_tax_base", "raw_income_tax", "gv_exemption", "income_tax", "raw_stamp_tax", "dv_exemption", "stamp_tax", "net_pay", "sgk_employer", "unemp_employer", "total_cost"]}
                
                for m_item in months_data:
                    row = {
                        "Ay": m_item['month_name'],
                        "Brüt Ücret": m_item['gross_wage'],
                        "SGK İşçi": m_item['sgk_worker'],
                        "İşsizlik İşçi": m_item['unemp_worker'],
                        "GV Matrahı": m_item['income_tax_base'],
                        "Kümülatif GV Matrahı": m_item['cumulative_tax_base'], # Bunun toplamı olmaz
                        "Hesaplanan GV": m_item['raw_income_tax'],
                        "GV İstisnası": m_item['gv_exemption'],
                        "Ödenecek GV": m_item['income_tax'],
                        "Hesaplanan DV": m_item['raw_stamp_tax'],
                        "DV İstisnası": m_item['dv_exemption'],
                        "Ödenecek DV": m_item['stamp_tax'],
                        "Net Ele Geçen": m_item['net_pay'],
                        "SGK İşveren": m_item['sgk_employer'],
                        "İşsizlik İşveren": m_item['unemp_employer'],
                        "Toplam Maliyet": m_item['total_cost']
                    }
                    payroll_rows.append(row)
                    
                    # Toplamları güncelle
                    for k in totals.keys():
                        if k in m_item:
                            totals[k] += m_item[k]
                
                # Toplam Satırı Ekle
                total_row = {
                    "Ay": "TOPLAM",
                    "Brüt Ücret": totals['gross_wage'],
                    "SGK İşçi": totals['sgk_worker'],
                    "İşsizlik İşçi": totals['unemp_worker'],
                    "GV Matrahı": totals['income_tax_base'],
                    "Kümülatif GV Matrahı": 0, # Anlamsız
                    "Hesaplanan GV": totals['raw_income_tax'],
                    "GV İstisnası": totals['gv_exemption'],
                    "Ödenecek GV": totals['income_tax'],
                    "Hesaplanan DV": totals['raw_stamp_tax'],
                    "DV İstisnası": totals['dv_exemption'],
                    "Ödenecek DV": totals['stamp_tax'],
                    "Net Ele Geçen": totals['net_pay'],
                    "SGK İşveren": totals['sgk_employer'],
                    "İşsizlik İşveren": totals['unemp_employer'],
                    "Toplam Maliyet": totals['total_cost']
                }
                payroll_rows.append(total_row)
                
                payroll_df = pd.DataFrame(payroll_rows)
                
                # Formatlama
                format_dict = {col: "{:,.2f}" for col in payroll_df.columns if col != "Ay"}
                
                st.dataframe(payroll_df.style.format(format_dict))
                
                # Excel İndir (Seçili Personel)
                p_output = io.BytesIO()
                with pd.ExcelWriter(p_output, engine='openpyxl') as writer:
                    payroll_df.to_excel(writer, index=False, sheet_name=f'{selected_person[:30]}')
                
                st.download_button(
                    label=f"📥 {selected_person} - Detaylı Bordrosunu İndir",
                    data=p_output.getvalue(),
                    file_name=f"Bordro_{selected_person}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

    except Exception as e:
        st.error(f"Bir hata oluştu: {e}")
else:
    st.info("Lütfen sol menüden parametreleri ayarlayın ve bir Excel dosyası yükleyin.")
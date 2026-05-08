import sys
import os
import subprocess
import json
import time
import re
import requests
import streamlit as st
import pandas as pd
import sqlite3

# ==========================================
# 🚀 GÜVENLİ ÇİFT TIKLAMA BAŞLATICISI (LOKAL İÇİN)
# ==========================================
if __name__ == '__main__':
    if "streamlit" not in sys.argv[0].lower() and os.environ.get("STREAMLIT_KILIDI") != "ACIK":
        os.environ["STREAMLIT_KILIDI"] = "ACIK"
        print("🎯 Tüm Zamanlar Analiz Merkezi Başlatılıyor...")
        subprocess.Popen([sys.executable, "-m", "streamlit", "run", os.path.abspath(__file__)])
        sys.exit(0)

# ==========================================
# SAYFA AYARLARI (ZORUNLU OLARAK EN ÜSTTE)
# ==========================================
st.set_page_config(page_title="Tüm Zamanlar Analiz Merkezi", layout="wide", page_icon="🎯")

# ==========================================
# AYARLAR VE GOOGLE DRIVE LİNKİ
# ==========================================
db_yolu = "arsiv.db"
sablon_dosyasi = "sablonlar.json"
METIN_SUTUNLARI = ["Match ID", "Bülten Kodu", "Tarih", "Saat", "Ülke", "Lig", "Ev Sahibi", "Deplasman", "İY/MS"]

# ⚠️ DİKKAT: GOOGLE DRIVE LİNKİNİ AŞAĞIDAKİ TIRNAKLARIN İÇİNE YAPIŞTIR:
GDRIVE_LINK = "BURAYA_LINK_GELECEK"

# ==========================================
# ☁️ BULUT İÇİN CANLI İNDİRME MOTORU (ÇÖKME ÖNLEYİCİ)
# ==========================================
def drive_id_bul(url):
    match = re.search(r"/d/([a-zA-Z0-9_-]+)", url)
    return match.group(1) if match else url

def veritabani_indir(file_id, destination):
    URL = "https://docs.google.com/uc?export=download&confirm=t"
    session = requests.Session()
    
    st.warning("☁️ Veritabanı Google Drive'dan çekiliyor... Lütfen sayfayı kapatmayın.")
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    response = session.get(URL, params={'id': file_id}, stream=True)
    
    # Drive virüs taraması uyarısını (Büyük dosya engeli) aşmak için
    for key, value in response.cookies.items():
        if key.startswith('download_warning'):
            response = session.get(URL, params={'id': file_id, 'confirm': value}, stream=True)
            break

    CHUNK_SIZE = 1024 * 1024 * 2  # 2 MB Parçalar halinde indir (Hızlı ve donmaz)
    indirilmis = 0
    tahmini_boyut_mb = 295.0 # Veritabanının yaklaşık boyutu
    
    with open(destination, "wb") as f:
        for chunk in response.iter_content(CHUNK_SIZE):
            if chunk:
                f.write(chunk)
                indirilmis += len(chunk)
                mb = indirilmis / (1024 * 1024)
                status_text.text(f"İndiriliyor: {mb:.1f} MB / {tahmini_boyut_mb} MB")
                
                # İlerleme çubuğunu doldur (Canlı tutucu)
                ilerleme = min(mb / tahmini_boyut_mb, 1.0)
                progress_bar.progress(ilerleme)
                
    status_text.success("✅ Veritabanı kusursuz bir şekilde indirildi!")
    time.sleep(1)
    st.rerun()

if not os.path.exists(db_yolu):
    if GDRIVE_LINK != "BURAYA_LINK_GELECEK" and "drive.google.com" in GDRIVE_LINK:
        drive_id = drive_id_bul(GDRIVE_LINK)
        veritabani_indir(drive_id, db_yolu)
    else:
        st.error("⚠️ Google Drive linki hatalı veya girilmemiş! Lütfen kodun içindeki GDRIVE_LINK kısmını doldurun.")
        st.stop()


# ==========================================
# 🧠 KARDEŞ LİG YAPAY ZEKA ALGORİTMASI
# ==========================================
def lig_seviyesi_bul(ulke, lig):
    lig = str(lig).lower()
    ulke = str(ulke).lower()

    if ulke == "türkiye" and "1. lig" in lig: return "Tier 2"
    if ulke == "türkiye" and "2. lig" in lig: return "Tier 3"
    if ulke == "ingiltere" and "championship" in lig: return "Tier 2"
    if ulke == "ingiltere" and ("league one" in lig or "league two" in lig): return "Tier 3"
    if ulke == "almanya" and "2. bundesliga" in lig: return "Tier 2"
    if ulke == "almanya" and "3. liga" in lig: return "Tier 3"
    if ulke == "ispanya" and "laliga 2" in lig: return "Tier 2"
    if ulke == "italya" and "serie b" in lig: return "Tier 2"
    if ulke == "italya" and "serie c" in lig: return "Tier 3"
    if ulke == "fransa" and "ligue 2" in lig: return "Tier 2"

    tier_2_keywords = ["2. lig", "2. division", "serie b", "ligue 2", "superettan", "obos", "erste", "challenge", "championship", "segunda", "b", "2"]
    for kw in tier_2_keywords:
        if kw in lig: return "Tier 2"

    tier_1_keywords = ["premier", "super", "süper", "bundesliga", "serie a", "ligue 1", "la liga", "eredivisie", "allsvenskan", "eliteserien", "pro lig", "primeira", "1. lig", "1. division", "1. hnl", "1. liga", "ekstraklasa", "nb i", "liga profesional", "serie a"]
    for kw in tier_1_keywords:
        if kw in lig: return "Tier 1"

    return "Tier 3"

def ulke_bolgesi_bul(ulke):
    ulke = str(ulke).lower()
    elit_avrupa = ["ingiltere", "almanya", "ispanya", "italya", "fransa"]
    iskandinav = ["isveç", "norveç", "danimarka", "finlandiya", "izlanda", "faroe adaları"]
    orta_dogu_avrupa = ["türkiye", "hollanda", "belçika", "portekiz", "avusturya", "isviçre", "iskoçya", "polonya", "çekya", "macaristan", "hırvatistan", "sırbistan", "yunanistan", "romanya", "bulgaristan", "slovakya", "slovenya", "ukrayna", "rusya"]
    guney_amerika = ["brezilya", "arjantin", "kolombiya", "şili", "uruguay", "peru", "ekvador", "paraguay", "bolivya", "venezuela"]
    kuzey_amerika = ["abd", "meksika", "kosta rika", "honduras", "kanada"]
    asya_okyanusya = ["japonya", "güney kore", "avustralya", "çin", "suudi arabistan", "bae", "katar", "iran", "ırak", "özbekistan", "endonezya", "hindistan"]
    afrika = ["mısır", "fas", "güney afrika", "cezayir", "tunus", "nijerya", "gana", "kamerun"]
    uluslararasi = ["avrupa", "dünya", "uluslararası", "güney amerika (kıta)"]

    if ulke in elit_avrupa: return "Elit Avrupa"
    if ulke in iskandinav: return "İskandinav"
    if ulke in orta_dogu_avrupa: return "Orta/Doğu Avrupa"
    if ulke in guney_amerika: return "Güney Amerika"
    if ulke in kuzey_amerika: return "Kuzey/Orta Amerika"
    if ulke in asya_okyanusya: return "Asya/Okyanusya"
    if ulke in afrika: return "Afrika"
    if ulke in uluslararasi: return "Uluslararası Turnuvalar"

    return "Dünya Geneli (Diğer)"

def akilli_kardes_bul(secilen_kombineler, ulke_lig_df):
    eklenecekler = set(secilen_kombineler)
    secilen_profiller = set()
    
    for kombine in secilen_kombineler:
        if " - " in kombine:
            ulke, lig = kombine.split(' - ', 1)
            bolge = ulke_bolgesi_bul(ulke)
            seviye = lig_seviyesi_bul(ulke, lig)
            secilen_profiller.add((bolge, seviye))
            
    for idx, row in ulke_lig_df.iterrows():
        bolge = ulke_bolgesi_bul(row['Ülke'])
        seviye = lig_seviyesi_bul(row['Ülke'], row['Lig'])
        if (bolge, seviye) in secilen_profiller:
            eklenecekler.add(row['Kombine'])
            
    return list(eklenecekler)

# --- SQL FONKSİYONLARI ---
@st.cache_data
def sutunlari_getir():
    conn = sqlite3.connect(db_yolu)
    df_ornek = pd.read_sql_query("SELECT * FROM maclar LIMIT 1", conn)
    conn.close()
    return df_ornek.columns.tolist()

@st.cache_data
def benzersiz_degerleri_getir(sutun):
    conn = sqlite3.connect(db_yolu)
    df_benzersiz = pd.read_sql_query(f"SELECT DISTINCT [{sutun}] FROM maclar WHERE [{sutun}] IS NOT NULL ORDER BY [{sutun}]", conn)
    conn.close()
    return df_benzersiz[sutun].tolist()

def gercek_olasilik_bandi(hedef_oran, bant_yuzdesi):
    if hedef_oran <= 1.0: return 1.01, 1.01
    hedef_olasilik = 100.0 / hedef_oran
    alt_olasilik = hedef_olasilik - bant_yuzdesi
    ust_olasilik = hedef_olasilik + bant_yuzdesi
    
    if alt_olasilik <= 0.01: alt_olasilik = 0.01
    if ust_olasilik > 100.0: ust_olasilik = 100.0
    
    alt_sinir = 100.0 / ust_olasilik
    ust_sinir = 100.0 / alt_olasilik
    return alt_sinir, ust_sinir

def dinamik_analiz_yap(filtre_sozlugu, bant_yuzdesi):
    conn = sqlite3.connect(db_yolu)
    sorgu = "SELECT * FROM maclar WHERE 1=1"
    parametreler = []

    for sutun, data in filtre_sozlugu.items():
        if data['tip'] == 'kategori':
            yer_tutucular = ','.join(['?'] * len(data['deger']))
            sorgu += f" AND [{sutun}] IN ({yer_tutucular})"
            parametreler.extend(data['deger'])
            
        elif data['tip'] == 'kombine': 
            yer_tutucular = ','.join(['?'] * len(data['deger']))
            sorgu += f" AND ([Ülke] || ' - ' || [Lig]) IN ({yer_tutucular})"
            parametreler.extend(data['deger'])
            
        elif data['tip'] == 'oran':
            hedef = data['deger']
            yontem = data.get('yontem', 'Bant (%)')
            
            if yontem == 'Bant (%)':
                kullanilacak_bant = data.get('ozel_bant', bant_yuzdesi)
                alt_sinir, ust_sinir = gercek_olasilik_bandi(hedef, kullanilacak_bant)
                sorgu += f" AND [{sutun}] >= ? AND [{sutun}] <= ?"
                parametreler.extend([alt_sinir, ust_sinir])
            elif yontem == 'Büyüktür (>)':
                sorgu += f" AND [{sutun}] >= ?"
                parametreler.append(hedef)
            elif yontem == 'Küçüktür (<)':
                sorgu += f" AND [{sutun}] <= ?"
                parametreler.append(hedef)
            elif yontem == 'Eşittir (=)':
                sorgu += f" AND [{sutun}] = ?"
                parametreler.append(hedef)

    df_sonuc = pd.read_sql_query(sorgu, conn, params=parametreler)
    conn.close()
    return df_sonuc

@st.cache_data
def csv_hazirla(df):
    return df.to_csv(index=False).encode('utf-8-sig')

def yuzde_hesapla(kosul_serisi, toplam_mac):
    if toplam_mac == 0: return "-"
    return f"%{(kosul_serisi.sum() / toplam_mac * 100):.1f}"

def tarihi_yil_ay_gun_yap(df):
    if not df.empty and "Tarih" in df.columns:
        try:
            zaman_serisi = df["Tarih"].astype(str)
            if "Saat" in df.columns:
                zaman_serisi = zaman_serisi + " " + df["Saat"].astype(str)
                
            df['Gercek_Zaman'] = pd.to_datetime(zaman_serisi, dayfirst=True, errors='coerce')
            df = df.sort_values(by='Gercek_Zaman', ascending=False)
            df['Tarih'] = df['Gercek_Zaman'].dt.strftime('%Y-%m-%d')
            df = df.drop(columns=['Gercek_Zaman'], errors='ignore')
        except Exception:
            pass
    return df

# ==========================================
# 🧠 AKILLI HAFIZA EŞİTLEYİCİ
# ==========================================
if "update_sutunlar" in st.session_state:
    st.session_state["secilen_sutunlar_widget"] = st.session_state["update_sutunlar"]
    del st.session_state["update_sutunlar"]

for key in list(st.session_state.keys()):
    if key.startswith("update_yontem_"):
        real_key = key.replace("update_yontem_", "yontem_")
        st.session_state[real_key] = st.session_state[key]
        del st.session_state[key]
    elif key.startswith("update_bant_"):
        real_key = key.replace("update_bant_", "bant_")
        st.session_state[real_key] = st.session_state[key]
        del st.session_state[key]
    elif key.startswith("update_filter_"):
        real_key = key.replace("update_filter_", "filter_")
        st.session_state[real_key] = st.session_state[key]
        del st.session_state[key]

# --- ARAYÜZ ---
st.title("📊 Profesyonel Analiz Terminali")

# ==========================================
# YATAY KONTROL PANELİ
# ==========================================
st.markdown("### ⚙️ Genel Ayarlar ve Filtre Seçimi")
ust_col1, ust_col2, ust_col3 = st.columns([1.5, 3, 0.5])

with ust_col1:
    bant_yuzdesi = st.number_input("🎯 Genel Olasılık Bandı (+/- %):", min_value=0.0, max_value=50.0, value=10.0, step=1.0)

with ust_col2:
    sutunlar = sutunlari_getir()
    secilen_sutunlar = st.multiselect("🔍 Filtrelemek istediğiniz sütunları seçin:", sutunlar, key="secilen_sutunlar_widget")

with ust_col3:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🧹 Sıfırla", use_container_width=True):
        for key in list(st.session_state.keys()):
            if key.startswith("filter_"):
                st.session_state[key] = None if "filter_" in key and not isinstance(st.session_state[key], list) else []
        st.rerun()

st.markdown("---")
aktif_filtreler = {}

if secilen_sutunlar:
    st.markdown("### 🎯 Filtre Değerleri")
    
    secilen_ulkeler_listesi = []
    
    sutun_genisligi = 4 
    for i in range(0, len(secilen_sutunlar), sutun_genisligi):
        cols = st.columns(sutun_genisligi)
        for j in range(sutun_genisligi):
            if i + j < len(secilen_sutunlar):
                sutun = secilen_sutunlar[i + j]
                with cols[j]:
                    if sutun == "Ülke":
                        ulkeler = benzersiz_degerleri_getir("Ülke")
                        secilen_ulkeler = st.multiselect("Sadece bu ülkelerin liglerini göster:", ulkeler, key="filter_ulke")
                        if secilen_ulkeler:
                            aktif_filtreler["Ülke"] = {'tip': 'kategori', 'deger': secilen_ulkeler}
                            secilen_ulkeler_listesi = secilen_ulkeler
                    
                    elif sutun == "Lig":
                        conn = sqlite3.connect(db_yolu)
                        ulke_lig_df = pd.read_sql_query("SELECT DISTINCT Ülke, Lig FROM maclar WHERE Lig IS NOT NULL AND Ülke IS NOT NULL", conn)
                        conn.close()
                        
                        ulke_lig_df['Kombine'] = ulke_lig_df['Ülke'] + ' - ' + ulke_lig_df['Lig']
                        tum_kombineler = ulke_lig_df['Kombine'].sort_values().tolist()
                        
                        if secilen_ulkeler_listesi:
                            tum_kombineler = ulke_lig_df[ulke_lig_df['Ülke'].isin(secilen_ulkeler_listesi)]['Kombine'].sort_values().tolist()
                            
                        secilen_ligler = st.multiselect("Lig Seçiniz (Ülke - Lig Kombinasyonu):", tum_kombineler, key="filter_lig")
                        
                        if secilen_ligler:
                            kardes_secili_mi = st.checkbox("🤝 Kardeş Ligleri Otomatik Dahil Et", value=False, key="kardes_check")
                            if kardes_secili_mi:
                                genisletilmis_ligler = akilli_kardes_bul(secilen_ligler, ulke_lig_df)
                                aktif_filtreler["Lig"] = {'tip': 'kombine', 'deger': genisletilmis_ligler}
                                st.caption(f"*(Yapay Zeka Devrede: Seçtiğiniz ligin oyun stiline tam uyan **{len(genisletilmis_ligler)}** kardeş lig taranıyor!)*")
                            else:
                                aktif_filtreler["Lig"] = {'tip': 'kombine', 'deger': secilen_ligler}
                            
                    elif sutun in METIN_SUTUNLARI and sutun not in ["Ülke", "Lig"]:
                        benzersizler = benzersiz_degerleri_getir(sutun)
                        secilen_metinler = st.multiselect(f"{sutun}:", benzersizler, key=f"filter_{sutun}")
                        if secilen_metinler:
                            aktif_filtreler[sutun] = {'tip': 'kategori', 'deger': secilen_metinler}
                    
                    elif sutun not in METIN_SUTUNLARI:
                        st.markdown(f"**{sutun}**")
                        
                        yontem = st.selectbox("Yöntem:", ["Bant (%)", "Büyüktür (>)", "Küçüktür (<)", "Eşittir (=)"], key=f"yontem_{sutun}", label_visibility="collapsed")
                        oran_girisi = st.number_input("Değer:", value=None, format="%.2f", placeholder="Oran Girin...", key=f"filter_{sutun}", label_visibility="collapsed")
                        
                        if oran_girisi is not None:
                            if yontem == "Bant (%)":
                                ozel_bant = st.number_input("↳ Bant (+/-%):", value=float(bant_yuzdesi), step=1.0, key=f"bant_{sutun}")
                                aktif_filtreler[sutun] = {'tip': 'oran', 'yontem': yontem, 'deger': oran_girisi, 'ozel_bant': ozel_bant}
                            else:
                                aktif_filtreler[sutun] = {'tip': 'oran', 'yontem': yontem, 'deger': oran_girisi}
    st.markdown("---")

# ==========================================
# 💾 ŞABLONLAR (FİLTRELERİM) SİSTEMİ
# ==========================================
with st.expander("💾 Şablonlarım (Filtre Kalıplarını Kaydet & Yükle)"):
    sablon_col1, sablon_col2 = st.columns(2)
    
    try:
        with open(sablon_dosyasi, "r", encoding="utf-8") as f:
            sablonlar_dict = json.load(f)
    except:
        sablonlar_dict = {}

    with sablon_col1:
        st.markdown("**📌 Sadece Kalıbı Kaydet (Oran Değerleri Hariç)**")
        yeni_sablon_adi = st.text_input("Şablon Adı:", placeholder="Örn: İY/MS Sistemi")
        if st.button("💾 Şablonu Kaydet"):
            if yeni_sablon_adi and secilen_sutunlar:
                sablon_yapisi = {}
                for s in secilen_sutunlar:
                    if s in METIN_SUTUNLARI:
                        sablon_yapisi[s] = {'tip': 'kategori'}
                    else:
                        sablon_yapisi[s] = {
                            'tip': 'oran',
                            'yontem': st.session_state.get(f"yontem_{s}", "Bant (%)"),
                            'bant': st.session_state.get(f"bant_{s}", float(bant_yuzdesi))
                        }
                sablonlar_dict[yeni_sablon_adi] = sablon_yapisi
                with open(sablon_dosyasi, "w", encoding="utf-8") as f:
                    json.dump(sablonlar_dict, f, ensure_ascii=False, indent=4)
                st.success(f"'{yeni_sablon_adi}' şablon kalıbı kaydedildi!")
                st.rerun()
            else:
                st.warning("Kaydetmek için bir isim yazmalı ve en az 1 sütun seçmiş olmalısınız.")
                
    with sablon_col2:
        st.markdown("**📂 Kayıtlı Kalıbı Yükle**")
        if sablonlar_dict:
            secilen_sablon = st.selectbox("Şablon Seç:", ["Seçiniz..."] + list(sablonlar_dict.keys()))
            
            btn_col_a, btn_col_b = st.columns(2)
            with btn_col_a:
                if st.button("🚀 Uygula") and secilen_sablon != "Seçiniz...":
                    yuklenecek = sablonlar_dict[secilen_sablon]
                    
                    st.session_state['update_sutunlar'] = list(yuklenecek.keys())
                    
                    for key in list(st.session_state.keys()):
                        if key.startswith("filter_"):
                            st.session_state[f"update_{key}"] = None 
                            
                    for s, d in yuklenecek.items():
                        if d['tip'] == 'oran':
                            if 'yontem' in d:
                                st.session_state[f"update_yontem_{s}"] = d['yontem']
                            if 'bant' in d:
                                st.session_state[f"update_bant_{s}"] = d['bant']
                    st.rerun()
                    
            with btn_col_b:
                if st.button("🗑️ Sil") and secilen_sablon != "Seçiniz...":
                    del sablonlar_dict[secilen_sablon]
                    with open(sablon_dosyasi, "w", encoding="utf-8") as f:
                        json.dump(sablonlar_dict, f, ensure_ascii=False, indent=4)
                    st.success("Şablon silindi!")
                    st.rerun()
        else:
            st.info("Henüz kayıtlı bir şablonunuz bulunmuyor.")

st.markdown("---")

# ==========================================
# AKILLI GÖRÜNÜM MOTORU
# ==========================================

if len(aktif_filtreler) == 0:
    st.info("ℹ️ **ARŞİV BEKLEME MODU:** Şu an herhangi bir filtre girmediğiniz için veritabanındaki son 1000 maç listeleniyor. Tablodan bir maça tıklayarak oranlarını inceleyebilir ve yukarıdaki filtrelere anında aktarabilirsiniz.")
    
    conn = sqlite3.connect(db_yolu)
    toplam_sayi_df = pd.read_sql_query("SELECT COUNT(*) as sayi FROM maclar", conn)
    toplam_mac = toplam_sayi_df['sayi'].iloc[0]
    
    df_tablo = pd.read_sql_query("SELECT * FROM maclar ORDER BY rowid DESC LIMIT 1000", conn)
    conn.close()
    
    st.metric("📦 Arşivdeki Toplam Maç", toplam_mac)
    
    gosterilecek_df = tarihi_yil_ay_gun_yap(df_tablo)
    
    if "Match ID" in gosterilecek_df.columns:
        gosterilecek_df["Maça Git"] = "https://arsiv.mackolik.com/Mac/" + gosterilecek_df["Match ID"].astype(str) + "/"
        sutun_sirasi = ["Maça Git"] + [col for col in gosterilecek_df.columns if col not in ["Maça Git", "Match ID"]]
        gosterilecek_df = gosterilecek_df[sutun_sirasi]
        
    st.markdown("##### 🔍 Tüm Zamanlar Arşivi (Son 1000 Maç)")
    secim_olayi = st.dataframe(
        gosterilecek_df, 
        column_config={"Maça Git": st.column_config.LinkColumn("🔗 Link", display_text="Detay")}, 
        use_container_width=True, 
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row"
    )
    
    secili_satirlar = secim_olayi.selection.rows
    if secili_satirlar:
        secili_index = secili_satirlar[0]
        secili_mac = gosterilecek_df.iloc[secili_index]
        
        st.success(f"📌 Seçilen Maç: **{secili_mac.get('Ev Sahibi', '')} vs {secili_mac.get('Deplasman', '')}**")
        st.markdown("Aşağıdaki butonlara tıklayarak o oranı **doğrudan filtrelere** aktarabilirsiniz:")
        
        btn_cols = st.columns(6)
        col_idx = 0
        for c_name, c_val in secili_mac.items():
            if c_name not in METIN_SUTUNLARI and c_name != "Maça Git":
                try:
                    num_val = float(str(c_val).replace(',', '.'))
                    if pd.notna(num_val):
                        with btn_cols[col_idx % 6]:
                            if st.button(f"➕ {c_name}\n{num_val:.2f}", key=f"add_{c_name}_{num_val}"):
                                mevcut_secilenler = st.session_state.get('secilen_sutunlar_widget', [])
                                if c_name not in mevcut_secilenler:
                                    st.session_state['update_sutunlar'] = mevcut_secilenler + [c_name]
                                
                                st.session_state[f"update_filter_{c_name}"] = num_val
                                st.rerun()
                        col_idx += 1
                except:
                    pass

else:
    sonuc_df = dinamik_analiz_yap(aktif_filtreler, bant_yuzdesi)
    sonuc_df = tarihi_yil_ay_gun_yap(sonuc_df)

    if not sonuc_df.empty:
        st.markdown("### 🚀 Analiz Sonuçları")
        m_col1, m_col2, m_col3 = st.columns(3)
        m_col1.metric("⚡ Bulunan Toplam Maç", len(sonuc_df))
        if "MS Toplam" in sonuc_df.columns:
            ort_gol = pd.to_numeric(sonuc_df["MS Toplam"], errors='coerce').mean()
            m_col2.metric("⚽ Ort. Gol", f"{ort_gol:.2f}")
        
        csv_data = csv_hazirla(sonuc_df)
        m_col3.download_button("📥 Tabloyu İndir (CSV)", data=csv_data, file_name="Analiz.csv", mime="text/csv", use_container_width=True)
        st.markdown("<br>", unsafe_allow_html=True)

        tab_iy, tab_iy_ev, tab_iy_dep, tab_ms, tab_ms_ev, tab_ms_dep, tab_diger = st.tabs([
            "⏱️ İY", "🏠 İY EV", "✈️ İY DEP", "🔥 MS", "🏠 MS EV", "✈️ MS DEP", "📌 DİĞER"
        ])

        gerekli_sutunlar = ["MS 1", "MS 2", "İY 1", "İY 2", "MS Toplam", "İY Toplam"]
        if all(col in sonuc_df.columns for col in gerekli_sutunlar):
            df_stat = sonuc_df.copy()
            for col in gerekli_sutunlar:
                df_stat[col] = pd.to_numeric(df_stat[col], errors='coerce')
            df_stat = df_stat.dropna(subset=gerekli_sutunlar)
            t = len(df_stat)

            if t > 0:
                with tab_ms:
                    cols_ms = pd.MultiIndex.from_tuples([("SONUÇ", "1"), ("SONUÇ", "0"), ("SONUÇ", "2"), ("0.5", "ALT"), ("0.5", "ÜST"), ("1.5", "ALT"), ("1.5", "ÜST"), ("2.5", "ALT"), ("2.5", "ÜST"), ("3.5", "ALT"), ("3.5", "ÜST"), ("4.5", "ALT"), ("4.5", "ÜST"), ("KG", "VAR"), ("KG", "YOK")])
                    row_ms = [yuzde_hesapla(df_stat["MS 1"] > df_stat["MS 2"], t), yuzde_hesapla(df_stat["MS 1"] == df_stat["MS 2"], t), yuzde_hesapla(df_stat["MS 1"] < df_stat["MS 2"], t), yuzde_hesapla(df_stat["MS Toplam"] < 0.5, t), yuzde_hesapla(df_stat["MS Toplam"] > 0.5, t), yuzde_hesapla(df_stat["MS Toplam"] < 1.5, t), yuzde_hesapla(df_stat["MS Toplam"] > 1.5, t), yuzde_hesapla(df_stat["MS Toplam"] < 2.5, t), yuzde_hesapla(df_stat["MS Toplam"] > 2.5, t), yuzde_hesapla(df_stat["MS Toplam"] < 3.5, t), yuzde_hesapla(df_stat["MS Toplam"] > 3.5, t), yuzde_hesapla(df_stat["MS Toplam"] < 4.5, t), yuzde_hesapla(df_stat["MS Toplam"] > 4.5, t), yuzde_hesapla((df_stat["MS 1"] > 0) & (df_stat["MS 2"] > 0), t), yuzde_hesapla((df_stat["MS 1"] == 0) | (df_stat["MS 2"] == 0), t)]
                    st.dataframe(pd.DataFrame([row_ms], columns=cols_ms, index=["Yüzde"]), use_container_width=True)

                with tab_iy:
                    cols_iy = pd.MultiIndex.from_tuples([("SONUÇ", "1"), ("SONUÇ", "0"), ("SONUÇ", "2"), ("0.5", "ALT"), ("0.5", "ÜST"), ("1.5", "ALT"), ("1.5", "ÜST"), ("2.5", "ALT"), ("2.5", "ÜST"), ("KG", "VAR"), ("KG", "YOK")])
                    row_iy = [yuzde_hesapla(df_stat["İY 1"] > df_stat["İY 2"], t), yuzde_hesapla(df_stat["İY 1"] == df_stat["İY 2"], t), yuzde_hesapla(df_stat["İY 1"] < df_stat["İY 2"], t), yuzde_hesapla(df_stat["İY Toplam"] < 0.5, t), yuzde_hesapla(df_stat["İY Toplam"] > 0.5, t), yuzde_hesapla(df_stat["İY Toplam"] < 1.5, t), yuzde_hesapla(df_stat["İY Toplam"] > 1.5, t), yuzde_hesapla(df_stat["İY Toplam"] < 2.5, t), yuzde_hesapla(df_stat["İY Toplam"] > 2.5, t), yuzde_hesapla((df_stat["İY 1"] > 0) & (df_stat["İY 2"] > 0), t), yuzde_hesapla((df_stat["İY 1"] == 0) | (df_stat["İY 2"] == 0), t)]
                    st.dataframe(pd.DataFrame([row_iy], columns=cols_iy, index=["Yüzde"]), use_container_width=True)

                cols_team = pd.MultiIndex.from_tuples([("0.5", "ALT"), ("0.5", "ÜST"), ("1.5", "ALT"), ("1.5", "ÜST"), ("2.5", "ALT"), ("2.5", "ÜST"), ("3.5", "ALT"), ("3.5", "ÜST")])
                with tab_ms_ev:
                    row_ms_ev = [yuzde_hesapla(df_stat["MS 1"] < 0.5, t), yuzde_hesapla(df_stat["MS 1"] > 0.5, t), yuzde_hesapla(df_stat["MS 1"] < 1.5, t), yuzde_hesapla(df_stat["MS 1"] > 1.5, t), yuzde_hesapla(df_stat["MS 1"] < 2.5, t), yuzde_hesapla(df_stat["MS 1"] > 2.5, t), yuzde_hesapla(df_stat["MS 1"] < 3.5, t), yuzde_hesapla(df_stat["MS 1"] > 3.5, t)]
                    st.dataframe(pd.DataFrame([row_ms_ev], columns=cols_team, index=["Yüzde"]), use_container_width=True)
                with tab_ms_dep:
                    row_ms_dep = [yuzde_hesapla(df_stat["MS 2"] < 0.5, t), yuzde_hesapla(df_stat["MS 2"] > 0.5, t), yuzde_hesapla(df_stat["MS 2"] < 1.5, t), yuzde_hesapla(df_stat["MS 2"] > 1.5, t), yuzde_hesapla(df_stat["MS 2"] < 2.5, t), yuzde_hesapla(df_stat["MS 2"] > 2.5, t), yuzde_hesapla(df_stat["MS 2"] < 3.5, t), yuzde_hesapla(df_stat["MS 2"] > 3.5, t)]
                    st.dataframe(pd.DataFrame([row_ms_dep], columns=cols_team, index=["Yüzde"]), use_container_width=True)
                
                with tab_iy_ev:
                    row_iy_ev = [yuzde_hesapla(df_stat["İY 1"] < 0.5, t), yuzde_hesapla(df_stat["İY 1"] > 0.5, t), yuzde_hesapla(df_stat["İY 1"] < 1.5, t), yuzde_hesapla(df_stat["İY 1"] > 1.5, t), yuzde_hesapla(df_stat["İY 1"] < 2.5, t), yuzde_hesapla(df_stat["İY 1"] > 2.5, t), "-", "-"]
                    st.dataframe(pd.DataFrame([row_iy_ev], columns=cols_team, index=["Yüzde"]), use_container_width=True)
                with tab_iy_dep:
                    row_iy_dep = [yuzde_hesapla(df_stat["İY 2"] < 0.5, t), yuzde_hesapla(df_stat["İY 2"] > 0.5, t), yuzde_hesapla(df_stat["İY 2"] < 1.5, t), yuzde_hesapla(df_stat["İY 2"] > 1.5, t), yuzde_hesapla(df_stat["İY 2"] < 2.5, t), yuzde_hesapla(df_stat["İY 2"] > 2.5, t), "-", "-"]
                    st.dataframe(pd.DataFrame([row_iy_dep], columns=cols_team, index=["Yüzde"]), use_container_width=True)

                with tab_diger:
                    d_col1, d_col2 = st.columns(2)
                    with d_col1:
                        st.markdown("##### ⚽ Toplam Gol Dağılımı")
                        df_toplam_gol = pd.DataFrame({
                            "Gol Sayısı": ["0-1 Gol", "2-3 Gol", "4-5 Gol", "6+ Gol"],
                            "Yüzde": [yuzde_hesapla(df_stat["MS Toplam"] <= 1, t), yuzde_hesapla((df_stat["MS Toplam"] >= 2) & (df_stat["MS Toplam"] <= 3), t), yuzde_hesapla((df_stat["MS Toplam"] >= 4) & (df_stat["MS Toplam"] <= 5), t), yuzde_hesapla(df_stat["MS Toplam"] >= 6, t)]
                        })
                        st.dataframe(df_toplam_gol, use_container_width=True, hide_index=True)
                    with d_col2:
                        st.markdown("##### 🔄 İY/MS Dağılımı")
                        if "İY/MS" in sonuc_df.columns:
                            iyms_dagilim = sonuc_df["İY/MS"].value_counts(normalize=True).head(9) * 100
                            df_iyms = pd.DataFrame({"İhtimal": iyms_dagilim.index, "Yüzde": [f"%{val:.1f}" for val in iyms_dagilim.values]})
                            st.dataframe(df_iyms, use_container_width=True, hide_index=True)
            else:
                st.warning("Eksik veri.")
        else:
            st.warning("Veritabanında eksik sütunlar var.")

        st.markdown("---")
        
        if "Match ID" in sonuc_df.columns:
            sonuc_df["Maça Git"] = "https://arsiv.mackolik.com/Mac/" + sonuc_df["Match ID"].astype(str) + "/"
            sutun_sirasi = ["Maça Git"] + [col for col in sonuc_df.columns if col not in ["Maça Git", "Match ID"]]
            sonuc_df = sonuc_df[sutun_sirasi]
        
        gosterilecek_df = sonuc_df.head(1000)
        
        st.markdown("##### 🔍 Filtrelenmiş Tablo (Satıra Tıklayarak Maç Oranlarını İnceleyebilirsiniz)")
        secim_olayi = st.dataframe(
            gosterilecek_df, 
            column_config={"Maça Git": st.column_config.LinkColumn("🔗 Link", display_text="Detay")}, 
            use_container_width=True, 
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row"
        )
        
        secili_satirlar = secim_olayi.selection.rows
        if secili_satirlar:
            secili_index = secili_satirlar[0]
            secili_mac = gosterilecek_df.iloc[secili_index]
            
            st.success(f"📌 Seçilen Maç: **{secili_mac.get('Ev Sahibi', '')} vs {secili_mac.get('Deplasman', '')}**")
            st.markdown("Aşağıdaki butonlara tıklayarak o oranı **doğrudan filtrelere** aktarabilirsiniz:")
            
            btn_cols = st.columns(6)
            col_idx = 0
            for c_name, c_val in secili_mac.items():
                if c_name not in METIN_SUTUNLARI and c_name != "Maça Git":
                    try:
                        num_val = float(str(c_val).replace(',', '.'))
                        if pd.notna(num_val):
                            with btn_cols[col_idx % 6]:
                                if st.button(f"➕ {c_name}\n{num_val:.2f}", key=f"add_{c_name}_{num_val}"):
                                    mevcut_secilenler = st.session_state.get('secilen_sutunlar_widget', [])
                                    if c_name not in mevcut_secilenler:
                                        st.session_state['update_sutunlar'] = mevcut_secilenler + [c_name]
                                    
                                    st.session_state[f"update_filter_{c_name}"] = num_val
                                    st.rerun()
                            col_idx += 1
                    except:
                        pass

    else:
        st.error("Girdiğiniz filtrelere uygun geçmiş maç bulunamadı.")
import sys
import os
import subprocess
import json
import zipfile
import streamlit as st
import pandas as pd
import sqlite3

# ==========================================
# 📦 BULUT İÇİN OTOMATİK ZİP AÇICI (292MB ÇÖZÜMÜ)
# ==========================================
# Eğer bilgisayarda değilsek (buluttaysak) zip'i açar
if not os.path.exists("arsiv.db") and os.path.exists("arsiv.zip"):
    with zipfile.ZipFile("arsiv.zip", 'r') as zip_ref:
        zip_ref.extractall(".")

# ==========================================
# AYARLAR (BULUT UYUMLU YOLLAR)
# ==========================================
db_yolu = "arsiv.db"
sablon_dosyasi = "sablonlar.json"
METIN_SUTUNLARI = ["Match ID", "Bülten Kodu", "Tarih", "Saat", "Ülke", "Lig", "Ev Sahibi", "Deplasman", "İY/MS"]

# Sayfa Konfigürasyonu
st.set_page_config(page_title="Tüm Zamanlar Analiz Merkezi", layout="wide", page_icon="🎯")

# ... (Buradan aşağısı mevcut analiz kodunla aynı devam edecek) ...
# (Önceki mesajdaki "Kusursuz ve Tam Sürüm" kodunun geri kalanını buraya ekleyebilirsin)
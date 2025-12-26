import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path

from Ana_Sayfa import COL_PROJE

# =================================================
# SAYFA AYARI
# =================================================
st.set_page_config(
    page_title="HUM | Maliyetler",
    page_icon="📊",
    layout="wide"
)

BASE_DIR = Path(__file__).resolve().parent.parent
EXCEL_PATH = BASE_DIR / "data" / "HUM_DATA2.xlsx"
LOGO_PATH = BASE_DIR / "hum_logo.png"

SHEET_COST = "ARPV_PROJE_MALIYET (2)"
SHEET_DIM  = "DIM_PROJELER1"

COL_COST = "PROJELERİN EURO MALİYET TUTARLARI"

# =================================================
# ✅ KPI İÇİN DIM KOLON İSİMLERİ (ANA SAYFA İLE AYNI)
# =================================================
COL_SIPARIS = "PROJE SİPARİŞ EURO TUTARLARI"
COL_SATIS   = "PROJE SATIŞ EURO TUTARLARI"
COL_MALIYET = "PROJE MALİYET EURO TUTARLARI"
COL_TAHSIL  = "PROJELERDE GELEN EURO ÖDEMELERİ TUTARI"

# =================================================
# FORMAT
# =================================================
def fmt_money(x: float) -> str:
    try:
        return f"{float(x):,.0f}".replace(",", "_").replace(".", ",").replace("_", ".")
    except:
        return str(x)

def to_number_tr(s: pd.Series) -> pd.Series:
    """
    Türkçe sayı formatlarını güvenli çevirir.
    Örnekler:
      "1.234.567,89" -> 1234567.89
      "123.456"      -> 123456
      "12,5"         -> 12.5
    """
    if s is None:
        return pd.Series(dtype="float")
    if pd.api.types.is_numeric_dtype(s):
        return s.fillna(0.0)

    s = s.astype(str).str.replace("\u00a0", " ", regex=False).str.strip()
    s = s.replace({"": None, "None": None, "nan": None, "NaN": None})

    # Parantez negatif (opsiyonel)
    s = s.str.replace(r"^\((.*)\)$", r"-\1", regex=True)

    # Sadece rakam , . - kalsın
    s = s.str.replace(r"[^\d,.\-]", "", regex=True)

    # Eğer hem nokta hem virgül varsa: genelde TR formatıdır (1.234,56)
    has_dot = s.str.contains(r"\.", regex=True, na=False)
    has_com = s.str.contains(r",", regex=True, na=False)

    # Binlik noktaları kaldır, virgülü noktaya çevir
    s.loc[has_dot & has_com] = (
        s.loc[has_dot & has_com]
        .str.replace(".", "", regex=False)
        .str.replace(",", ".", regex=False)
    )

    # Sadece virgül varsa: ondalık virgüldür
    s.loc[~has_dot & has_com] = s.loc[~has_dot & has_com].str.replace(",", ".", regex=False)

    # Sadece nokta varsa: zaten ondalık olabilir -> dokunma
    return pd.to_numeric(s, errors="coerce").fillna(0.0)

# =================================================
# ✅ KPI HESABI (ANA SAYFA İLE AYNI)
# =================================================
def hesapla_kpi(df_dim: pd.DataFrame) -> dict:
    sip = float(df_dim[COL_SIPARIS].sum()) if len(df_dim) else 0.0
    sat = float(df_dim[COL_SATIS].sum()) if len(df_dim) else 0.0
    mal = float(df_dim[COL_MALIYET].sum()) if len(df_dim) else 0.0
    tah = float(df_dim[COL_TAHSIL].sum()) if len(df_dim) else 0.0

    kar = sat - mal
    kar_orani = (kar / sat * 100) if sat else 0.0

    return {
        "proje_sayisi": int(df_dim["ProjeKodu"].nunique()) if "ProjeKodu" in df_dim.columns else 0,
        "siparis": sip,
        "satis": sat,
        "maliyet": mal,
        "tahsilat": tah,
        "kar": kar,
        "kar_orani": kar_orani
    }

# =================================================
# DATA LOAD
# =================================================
@st.cache_data(show_spinner=False)
def load_data():
    # FACT: Maliyet
    df_cost = pd.read_excel(EXCEL_PATH, sheet_name=SHEET_COST, engine="openpyxl")
    df_cost.columns = df_cost.columns.str.strip()

    # Kolon zorunlu kontrol
    required_cost = ["ProjeKodu", "MALIYET_TIPI", "STOK_ADI", "EKIPMAN_ADI", COL_COST]
    missing = [c for c in required_cost if c not in df_cost.columns]
    if missing:
        raise KeyError(f"{SHEET_COST} sayfasında eksik kolon(lar): {missing}")

    df_cost["ProjeKodu"] = df_cost["ProjeKodu"].astype(str).str.strip()
    df_cost[COL_COST] = to_number_tr(df_cost[COL_COST])

    # DIM: Şirket + Cari (sadece filtre için)
    df_dim = pd.read_excel(EXCEL_PATH, sheet_name=SHEET_DIM, engine="openpyxl")
    df_dim.columns = df_dim.columns.str.strip()

    # DIM kolon adları (senin dosyada şapkalı!)
    required_dim = ["ProjeKodu", "ŞİRKET", "CARİ İSİM"]
    missing_dim = [c for c in required_dim if c not in df_dim.columns]
    if missing_dim:
        raise KeyError(f"{SHEET_DIM} sayfasında eksik kolon(lar): {missing_dim}")

    df_dim = df_dim[required_dim].copy()
    df_dim["ProjeKodu"] = df_dim["ProjeKodu"].astype(str).str.strip()
    df_dim["ŞİRKET"] = df_dim["ŞİRKET"].astype(str).str.strip()
    df_dim["CARİ İSİM"] = df_dim["CARİ İSİM"].astype(str).str.strip()

    # 🔒 KRİTİK: DIM'i ProjeKodu bazında TEKİL yap
    df_dim = df_dim.dropna(subset=["ProjeKodu"])
    df_dim = df_dim.sort_values(["ProjeKodu"]).drop_duplicates(subset=["ProjeKodu"], keep="first")

    # JOIN: many-to-one olmalı (maliyet çok satır, dim tek satır)
    df = df_cost.merge(df_dim, on="ProjeKodu", how="left", validate="many_to_one")

    return df

df_raw = load_data()

# =================================================
# ÜST BAŞLIK + GÜNCELLE BUTONU
# =================================================
c1, c2 = st.columns([1, 6], vertical_alignment="center")
with c1:
    if LOGO_PATH.exists():
        st.image(str(LOGO_PATH), width=110)
with c2:
    st.markdown("## HUM | Maliyetler")
    st.caption("Proje / Şirket / Cari bazlı maliyet analizi")

st.sidebar.markdown("---")
if st.sidebar.button("🔄 Verileri Güncelle"):
    st.cache_data.clear()
    st.success("Veriler güncellendi")
    st.rerun()

st.divider()

# =================================================
# SIDEBAR – FİLTRELER
# =================================================
st.sidebar.markdown("### 🔎 Filtreler")

df = df_raw.copy()

sirket = st.sidebar.selectbox("Şirket", ["Tümü"] + sorted(df["ŞİRKET"].dropna().unique()))
if sirket != "Tümü":
    df = df[df["ŞİRKET"] == sirket]

cari = st.sidebar.selectbox("Cari", ["Tümü"] + sorted(df["CARİ İSİM"].dropna().unique()))
if cari != "Tümü":
    df = df[df["CARİ İSİM"] == cari]

maliyet_tipi = st.sidebar.selectbox("Maliyet Tipi", ["Tümü"] + sorted(df["MALIYET_TIPI"].dropna().unique()))
if maliyet_tipi != "Tümü":
    df = df[df["MALIYET_TIPI"] == maliyet_tipi]

# -------------------------------------------------
# PROJE KODU – İÇERENLERE GÖRE FİLTRE
# -------------------------------------------------
st.sidebar.markdown("### Proje Kodu (İçeren)")

proje_ara = st.sidebar.text_input(
    "Ara (örn: C25, 347, HUM)",
    placeholder="Proje kodu yaz..."
)

if proje_ara:
    df = df[
        df["ProjeKodu"]
        .astype(str)
        .str.contains(proje_ara, case=False, na=False)
    ]

proje_kodu = st.sidebar.selectbox("Proje Kodu", ["Tümü"] + sorted(df["ProjeKodu"].dropna().astype(str).unique()))
if proje_kodu != "Tümü":
    df = df[df["ProjeKodu"].astype(str) == str(proje_kodu)]

# =================================================
# KPI (ANA SAYFA İLE AYNI KPI SETİ - DIM'DEN)
# =================================================
@st.cache_data(show_spinner=False)
def load_dim_kpi():
    df_dim = pd.read_excel(EXCEL_PATH, sheet_name="DIM_PROJELER1", engine="openpyxl")
    df_dim.columns = df_dim.columns.str.strip()

    # Sayısal kolonlar
    for c in [COL_SIPARIS, COL_SATIS, COL_MALIYET, COL_TAHSIL]:
        if c in df_dim.columns:
            df_dim[c] = to_number_tr(df_dim[c])
        else:
            df_dim[c] = 0.0

    # Metin kolonlar
    for c in ["ProjeKodu", "ŞİRKET", "CARİ İSİM"]:
        if c in df_dim.columns:
            df_dim[c] = df_dim[c].astype(str).str.strip()

    return df_dim

df_dim_kpi = load_dim_kpi()

# Filtreleri DIM'e uygula (maliyet_tipi DIM'de yok → doğal olarak uygulanmıyor)
df_kpi = df_dim_kpi.copy()

if sirket != "Tümü":
    df_kpi = df_kpi[df_kpi["ŞİRKET"] == sirket]
if cari != "Tümü":
    df_kpi = df_kpi[df_kpi["CARİ İSİM"] == cari]
if proje_kodu != "Tümü":
    df_kpi = df_kpi[df_kpi["ProjeKodu"] == str(proje_kodu)]

kpi = hesapla_kpi(df_kpi)

# ✅ KPI GÖSTERİMİ (ANA SAYFA İLE AYNI)
k1, k2, k3, k4, k5, k6 = st.columns(6)
k1.metric("Proje Sayısı", kpi["proje_sayisi"])
k2.metric("Sipariş (€)", fmt_money(kpi["siparis"]))
k3.metric("Satış (€)", fmt_money(kpi["satis"]))
k4.metric("Maliyet (€)", fmt_money(kpi["maliyet"]))
k5.metric("Tahsilat (€)", fmt_money(kpi["tahsilat"]))
k6.metric("Kâr (€)", fmt_money(kpi["kar"]))

st.caption(f"💡 **Kâr Oranı:** {kpi['kar_orani']:.2f}%".replace(".", ","))

st.divider()

# =================================================
# PROJE TOPLAM MALİYET (GRAFİK VERİSİ)  -> COST SHEET'TEN
# =================================================
proj_chart = (
    df.groupby("ProjeKodu", as_index=False)
      .agg(Toplam_Maliyet=(COL_COST, "sum"))
      .sort_values("Toplam_Maliyet", ascending=False)
)

st.subheader("📊 En Yüksek Maliyete Sahip Projeler")

ROW_HEIGHT = 26
fig_height = max(500, len(proj_chart) * ROW_HEIGHT)

fig = px.bar(
    proj_chart,
    y="ProjeKodu",
    x="Toplam_Maliyet",
    orientation="h",
    text=proj_chart["Toplam_Maliyet"].apply(fmt_money)
)

fig.update_traces(
    marker_color="#c62828",
    textposition="outside",
    textfont_size=11,
    cliponaxis=False
)

fig.update_layout(
    height=fig_height,
    plot_bgcolor="white",
    yaxis=dict(autorange="reversed", title="", automargin=True),
    margin=dict(l=140, r=30, t=10, b=10),
    xaxis_title="Toplam Maliyet (€)"
)

with st.container(height=320):
    st.plotly_chart(fig, use_container_width=True)

# =================================================
# DETAY – PROJE SEÇ
# =================================================
st.markdown("### 🔍 Proje Seç (Detay için)")

secili_proje = st.selectbox("Proje", proj_chart["ProjeKodu"].astype(str).unique())
df_detay = df[df["ProjeKodu"].astype(str) == str(secili_proje)].copy()

st.markdown(f"### ⚙️ {secili_proje} – Ekipman Bazlı Maliyet Detayı")

st.dataframe(
    df_detay[[
        "EKIPMAN_ADI",
        "MALIYET_TIPI",
        "STOK_ADI",
        COL_COST
    ]].rename(columns={COL_COST: "Maliyet (€)"}),
    use_container_width=True,
    height=420
)


import streamlit as st
import pandas as pd
from pathlib import Path
import plotly.express as px

# =================================================
# SAYFA AYARI
# =================================================
st.set_page_config(
    page_title="HUM | Proje Genel Finansal Görünüm",
    page_icon="📊",
    layout="wide"
)

# =================================================
# DOSYA YOLLARI
# =================================================
BASE_DIR = Path(__file__).resolve().parent
EXCEL_PATH = BASE_DIR / "data" / "HUM_DATA2.xlsx"
LOGO_PATH = BASE_DIR / "hum_logo.png"
SHEET = "DIM_PROJELER1"

# =================================================
# KOLON İSİMLERİ
# =================================================
COL_PROJE   = "ProjeKodu"
COL_SIPARIS = "PROJE SİPARİŞ EURO TUTARLARI"
COL_SATIS   = "PROJE SATIŞ EURO TUTARLARI"
COL_MALIYET = "PROJE MALİYET EURO TUTARLARI"
COL_TAHSIL  = "PROJELERDE GELEN EURO ÖDEMELERİ TUTARI"
COL_SIRKET  = "ŞİRKET"
COL_CARI    = "CARİ İSİM"
COL_ULKE    = "ÜLKE ADI"
COL_TESLIM  = "SİPARİŞ TESLİM TARİHİ"
COL_ACIK    = "PROJE AÇIKLAMA"

# =================================================
# YARDIMCI
# =================================================
def to_num(s):
    if pd.api.types.is_numeric_dtype(s):
        return s.fillna(0)
    return (
        s.astype(str)
        .str.replace(".", "", regex=False)
        .str.replace(",", ".", regex=False)
        .str.replace(r"[^\d\-\.]", "", regex=True)
        .astype(float)
        .fillna(0)
    )

def money(x):
    return f"{x:,.0f}".replace(",", "_").replace(".", ",").replace("_", ".")

# =================================================
# DATA LOAD
# =================================================
@st.cache_data(show_spinner=False)
def load_data():
    df = pd.read_excel(EXCEL_PATH, sheet_name=SHEET)
    df.columns = df.columns.str.strip()

    for c in [COL_SIPARIS, COL_SATIS, COL_MALIYET, COL_TAHSIL]:
        df[c] = to_num(df[c])

    for c in [COL_PROJE, COL_SIRKET, COL_CARI, COL_ULKE]:
        df[c] = df[c].astype(str)

    df["KAR_EURO"] = df[COL_SATIS] - df[COL_MALIYET]
    df["KAR_ORANI"] = df.apply(
        lambda r: (r["KAR_EURO"] / r[COL_SATIS] * 100) if r[COL_SATIS] else 0,
        axis=1
    )

    if COL_TESLIM in df.columns:
        df[COL_TESLIM] = pd.to_datetime(df[COL_TESLIM], errors="coerce")

    return df

df = load_data()
df_f = df.copy()

# =================================================
# HEADER
# =================================================
c1, c2 = st.columns([1, 7])
with c1:
    if LOGO_PATH.exists():
        st.image(LOGO_PATH, width=120)
with c2:
    st.markdown("## **HUM | Proje Genel Finansal Görünüm**")
    st.caption("Sipariş – Satış – Maliyet – Tahsilat – Kâr")

st.divider()

# =================================================
# SIDEBAR
# =================================================
st.sidebar.markdown("### 🔎 Filtreler")

if st.sidebar.button("🔄 Verileri Güncelle", use_container_width=True):
    st.cache_data.clear()
    st.rerun()

def sb_filter(label, col):
    global df_f
    opts = ["Tümü"] + sorted(df_f[col].dropna().unique())
    val = st.sidebar.selectbox(label, opts)
    if val != "Tümü":
        df_f = df_f[df_f[col] == val]

sb_filter("Şirket", COL_SIRKET)
sb_filter("Cari", COL_CARI)
sb_filter("Ülke", COL_ULKE)

proje_ara = st.sidebar.text_input("Proje Kodu Ara")
if proje_ara:
    df_f = df_f[df_f[COL_PROJE].str.contains(proje_ara, case=False, na=False)]

sb_filter("Proje Kodu", COL_PROJE)

# =================================================
# KPI
# =================================================
k1, k2, k3, k4, k5, k6 = st.columns(6)

sip = df_f[COL_SIPARIS].sum()
sat = df_f[COL_SATIS].sum()
mal = df_f[COL_MALIYET].sum()
tah = df_f[COL_TAHSIL].sum()
kar = sat - mal
kor = (kar / sat * 100) if sat else 0

k1.metric("Proje Sayısı", df_f[COL_PROJE].nunique())
k2.metric("Sipariş (€)", money(sip))
k3.metric("Satış (€)", money(sat))
k4.metric("Maliyet (€)", money(mal))
k5.metric("Tahsilat (€)", money(tah))
k6.metric("Kâr (€)", money(kar))

st.caption(f"💡 **Kâr Oranı:** {kor:.2f}%".replace(".", ","))

st.divider()

# =================================================
# PROJE SİPARİŞ GRAFİĞİ (HOVER GELİŞTİRİLMİŞ)
# =================================================
st.subheader("📦 En Yüksek Sipariş Tutarına Sahip Projeler")

proj_chart = (
    df_f
    .groupby([COL_PROJE, COL_CARI], as_index=False)
    .agg(
        Toplam_Siparis=(COL_SIPARIS, "sum"),
        Toplam_Satis=(COL_SATIS, "sum"),
        Toplam_Maliyet=(COL_MALIYET, "sum"),
        Toplam_Tahsilat=(COL_TAHSIL, "sum")
    )
    .sort_values("Toplam_Siparis", ascending=False)
)

ROW_HEIGHT = 26
fig_height = max(500, len(proj_chart) * ROW_HEIGHT)

fig = px.bar(
    proj_chart,
    y=COL_PROJE,
    x="Toplam_Siparis",
    orientation="h",
    text=proj_chart["Toplam_Siparis"].apply(money),
    custom_data=[
        COL_CARI,
        "Toplam_Satis",
        "Toplam_Maliyet",
        "Toplam_Tahsilat"
    ]
)

fig.update_traces(
    marker_color="#1f77b4",
    textposition="outside",
    textfont_size=13,
    hovertemplate=
        "<b>Proje:</b> %{y}<br>"
        "<b>Cari:</b> %{customdata[0]}<br><br>"
        "📦 Sipariş: %{x:,.0f} €<br>"
        "💰 Satış: %{customdata[1]:,.0f} €<br>"
        "🧾 Maliyet: %{customdata[2]:,.0f} €<br>"
        "🏦 Tahsilat: %{customdata[3]:,.0f} €<br>"
        "<extra></extra>"
)

fig.update_layout(
    height=fig_height,
    plot_bgcolor="white",
    yaxis=dict(autorange="reversed", title=""),
    margin=dict(l=140, r=40, t=10, b=10),
    xaxis_title="Sipariş Tutarı (€)"
)

with st.container(height=340):
    st.plotly_chart(fig, use_container_width=True)
# =================================================
# CARİ SATIŞ GRAFİĞİ
# =================================================
st.subheader("💼 Carilerin Satış Tutarları")

cari_chart = (
    df_f.groupby(COL_CARI, as_index=False)[COL_SATIS]
        .sum()
        .sort_values(COL_SATIS, ascending=False)
        .rename(columns={COL_SATIS: "Toplam_Satis"})
)

ROW_HEIGHT = 26
fig_height = max(500, len(cari_chart) * ROW_HEIGHT)

fig2 = px.bar(
    cari_chart,
    y=COL_CARI,
    x="Toplam_Satis",
    orientation="h",
    text=cari_chart["Toplam_Satis"].apply(money)
)

fig2.update_traces(
    marker_color="#2ca02c",
    textposition="outside",
    textfont_size=13
)

fig2.update_layout(
    height=fig_height,
    plot_bgcolor="white",
    yaxis=dict(autorange="reversed", title=""),
    margin=dict(l=220, r=40, t=10, b=10),
    xaxis_title="Satış Tutarı (€)"
)

with st.container(height=340):
    st.plotly_chart(fig2, use_container_width=True)

# =================================================
# DETAY TABLO
# =================================================
st.subheader("📋 Proje Detayları")

st.dataframe(
    df_f[
        [
            COL_PROJE,
            COL_CARI,
            COL_SIRKET,
            COL_ULKE,
            COL_SIPARIS,
            COL_SATIS,
            COL_MALIYET,
            COL_TAHSIL,
            "KAR_EURO",
            "KAR_ORANI",
            COL_TESLIM,
            COL_ACIK,
        ]
    ],
    use_container_width=True,
    height=520
)
import streamlit.components.v1 as components

st.markdown("### 🧾 Yeni Eklenen Projeler")

son_projeler = (
    df_f[
        df_f[COL_SIRKET].notna() &
        (df_f[COL_SIRKET].str.strip() != "") &
        (df_f[COL_SIRKET].str.lower() != "nan")
    ]
    .tail(3)
)


html = "<div style='display:flex; gap:24px;'>"

for _, row in son_projeler.iterrows():
    html += f"""
    <div style="
        flex:1;
        background:#ffffff;
        padding:20px;
        border-radius:16px;
        box-shadow:0 8px 22px rgba(0,0,0,0.08);
        border-left:6px solid #0A66C2;
        font-family:Arial, sans-serif;
    ">
        <div style="font-size:16px; font-weight:700; margin-bottom:6px;">
            📦 {row[COL_PROJE]}
        </div>

        <div style="font-size:13px; color:#555; margin-bottom:14px;">
            👤 {row[COL_CARI]}
        </div>

        <div style="font-size:13px; line-height:1.8; color:#333;">
            🧾 <b>Sipariş:</b> € {money(row[COL_SIPARIS])}<br>
            💰 <b>Satış:</b> € {money(row[COL_SATIS])}<br>
            🧮 <b>Maliyet:</b> € {money(row[COL_MALIYET])}<br>
            🏦 <b>Tahsilat:</b> € {money(row[COL_TAHSIL])}
        </div>
    </div>
    """

html += "</div>"

components.html(html, height=260)

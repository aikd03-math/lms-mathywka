import pandas as pd
import streamlit as st

# ==========================================
# 1. KONEKSI SPREADSHEET 3 KELAS
# ==========================================
SPREADSHEET_ID = "1D_1VYbIu6qLTySkpPpxdNon_zmkgtY6ZMXOqK4MDGMs"
SHEETS = ["Kelas 7", "Kelas 8", "Kelas 9"]


@st.cache_data(ttl=60)
def load_all_data():
    all_students = []

    for sheet in SHEETS:
        # Fetch data CSV untuk tiap tab kelas
        url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/gviz/tq?tqx=out:csv&sheet={sheet.replace(' ', '%20')}"
        try:
            df_raw = pd.read_csv(url)

            # Rapikan header ganda pada Google Sheets jika ada
            if (
                "Induk" in df_raw.iloc[0].values
                or "Nama Siswa" in df_raw.iloc[0].values
            ):
                df_raw.columns = df_raw.iloc[0]
                df_raw = df_raw[1:].reset_index(drop=True)

            # Identifikasi kolom utama
            nis_col = next(
                (c for c in df_raw.columns if "Induk" in str(c) or "NIS" in str(c)),
                None,
            )
            nama_col = next(
                (c for c in df_raw.columns if "Nama" in str(c)), None
            )

            if not nis_col or not nama_col:
                continue

            # Standardisasi Nama & NIS
            df = df_raw.copy()
            df = df.rename(columns={nis_col: "NIS", nama_col: "Nama"})
            df["Kelas"] = sheet
            df["NIS"] = (
                df["NIS"]
                .astype(str)
                .str.replace(".0", "", regex=False)
                .str.strip()
            )
            df["Nama"] = df["Nama"].astype(str).str.strip()

            # Filter baris data siswa yang valid
            df = df[
                (df["NIS"].str.len() > 0)
                & (df["Nama"].str.len() > 0)
                & (df["NIS"] != "nan")
            ]

            # Deteksi kolom nilai/ulangan (selain kolom identitas)
            kolom_abaikan = [
                "Urt.",
                "Nomor",
                "NIS",
                "NISN",
                "Nama",
                "Nama Siswa",
                "L/P",
                "Kelas",
            ]
            kolom_nilai = [
                c for c in df.columns if str(c).strip() not in kolom_abaikan
            ]

            # Konversi kolom nilai ke angka (numeric)
            for col in kolom_nilai:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

            # Hitung Total Rata-rata (To)
            if kolom_nilai:
                df["Total_Rata"] = df[kolom_nilai].mean(axis=1).round(2)
            else:
                df["Total_Rata"] = 0.0

            # Hitung Peringkat se-kelas untuk tiap ulangan dan Total
            for col in kolom_nilai:
                df[f"Peringkat_{col}"] = (
                    df[col].rank(ascending=False, method="min").astype(int)
                )

            df["Peringkat_Total_Rata"] = (
                df["Total_Rata"]
                .rank(ascending=False, method="min")
                .astype(int)
            )

            all_students.append(df)
        except Exception as e:
            st.warning(f"Gagal membaca data {sheet}: {e}")

    if all_students:
        return pd.concat(all_students, ignore_index=True)
    return pd.DataFrame()


# Load Data
try:
    df_all = load_all_data()
except Exception as e:
    st.error("Terjadi kesalahan saat memuat data dari Google Sheets.")
    st.stop()

# Config Halaman
st.set_page_config(page_title="LMS Math", page_icon="📐", layout="centered")

# State Navigasi Laman (1, 2, atau 3)
if "laman" not in st.session_state:
    st.session_state.laman = 1
if "siswa_login" not in st.session_state:
    st.session_state.siswa_login = None
if "pilihan_ulangan" not in st.session_state:
    st.session_state.pilihan_ulangan = None


# ==========================================
# LAMAN 1: LOGIN (LMS Math)
# ==========================================
if st.session_state.laman == 1:
    st.title("📐 LMS Math")
    st.write("---")

    with st.form("form_login"):
        nama_input = st.text_input("Nama Lengkap")
        nis_input = st.text_input("NIS (Nomor Induk)")
        submit = st.form_submit_button("Masuk")

        if submit:
            if df_all.empty:
                st.error("Data siswa tidak ditemukan di Google Sheets.")
            else:
                # Pencarian case-insensitive pada NIS dan Nama
                match = df_all[
                    (df_all["NIS"].str.strip() == nis_input.strip())
                    & (
                        df_all["Nama"].str.lower().str.strip()
                        == nama_input.strip().lower()
                    )
                ]

                if not match.empty:
                    st.session_state.siswa_login = match.iloc[0]
                    st.session_state.laman = 2  # Lanjut ke Laman 2
                    st.rerun()
                else:
                    st.error("Nama atau NIS tidak ditemukan / tidak cocok!")


# ==========================================
# LAMAN 2: PEROLEHAN NILAI ULANGAN
# ==========================================
elif st.session_state.laman == 2:
    siswa = st.session_state.siswa_login

    st.title("Perolehan Nilai Ulangan")
    st.caption(
        f"👤 Siswa: **{siswa['Nama']}** | 🆔 NIS: **{siswa['NIS']}** | 🏫"
        f" **{siswa['Kelas']}**"
    )
    st.write("---")
    st.write("Klik tombol ulangan di bawah untuk melihat detail nilai:")

    # Ambil kolom-kolom ulangan yang tersedia
    kolom_abaikan = [
        "Urt.",
        "Nomor",
        "NIS",
        "NISN",
        "Nama",
        "Nama Siswa",
        "L/P",
        "Kelas",
        "Total_Rata",
    ]
    daftar_ulangan = [
        c
        for c in siswa.index
        if c not in kolom_abaikan and not c.startswith("Peringkat_")
    ]

    # Tampilkan tombol per ulangan + tombol Total Rata-rata (To)
    semua_tombol = daftar_ulangan + ["Total_Rata"]
    cols = st.columns(len(semua_tombol))

    for idx, key_ulangan in enumerate(semua_tombol):
        label_tombol = "To" if key_ulangan == "Total_Rata" else key_ulangan
        with cols[idx]:
            if st.button(label_tombol, key=f"btn_{idx}", use_container_width=True):
                st.session_state.pilihan_ulangan = key_ulangan
                st.session_state.laman = 3
                st.rerun()

    st.write("---")
    if st.button("🚪 Keluar / Logout"):
        st.session_state.laman = 1
        st.session_state.siswa_login = None
        st.rerun()


# ==========================================
# LAMAN 3: DETAIL NILAI & PERINGKAT
# ==========================================
elif st.session_state.laman == 3:
    siswa = st.session_state.siswa_login
    pilihan = st.session_state.pilihan_ulangan

    nilai_ulangan = siswa[pilihan]
    peringkat = siswa[f"Peringkat_{pilihan}"]

    # Hitung total siswa di kelas yang sama
    total_siswa_sekelas = len(df_all[df_all["Kelas"] == siswa["Kelas"]])

    judul_tampilan = (
        "Total Rata-Rata Nilai" if pilihan == "Total_Rata" else pilihan
    )

    st.title(f"📝 {judul_tampilan}")
    st.caption(f"Kelas: **{siswa['Kelas']}**")
    st.write("---")

    # Tampilan Dua Kotak Sesuai Gambar Sketsa (Laman 3)
    col_nilai, col_peringkat = st.columns(2)

    with col_nilai:
        st.metric(label="Nilai", value=f"{nilai_ulangan}")
        st.caption("Nilai ulangan pribadi")

    with col_peringkat:
        st.metric(
            label="Peringkat",
            value=f"Peringkat {peringkat} / {total_siswa_sekelas}",
        )
        st.caption("Se-angkatan / se-kelas")

    st.write("---")
    if st.button("⬅️ Kembali ke Perolehan Nilai"):
        st.session_state.laman = 2
        st.rerun()
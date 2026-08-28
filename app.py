import pandas as pd
import streamlit as st

# ==========================================
# 1. KONFIGURASI NAMA PORTAL & SPREADSHEET
# ==========================================
NAMA_PORTAL = "Leaderboard Math SMP YWKA Bandung"
SPREADSHEET_ID = "1D_1VYbIu6qLTySkpPpxdNon_zmkgtY6ZMXOqK4MDGMs"
SHEETS = ["KELAS 7", "KELAS 8", "KELAS 9"]


@st.cache_data(ttl=60)
def load_all_data():
    all_students = []

    for sheet_name in SHEETS:
        url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/gviz/tq?tqx=out:csv&sheet={sheet_name.replace(' ', '%20')}"
        try:
            # Baca CSV tanpa baris header
            df_raw = pd.read_csv(url, header=None)

            # Cari baris pertama tempat data siswa dimulai (misal Induk bernilai angka 9 digit)
            data_start_idx = None
            for idx, row in df_raw.iterrows():
                val_col1 = str(row[1]).strip()
                if val_col1.isdigit() and len(val_col1) >= 6:
                    data_start_idx = idx
                    break

            if data_start_idx is None:
                continue

            # Ambil baris header di atas data siswa untuk mengambil judul ulangan
            header_rows = df_raw.iloc[:data_start_idx]

            # Pemetaan kolom berdasarkan posisi indeks
            col_names = []
            for c_idx in range(df_raw.shape[1]):
                if c_idx == 1:
                    col_names.append("NIS")
                elif c_idx == 3:
                    col_names.append("Nama")
                elif c_idx >= 5:
                    # Ambil nama ulangan dari baris header di kolom ini
                    h_vals = [
                        str(v).strip()
                        for v in header_rows[c_idx].values
                        if pd.notna(v)
                        and str(v).strip() != ""
                        and "Pertemuan" not in str(v)
                        and "Unnamed" not in str(v)
                        and "nan" not in str(v)
                    ]
                    if h_vals:
                        col_names.append(h_vals[-1])
                    else:
                        col_names.append(f"Ulangan_{c_idx-4}")
                else:
                    col_names.append(f"Ignored_{c_idx}")

            # Ambil hanya baris data siswa
            df_data = df_raw.iloc[data_start_idx:].copy()
            df_data.columns = col_names
            df_data["Kelas"] = sheet_name.title()

            # Pembersihan Format NIS & Nama
            df_data["NIS"] = (
                df_data["NIS"]
                .astype(str)
                .str.replace(".0", "", regex=False)
                .str.strip()
            )
            df_data["Nama"] = df_data["Nama"].astype(str).str.strip()

            # Filter daftar kolom ulangan murni
            kolom_nilai = [
                c
                for c in col_names
                if c not in ["NIS", "Nama", "Kelas"]
                and not c.startswith("Ignored_")
            ]

            # Konversi nilai ke angka
            for col in kolom_nilai:
                df_data[col] = pd.to_numeric(
                    df_data[col], errors="coerce"
                ).fillna(0)

            # Hitung Total Rata-Rata (To)
            if kolom_nilai:
                df_data["Total_Rata"] = df_data[kolom_nilai].mean(
                    axis=1
                ).round(1)
            else:
                df_data["Total_Rata"] = 0.0

            # Hitung Peringkat se-kelas
            for col in kolom_nilai:
                df_data[f"Peringkat_{col}"] = (
                    df_data[col]
                    .rank(ascending=False, method="min")
                    .astype(int)
                )

            df_data["Peringkat_Total_Rata"] = (
                df_data["Total_Rata"]
                .rank(ascending=False, method="min")
                .astype(int)
            )

            all_students.append(df_data)
        except Exception:
            continue

    if all_students:
        return pd.concat(all_students, ignore_index=True)
    return pd.DataFrame()


# Load Data
df_all = load_all_data()

# Konfigurasi Tampilan
st.set_page_config(page_title=NAMA_PORTAL, page_icon="📐", layout="centered")

# Managing State Navigasi Laman (1, 2, atau 3)
if "laman" not in st.session_state:
    st.session_state.laman = 1
if "siswa_login" not in st.session_state:
    st.session_state.siswa_login = None
if "pilihan_ulangan" not in st.session_state:
    st.session_state.pilihan_ulangan = None


# ==========================================
# LAMAN 1: LOGIN
# ==========================================
if st.session_state.laman == 1:
    st.title(f"📐 Mathematics Leaderboard SMP YWKA Bandung")
    st.caption("Masukkan Nama Lengkap dan Nomor Induk (NIS) siswa")
    st.divider()

    with st.form("form_login"):
        nama_input = st.text_input("Nama Lengkap")
        nis_input = st.text_input("Nomor Induk (NIS / Induk)")
        submit = st.form_submit_button("Masuk ke Portal")

        if submit:
            if df_all.empty:
                st.error(
                    "Gagal membaca data dari Google Sheets. Pastikan akses"
                    " berbagi sudah diset ke 'Siapa saja yang memiliki link'."
                )
            else:
                match = df_all[
                    (df_all["NIS"].str.strip() == nis_input.strip())
                    & (
                        df_all["Nama"].str.lower().str.strip()
                        == nama_input.strip().lower()
                    )
                ]

                if not match.empty:
                    st.session_state.siswa_login = match.iloc[0]
                    st.session_state.laman = 2
                    st.rerun()
                else:
                    st.error("Nama atau Nomor Induk tidak cocok / ditemukan!")


# ==========================================
# LAMAN 2: PEROLEHAN NILAI ULANGAN
# ==========================================
elif st.session_state.laman == 2:
    siswa = st.session_state.siswa_login

    st.title("Perolehan Nilai Ulangan")
    st.markdown(
        f"👤 **{siswa['Nama']}** | 🆔 Nomor Induk: **{siswa['NIS']}** | 🏫"
        f" **{siswa['Kelas']}**"
    )
    st.divider()

    # Dapatkan daftar kolom ulangan + Total Rata-rata
    daftar_ulangan = [
        c
        for c in siswa.index
        if c not in ["NIS", "Nama", "Kelas"]
        and not str(c).startswith("Ignored_")
        and not str(c).startswith("Peringkat_")
    ]

    st.write("Pilih salah satu menu di bawah ini:")

    n_cols = min(len(daftar_ulangan), 4)
    cols = st.columns(n_cols if n_cols > 0 else 1)

    for idx, key_ulangan in enumerate(daftar_ulangan):
        label_tampil = (
            "Total Rata2 (To)" if key_ulangan == "Total_Rata" else key_ulangan
        )
        col_idx = idx % n_cols
        with cols[col_idx]:
            if st.button(
                label_tampil, key=f"btn_{idx}", use_container_width=True
            ):
                st.session_state.pilihan_ulangan = key_ulangan
                st.session_state.laman = 3
                st.rerun()

    st.divider()
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
    total_siswa_sekelas = len(df_all[df_all["Kelas"] == siswa["Kelas"]])

    judul_tampilan = (
        "Total Rata-Rata Nilai" if pilihan == "Total_Rata" else pilihan
    )

    st.title(f"📝 {judul_tampilan}")
    st.caption(f"Laporan Evaluasi: {siswa['Nama']} ({siswa['Kelas']})")
    st.divider()

    col_nilai, col_peringkat = st.columns(2)

    with col_nilai:
        st.metric(label="Nilai Ulangan", value=f"{nilai_ulangan}")
        st.caption("Nilai ulangan pribadi")

    with col_peringkat:
        st.metric(
            label="Peringkat",
            value=f"Ke-{peringkat} dari {total_siswa_sekelas}",
        )
        st.caption(f"Posisi di {siswa['Kelas']}")

    st.divider()
    if st.button("⬅️ Kembali ke Perolehan Nilai"):
        st.session_state.laman = 2
        st.rerun()

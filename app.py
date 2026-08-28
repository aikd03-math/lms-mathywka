import pandas as pd
import streamlit as st

# ==========================================
# 1. KONFIGURASI NAMA PORTAL & SPREADSHEET
# ==========================================
NAMA_PORTAL = "Portal Nilai Siswa"
SPREADSHEET_ID = "1D_1VYbIu6qLTySkpPpxdNon_zmkgtY6ZMXOqK4MDGMs"
SHEETS = ["KELAS 7", "KELAS 8", "KELAS 9"]

# Daftar nama kolom non-ulangan yang disaring dari tombol
KOLOM_NON_ULANGAN = [
    "Urt.",
    "Nomor",
    "Induk",
    "NISN",
    "Nama",
    "Nama Siswa",
    "L/P",
    "Kelas",
    "Total_Rata",
    "Pertemuan ke …….",
    "Pertemuan ke .......",
]


@st.cache_data(ttl=60)
def load_all_data():
    all_students = []

    for sheet_name in SHEETS:
        url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/gviz/tq?tqx=out:csv&sheet={sheet_name.replace(' ', '%20')}"
        try:
            df_raw = pd.read_csv(url, header=None)

            # Cari baris yang memuat nama kolom utama
            idx_header = None
            for idx, row in df_raw.iterrows():
                row_items = [str(x).strip() for x in row.values]
                if (
                    "Induk" in row_items
                    or "NISN" in row_items
                    or "Nama Siswa" in row_items
                ):
                    idx_header = idx
                    break

            if idx_header is not None:
                # Ambil gabungan teks header jika ada gabungan sel
                header_row_1 = [
                    str(x).strip() if pd.notna(x) else ""
                    for x in df_raw.iloc[
                        idx_header - 1 if idx_header > 0 else idx_header
                    ].values
                ]
                header_row_2 = [
                    str(x).strip() if pd.notna(x) else ""
                    for x in df_raw.iloc[idx_header].values
                ]

                # Tentukan nama kolom terbaik
                final_headers = []
                for h1, h2 in zip(header_row_1, header_row_2):
                    if h2 and h2 != "nan" and not h2.startswith("Unnamed"):
                        final_headers.append(h2)
                    elif h1 and h1 != "nan" and not h1.startswith("Unnamed"):
                        final_headers.append(h1)
                    else:
                        final_headers.append("Unknown")

                df = df_raw.iloc[idx_header + 1 :].copy()
                df.columns = final_headers
            else:
                df = df_raw.copy()

            # Deteksi Kolom Induk/NIS dan Nama Siswa
            col_nis = next(
                (
                    c
                    for c in df.columns
                    if "Induk" in str(c) or "NIS" in str(c) or "NISN" in str(c)
                ),
                None,
            )
            col_nama = next(
                (
                    c
                    for c in df.columns
                    if "Nama" in str(c) or "Siswa" in str(c)
                ),
                None,
            )

            if not col_nis or not col_nama:
                continue

            # Standardisasi kolom
            df = df.rename(columns={col_nis: "NIS", col_nama: "Nama"})
            df["Kelas"] = sheet_name.title()  # e.g. Kelas 7

            # Pembersihan Format NIS dan Nama
            df["NIS"] = (
                df["NIS"]
                .astype(str)
                .str.replace(".0", "", regex=False)
                .str.strip()
            )
            df["Nama"] = df["Nama"].astype(str).str.strip()

            # Hapus baris data kosong atau header tersisa
            df = df[
                (df["NIS"].str.len() > 0)
                & (df["Nama"].str.len() > 0)
                & (df["NIS"] != "nan")
                & (df["Nama"] != "nan")
                & (df["NIS"] != "Induk")
            ]

            # Identifikasi kolom ulangan/nilai murni
            kolom_nilai = []
            for col in df.columns:
                c_str = str(col).strip()
                if (
                    c_str not in KOLOM_NON_ULANGAN
                    and not c_str.startswith("Unnamed")
                    and "Pertemuan" not in c_str
                    and c_str != "Unknown"
                ):
                    kolom_nilai.append(col)

            # Konversi nilai ke tipe numerik
            for col in kolom_nilai:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

            # Hitung Total Rata-Rata (To)
            if kolom_nilai:
                df["Total_Rata"] = df[kolom_nilai].mean(axis=1).round(1)
            else:
                df["Total_Rata"] = 0.0

            # Hitung Peringkat se-kelas
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
        except Exception:
            continue

    if all_students:
        return pd.concat(all_students, ignore_index=True)
    return pd.DataFrame()


# Memuat data dari Google Sheets
df_all = load_all_data()

# Konfigurasi Halaman Streamlit
st.set_page_config(page_title=NAMA_PORTAL, page_icon="📖", layout="centered")

# Mengelola Session Navigasi Laman (1, 2, atau 3)
if "laman" not in st.session_state:
    st.session_state.laman = 1
if "siswa_login" not in st.session_state:
    st.session_state.siswa_login = None
if "pilihan_ulangan" not in st.session_state:
    st.session_state.pilihan_ulangan = None


# ==========================================
# LAMAN 1: LOGIN (SKETSA LAMAN 1)
# ==========================================
if st.session_state.laman == 1:
    st.title(f"📖 {MATEMATIKA SMP YWKA BANDUNG}")
    st.caption("Masukkan Nama Lengkap dan Nomor Induk (NIS) siswa")
    st.divider()

    with st.form("form_login"):
        nama_input = st.text_input("Nama Lengkap")
        nis_input = st.text_input("Nomor Induk (NIS / Induk)")
        submit = st.form_submit_button("Masuk ke Portal")

        if submit:
            if df_all.empty:
                st.error("Gagal membaca data dari Google Sheets.")
            else:
                # Mencari data siswa
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
                    st.error("Nama atau Nomor Induk tidak cocok/ditemukan!")


# ==========================================
# LAMAN 2: PEROLEHAN NILAI ULANGAN (SKETSA LAMAN 2)
# ==========================================
elif st.session_state.laman == 2:
    siswa = st.session_state.siswa_login

    st.title("Perolehan Nilai Ulangan")
    st.markdown(
        f"👤 **{siswa['Nama']}** | 🆔 Nomor Induk: **{siswa['NIS']}** | 🏫"
        f" **{siswa['Kelas']}**"
    )
    st.divider()

    # Dapatkan daftar kolom ulangan murni + Total Rata-rata
    daftar_ulangan = [
        c
        for c in siswa.index
        if c not in KOLOM_NON_ULANGAN
        and not str(c).startswith("Peringkat_")
        and not str(c).startswith("Unnamed")
        and "Pertemuan" not in str(c)
    ]

    st.write("Pilih salah satu menu di bawah ini:")

    # Menampilkan grid tombol secara simetris
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
# LAMAN 3: DETAIL NILAI & PERINGKAT (SKETSA LAMAN 3)
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

    # Tampilan Kotak Nilai dan Peringkat Sesuai Sketsa
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

import re
import pandas as pd
import streamlit as st

# ==========================================
# 1. KONFIGURASI SPREADSHEET
# ==========================================
NAMA_PORTAL = "Leaderboard Math SMP YWKA Bandung"
SPREADSHEET_ID = "1D_1VYbIu6qLTySkpPpxdNon_zmkgtY6ZMXOqK4MDGMs"
SHEETS = ["KELAS 7", "KELAS 8", "KELAS 9"]


@st.cache_data(ttl=30)
def load_all_data():
    all_students = []

    for sheet_name in SHEETS:
        # Menggunakan format URL ekspor CSV resmi dari Google Sheets
        url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&sheet={sheet_name.replace(' ', '%20')}"

        try:
            df_raw = pd.read_csv(url, header=None, dtype=str)

            if df_raw.empty or df_raw.shape[1] < 4:
                continue

            # Cari baris tempat header utama (Induk / NISN / Nama) berada
            header_idx = None
            for idx, row in df_raw.iterrows():
                row_str = " ".join([str(x) for x in row.values if pd.notna(x)])
                if (
                    "Induk" in row_str
                    or "NISN" in row_str
                    or "Nama" in row_str
                ):
                    header_idx = idx
                    break

            if header_idx is None:
                continue

            # Ambil data setelah baris header
            df_data = df_raw.iloc[header_idx + 1 :].copy()
            headers = [
                str(h).strip() if pd.notna(h) else ""
                for h in df_raw.iloc[header_idx].values
            ]

            # Cari indeks kolom NIS (Induk/NISN) dan Nama
            nis_col_idx = None
            nama_col_idx = None

            for i, h in enumerate(headers):
                if any(k in h for k in ["Induk", "NIS", "NISN"]) and (
                    nis_col_idx is None
                ):
                    nis_col_idx = i
                elif "Nama" in h and (nama_col_idx is None):
                    nama_col_idx = i

            # Jika tidak terdeteksi via header, gunakan standar posisi kolom (Col 1: NIS, Col 3: Nama)
            if nis_col_idx is None:
                nis_col_idx = 1
            if nama_col_idx is None:
                nama_col_idx = 3

            # Ambil daftar kolom ulangan (mulai dari kolom setelah nama)
            ulangan_cols = {}
            for i in range(nama_col_idx + 1, df_raw.shape[1]):
                col_name = headers[i] if i < len(headers) else ""
                if not col_name or col_name == "nan" or "L/P" in col_name:
                    # Cek header baris di atasnya jika merged cells
                    upper_val = (
                        str(df_raw.iloc[header_idx - 1, i]).strip()
                        if header_idx > 0
                        else ""
                    )
                    if upper_val and upper_val != "nan":
                        col_name = upper_val
                    else:
                        col_name = f"Ulangan_{i - nama_col_idx}"

                if "Pertemuan" not in col_name and "L/P" not in col_name:
                    ulangan_cols[i] = col_name

            # Olah data per siswa
            rows_list = []
            for _, row in df_data.iterrows():
                raw_nis = (
                    str(row[nis_col_idx]).strip()
                    if pd.notna(row[nis_col_idx])
                    else ""
                )
                raw_nama = (
                    str(row[nama_col_idx]).strip()
                    if pd.notna(row[nama_col_idx])
                    else ""
                )

                # Bersihkan NIS dari format desimal
                clean_nis = re.sub(r"\.0$", "", raw_nis)

                if (
                    clean_nis
                    and clean_nis != "nan"
                    and raw_nama
                    and raw_nama != "nan"
                ):
                    student_data = {
                        "NIS": clean_nis,
                        "Nama": raw_nama,
                        "Kelas": sheet_name.title(),
                    }

                    for col_i, u_name in ulangan_cols.items():
                        score_val = (
                            str(row[col_i]).strip()
                            if col_i < len(row) and pd.notna(row[col_i])
                            else "0"
                        )
                        try:
                            student_data[u_name] = float(score_val)
                        except ValueError:
                            student_data[u_name] = 0.0

                    rows_list.append(student_data)

            if rows_list:
                df_sheet = pd.DataFrame(rows_list)
                all_students.append(df_sheet)

        except Exception:
            continue

    if all_students:
        df_combined = pd.concat(all_students, ignore_index=True)

        kolom_ulangan = [
            c
            for c in df_combined.columns
            if c not in ["NIS", "Nama", "Kelas"]
        ]

        if kolom_ulangan:
            # Hitung Total Rata-Rata
            df_combined["Total_Rata"] = (
                df_combined[kolom_ulangan].mean(axis=1).round(1)
            )

            # Hitung Peringkat se-kelas
            for c in kolom_ulangan:
                df_combined[f"Peringkat_{c}"] = (
                    df_combined.groupby("Kelas")[c]
                    .rank(ascending=False, method="min")
                    .astype(int)
                )

            df_combined["Peringkat_Total_Rata"] = (
                df_combined.groupby("Kelas")["Total_Rata"]
                .rank(ascending=False, method="min")
                .astype(int)
            )

        return df_combined

    return pd.DataFrame()


# Memuat Data
df_all = load_all_data()

# Konfigurasi Tampilan
st.set_page_config(page_title=NAMA_PORTAL, page_icon="📐", layout="centered")

# State Navigasi
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
    st.title(f"📐 {NAMA_PORTAL}")
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
                    " 'Siapa saja yang memiliki link' sudah aktif."
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

    daftar_ulangan = [
        c
        for c in siswa.index
        if c not in ["NIS", "Nama", "Kelas"]
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

import pandas as pd
import streamlit as st

# ==========================================
# 1. KONFIGURASI PORTAL & SPREADSHEET
# ==========================================
NAMA_PORTAL = "Leaderboard Math SMP YWKA Bandung"
SPREADSHEET_ID = "1D_1VYbIu6qLTySkpPpxdNon_zmkgtY6ZMXOqK4MDGMs"
SHEETS = ["KELAS 7", "KELAS 8", "KELAS 9"]


def load_all_data():
    all_students = []
    error_messages = []

    for sheet_name in SHEETS:
        url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/gviz/tq?tqx=out:csv&sheet={sheet_name.replace(' ', '%20')}"
        try:
            # Baca CSV tanpa header otomatis
            df_raw = pd.read_csv(url, header=None, dtype=str)

            if df_raw.empty or df_raw.shape[1] < 4:
                continue

            # 1. Identifikasi Nama Kolom Ulangan (Kolom F / indeks 5 ke atas)
            nama_ulangan_cols = {}
            for col_idx in range(5, df_raw.shape[1]):
                header_texts = []
                for row_idx in range(min(3, len(df_raw))):
                    val = str(df_raw.iloc[row_idx, col_idx]).strip()
                    if (
                        val
                        and val != "nan"
                        and "Pertemuan" not in val
                        and "Unnamed" not in val
                    ):
                        header_texts.append(val)

                if header_texts:
                    nama_ulangan_cols[col_idx] = header_texts[-1]
                else:
                    nama_ulangan_cols[col_idx] = f"Ulangan_{col_idx-4}"

            # 2. Ambil Data Siswa (NIS di Kolom Index 1 & Nama di Kolom Index 3)
            rows_data = []
            for _, row in df_raw.iterrows():
                val_nis = str(row[1]).strip() if pd.notna(row[1]) else ""
                val_nama = str(row[3]).strip() if pd.notna(row[3]) else ""

                # Filter baris siswa valid (NIS angka & Nama ada)
                if val_nis.isdigit() and len(val_nis) >= 5 and val_nama:
                    student_dict = {
                        "NIS": val_nis,
                        "Nama": val_nama,
                        "Kelas": sheet_name.title(),
                    }

                    for col_idx, u_name in nama_ulangan_cols.items():
                        if col_idx < len(row):
                            val_score = str(row[col_idx]).strip()
                            try:
                                student_dict[u_name] = float(val_score)
                            except ValueError:
                                student_dict[u_name] = 0.0
                        else:
                            student_dict[u_name] = 0.0

                    rows_data.append(student_dict)

            if rows_data:
                df_sheet = pd.DataFrame(rows_data)
                all_students.append(df_sheet)

        except Exception as e:
            error_messages.append(f"Gagal membaca tab {sheet_name}: {e}")

    if error_messages:
        for err in error_messages:
            st.warning(err)

    if all_students:
        df_combined = pd.concat(all_students, ignore_index=True)

        kolom_ulangan = [
            c
            for c in df_combined.columns
            if c not in ["NIS", "Nama", "Kelas"]
        ]

        if kolom_ulangan:
            # Hitung Total Rata-Rata (To)
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


# Memuat data tanpa caching sementara agar data langsung terbarui
df_all = load_all_data()

# Konfigurasi Tampilan
st.set_page_config(page_title=NAMA_PORTAL, page_icon="📐", layout="centered")

# Management Navigasi Laman (1, 2, atau 3)
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

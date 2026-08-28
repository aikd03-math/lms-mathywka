import io
import pandas as pd
import requests
import streamlit as st

# ==========================================
# 1. KONFIGURASI PORTAL & SPREADSHEET
# ==========================================
NAMA_PORTAL = "Leaderboard Math SMP YWKA Bandung"
SPREADSHEET_ID = "1D_1VYbIu6qLTySkpPpxdNon_zmkgtY6ZMXOqK4MDGMs"
SHEETS = ["KELAS 7", "KELAS 8", "KELAS 9"]


def fetch_sheet_data(sheet_name):
  sheet_encoded = sheet_name.replace(" ", "%20")
  url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/gviz/tq?tqx=out:csv&sheet={sheet_encoded}"

  # Header User-Agent agar tidak diblokir Google Server di Streamlit Cloud
  headers = {
      "User-Agent": (
          "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
      )
  }

  res = requests.get(url, headers=headers, timeout=10)
  if res.status_code != 200:
    url_alt = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&sheet={sheet_encoded}"
    res = requests.get(url_alt, headers=headers, timeout=10)

  if res.status_code != 200:
    raise Exception(f"HTTP Error {res.status_code}")

  df_raw = pd.read_csv(
      io.StringIO(res.text), header=None, dtype=str, on_bad_lines="skip"
  )
  return df_raw


def process_all_data():
  all_students = []
  errors = []

  for sheet in SHEETS:
    try:
      df_raw = fetch_sheet_data(sheet)
      if df_raw.empty:
        continue

      # Ekstrak judul ulangan dari baris header (kolom F / indeks 5 ke atas)
      ulangan_headers = {}
      for col_idx in range(5, df_raw.shape[1]):
        header_name = f"Ulangan {col_idx - 4}"
        for row_idx in range(min(5, len(df_raw))):
          val = str(df_raw.iloc[row_idx, col_idx]).strip()
          if (
              val
              and val.lower() != "nan"
              and "pertemuan" not in val.lower()
              and "unnamed" not in val.lower()
          ):
            header_name = val
            break
        ulangan_headers[col_idx] = header_name

      # Ekstrak data siswa (Induk di kolom indeks 1, Nama di kolom indeks 3)
      rows_list = []
      for _, row in df_raw.iterrows():
        if len(row) > 3:
          val_nis = str(row[1]).strip() if pd.notna(row[1]) else ""
          val_nama = str(row[3]).strip() if pd.notna(row[3]) else ""

          # Cek baris siswa valid (NIS berupa angka minimal 5 digit)
          if val_nis.isdigit() and len(val_nis) >= 5 and val_nama:
            student_data = {
                "NIS": val_nis,
                "Nama": val_nama,
                "Kelas": sheet.title(),
            }

            for col_idx, u_title in ulangan_headers.items():
              if col_idx < len(row):
                score_str = (
                    str(row[col_idx])
                    .strip()
                    .replace(",", ".")
                    .replace("-", "0")
                )
                try:
                  student_data[u_title] = float(score_str)
                except ValueError:
                  student_data[u_title] = 0.0
              else:
                student_data[u_title] = 0.0

            rows_list.append(student_data)

      if rows_list:
        df_sheet = pd.DataFrame(rows_list)
        all_students.append(df_sheet)

    except Exception as e:
      errors.append(f"Tab {sheet}: {str(e)}")

  if all_students:
    df_combined = pd.concat(all_students, ignore_index=True)

    kolom_ulangan = [
        c for c in df_combined.columns if c not in ["NIS", "Nama", "Kelas"]
    ]

    if kolom_ulangan:
      df_combined["Total_Rata"] = (
          df_combined[kolom_ulangan].mean(axis=1).round(1)
      )

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

    return df_combined, errors

  return pd.DataFrame(), errors


# Load Data dari Google Sheets
df_all, fetch_errors = process_all_data()

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
            "Gagal membaca data dari Google Sheets. Detail error:\n"
            + "\n".join(fetch_errors)
        )
      else:
        nis_clean = nis_input.strip()
        nama_clean = nama_input.strip().lower()

        match_nis = df_all[df_all["NIS"].str.strip() == nis_clean]

        if match_nis.empty:
          st.error(
              f"Nomor Induk (NIS) '{nis_input}' tidak ditemukan di database."
          )
        else:
          exact_match = match_nis[
              match_nis["Nama"].str.lower().str.strip() == nama_clean
          ]

          if not exact_match.empty:
            st.session_state.siswa_login = exact_match.iloc[0]
            st.session_state.laman = 2
            st.rerun()
          else:
            nama_db = match_nis.iloc[0]["Nama"]
            st.warning(
                f"NIS **{nis_clean}** ditemukan! Namun nama di Google Sheets"
                f" terdaftar sebagai:\n\n👉 **{nama_db}**\n\nSilakan ketik nama"
                " persis seperti tulisan di atas."
            )


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
      if st.button(label_tampil, key=f"btn_{idx}", use_container_width=True):
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

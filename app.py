import csv
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


def fetch_sheet_csv(sheet_name):
  sheet_enc = sheet_name.replace(" ", "%20")
  urls = [
      f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/gviz/tq?tqx=out:csv&sheet={sheet_enc}",
      f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv&sheet={sheet_enc}",
  ]
  headers = {
      "User-Agent": (
          "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
      )
  }

  for url in urls:
    try:
      resp = requests.get(url, headers=headers, timeout=10)
      if resp.status_code == 200 and len(resp.text) > 50:
        return resp.text
    except Exception:
      pass
  return None


def parse_smart_data(csv_text, sheet_label):
  reader = csv.reader(io.StringIO(csv_text))
  rows = list(reader)
  if not rows:
    return []

  # Detect Header/Score Columns
  score_cols = {}
  for r_idx in range(min(5, len(rows))):
    row = rows[r_idx]
    for c_idx, cell in enumerate(row):
      c_text = cell.strip()
      if c_text and not any(
          x in c_text.lower()
          for x in ["nama", "l/p"]
      ):
        score_cols[c_idx] = c_text

  if not score_cols:
    score_cols = {5: "Diagnostik"}

  students = []
  for row in rows:
    if len(row) < 4:
      continue

    nis = None
    nama = None

    # Smart Search NIS & Nama
    for cell in row:
      val = cell.strip()
      # NIS : Angka murni panjang 6 - 12 digit
      if not nis and val.isdigit() and 6 <= len(val) <= 12:
        nis = val
      # Nama : Teks selain header/kata kunci
      elif (
          val
          and not val.isdigit()
          and len(val) > 3
          and not nama
          and not any(
              x in val.lower()
              for x in [
                  "Nama Siswa",
                  "L/P",
              ]
          )
      ):
        nama = val

    if nis and nama:
      st_item = {"NIS": nis, "Nama": nama, "Kelas": sheet_label}

      for c_idx, s_name in score_cols.items():
        val_score = 0.0
        if c_idx < len(row):
          raw_val = row[c_idx].strip().replace(",", ".").replace("-", "0")
          try:
            val_score = float(raw_val)
          except ValueError:
            val_score = 0.0
        st_item[s_name] = val_score

      students.append(st_item)

  return students


@st.cache_data(ttl=30)
def load_all_students():
  combined_list = []
  for sheet in SHEETS:
    csv_raw = fetch_sheet_csv(sheet)
    if csv_raw:
      parsed = parse_smart_data(csv_raw, sheet.title())
      combined_list.extend(parsed)

  if not combined_list:
    return pd.DataFrame()

  df = pd.DataFrame(combined_list)
  score_cols = [c for c in df.columns if c not in ["NIS", "Nama", "Kelas"]]

  if score_cols:
    df["Total_Rata"] = df[score_cols].mean(axis=1).round(1)

    for c in score_cols:
      df[f"Peringkat_{c}"] = (
          df.groupby("Kelas")[c]
          .rank(ascending=False, method="min")
          .astype(int)
      )

    df["Peringkat_Total_Rata"] = (
        df.groupby("Kelas")["Total_Rata"]
        .rank(ascending=False, method="min")
        .astype(int)
    )

  return df


# Load Master Data
df_all = load_all_students()

# Config UI
st.set_page_config(page_title=NAMA_PORTAL, page_icon="📐", layout="centered")

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
            "⚠️ Gagal terhubung ke Google Sheets!\n\nPastikan di Google Sheets"
            " Anda sudah klik: **File > Bagikan > Publikasikan ke Web**."
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

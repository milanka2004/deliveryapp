import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from dateutil import parser, relativedelta

# ----- Dependency check -----
try:
    import gspread
    from oauth2client.service_account import ServiceAccountCredentials
except ModuleNotFoundError as e:
    st.error(f"Missing package: {e.name}. Did you list it in requirements.txt?")
    st.stop()

# ----- Secrets check -----
if "gcp_service_account" not in st.secrets:
    st.error(
        "❌ No `gcp_service_account` found in Streamlit Cloud Secrets.\n"
        "Go to *Manage app ▸ Secrets* and paste your service-account JSON there."
    )
    st.stop()

creds_dict = st.secrets["gcp_service_account"]

# ----- Google Sheets auth -----
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]

try:
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
except Exception as e:
    st.error(f"❌ Couldn’t authorise Google Sheets: {e}")
    st.stop()

# ----- Open spreadsheet -----
try:
    spreadsheet = client.open("Deliveries")
    sheet = spreadsheet.sheet1
except Exception as e:
    st.error(f"❌ Couldn’t open spreadsheet: {e}")
    st.stop()

# ----- Load data into DataFrame -----
try:
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
except Exception as e:
    st.error(f"❌ Failed to load data: {e}")
    st.stop()

# ================= Streamlit UI =================
st.markdown("""
<style>
.main .block-container {max-width: 1800px;}
.stTextInput>div>div>input,.stSelectbox>div[data-baseweb="select"]{width:100%!important}
.stDataEditorRow {border-bottom:1px solid #ddd !important;}
</style>
""", unsafe_allow_html=True)

st.title("📦 Deliveries Tracker")
st.subheader("Delivery Overview")

status_options = ["Not started", "In progress", "Completed"]
priority_options = ["Low", "Medium", "High"]
frequency_map = {
    "weekly": relativedelta.relativedelta(weeks=1),
    "monthly": relativedelta.relativedelta(months=1),
    "quarterly": relativedelta.relativedelta(months=3),
    "semesterly": relativedelta.relativedelta(months=6),
}

df["Due"] = pd.to_datetime(df["Due"], errors='coerce', dayfirst=True)  # Convert to datetime
df = df.sort_values("Due")  # Sort by due date ascending

# Prepare dataframe for data_editor
view_df = df.copy()
view_df["Done"] = view_df["Done"].astype(str).str.upper() == "TRUE"

edited = st.data_editor(
    view_df,
    hide_index=True,
    column_config={
        "Done": st.column_config.CheckboxColumn("Done"),
        "Priority": st.column_config.SelectboxColumn("Priority", options=priority_options),
        "Status": st.column_config.SelectboxColumn("Status", options=status_options),
        "Notes": st.column_config.TextColumn("Notes"),
    },
    use_container_width=True,
    key="editor",
)

# Detect changes and sync
for i, new_row in edited.iterrows():
    old_row = df.iloc[i]

    # Handle tick
    if new_row["Done"] and str(old_row["Done"]).upper() != "TRUE":
        try:
            # 1️⃣ Move due date forward according to frequency
            due = parser.parse(str(old_row["Due"]), dayfirst=True)
            freq_key = new_row["Frequency"].strip().lower()
            delta = frequency_map.get(freq_key)
            if delta:
                new_due = due + delta
                # 2️⃣ Update cells individually to keep column order intact
                sheet.update_cell(i + 2, df.columns.get_loc("Due") + 1, new_due.strftime("%Y-%m-%d"))
                sheet.update_cell(i + 2, df.columns.get_loc("Status") + 1, "Not started")
                sheet.update_cell(i + 2, df.columns.get_loc("Done") + 1, False)  # un‑tick
                st.rerun()
        except Exception as e:
            st.error(f"❌ Tick update failed on row {i+2}: {e}")
            st.error(f"❌ Tick update failed on row {i+2}: {e}")

    # Handle editable fields
    for col in ["Priority","Status","Notes"]:
        if str(new_row[col]) != str(old_row[col]):
            try:
                sheet.update_cell(i+2, df.columns.get_loc(col)+1, new_row[col])
                st.rerun()
            except Exception as e:
                st.error(f"❌ Failed updating {col} at row {i+2}: {e}")

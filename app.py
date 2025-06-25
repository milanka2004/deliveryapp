import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd

# Define Google API scope
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]

# Load credentials from secrets.toml
creds_dict = st.secrets["gcp_service_account"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

# Open Google Sheet
spreadsheet = client.open("Deliveries")  # Alternatively: .open_by_url("...")
sheet = spreadsheet.sheet1

# Load sheet data into DataFrame
data = sheet.get_all_records()
df = pd.DataFrame(data)

# --- Streamlit UI ---
st.title("📦 Deliveries Tracker")

# Display sheet
st.dataframe(df)

# Allow editing of rows
st.subheader("✏️ Edit Existing Entry")
row = st.number_input("Edit row number (starting from 2)", min_value=2, max_value=len(df)+1)
col = st.selectbox("Select column", df.columns)
new_value = st.text_input("New value")

if st.button("Update Cell"):
    sheet.update_cell(row, df.columns.get_loc(col) + 1, new_value)
    st.success("✅ Cell updated!")

# Add a new row
st.subheader("➕ Add New Delivery")
with st.form("new_delivery"):
    new_data = [st.text_input(col) for col in df.columns]
    submitted = st.form_submit_button("Add Row")
    if submitted:
        sheet.append_row(new_data)
        st.success("✅ New row added!")

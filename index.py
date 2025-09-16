import streamlit as st
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime

# Set page config
st.set_page_config(
    page_title="Construction Expense Tracker",
    page_icon="💰",
    layout="wide"
)

# Configuration
SPREADSHEET_ID = '1jk-I4DZg2VXQnB8q6te-ylR14Ht48l6EsoYhlmrXGBg'
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
SHEET_NAME = 'Sheet1'
SERVICE_ACCOUNT_FILE = dict(st.secrets["gcp_service_account"])

# ---------- AUTH ----------
def check_login():
    return st.session_state.get('authenticated', False)

def login_page():
    st.title("🔐 Login to Construction Expense Tracker")
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        with st.form("login_form"):
            username = st.text_input("Username", placeholder="Enter your username")
            password = st.text_input("Password", type="password", placeholder="Enter your password")
            login_button = st.form_submit_button("🚀 Login", use_container_width=True, type="primary")

            if login_button:
                try:
                    valid_username = st.secrets["auth"]["username"]
                    valid_password = st.secrets["auth"]["password"]

                    if username == valid_username and password == valid_password:
                        st.session_state.authenticated = True
                        st.success("✅ Login successful!")
                        st.rerun()
                    else:
                        st.error("❌ Invalid username or password!")
                except KeyError:
                    st.error("❌ Authentication configuration not found.")

def logout():
    st.session_state.authenticated = False
    st.rerun()

# ---------- GOOGLE SHEETS ----------
@st.cache_resource
def init_gsheet():
    try:
        creds = Credentials.from_service_account_info(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        service = build('sheets', 'v4', credentials=creds)
        return service
    except Exception as e:
        st.error(f"Error connecting to Google Sheets: {str(e)}")
        return None

def get_sheet_data(service, range_name='Sheet1!A:F'):
    try:
        result = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID, range=range_name
        ).execute()
        return result.get('values', [])
    except Exception as e:
        st.error(f"Error getting sheet data: {str(e)}")
        return []

def update_sheet_data(service, values, range_name='Sheet1!A:F'):
    try:
        body = {'values': values}
        service.spreadsheets().values().update(
            spreadsheetId=SPREADSHEET_ID,
            range=range_name,
            valueInputOption='USER_ENTERED',
            body=body
        ).execute()
        return True
    except Exception as e:
        st.error(f"Error updating sheet: {str(e)}")
        return False

# ---------- SORTING ----------
def sort_data(all_data, newest_first=True):
    if len(all_data) <= 1:
        return all_data
    headers = all_data[0]
    data_rows = all_data[1:]
    def parse_date(date_str):
        try:
            return datetime.strptime(str(date_str), '%d/%m/%Y')
        except:
            return datetime.min
    sorted_rows = sorted(
        data_rows,
        key=lambda row: parse_date(row[1]) if len(row) > 1 else datetime.min,
        reverse=newest_first
    )
    for i, row in enumerate(sorted_rows, 1):
        row[0] = i
    return [headers] + sorted_rows

# ---------- MAIN APP ----------
def expense_tracker_app():
    with st.sidebar:
        st.markdown("### User Options")
        if st.button("🚪 Logout", type="secondary", use_container_width=True):
            logout()

    st.title("💰 Construction Expense Tracker")
    st.markdown("---")

    service = init_gsheet()
    if service is None:
        return

    all_data = get_sheet_data(service)
    if not all_data:
        headers = ['Sl No', 'Date', 'Item Description', 'Vendor', 'Bill Number', 'Amount']
        update_sheet_data(service, [headers])
        all_data = [headers]

    # Suggestions for autocomplete
    vendors = list(set([row[3] for row in all_data[1:] if len(row) > 3]))
    items = list(set([row[2] for row in all_data[1:] if len(row) > 2]))

    col1, col2 = st.columns([1, 2])
    # ---------- ADD EXPENSE ----------
    with col1:
        st.subheader("Add New Expense")

        with st.form("expense_form", clear_on_submit=True):
            expense_date = st.date_input("Date", value=datetime.now().date())

            # --- Item Description ---
            item_options = (items if items else [])
            desc_suggestion = st.selectbox(
                "Item Description",
                options=item_options,
                key="desc_select",
                accept_new_options=True
            )

            description = desc_suggestion

            # --- Vendor ---
            vendor_options = (vendors if vendors else [])
            vendor_suggestion = st.selectbox(
                "Vendor",
                options=vendor_options,
                key="vendor_select"
            )

            vendor = vendor_suggestion

            # --- Other fields ---
            bill_number = st.text_input("Bill Number")
            amount = st.number_input("Amount (₹)", min_value=0.0, step=0.01, format="%.2f")

            # --- Submit ---
            submitted = st.form_submit_button("Add Expense", use_container_width=True, type="primary")

            if submitted:
                if description and vendor and amount > 0:
                    new_row = [
                        len(all_data),
                        expense_date.strftime('%d/%m/%Y'),
                        description.strip(),
                        vendor.strip(),
                        bill_number if bill_number else "N/A",
                        amount
                    ]
                    all_data.append(new_row)
                    all_data = sort_data(all_data, newest_first=False)
                    update_sheet_data(service, all_data)
                    st.success("✅ Expense added successfully!")
                    st.rerun()
                else:
                    st.warning("⚠️ Please fill all required fields.")

    # ---------- VIEW & EDIT ----------
    with col2:
        st.subheader("Expenses")
        sort_col1, sort_col2 = st.columns([1,1])
        if sort_col1.button("⬆️ Oldest → Newest"):
            all_data = sort_data(all_data, newest_first=False)
            update_sheet_data(service, all_data)
            st.rerun()
        if sort_col2.button("⬇️ Newest → Oldest"):
            all_data = sort_data(all_data, newest_first=True)
            update_sheet_data(service, all_data)
            st.rerun()

        if len(all_data) > 1:
            df = pd.DataFrame(all_data[1:], columns=all_data[0])

            # ---- SUMMARY ----
            num_entries = len(df)
            total_expenses = pd.to_numeric(df["Amount"], errors="coerce").sum()

            st.markdown("### 📊 Summary")
            col_a, col_b = st.columns(2)
            col_a.metric("Number of Entries", num_entries)
            col_b.metric("Total Expenses (₹)", f"{total_expenses:,.2f}")

            edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True)
            if st.button("💾 Save Changes", type="primary", use_container_width=True):
                new_values = [all_data[0]] + edited_df.values.tolist()
                update_sheet_data(service, new_values)
                st.success("✅ Changes saved!")
                st.rerun()
        else:
            st.info("No expenses recorded yet.")

# ---------- MAIN ----------
def main():
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if not check_login():
        login_page()
    else:
        expense_tracker_app()

if __name__ == "__main__":
    main()

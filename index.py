import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime
import json

# Set page config
st.set_page_config(
    page_title="Construction Expense Tracker",
    page_icon="💰",
    layout="wide"
)

# Configuration
SERVICE_ACCOUNT_FILE = 'subtle-photon-2025-259017038b64.json'
SPREADSHEET_ID = '1jk-I4DZg2VXQnB8q6te-ylR14Ht48l6EsoYhlmrXGBg'
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']


# Google Sheets setup
@st.cache_resource
def init_gsheet():
    """Initialize Google Sheets connection"""
    try:
        # Load credentials from JSON file
        creds = Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES
        )

        # Use gspread for easier operations
        gc = gspread.service_account(filename=SERVICE_ACCOUNT_FILE)
        spreadsheet = gc.open_by_key(SPREADSHEET_ID)
        worksheet = spreadsheet.worksheet("Sheet1")  # or get_worksheet(0)

        return worksheet
    except FileNotFoundError:
        st.error(f"Service account key file not found at {SERVICE_ACCOUNT_FILE}")
        st.info("Please ensure the JSON key file is in the same directory as this script.")
        return None
    except Exception as e:
        st.error(f"Error connecting to Google Sheets: {str(e)}")
        return None


def add_expense_to_sheet(worksheet, expense_data):
    """Add expense data to Google Sheet"""
    try:
        # Get current data to determine next serial number
        existing_data = worksheet.get_all_records()
        next_sl_no = len(existing_data) + 1

        # Prepare row data
        row_data = [
            next_sl_no,
            expense_data['date'],
            expense_data['description'],
            expense_data['vendor'],
            expense_data['bill_number'],
            expense_data['amount']
        ]

        # Add the new row
        worksheet.append_row(row_data)

        # Sort the sheet by date (newest to oldest) and update serial numbers
        sort_sheet_by_date(worksheet)

        return True
    except Exception as e:
        st.error(f"Error adding expense: {str(e)}")
        return False


def sort_sheet_by_date(worksheet):
    """Sort sheet by date (newest to oldest) and update serial numbers"""
    try:
        # Get all data including headers
        all_data = worksheet.get_all_values()

        if len(all_data) <= 1:  # Only headers or empty
            return

        headers = all_data[0]
        data_rows = all_data[1:]

        # Convert date strings to datetime objects for sorting
        def parse_date(date_str):
            try:
                return datetime.strptime(date_str, '%d/%m/%Y')
            except:
                return datetime.min  # Put invalid dates at the end

        # Sort by date (newest first) - index 1 is the date column
        sorted_rows = sorted(data_rows, key=lambda row: parse_date(row[1]) if len(row) > 1 else datetime.min,
                             reverse=True)

        # Update serial numbers
        for i, row in enumerate(sorted_rows, 1):
            if len(row) > 0:
                row[0] = i  # Update serial number

        # Clear the sheet and rewrite with sorted data
        worksheet.clear()

        # Write headers first
        worksheet.append_row(headers)

        # Write sorted data
        for row in sorted_rows:
            worksheet.append_row(row)

    except Exception as e:
        st.error(f"Error sorting sheet: {str(e)}")


def get_expenses_from_sheet(worksheet):
    """Retrieve expenses from Google Sheet (already sorted)"""
    try:
        # Ensure sheet is sorted before fetching
        sort_sheet_by_date(worksheet)

        records = worksheet.get_all_records()
        if records:
            df = pd.DataFrame(records)
            return df
        else:
            return pd.DataFrame()
    except Exception as e:
        st.error(f"Error retrieving expenses: {str(e)}")
        return pd.DataFrame()


def setup_sheet_headers(worksheet):
    """Setup headers if sheet is empty"""
    try:
        if not worksheet.get_all_values():
            headers = ['Sl No', 'Date', 'Item Description', 'Vendor', 'Bill Number', 'Amount']
            worksheet.append_row(headers)
    except Exception as e:
        st.error(f"Error setting up headers: {str(e)}")


# Main app
def main():
    st.title("💰 Construction Expense Tracker")
    st.markdown("---")

    # Initialize Google Sheets
    worksheet = init_gsheet()

    if worksheet is None:
        st.error("Could not connect to Google Sheets. Please check your configuration.")
        st.info("""
        To use this app, you need to:
        1. Place your service account JSON file in the same directory as this script
        2. Make sure the JSON file name matches: 'subtle-photon-2025-259017038b64.json'
        3. Ensure your Google Sheet is shared with the service account email
        4. Verify the SPREADSHEET_ID is correct
        """)
        return

    # Setup headers if needed
    setup_sheet_headers(worksheet)

    # Create two columns
    col1, col2 = st.columns([1, 2])

    with col1:
        st.subheader("Add New Expense")

        # Expense form in a card-like container
        with st.container():
            st.markdown("""
            <div style="
                border: 1px solid #ddd;
                border-radius: 10px;
                padding: 20px;
                background-color: #f9f9f9;
                margin-bottom: 20px;
            ">
            """, unsafe_allow_html=True)

            with st.form("expense_form", clear_on_submit=True):
                # Date input
                expense_date = st.date_input(
                    "Date",
                    value=datetime.now().date(),
                    help="Select the expense date"
                )

                # Item description
                description = st.text_input(
                    "Item Description",
                    placeholder="Enter item description..."
                )

                # Vendor
                vendor = st.text_input(
                    "Vendor",
                    placeholder="Enter vendor name..."
                )

                # Bill number
                bill_number = st.text_input(
                    "Bill Number",
                    placeholder="Enter bill number..."
                )

                # Amount
                amount = st.number_input(
                    "Amount (₹)",
                    min_value=0.0,
                    step=0.01,
                    format="%.2f"
                )

                # Submit button
                submitted = st.form_submit_button(
                    "Add Expense",
                    use_container_width=True,
                    type="primary"
                )

                if submitted:
                    if description and vendor and amount > 0:
                        expense_data = {
                            'date': expense_date.strftime('%d/%m/%Y'),
                            'description': description,
                            'vendor': vendor,
                            'bill_number': bill_number if bill_number else 'N/A',
                            'amount': amount
                        }

                        if add_expense_to_sheet(worksheet, expense_data):
                            st.success("✅ Expense added successfully!")
                            st.rerun()
                        else:
                            st.error("❌ Failed to add expense.")
                    else:
                        st.warning("⚠️ Please fill in all required fields.")

            st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        st.subheader("Recent Expenses")

        # Refresh button
        col_refresh, col_sort = st.columns([1, 1])

        with col_refresh:
            if st.button("🔄 Refresh Data", key="refresh"):
                st.rerun()

        with col_sort:
            if st.button("📊 Sort by Date", key="sort"):
                sort_sheet_by_date(worksheet)
                st.success("✅ Sheet sorted by date!")
                st.rerun()

        # Display expenses
        expenses_df = get_expenses_from_sheet(worksheet)

        if not expenses_df.empty:
            # Format amount column for better display
            if 'Amount' in expenses_df.columns:
                expenses_df['Amount'] = expenses_df['Amount'].apply(
                    lambda x: f"₹{float(x):,.2f}" if pd.notnull(x) else "₹0.00"
                )

            # Display as table
            st.dataframe(
                expenses_df,
                use_container_width=True,
                hide_index=True
            )

            # Summary statistics
            st.markdown("---")
            col_a, col_b= st.columns(2)

            with col_a:
                total_expenses = len(expenses_df)
                st.metric("Total Entries", total_expenses)

            with col_b:
                if 'Amount' in expenses_df.columns:
                    # Convert back to float for calculation
                    amounts = expenses_df['Amount'].str.replace('₹', '').str.replace(',', '').astype(float)
                    total_amount = amounts.sum()
                    st.metric("Total Amount", f"₹{total_amount:,.2f}")

        else:
            st.info("No expenses recorded yet. Add your first expense using the form on the left!")


if __name__ == "__main__":
    main()
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


# Google Sheets setup
@st.cache_resource
def init_gsheet():
    """Initialize Google Sheets connection"""
    try:
        # Load credentials from service account info
        creds = Credentials.from_service_account_info(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES
        )

        # Build the service
        service = build('sheets', 'v4', credentials=creds)

        return service
    except Exception as e:
        st.error(f"Error connecting to Google Sheets: {str(e)}")
        return None


def get_sheet_data(service, range_name='Sheet1!A:F'):
    """Get data from Google Sheet"""
    try:
        result = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=range_name
        ).execute()
        values = result.get('values', [])
        return values
    except Exception as e:
        st.error(f"Error getting sheet data: {str(e)}")
        return []


def append_to_sheet(service, values, range_name='Sheet1!A:F'):
    """Append data to Google Sheet"""
    try:
        body = {
            'values': [values]
        }
        result = service.spreadsheets().values().append(
            spreadsheetId=SPREADSHEET_ID,
            range=range_name,
            valueInputOption='USER_ENTERED',
            body=body
        ).execute()
        return True
    except Exception as e:
        st.error(f"Error appending to sheet: {str(e)}")
        return False


def update_sheet_data(service, values, range_name='Sheet1!A:F'):
    """Update entire sheet with new data"""
    try:
        body = {
            'values': values
        }
        result = service.spreadsheets().values().update(
            spreadsheetId=SPREADSHEET_ID,
            range=range_name,
            valueInputOption='USER_ENTERED',
            body=body
        ).execute()
        return True
    except Exception as e:
        st.error(f"Error updating sheet: {str(e)}")
        return False


def clear_sheet(service, range_name='Sheet1!A:F'):
    """Clear sheet data"""
    try:
        service.spreadsheets().values().clear(
            spreadsheetId=SPREADSHEET_ID,
            range=range_name
        ).execute()
        return True
    except Exception as e:
        st.error(f"Error clearing sheet: {str(e)}")
        return False


def add_expense_to_sheet(service, expense_data):
    """Add expense data to Google Sheet"""
    try:
        # Get current data
        all_data = get_sheet_data(service)

        # If no data exists, create headers
        if not all_data:
            headers = ['Sl No', 'Date', 'Item Description', 'Vendor', 'Bill Number', 'Amount']
            all_data = [headers]

        # Determine next serial number
        next_sl_no = len(all_data)  # Since we include headers

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
        all_data.append(row_data)

        # Sort the data by date (newest to oldest) and update serial numbers
        sorted_data = sort_data_by_date(all_data)

        # Update the entire sheet with sorted data
        update_sheet_data(service, sorted_data)

        return True
    except Exception as e:
        st.error(f"Error adding expense: {str(e)}")
        return False


def sort_data_by_date(all_data):
    """Sort data by date (newest to oldest) and update serial numbers"""
    try:
        if len(all_data) <= 1:  # Only headers or empty
            return all_data

        headers = all_data[0]
        data_rows = all_data[1:]

        # Convert date strings to datetime objects for sorting
        def parse_date(date_str):
            try:
                return datetime.strptime(str(date_str), '%d/%m/%Y')
            except:
                return datetime.min  # Put invalid dates at the end

        # Sort by date (newest first) - index 1 is the date column
        sorted_rows = sorted(data_rows,
                             key=lambda row: parse_date(row[1]) if len(row) > 1 else datetime.min,
                             reverse=True)

        # Update serial numbers
        for i, row in enumerate(sorted_rows, 1):
            if len(row) > 0:
                row[0] = i  # Update serial number

        # Return headers + sorted data
        return [headers] + sorted_rows

    except Exception as e:
        st.error(f"Error sorting data: {str(e)}")
        return all_data


def get_expenses_from_sheet(service):
    """Retrieve expenses from Google Sheet (already sorted)"""
    try:
        # Get all data
        all_data = get_sheet_data(service)

        if len(all_data) <= 1:  # Only headers or empty
            return pd.DataFrame()

        # Sort data before returning
        sorted_data = sort_data_by_date(all_data)

        # Update sheet with sorted data
        update_sheet_data(service, sorted_data)

        # Convert to DataFrame
        headers = sorted_data[0]
        data_rows = sorted_data[1:]

        if data_rows:
            df = pd.DataFrame(data_rows, columns=headers)
            return df
        else:
            return pd.DataFrame()

    except Exception as e:
        st.error(f"Error retrieving expenses: {str(e)}")
        return pd.DataFrame()


def setup_sheet_headers(service):
    """Setup headers if sheet is empty"""
    try:
        all_data = get_sheet_data(service)
        if not all_data:
            headers = ['Sl No', 'Date', 'Item Description', 'Vendor', 'Bill Number', 'Amount']
            append_to_sheet(service, headers)
    except Exception as e:
        st.error(f"Error setting up headers: {str(e)}")


def manual_sort_sheet(service):
    """Manually sort the sheet by date"""
    try:
        all_data = get_sheet_data(service)
        if len(all_data) > 1:
            sorted_data = sort_data_by_date(all_data)
            update_sheet_data(service, sorted_data)
            return True
        return False
    except Exception as e:
        st.error(f"Error manually sorting sheet: {str(e)}")
        return False


# Main app
def main():
    st.title("💰 Construction Expense Tracker")
    st.markdown("---")

    # Initialize Google Sheets
    service = init_gsheet()

    if service is None:
        st.error("Could not connect to Google Sheets. Please check your configuration.")
        st.info("""
        To use this app, you need to:
        1. Add your service account credentials to Streamlit secrets
        2. Ensure your Google Sheet is shared with the service account email
        3. Verify the SPREADSHEET_ID is correct
        """)
        return

    # Setup headers if needed
    setup_sheet_headers(service)

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

                        if add_expense_to_sheet(service, expense_data):
                            st.success("✅ Expense added successfully!")
                            st.rerun()
                        else:
                            st.error("❌ Failed to add expense.")
                    else:
                        st.warning("⚠️ Please fill in all required fields.")

            st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        st.subheader("Recent Expenses")

        # Refresh and sort buttons
        col_refresh, col_sort = st.columns([1, 1])

        with col_refresh:
            if st.button("🔄 Refresh Data", key="refresh"):
                st.rerun()

        with col_sort:
            if st.button("📊 Sort by Date", key="sort"):
                if manual_sort_sheet(service):
                    st.success("✅ Sheet sorted by date!")
                    st.rerun()

        # Display expenses
        expenses_df = get_expenses_from_sheet(service)

        if not expenses_df.empty:
            # Format amount column for better display
            if 'Amount' in expenses_df.columns:
                expenses_df['Amount'] = expenses_df['Amount'].apply(
                    lambda x: f"₹{float(x):,.2f}" if pd.notnull(x) and str(x).replace('.', '').isdigit() else "₹0.00"
                )

            # Display as table
            st.dataframe(
                expenses_df,
                use_container_width=True,
                hide_index=True
            )

            # Summary statistics
            st.markdown("---")
            col_a, col_b = st.columns(2)

            with col_a:
                total_expenses = len(expenses_df)
                st.metric("Total Entries", total_expenses)

            with col_b:
                if 'Amount' in expenses_df.columns:
                    try:
                        # Convert back to float for calculation
                        amounts = expenses_df['Amount'].str.replace('₹', '').str.replace(',', '').astype(float)
                        total_amount = amounts.sum()
                        st.metric("Total Amount", f"₹{total_amount:,.2f}")
                    except:
                        st.metric("Total Amount", "₹0.00")

        else:
            st.info("No expenses recorded yet. Add your first expense using the form on the left!")


if __name__ == "__main__":
    main()
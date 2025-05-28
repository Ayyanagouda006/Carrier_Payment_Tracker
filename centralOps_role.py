import streamlit as st
import pandas as pd
from datetime import datetime
import os
from streamlit_option_menu import option_menu

EXCEL_FILE = r"data/payment_requests.xlsx"

def save_to_excel(data_rows):
    df = pd.DataFrame(data_rows)
    if os.path.exists(EXCEL_FILE):
        existing = pd.read_excel(EXCEL_FILE)
        df = pd.concat([existing, df], ignore_index=True)
    df.to_excel(EXCEL_FILE, index=False)

def display_payment_form():
    if os.path.exists(EXCEL_FILE):
        df = pd.read_excel(EXCEL_FILE)

        # Ensure consistent column names
        df.columns = df.columns.str.strip()

        # Force specific types
        df['MBL #'] = df['MBL #'].astype(str)
        df['Carrier Invoice #'] = df['Carrier Invoice #'].astype(str)
        df['Amount'] = df['Amount'].astype(float)
        df['LDC Cut-off'] = df['LDC Cut-off'].astype(str)

        # List of columns to convert
        date_columns = [
            'Date of Creation', 'Invoice Date', 'SOB', 'ETA',
            'Payment Request Date', 'Payment Date'
        ]

        # Convert date columns to datetime
        for col in date_columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')

        shipping_companies = ["ONE", "MAERSK", "SCI", "CMT", "MSC", "CMA CGM", "HAPAG", "COSCO", "HMM", "ANL", "SEA LEAD", "ALLCARGO", "CMA", "RCL", "SEABRIDGE", "SEA TRADE", "MOONSTAR", "OMEGA SHIPPING", "GLOBELINK", "HYUNDAI", "TRISEA", "OOCL", "DIAMOND", "MAXICON", "EVERGREEN", "ECON", "WAN HAI", "KMS MARITIME", "TS LINE", "EMINENT SHIPPING", "ENTRUST"]
        charge_types = [
            "OCEAN FREIGHT", "LOCAL CHARGES", "SURRENDER FEE", "LATE BL FEE",
            "AMENDMENT FEE", "BOOKING CANCELLATION FEE", "CREDIT NOTE", "DETENTION",
            "STORAGE", "MANIFEST CORRECTION FEE", "SHORT TRANSIT", "SURRENDER CHARGES",
            "PEAK SEASON CHARGES", "LDC INVOICE", "LDC CHARGES", "BL SURRENDER FEES",
            "COMMITTED VOLUME AGREEMENT", "OBL SURRENDER", "BL RELEASED",
            "OUTSTATION CHARGES", "GROUND RENT CHARGES", "STORAGE CHARGES",
            "URGENT PAYMENT - SHORT TRANSIT", "EXPORT DETENTION"
        ]


        # Display editable data
        edited_df = st.data_editor(
            df,
            hide_index=True,
            use_container_width=True,
            disabled=[
                'Date of Creation', 'BL Released?', 'Payment Date', 'Payment Reference Number', 'Status',
                'Amount Paid Currency', 'Amount Paid', 'Payment Mode', 'SWIFT Certificate Link',
                'IRN Invoice', 'Payment Request Date',
                'Scheduled Payment Date','Amount_INR','Amount_USD','Payment Updated Date'
            ],
            num_rows="dynamic",
            column_config={
                'Date of Creation': st.column_config.DateColumn(label="Date of Creation", format="DD-MM-YYYY"),
                'Carrier Invoice Link':st.column_config.LinkColumn(label='Carrier Invoice Link'),
                'Carrier': st.column_config.SelectboxColumn(label="Carrier", options=shipping_companies),
                'Remarks': st.column_config.SelectboxColumn(label="Remarks", options=charge_types),
                'Payment Request Date': st.column_config.DateColumn(label='Payment Request Date', format="DD-MM-YYYY"),
                'Payment Date': st.column_config.DateColumn(label="Payment Date", format="DD-MM-YYYY"),
                "Invoice Date": st.column_config.DateColumn(label="Invoice Date", format="DD-MM-YYYY", step=1),
                "Currency": st.column_config.SelectboxColumn(label="Currency", options=["INR", "USD"]),
                "Amount": st.column_config.NumberColumn(label="Amount", step=0.01, format="%.2f"),
                "GST Amount in INR (If Freight in USD and GST in INR)": st.column_config.NumberColumn(
                    label="GST Amount in INR (If Freight in USD and GST in INR)", step=0.01, format="%.2f"
                ),
                "SOB": st.column_config.DateColumn(label="SOB", format="DD-MM-YYYY", step=1),
                "ETA": st.column_config.DateColumn(label="ETA", format="DD-MM-YYYY", step=1),
                "BL Type": st.column_config.SelectboxColumn(label="BL Type", options=["DIRECT", "MASTER"])
            },
        )

        # Save button
        if st.button("Update"):
            try:
                # Auto-fill today's date for empty 'Date of Creation'
                today = pd.Timestamp.today().normalize()
                edited_df['Date of Creation'].fillna(today, inplace=True)
                edited_df['Payment Request Date'].fillna(today, inplace=True)
                # Save to Excel
                edited_df.to_excel(EXCEL_FILE, index=False)
                st.success("Data successfully updated.")
                st.rerun()
            except Exception as e:
                st.error(f"Failed to update data: {e}")

def bl_release():
    if os.path.exists(EXCEL_FILE):
        df = pd.read_excel(EXCEL_FILE)

        # Ensure consistent column names
        df.columns = df.columns.str.strip()

        # Filter for relevant rows (paid & not yet released)
        df_filtered = df[
            (df['Status'].astype(str).str.strip().str.lower() == 'paid') &
            (df['BL Released?'].astype(str).str.strip().str.lower() != 'released')
        ].copy()  # Use .copy() to avoid SettingWithCopyWarning

        # Convert 'BL Released?' to checkbox-friendly format
        df_filtered['BL Released?'] = df_filtered['BL Released?'].astype(str).str.strip().str.lower() == 'released'

        # Define editable columns
        editable_columns = ['BL Released?']
        disabled_columns = [col for col in df_filtered.columns if col not in editable_columns]

        # Show the editor
        edited_df = st.data_editor(
            df_filtered,
            hide_index=True,
            use_container_width=True,
            disabled=disabled_columns,
            column_config={
                'BL Released?': st.column_config.CheckboxColumn(label='BL Released?')
            }
        )

        # Update logic
        if st.button("Update"):
            update_count = 0
            for _, row in edited_df.iterrows():
                if row['BL Released?']:  # Only update if checkbox is checked
                    cond = (
                        (df['MBL #'] == row['MBL #']) &
                        (df['Carrier Invoice #'] == row['Carrier Invoice #']) &
                        (df['Currency'] == row['Currency']) &
                        (df['Amount'] == row['Amount']) &
                        (df['Status'].astype(str).str.strip().str.lower() == 'paid')
                    )
                    df.loc[cond, 'BL Released?'] = 'Released'
                    update_count += 1

            df.to_excel(EXCEL_FILE, index=False)
            st.success(f"✅ {update_count} row(s) marked as 'Released'.")
            st.rerun()

def display_report():
    st.subheader("Payment Request Report")
    if os.path.exists(EXCEL_FILE):
        df = pd.read_excel(EXCEL_FILE)
        st.dataframe(df)
    else:
        st.info("No data available.")

def display_centralOps_report():
    with st.sidebar:
        selected = option_menu(
            menu_title="Central Ops Panel",
            options=["Payment Request","BL Release","Report"],
            # icons=["Form","table"],
            default_index=0,
            menu_icon="cast"
        )

    if selected == "Payment Request":
        display_payment_form()
    elif selected == "BL Release":
        bl_release()
    else:
        display_report()

        
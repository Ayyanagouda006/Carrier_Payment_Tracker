import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os
from streamlit_option_menu import option_menu

EXCEL_FILE = r"data/payment_requests.xlsx"

def pay_plan():
    if os.path.exists(EXCEL_FILE):
        ori_df = pd.read_excel(EXCEL_FILE)

        df = ori_df.copy()
        df = df[~df['Status'].isin(['Paid']) & ~df['Status'].str.startswith('Pay On:', na=False)]
        # Convert necessary columns
        df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce')
        df['GST Amount in INR (If Freight in USD and GST in INR)'] = pd.to_numeric(
            df['GST Amount in INR (If Freight in USD and GST in INR)'], errors='coerce'
        )
        df['Payment Request Date'] = pd.to_datetime(df['Payment Request Date'], errors='coerce')

        # Compute INR and USD values
        df['Amount_INR'] = df.apply(
            lambda row: row['Amount'] if row['Currency'] == 'INR' else row['GST Amount in INR (If Freight in USD and GST in INR)'],
            axis=1
        )
        df['Amount_USD'] = df.apply(
            lambda row: row['Amount'] if row['Currency'] == 'USD' else 0,
            axis=1
        )

        # Group by MBL # and aggregate
        summary = df.groupby('MBL #').agg({
            'LDC Cut-off': 'first',
            'BL Type': 'first',
            'Amount_INR': 'sum',
            'Amount_USD': 'sum',
            'Payment Request Date': 'max',
            'Status': 'first'
        }).reset_index()

        # Format columns
        summary.rename(columns={
            'Amount_INR': 'Amount (INR)',
            'Amount_USD': 'Amount (USD)',
        }, inplace=True)
        summary['Payment Request Date'] = summary['Payment Request Date'].dt.strftime('%d-%m-%Y')

        # Add checkbox column for selection
        summary['Selected'] = False

        # Show editable table with checkboxes
        edited_summary = st.data_editor(
            summary,
            hide_index = True,
            use_container_width=True,
            column_config={"Selected": st.column_config.CheckboxColumn("Select",pinned=True),
                           'LDC Cut-off': st.column_config.DateColumn(label='LDC Cut-off', format="DD-MM-YYYY")},
            disabled=["MBL #",'BL Type',"Amount (INR)", "Amount (USD)", "Payment Request Date",'LDC Cut-off','Status']
        )

        # Filter rows where Selected is True
        selected_rows = edited_summary[edited_summary['Selected'] == True]

        if not selected_rows.empty:
            total_inr = selected_rows['Amount (INR)'].sum()
            total_usd = selected_rows['Amount (USD)'].sum()

            st.markdown("### 🧾 Total Summary for Selected MBLs:")
            st.write(f"**Total Amount (INR): ₹ {total_inr:,.2f}**")
            st.write(f"**Total Amount (USD): $ {total_usd:,.2f}**")

            # Radio buttons for payment date
            payment_option = st.radio(
                "Select Payment Date:",
                ["Pay Today", "Pay Tomorrow", "Custom Date"],
                horizontal=True
            )

            # Set selected date
            if payment_option == "Pay Today":
                selected_date = datetime.today().date()
            elif payment_option == "Pay Tomorrow":
                selected_date = datetime.today().date() + timedelta(days=1)
            else:
                selected_date = st.date_input("Select Custom Payment Date:", value=datetime.today().date())

            st.success(f"🗓️ Payment Scheduled Date: {selected_date.strftime('%d-%m-%Y')}")

            if st.button("✅ Update Payment Date for Selected MBLs"):
                try:
                    # Ensure necessary columns exist
                    if 'Scheduled Payment Date' not in ori_df.columns:
                        ori_df['Scheduled Payment Date'] = pd.NaT
                    if 'Status' not in ori_df.columns:
                        ori_df['Status'] = ""

                    # Convert MBL # to string in both DataFrames
                    ori_df['MBL #'] = ori_df['MBL #'].astype(str)
                    selected_rows['MBL #'] = selected_rows['MBL #'].astype(str)

                    selected_mbls = selected_rows['MBL #'].tolist()

                    # Check if MBLs exist in ori_df
                    matching_rows = ori_df[ori_df['MBL #'].isin(selected_mbls)]

                    if matching_rows.empty:
                        st.warning("⚠️ No matching MBLs found in original data.")
                    else:
                        # Format date and status
                        formatted_date = pd.to_datetime(selected_date)
                        status_text = f"Pay On: {formatted_date.strftime('%d-%b-%Y')}"

                        # Update both columns
                        ori_df.loc[ori_df['MBL #'].isin(selected_mbls), 'Scheduled Payment Date'] = formatted_date
                        ori_df.loc[ori_df['MBL #'].isin(selected_mbls), 'Status'] = status_text

                        date_columns = [
                            'Date of Creation', 'Invoice Date', 'SOB', 'ETA',
                            'Payment Request Date', 'Payment Date'
                        ]

                        # Convert to datetime and then format to dd-mm-yyyy
                        for col in date_columns:
                            ori_df[col] = pd.to_datetime(ori_df[col], errors='coerce').dt.strftime('%d-%m-%Y')

                        # Save to Excel
                        ori_df.to_excel(EXCEL_FILE, index=False)

                        st.success("✅ Updated Scheduled Payment Date and Status.")
                        st.rerun()

                except Exception as e:
                    st.error(f"❌ Error updating rows: {e}")
    else:
        st.info("No data available.")



def payment_planner():
    with st.sidebar:
        selected = option_menu(
            menu_title="Payment Planner Panel",
            options=["Payment Planning"],
            icons=["table"],
            default_index=0,
            menu_icon="cast"
        )

    if selected == "Payment Planning":
        pay_plan()

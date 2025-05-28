import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os
from io import BytesIO
from streamlit_option_menu import option_menu

EXCEL_FILE = r"data/payment_requests.xlsx"

def pay_make():
    if os.path.exists(EXCEL_FILE):
        df = pd.read_excel(EXCEL_FILE)

        # Convert Scheduled Payment Date to datetime
        df['Scheduled Payment Date'] = pd.to_datetime(df['Scheduled Payment Date'], errors='coerce')
        df['Payment Request Date'] = pd.to_datetime(df['Payment Request Date'], errors='coerce')

        # Payment Date Filter
        filter_option = st.radio(
            "📅 Filter payments scheduled for:",
            ("Today", "Tomorrow", "Custom Date")
        )

        selected_date = None
        today = datetime.today().date()

        if filter_option == "Today":
            selected_date = today
        elif filter_option == "Tomorrow":
            selected_date = today + timedelta(days=1)
        else:
            selected_date = st.date_input("Select Custom Date")

        # Filter rows
        df_filtered = df[
            (df['Status'].astype(str).str.strip().str.lower() != 'paid') &
            (df['Scheduled Payment Date'].dt.date == selected_date)
        ]

        df_filtered['Payment Date'] = pd.to_datetime(df_filtered['Payment Date'], errors='coerce')
        df_filtered['IRN Required?'] = False  # UI-only column


        # Show count of payments
        st.markdown(f"### 💳 Number of payments: **{len(df_filtered)}**")

        # Define editable columns
        editable_columns = [
            'Payment Date', 'Payment Reference Number', 'Amount Paid Currency',
            'Amount Paid', 'Payment Mode', 'SWIFT Certificate Link','IRN Required?'
        ]
        disabled_columns = [col for col in df_filtered.columns if col not in editable_columns]

        # Display editable DataFrame
        edited_df = st.data_editor(
            df_filtered,
            hide_index=True,
            use_container_width=True,
            disabled=disabled_columns,
            column_config={
                "Payment Date": st.column_config.DateColumn(
                    label="Payment Date",
                    format="DD-MM-YYYY",
                    step=1
                ),
                "Amount Paid Currency": st.column_config.SelectboxColumn(
                    label="Amount Paid Currency",
                    options=["INR"]
                ),
                "Amount Paid": st.column_config.NumberColumn(
                    label="Amount Paid",
                    step=0.01,
                    format="%.2f"
                ),
                "SWIFT Certificate Link": st.column_config.LinkColumn(
                    label="SWIFT Certificate Link"
                ),
                'IRN Required?': st.column_config.CheckboxColumn(
                    label='IRN Required?'
                )
            }
        )

        # Button to save changes
        if st.button("Update"):
            today = datetime.today().date()

            for mbl in edited_df['MBL #'].unique():
                mbl_rows = edited_df[edited_df['MBL #'] == mbl]

                total_expected_inr = 0
                total_expected_usd = 0
                total_paid_inr = 0
                usd_payment = False
                status = ''
                for _, row in mbl_rows.iterrows():
                    irn_required = row.get('IRN Required?', False)
                    irn_value = "Required" if irn_required else ""
                    df.loc[
                        (df['MBL #'] == row['MBL #']) &
                        (df['Currency'] == row['Currency']) &
                        (df['Amount'] == row['Amount']),
                        'IRN Invoice'
                    ] = ('Required' if row.get('IRN Required?', False) else None)

                    status = row['Status']
                    if pd.notna(row['SWIFT Certificate Link']) and row['SWIFT Certificate Link'].strip() != '':
                        usd_payment = True

                    # Update payment details in original DataFrame
                    df.loc[
                        (df['MBL #'] == row['MBL #']) &
                        (df['Currency'] == row['Currency']) &
                        (df['Amount'] == row['Amount']),
                        editable_columns
                    ] = row[editable_columns].values

                    if row['Currency'] == 'INR':
                        amt = pd.to_numeric(row['Amount'], errors='coerce')
                        amt = 0 if pd.isna(amt) else amt
                        total_expected_inr += amt

                    gst_amt = pd.to_numeric(
                        row.get('GST Amount in INR (If Freight in USD and GST in INR)', 0),
                        errors='coerce'
                    )
                    gst_amt = 0 if pd.isna(gst_amt) else gst_amt
                    total_expected_inr += gst_amt

                    if row['Currency'] == 'USD':
                        samt = pd.to_numeric(row['Amount'], errors='coerce')
                        samt = 0 if pd.isna(samt) else samt
                        total_expected_usd += samt

                    if row['Amount Paid Currency'] == 'INR':
                        total_paid_inr += pd.to_numeric(row['Amount Paid'], errors='coerce') or 0

                print(mbl,total_expected_inr)
                # Determine payment status
                if total_paid_inr == total_expected_inr:
                    if total_expected_usd > 0:
                        if not usd_payment:
                            status_text = 'USD Pending'
                            payment_date = today
                        else:
                            status_text = 'Paid'
                            payment_date = today
                    else:
                        status_text = 'Paid'
                        payment_date = today
                elif (total_paid_inr < total_expected_inr) and total_paid_inr!=0:
                    difference = round(total_expected_inr - total_paid_inr, 2)
                    if total_expected_usd > 0:
                        if not usd_payment:
                            status_text = f'Part Payment: ₹{difference} Pending | USD Pending'
                            payment_date = today
                        else:
                            status_text = f'Part Payment: ₹{difference} Pending'
                            payment_date = today
                    else:
                        status_text = f'Part Payment: ₹{difference} Pending'
                        payment_date = today
                elif total_paid_inr > total_expected_inr:
                    status_text = 'Over Paid: Check Amount'
                    payment_date = today
                else:
                    status_text = status
                    payment_date = None

                # Apply status to all rows of this MBL
                df.loc[df['MBL #'] == mbl, 'Status'] = status_text
                df.loc[df['MBL #'] == mbl,'Payment Updated Date'] = payment_date

            # Format date columns
            date_columns = [
                'Date of Creation', 'Invoice Date', 'SOB', 'ETA',
                'Payment Request Date', 'Payment Date', 'Payment Updated Date'
            ]
            for col in date_columns:
                df[col] = pd.to_datetime(df[col], errors='coerce').dt.strftime('%d-%m-%Y')

            df.to_excel(EXCEL_FILE, index=False)
            st.success("✅ Payment details updated successfully!")
            st.rerun()
    else:
        st.info("No data available.")

def convert_df_to_excel(df):
    """Convert DataFrame to an Excel file and return as bytes for downloading."""
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name='Report')
    processed_data = output.getvalue()
    return processed_data

def show_all_payments():
    if os.path.exists(EXCEL_FILE):
        df = pd.read_excel(EXCEL_FILE)

        st.markdown("### 📄 All Payment Records")
        st.dataframe(df, use_container_width=True, hide_index=True)

        # Download as Excel
        download_filename = f"All_Payments_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

        excel_data = convert_df_to_excel(pd.read_excel(EXCEL_FILE))

        st.download_button(
            label="⬇️ Download All Payments as Excel",
            data=excel_data,
            file_name=download_filename,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.warning("⚠️ No data found.")


def payment_maker():
    with st.sidebar:
        selected = option_menu(
            menu_title="Finance Panel",
            options=["Payment Details",  "All Payments"],
            icons=["table", "download"],
            default_index=0,
            menu_icon="cast"
        )


    if selected == "Payment Details":
        pay_make()
    elif selected == "All Payments":
        show_all_payments()


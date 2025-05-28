import streamlit as st
import pandas as pd
import logging


from financerole import payment_maker
from payment_planing import payment_planner
from centralOps_role import display_centralOps_report
# from admin_role import admin

# ---------- Setup Logging ----------
log_file = r"logs/access_logs.log"
logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def log_event(email, event, status="SUCCESS"):
    logging.info(f" {email} | {event} | {status}")

# ---------- Streamlit Config ----------
st.set_page_config(layout="wide")
st.logo(r'data/logo.jpg', size="large")

@st.cache_data
def load_all_sheets():
    try:
        xls = pd.ExcelFile(r"data/Users.xlsx")
        sheet_data = {sheet: xls.parse(sheet) for sheet in xls.sheet_names}
        return sheet_data
    except Exception as e:
        logging.error(f"Failed to load user data sheets: {e}")
        st.error("Failed to load user data.")
        return {}

def get_user_role(email, sheets):
    email = email.strip().lower()

    role_found = []
    for sheet_name, df in sheets.items():
        df['email'] = df['email'].astype(str).str.strip().str.lower()
        if email in df['email'].values:
            role_found.append(sheet_name)

    if not role_found:
        log_event(email, "Role Assigned: view")
        return "view", None
    else:
        log_event(email, f"Role Assigned: {role_found[0]}")
        return role_found[0], None

def main():
    st.markdown("""
    <h1 style='text-align: center; color: #1f77b4;'>🚛💰Carrier Payment Tracker</h1>
    <p style='text-align: center; color: grey;'>Virya Logistics Technologies Pvt Ltd</p>
    """, unsafe_allow_html=True)

    sheets = load_all_sheets()

    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'role' not in st.session_state:
        st.session_state.role = None
    if 'email' not in st.session_state:
        st.session_state.email = None

    if not st.session_state.logged_in:
        email_input = st.text_input("Enter your Agraga Email ID", key="email_input")
        if email_input:
            log_event(email_input.strip(), "Login Attempt")
            role, error = get_user_role(email_input.strip(), sheets)
            if error:
                st.error(error)
            else:
                st.session_state.logged_in = True
                st.session_state.role = role
                st.session_state.email = email_input
                log_event(email_input.strip(), "Login Successful")
                st.rerun()
    else:
        show_role_page(st.session_state.email, st.session_state.role)

    logging.shutdown()

def show_role_page(email, role):
    # st.subheader(f"Welcome, {email.upper()}!")


    if role == "Admin" and email == "anoop.raghavan@agraga.com":
        payment_planner()
    elif role == "Central Ops":
        display_centralOps_report()
    elif role == "Finance":
        payment_maker()
    # elif role == "view":
    #     display_view_report()
    else:
        log_event(email, f"Unrecognized Role: {role}", "WARNING")
        st.warning("Unrecognized role.")

if __name__ == "__main__":
    main()

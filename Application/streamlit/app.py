import streamlit as st
from pagess.login import show_login_page
from pagess.home import show_home_page
from pagess.restaurants import show_restaurants_page
from pagess.regulations import show_regulations_page
from pagess.qn import show_qn_page
import os
from dotenv import load_dotenv

load_dotenv()
FASTAPI_BASE_URL = os.getenv('FASTAPI_URL', 'http://localhost:8000')
SERPI_URL = os.getenv("SERPI_URL")
if 'token' not in st.session_state:
    st.session_state.token = None
if 'page' not in st.session_state:
    st.session_state.page = 'login'
if 'zip_code' not in st.session_state:
    st.session_state.zip_code = ''

def logout():
    if 'token' in st.session_state:
        del st.session_state['token']
    st.session_state.page = "login"
    st.rerun()

def global_sidebar():
    st.sidebar.title("Navigation")
    page_selection = st.sidebar.radio("Go to:", ["Home", "Restaurants", "Regulations Q&A", "Q&N"])

    # Global ZIP code input
    zip_input = st.sidebar.text_input("Enter ZIP code:", value=st.session_state.zip_code)
    if zip_input != st.session_state.zip_code:
        st.session_state.zip_code = zip_input

    if st.sidebar.button("Logout"):
        logout()

    return page_selection

def main():
    if st.session_state.page == "login":
        show_login_page(FASTAPI_BASE_URL)
    else:
        page_selection = global_sidebar()

        if page_selection == "Home":
            st.write(SERPI_URL)
            print("API : ", SERPI_URL)
            show_home_page(SERPI_URL)
            # show_home_page(FASTAPI_BASE_URL)
        elif page_selection == "Restaurants":
            show_restaurants_page(FASTAPI_BASE_URL)
        elif page_selection == "Regulations Q&A":
            show_regulations_page(FASTAPI_BASE_URL)
        elif page_selection == "Q&N":
            show_qn_page(FASTAPI_BASE_URL, st.session_state.zip_code)

if __name__ == "__main__":
    main()

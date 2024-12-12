# damg7245_final_project/Application/streamlit/pagess/login.py

import streamlit as st
import requests

def show_login_page(api_base_url):
    st.title("Login")

    # If already logged in, redirect to home
    if st.session_state.token:
        st.session_state.page = "home"
        st.rerun()

    with st.form(key='login_form'):
        username = st.text_input("Username")
        password = st.text_input("Password", type='password')
        login_button = st.form_submit_button("Login")

    if login_button:
        if not username or not password:
            st.error("Username and Password are required.")
        else:
            token_url = f"{api_base_url}/token"
            try:
                response = requests.post(token_url, data={"username": username, "password": password})
                if response.status_code == 200:
                    data = response.json()
                    st.session_state.token = data.get('access_token')
                    st.session_state.page = "home"
                    st.success("Login successful!")
                    st.rerun()
                else:
                    st.error("Invalid credentials or login failed.")
            except requests.exceptions.RequestException:
                st.error("Error connecting to authentication service.")

    st.markdown("---")
    st.write("Don't have an account? Register below:")
    with st.expander("Register"):
        show_register_form(api_base_url)


def show_register_form(api_base_url):
    with st.form(key='register_form'):
        register_username = st.text_input("Username", key='register_username')
        register_password = st.text_input("Password", type='password', key='register_password')
        register_button = st.form_submit_button("Register")

    if register_button:
        if not register_username or not register_password:
            st.error("Username and Password are required.")
        else:
            register_url = f"{api_base_url}/register"
            try:
                response = requests.post(register_url, json={"username": register_username, "password": register_password})
                if response.status_code == 200:
                    st.success("Registration successful! Please login.")
                elif response.status_code == 400:
                    st.error("User already exists.")
                else:
                    st.error("Registration failed. Please try again.")
            except requests.exceptions.RequestException:
                st.error("Error connecting to registration service.")

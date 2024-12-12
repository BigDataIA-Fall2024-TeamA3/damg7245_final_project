# damg7245_final_project/Application/streamlit/pagess/qn.py

import streamlit as st
import requests

def show_qn_page(api_base_url, city):
    st.title(f"In-depth Report on Opening a Restaurant in {city}")

    # Here, you can use an LLM or a custom endpoint to generate a comprehensive report:
    # - Competitor analysis
    # - Menu recommendation
    # - Legal regulation summary
    # - Steps involved
    # - Etc.

    # For now, just a placeholder:
    if st.button("Generate In-Depth Report"):
        report = generate_in_depth_report(api_base_url, city, st.session_state.token)
        st.write(report)

def generate_in_depth_report(api_base_url, city, token):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    # Mock call to a backend endpoint:
    # response = requests.post(f"{api_base_url}/generate_detailed_report", json={"city": city}, headers=headers)
    # if response.status_code == 200:
    #     return response.json()["report"]

    return f"**Detailed Report for {city}:**\n\n- Competitor Analysis: X number of restaurants...\n- Menu Recommendations: Consider vegetarian options...\n- Legal Regulations: Obtain a ServSafe certificate...\n- Steps: 1) Register your business 2) Obtain licenses..."

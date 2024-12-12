# damg7245_final_project/Application/streamlit/pagess/regulations.py

import streamlit as st
import requests
from io import BytesIO


def show_regulations_page(api_base_url):
    st.title("Government Food Regulations in Massachusetts")
    st.write("Ask questions about food regulations.")

    query = st.text_input("Ask a question about regulations:")
    
    # Handling the query and PDF upload
    if st.button("Ask"):
        if query.strip():
            payload = {"question": query}
            try:
                # Making a POST request to the FastAPI /ask endpoint
                response = requests.post(f"{api_base_url}/ask", json=payload)
                
                # Handling the response
                if response.status_code == 200:
                    answer = response.json().get("answer", "No answer found.")
                    st.write(f"**Answer:** {answer}")
                else:
                    error_detail = response.json().get('detail', 'Unknown error')
                    st.error(f"Error: {error_detail}")
            except Exception as e:
                st.error(f"Failed to connect to the backend: {e}")
        
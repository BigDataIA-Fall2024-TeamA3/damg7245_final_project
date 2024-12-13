# damg7245_final_project/Application/streamlit/pagess/qn.py
import streamlit as st
import requests
import os
import json
import math

def clean_data_for_json(obj):
    if isinstance(obj, float) and math.isnan(obj):
        return None
    return obj

def show_qn_page(api_base_url, city):
    st.title(f"In-depth Q&A & Business Planning Assistance for {city}")

    if 'token' not in st.session_state or not st.session_state.token:
        st.error("Please log in to access Q&N page.")
        return

    # Remind user they can ask for detailed plans:
    st.markdown("""
    **Ask for a detailed business plan, comprehensive competitive analysis, or other restaurant-business-related questions.**  
    For example:  
    - "Give me a comprehensive competitive analysis of restaurants at my ZIP code."  
    - "Help me prepare a detailed business plan to open a restaurant here."
    """)

    restaurants_data = st.session_state.get("restaurants_for_qn", [])
    zip_code = st.session_state.get("zip_code", "02115")

    cleaned_restaurants_data = []
    for r in restaurants_data:
        new_r = {}
        for k, v in r.items():
            if isinstance(v, float) and math.isnan(v):
                new_r[k] = None
            else:
                new_r[k] = v
        cleaned_restaurants_data.append(new_r)

    if "qn_history" not in st.session_state:
        st.session_state["qn_history"] = []

    user_input = st.text_input("Enter your query (e.g., 'Give me a detailed business plan for opening a restaurant'):")
    if st.button("Send"):
        if user_input.strip():
            st.session_state["qn_history"].append(("You", user_input))
            headers = {
                "Authorization": f"Bearer {st.session_state.token}",
                "Content-Type": "application/json"
            }
            payload = {
                "question": user_input,
                "restaurants_data": cleaned_restaurants_data,
                "zip_code": zip_code
            }

            json_payload = json.dumps(payload)

            response = requests.post(
                f"{api_base_url}/qn_agent", 
                data=json_payload,
                headers=headers
            )

            if response.status_code == 200:
                data = response.json()
                answer = data.get("answer", "No answer")
                st.session_state["qn_history"].append(("Assistant", answer))
            else:
                st.session_state["qn_history"].append(("Assistant", f"Error: {response.text}"))

    # Display conversation history
    for speaker, msg in st.session_state["qn_history"]:
        st.markdown(f"**{speaker}:** {msg}")

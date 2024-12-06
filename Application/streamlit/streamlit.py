import streamlit as st
import requests


st.title("Massachusetts Food Regulation Q&A")
st.write("Ask questions about food regulations in Massachusetts.")


question = st.text_input("Enter your question:")

if st.button("Ask"):
    if question.strip():
        try:
            url = "http://localhost:8000/ask"
            
            response = requests.post(url, json={"question": question})
        
            if response.status_code == 200:
                answer = response.json().get("answer", "No answer found.")
                st.write(f"**Answer:** {answer}")
            else:
                st.error(f"Error: {response.json().get('detail', 'Unknown error')}")
        except Exception as e:
            st.error(f"Failed to connect to backend: {e}")
    else:
        st.error("Please enter a valid question.")
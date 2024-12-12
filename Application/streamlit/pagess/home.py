# damg7245_final_project/Application/streamlit/pagess/home.py

import streamlit as st
import requests
import textwrap
import json
import os

articles_per_view = 3
SERPI_URL = os.getenv("SERPI_URL")
        
sample_news_json_name = os.path.join("sample_data", "sample_news_response.json")

# function to find the file path and read the json file
def get_news_json_path():
    current_dir = os.path.dirname(__file__)
    sample_news_json_path = os.path.join(current_dir, sample_news_json_name)
    return sample_news_json_path

# PRODUCTION
# @st.cache
def get_news(query_str = ""):
    try:
        # Set and send an ngrok-skip-browser-warning request header with any value.
        news_curator_url = f"{SERPI_URL}/get_news"
        headers = {"ngrok-skip-browser-warning": "any_value"}
        response = requests.get(news_curator_url, headers=headers)
        response.raise_for_status()
        articles = response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching articles: {e}")
        articles = []
    return articles



# Testing for local 
# comment in production
# def get_news():
#     with open(get_news_json_path(), "r") as f:
#         articles = json.load(f)
#     return articles



def display_row_news(articles = [], start_index = 0, articles_per_view = 3):
    cont = st.container()
    with cont:
        cols = st.columns(articles_per_view)

        for i in range(articles_per_view):
            article_index = start_index + i
            if article_index < len(articles):
                article = articles[article_index]

                # Truncate title and summary
                truncated_title = textwrap.shorten(article["title"], width=50, placeholder="...")
                truncated_summary = textwrap.shorten(article["article_summary"], width=100, placeholder="...")

                image_height = "200px"
                backup_image = "https://www.businessnewsdaily.com/_next/image?url=https%3A%2F%2Fimages.businessnewsdaily.com%2Fapp%2Fuploads%2F2019%2F05%2F14131923%2Fonline-reselling.png&w=3840&q=75"
                display_picture = article.get("display_picture", backup_image)
                if not display_picture:
                    display_picture = backup_image
                with cols[i]:
                    st.markdown(
                        f"""
                        <div style="border:1px solid #ccc; border-radius:5px; padding:10px; text-align:center;">
                            <a href="{article["article_link"]}" target="_blank" style="text-decoration:none; color:inherit;">
                                <img src="{display_picture}" 
                                     style="width:100%; height:{image_height}; object-fit:cover; border-radius:5px; margin-bottom:10px;" />
                                <h3 style="margin:10px 0; font-size:1.1em;">{truncated_title}</h3>
                            </a>
                            <p style="font-size:0.9em; color:#555;">{truncated_summary}</p>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )


def show_home_page(api_base_url=SERPI_URL):
    st.title(f"Welcome to Restaurant Business Assistant")
    st.write(f"Curated news for you")
    
    news_curator = st.container(border=True)
    with news_curator:
        # query_str=st.text_input("Enter the query string")
        articles = get_news()

        # Calculate the maximum starting index we can show without going out of range
        import math
        max_num_of_rows = max(1, math.ceil(len(articles) / articles_per_view))
        for row_num in range(max_num_of_rows):
            start_index = row_num * articles_per_view
            display_row_news(articles, start_index, articles_per_view)

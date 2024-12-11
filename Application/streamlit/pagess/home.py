import streamlit as st
import requests

def show_home_page(api_base_url):
    st.title(f"Welcome to Restaurant Business Assistant for {st.session_state.selected_city}")

    # Fetching news articles related to food, regulations, etc.
    # Assume you have a FastAPI endpoint that returns a list of news articles.
    # For demo, we’ll just mock a response.
    articles = fetch_news_articles(api_base_url, st.session_state.selected_city, st.session_state.token)

    if not articles:
        st.info("No news articles found.")
    else:
        for article in articles:
            st.subheader(article['title'])
            st.write(article['content'])

            # Generate summary using LLM (FastAPI endpoint)
            if st.button(f"Generate Summary for: {article['title']}"):
                summary = generate_article_summary(api_base_url, article['id'], st.session_state.token)
                st.write("**Summary:**")
                st.write(summary)


def fetch_news_articles(api_base_url, city, token):
    # Placeholder: You would implement an endpoint in FastAPI to fetch articles.
    # For now, we return a static list.
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    # response = requests.get(f"{api_base_url}/news?city={city}", headers=headers)
    # if response.status_code == 200:
    #     return response.json()

    return [
        {"id": 1, "title": f"New Food Trend in {city}", "content": "Chefs in the city are experimenting with new vegan dishes..."},
        {"id": 2, "title": f"Government Update on Regulations in {city}", "content": "The local government introduced new sanitary measures..."}
    ]

def generate_article_summary(api_base_url, article_id, token):
    # Placeholder for a summary endpoint
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    # response = requests.post(f"{api_base_url}/article_summary", json={"article_id": article_id}, headers=headers)
    # if response.status_code == 200:
    #     return response.json().get("summary", "No summary available")

    return "This is a mock summary for demonstration purposes."

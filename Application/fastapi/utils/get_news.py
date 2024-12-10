from newspaper import Article
from lxml_html_clean import Cleaner
from date_guesser import guess_date, Accuracy
from langdetect import detect, detect_langs

from typing import Annotated, TypedDict
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, END
import operator
from anthropic import Anthropic
from dotenv import load_dotenv, find_dotenv
import os
import time
from tenacity import retry, wait_exponential, stop_after_attempt
from serpapi import GoogleSearch

import requests
from datetime import datetime


# from extract_article import extract_article
# import requests_cache

#Custom global cache
# requests_cache.install_cache('serpapi_cache', expire_after=7200)  

# Load environment variables
dotenv_path = find_dotenv()
load_dotenv(dotenv_path)


# Set up Anthropic API key
os.environ["ANTHROPIC_API_KEY"] = ""
serpapi_api_key = ""


INITIAL_STATE = {
    "messages": [],
    "news_items": [],
    "user_input": "",
    "engineered_prompt": []
}

class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], operator.add]
    news_items: list[dict]
    user_input: str
    engineered_prompt: list[str]

graph = StateGraph(AgentState)

# Initialize Anthropic client
anthropic = Anthropic()

# cleaner utility
def validate_article(article_data):
    def validate_link(link):
        try:
            response = requests.head(link, allow_redirects=False, timeout=10)
            return response.status_code == 200
        except requests.RequestException:
            return False

    def validate_details(title, source, date):
        if not title or not isinstance(title, str):
            return False
        if not source or not isinstance(source, dict) or 'name' not in source or not source['name']:
            return False
        try:
            datetime.strptime(date, "%m/%d/%Y, %I:%M %p, %z UTC")
            return True
        except (ValueError, TypeError):
            return False

    details_valid = validate_details(
        article_data['title'],
        article_data['source'],
        article_data['date']
    )
    link_valid = validate_link(article_data['link'])

    return link_valid and details_valid


def extract_article(url=None):

    if url == None:
        return 'url parameter is required', 400

    article = Article(url)

    # article = newspaper.article(url)
    # print(article.summary)
    article.download()

    if (article.download_state == 2):
        article.parse()
        article_dict = {}
        article_dict['status'] = 'ok'

        article_dict['article'] = {}
        article_dict['article']['source_url'] = article.source_url


        try:
            guess = guess_date(url = url, html = article.html)
            article_dict['article']['published'] = guess.date
            article_dict['article']['published_method_found'] = guess.method
            article_dict['article']['published_guess_accuracy'] = None
            if guess.accuracy is Accuracy.PARTIAL:
                article_dict['article']['published_guess_accuracy'] = 'partial'
            if guess.accuracy is Accuracy.DATE:
                article_dict['article']['published_guess_accuracy'] = 'date'
            if guess.accuracy is Accuracy.DATETIME:
                article_dict['article']['published_guess_accuracy'] = 'datetime'
            if guess.accuracy is Accuracy.NONE:
                article_dict['article']['published_guess_accuracy'] = None
        except:
            article_dict['article']['published'] = article.publish_date
            article_dict['article']['published_method_found'] = None
            article_dict['article']['published_guess_accuracy'] = None

        article_dict['article']['title'] = article.title
        article_dict['article']['text'] = article.text
        article_dict['article']['authors'] = list(article.authors)

        try:
            title_lang = detect(article.title)
        except:
            title_lang = None


        try:
            text_lang = detect(article.text)
        except:
            text_lang = None

        article_dict['article']['images'] = list(article.images)
        article_dict['article']['top_image'] = article.top_image
        article_dict['article']['meta_image'] = article.meta_img
        article_dict['article']['movies'] = list(article.movies)
        article_dict['article']['meta_keywords'] = list(article.meta_keywords)
        article_dict['article']['summary'] = article.meta_description
        article_dict['article']['tags'] = list(article.tags)
        article_dict['article']['meta_description'] = article.meta_description
        article_dict['article']['meta_lang'] = article.meta_lang
        article_dict['article']['title_lang'] = str(title_lang)
        article_dict['article']['text_lang'] = str(text_lang)
        article_dict['article']['meta_favicon'] = article.meta_favicon
        # return jsonify(article_dict)
        return article_dict

    else:
        article_dict = {}
        article_dict['status'] = 'error'
        article_dict['article'] =  article.download_exception_msg
        # return jsonify(article_dict)
        return article_dict



# AGENT CODE

# Claude LLM function with retry logic
@retry(wait=wait_exponential(multiplier=1, min=4, max=10), stop=stop_after_attempt(3))
def claude_llm(prompt):
    try:
        response = anthropic.messages.create(
            model="claude-3-opus-20240229",
            max_tokens=1024,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        return response.content[0].text
    except anthropic.RateLimitError as e:
        print(f"Rate limit exceeded. Retrying in a few seconds...")
        time.sleep(5)  # Wait for 5 seconds before retrying
        raise e

# Prompt Engineer Agent
def prompt_engineer(state):
    user_input = state["user_input"]

    # News topic finder prompt
    news_topic_search_prompt = f'''
    You are a prompt engineer who specialises in creating prompts for google topic search for curated articles only for businesses in the following list,
      1. small restaurant owners
      2. food truck owners
      3. cafes
    and only in locations within massachusetts. This is the user input: {user_input}
    Can you generate a list of 2 topics that will be relevant to his query and intent?
    The topics should follow these guidelines
    positive_resources are including business growth, have valuable information, upcoming trends, truthful information, upcoming events in the locality
    cost-effective directives to compound growth.
    negative_resources are commercial blogs, seo blogs, ads, company product, influencer content, etc, false info

    Follow this format for output: "<topic 1>" | "<topic 2>" | ... | "<topic 10>"
    '''

    prompt = news_topic_search_prompt
    engineered_prompt = claude_llm(prompt)
    split_prompt = engineered_prompt.split(" | ")
    print("\n--- Prompt Engineer Output ---")
    print(f"Engineered Prompt: {split_prompt}")
    print({"engineered_prompt": split_prompt, "messages": state["messages"] + [HumanMessage(content="Prompt engineering completed.")]})
    return {"engineered_prompt": split_prompt, "messages": state["messages"] + [HumanMessage(content="Prompt engineering completed.")]}


# News Collector Agent using SerpAPI
def news_collector(state):
    final_results = []
    # UNCOMMENT in prod
    # engineered_prompt = state.get("engineered_prompt", ["Latest small business news for food business owners in massachusetts"])  
    
    # Dummy prompt result below
    engineered_prompt = ["Latest small business news for food business owners in massachusetts"]  # Use the engineered prompt
    
    for ep in engineered_prompt:
        print(f'topic: {ep}')
        search_params = {
            "engine": "google_news",
            "q": ep.strip(f'"'),
            "api_key": serpapi_api_key,
            "num": 20,
            "hl": "en",
            "location": "Massachusetts, United States",
            "tbs": "qdr:w"
        }
        # ,"tbs": "qdr:w"  # Last week

        search = GoogleSearch(search_params)
        results = search.get_dict()
        print(results)
        if results.get("error"):
            continue
        else:
          final_results+=(results.get("news_results", []))
          print(len(final_results))

    news_items = final_results

    print("\n--- News Collector Output ---")

    # check if errors
    if len(news_items) in [0, 1]:
        print("No news items found________", news_items)
        return {"news_items": [], "messages": state["messages"] + [HumanMessage(content="News collection completed.")]}

    print(f"Collected {len(news_items)} news items")
    cleaned_news_items = [article for article in news_items if validate_article(article)]

    # extract only live articles
    print(f"Collected {len(cleaned_news_items)} cleaned items")
    for item in cleaned_news_items:
        print(f"- {item['title']}")

    return {
        "news_items": cleaned_news_items,
        "messages": state["messages"] + [HumanMessage(content="News collection completed.")]
    }

# Summarizer Agent with rate limiting
def summarizer(state):
    summaries = []
    print("\n--- Summarizer Output ---")
    for item in state["news_items"]:
        # prompt = f"You are a summarizer. Provide a concise summary of this article: {item.get('link')}"
        # summary = claude_llm(prompt)
        item_info = item
        # summary = item.get('title')
        extracted_article = extract_article(item.get('link'))
        item_info["display_picture"]= item.get('thumbnail')
        item_info["article_link"]= item.get('link')
        try:
          item_info["article_summary"]= extracted_article['article']['summary']
        except:
          item_info["article_summary"]= "Article on growing your business and creating value"
        item_info["favorite_status"]= False

        summaries.append(item_info)


        print(f"Summarized: {item['title']}")
        print(f'''Summary: {item_info["article_summary"]}...''')
        # time.sleep(1)  # Wait for 12 seconds between API calls
    return {"news_items": summaries}


def get_news_articles(title_str = None, state=None):
    articles = []
    print("\n--- get_news_articles ---")
    if title_str is None or state is None:
        return articles
    try:
      titles_list = title_str.lower().split(" | ")
      news_items_dict = state.get("news_items")

      for item in news_items_dict:
        if item["title"].lower() in titles_list:
          articles.append(item)
      
      return articles
    except:
        print("No news items found")
        return articles


    

# Supervisor Agent
def supervisor(state):
    delimiter = " | "
    cleaned_article_list = state.get("news_items")
    cleaned_titles = ""
    for item in cleaned_article_list:
        cleaned_titles = cleaned_titles + delimiter + item['title']
    prompt = f'''
    You are a supervisor. Based on the users input and a given list of articles, select top 20 article titles that appear most relevant and for the user.
    This background of the possible consumer for these articles is a new enterprising food business owner only in the following industries
    (food business, food trucks, small restaurants, cafes) interested in new ideas, growth, cost optimization, latest trends, interesting ideas, innovation, etc.

    cleaned_article_list: {cleaned_titles}
    user_input: {state["user_input"]}

    output_format: answer this prompt only in the following format "<title 1> | <title 2> | ... | <title 20>" and no other text
    '''
    moderated_items = claude_llm(prompt)
    filtered_news_items = get_news_articles(moderated_items, state)
    
    print("\n--- Supervisor Output ---")
    print("Moderated Items:")
    print(moderated_items)
    print("filtered_news_items:")
    print(filtered_news_items)
    return {"news_items": filtered_news_items, "messages": [("human", "News aggregation complete.")]}

# Initialize the graph
def init_graph():
    graph.add_node("prompt_engineer", prompt_engineer)
    graph.add_node("news_collector", news_collector)
    graph.add_node("supervisor", supervisor)
    graph.add_node("summarizer", summarizer)

    graph.set_entry_point("prompt_engineer")

    graph.add_edge("prompt_engineer", "news_collector")
    graph.add_edge("news_collector", "supervisor")
    graph.add_edge("supervisor", "summarizer")
    # graph.add_edge("supervisor", END)
    
    graph.add_edge("summarizer", END)
    return graph

# Compile the graph with error handling
def get_news(user_input):
    graph = StateGraph(AgentState)

    graph.add_node("prompt_engineer", prompt_engineer)
    graph.add_node("news_collector", news_collector)
    graph.add_node("supervisor", supervisor)
    graph.add_node("summarizer", summarizer)

    graph.set_entry_point("prompt_engineer")

    graph.add_edge("prompt_engineer", "news_collector")
    graph.add_edge("news_collector", "supervisor")
    graph.add_edge("supervisor", "summarizer")
    # graph.add_edge("supervisor", END)
    
    graph.add_edge("summarizer", END)
    INITIAL_STATE["user_input"] = user_input
    workflow = graph.compile()

    # try:
    print("\n=== Starting News Aggregation Workflow ===")
    result = workflow.invoke(INITIAL_STATE)
    print("\n=== Final Output ===")
    print(result["news_items"])
    return result["news_items"]
    # except Exception as e:
    #     print(f"An error occurred: {str(e)}")
    #     return []


# Example usage for get_news (agent)

# if __name__ == "__main__":
#     results = get_news("Find the latest trends in small business technology.")
#     # sample output
#     # "[{'position': 4, 'title': 'After a slow summer, Boston restaurants are cautiously optimistic about fall', 'source': {'name': 'Boston.com', 'icon': 'https://lh3.googleusercontent.com/x2xbDovBkbHheGxsFJhA6hP0TjBuRQfYfRAt3RoNLhh3reh5PWPJhjMklVXTKYxaS8c1-fLWbw', 'authors': ['Katelyn Umholtz']}, 'link': 'https://www.boston.com/food/restaurants/2024/09/09/boston-restaurants-slow-summer-costs-industry/', 'thumbnail': 'https://bdc2020.o0bc.com/wp-content/uploads/2024/09/s3___bgmp-arc_arc-feeds_generic-photos_to-arc_clark_veggie_09-66db5a95c7306-scaled.jpg', 'thumbnail_small': 'https://news.google.com/api/attachments/CC8iK0NnNVBWbU4xZW1SeVlVWjFlbUZ5VFJDeUFSaWNBaWdCTWdhQllJeHV1UVU', 'date': '09/09/2024, 07:00 AM, +0000 UTC', 'display_picture': 'https://bdc2020.o0bc.com/wp-content/uploads/2024/09/s3___bgmp-arc_arc-feeds_generic-photos_to-arc_clark_veggie_09-66db5a95c7306-scaled.jpg', 'article_link': 'https://www.boston.com/food/restaurants/2024/09/09/boston-restaurants-slow-summer-costs-industry/', 'article_summary': "Summer was slow for Boston restaurants, on top of costs still rising. Now, they're hoping fall brings better business for survival.", 'favorite_status': False}, {'position': 5, 'title': 'Mass. is the only state in the nation to significantly cut food waste. How did we do it?', 'source': {'name': 'The Boston Globe', 'icon': 'https://lh3.googleusercontent.com/VojRvMjpootHN8YGYZ7EOZGelMo0fo_uKh61fo-BhjKrUcdlTeaBxU4RsT764Lo7WoxPCSh-uw', 'authors': ['Ivy Scott']}, 'link': 'https://www.bostonglobe.com/2024/12/02/science/massachusetts-food-waste-reduction-success/', 'thumbnail': 'https://bostonglobe-prod.cdn.arcpublishing.com/resizer/v2/6422ZNBHOLDB7GHRLDGHTJMD6U.JPG?auth=da2d0d3d79dc9c4b3f42ba5cd6d8f8834608efa5a578917a35553bbce59e5eed&width=1440', 'thumbnail_small': 'https://news.google.com/api/attachments/CC8iK0NnNHRaVlZzTmpFeGNrVkxkVkY2VFJDM0FSaVRBaWdCTWdZdEFaQ1lDQXc', 'date': '12/02/2024, 12:09 AM, +0000 UTC', 'display_picture': 'https://bostonglobe-prod.cdn.arcpublishing.com/resizer/v2/6422ZNBHOLDB7GHRLDGHTJMD6U.JPG?auth=da2d0d3d79dc9c4b3f42ba5cd6d8f8834608efa5a578917a35553bbce59e5eed&width=1440', 'article_link': 'https://www.bostonglobe.com/2024/12/02/science/massachusetts-food-waste-reduction-success/', 'article_summary': '“Massachusetts alone” has successfully reduced the amount of food sent to landfills, researchers wrote in a recent report.', 'favorite_status': False}]""


# test extract_article util
# y = extract_article("https://www.bonappetit.com/story/best-restaurant-meals-2023")
# print(y["article"]["meta_description"])


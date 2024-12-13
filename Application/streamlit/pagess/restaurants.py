# damg7245_final_project/Application/streamlit/pagess/restaurants.py

import streamlit as st
import requests
import pandas as pd
import altair as alt

def show_restaurants_page(api_base_url: str):
    st.title("Restaurants Nearby & Analysis")

    # Ensure user is logged in
    if 'token' not in st.session_state or not st.session_state.token:
        st.error("Please log in to access this page.")
        return

    zip_code = st.session_state.get("zip_code", "")
    if not zip_code:
        st.warning("Please enter a ZIP code in the sidebar.")
        return

    # We'll store data in st.session_state['restaurants_data'] keyed by zip_code
    if 'cached_zip_code' not in st.session_state or st.session_state.cached_zip_code != zip_code:
        # Fetch fresh data
        headers = {"Authorization": f"Bearer {st.session_state.token}"}
        url = f"{api_base_url}/restaurants"
        params = {"zip_code": zip_code}

        with st.spinner("Fetching restaurant data..."):
            response = requests.get(url, headers=headers, params=params)
            if response.status_code == 200:
                data = response.json()
                restaurants = data.get("restaurants", [])
                st.session_state.restaurants_data = restaurants
                st.session_state.cached_zip_code = zip_code
            else:
                st.error("Failed to fetch restaurants. Check your credentials and API endpoints.")
                return
    else:
        # Use cached data
        restaurants = st.session_state.restaurants_data

    if not restaurants:
        st.info("No restaurants found in this area.")
        return

    # Convert to dataframe for easy analysis
    df = pd.DataFrame(restaurants)

    # Save the data for QN agent use in qn.py (if needed)
    st.session_state["restaurants_for_qn"] = df.to_dict(orient='records')

    # Show basic table
    st.subheader("Restaurant Data")
    st.dataframe(df[["name", "address", "rating", "user_ratings_total", "cuisine_types", "website"]].fillna("N/A"))

    # Visualization: Count of restaurants by cuisine
    st.subheader("Restaurants by Cuisine Type")
    # Expand the cuisine_types column which might have lists
    expanded = df.explode('cuisine_types')
    cuisine_count = expanded.groupby('cuisine_types')['name'].count().reset_index().rename(columns={'name':'count'})
    cuisine_chart = alt.Chart(cuisine_count).mark_bar().encode(
        x='cuisine_types:N',
        y='count:Q',
        tooltip=['cuisine_types', 'count']
    ).properties(title="Count of Restaurants by Cuisine Type")
    st.altair_chart(cuisine_chart, use_container_width=True)

    # Visualization: Popular Restaurants by user ratings (top 10)
    st.subheader("Top 10 Popular Restaurants by User Ratings")
    # Sort by rating desc, then by user_ratings_total desc
    popular_rest = df.dropna(subset=["rating"]).sort_values(["rating", "user_ratings_total"], ascending=[False, False])[:10]
    popular_chart = alt.Chart(popular_rest).mark_bar().encode(
        x='rating:Q',
        y=alt.Y('name:N', sort='-x'),
        tooltip=['name', 'rating', 'user_ratings_total']
    ).properties(title="Top 10 Restaurants by Rating")
    st.altair_chart(popular_chart, use_container_width=True)

    # Visualization: Popular Cuisines by average rating
    st.subheader("Average Rating by Cuisine Type")
    cuisine_rating = expanded.dropna(subset=["rating"]).groupby('cuisine_types')['rating'].mean().reset_index()
    cuisine_rating_chart = alt.Chart(cuisine_rating).mark_bar().encode(
        x='cuisine_types:N',
        y='rating:Q',
        tooltip=['cuisine_types', 'rating']
    ).properties(title="Average Rating by Cuisine Type")
    st.altair_chart(cuisine_rating_chart, use_container_width=True)

    st.subheader("Distribution of User Ratings")
    user_rating_hist = alt.Chart(df.dropna(subset=["user_ratings_total"])).mark_bar().encode(
        alt.X('user_ratings_total:Q', bin=alt.Bin(maxbins=10)),
        y='count()',
        tooltip=['count()']
    ).properties(title="Distribution of Number of User Ratings")
    st.altair_chart(user_rating_hist, use_container_width=True)

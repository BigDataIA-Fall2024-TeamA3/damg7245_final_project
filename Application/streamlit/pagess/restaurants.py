# damg7245_final_project/Application/streamlit/pagess/restaurants.py
import streamlit as st
import requests

def show_restaurants_page(api_base_url: str):
    st.title("Restaurants Nearby")

    # Ensure user is logged in
    if 'token' not in st.session_state or not st.session_state.token:
        st.error("Please log in to access this page.")
        return

    # Fetch the zip code from session state
    zip_code = st.session_state.get("zip_code", "")
    if not zip_code:
        st.warning("Please select a ZIP code from the sidebar.")
        return

    headers = {"Authorization": f"Bearer {st.session_state.token}"}
    url = f"{api_base_url}/restaurants"
    params = {"zip_code": zip_code}

    with st.spinner("Fetching restaurants..."):
        try:
            response = requests.get(url, headers=headers, params=params)
            if response.status_code == 200:
                data = response.json()
                restaurants = data.get("restaurants", [])
                if not restaurants:
                    st.info("No restaurants found in this area.")
                else:
                    for r in restaurants:
                        st.subheader(r["name"])
                        st.write(f"**Address:** {r.get('address', 'N/A')}")
                        rating = r.get("rating")
                        if rating:
                            st.write(f"**Rating:** {rating} ⭐")
                        st.write(f"**User Ratings Total:** {r.get('user_ratings_total', 'N/A')}")
                        st.write(f"**Price Level:** {r.get('price_level', 'N/A')}")
                        st.markdown("---")
            else:
                st.error("Failed to fetch restaurants. Check your credentials and API endpoints.")
        except requests.exceptions.RequestException as e:
            st.error(f"Error fetching data: {e}")

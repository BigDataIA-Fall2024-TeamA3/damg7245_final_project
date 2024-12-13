# damg7245_final_project
# Final Project - Business Assistant Application

## Live application Links
[![new codelabs](https://img.shields.io/badge/codelabs-4285F4?style=for-the-badge&logo=codelabs&logoColor=white)](https://codelabs-preview.appspot.com/?file_id=1biLqN77C3DeM3uWuIz82lfHAJdetSz37mRf4Me9qksw#0)

- Fast API: http://18.209.251.244:8000/docs
- Streamlit Application: http://18.209.251.244:8501/
- Aiflow: http://3.233.200.141:8080/

## Problem Statement 
Opening a restaurant involves navigating a complex array of tasks, from understanding local landscape, market for the service, understanding and obtaining necessary permits and designing a competent service for this market. Small business owners often looking to establish a restaurant in Massachusetts, face challenges in understanding, gathering all the required information and making informed decisions. The "Business Assistant Application" aims to simplify this process by providing users with comprehensive tools and information tailored specifically to the restaurant industry in Massachusetts.

## Project Goals
1. The primary goal of this project is to develop a prototype Restaurant Business Assistant Application that leverages AI and local data to:
2. Provide user-friendly insights into Massachusetts-specific restaurant regulations.
3. Offer comprehensive and customizable business plans.
4. Deliver location-based competitive analysis and menu recommendations.
5. Streamline the data required for decision-making, thereby simplifying the process of starting a restaurant business.

## Technologies Used
[![GitHub](https://img.shields.io/badge/GitHub-100000?style=for-the-badge&logo=github&logoColor=white)](https://github.com/)
[![FastAPI](https://img.shields.io/badge/fastapi-109989?style=for-the-badge&logo=FASTAPI&logoColor=white)](https://fastapi.tiangolo.com/)
[![Python](https://img.shields.io/badge/Python-FFD43B?style=for-the-badge&logo=python&logoColor=blue)](https://www.python.org/)
[![Apache Airflow](https://img.shields.io/badge/Airflow-017CEE?style=for-the-badge&logo=Apache%20Airflow&logoColor=white)](https://airflow.apache.org/)
[![Docker](https://img.shields.io/badge/Docker-%232496ED?style=for-the-badge&logo=Docker&color=blue&logoColor=white)](https://www.docker.com)
[![Snowflake](https://img.shields.io/badge/snowflake-%234285F4?style=for-the-badge&logo=snowflake&link=https%3A%2F%2Fwww.snowflake.com%2Fen%2F%3F_ga%3D2.41504805.669293969.1706151075-1146686108.1701841103%26_gac%3D1.160808527.1706151104.Cj0KCQiAh8OtBhCQARIsAIkWb68j5NxT6lqmHVbaGdzQYNSz7U0cfRCs-STjxZtgPcZEV-2Vs2-j8HMaAqPsEALw_wcB&logoColor=white)
](https://www.snowflake.com/en/?_ga=2.41504805.669293969.1706151075-1146686108.1701841103&_gac=1.160808527.1706151104.Cj0KCQiAh8OtBhCQARIsAIkWb68j5NxT6lqmHVbaGdzQYNSz7U0cfRCs-STjxZtgPcZEV-2Vs2-j8HMaAqPsEALw_wcB)
[![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=Streamlit&logoColor=white)](https://streamlit.io/)
[![Pinecone](https://img.shields.io/badge/Pinecone-8C54FF?style=for-the-badge&logo=pinecone&logoColor=white)](https://www.pinecone.io/)
[![SERP API](https://img.shields.io/badge/SERP_API-009688?style=for-the-badge&logo=google&logoColor=white)](https://serpapi.com/)
[![Pydantic](https://img.shields.io/badge/Pydantic-00BFFF?style=for-the-badge&logo=python&logoColor=white)](https://pydantic-docs.helpmanual.io/)
[![Google Maps](https://img.shields.io/badge/Google%20Maps-4285F4?style=for-the-badge&logo=google-maps&logoColor=white)](https://maps.google.com/)
[![OpenAI](https://img.shields.io/badge/OpenAI-232323?style=for-the-badge&logo=OpenAI&logoColor=white)](https://openai.com/)


## Features

- **Detailed Regulatory Information:** Access and understand Massachusetts restaurant regulations effortlessly.
- **Comprehensive Business Plans:** Generate step-by-step business plans covering all essential aspects of opening a restaurant.
- **Competitive Market Analysis:** Analyze local competitors to identify opportunities and optimize business strategies.
- **Menu Optimization:** Receive data-driven suggestions to enhance your restaurant's menu offerings.
- **User Authentication:** Secure access to personalized data and tools.
- **Interactive Q&A:** Ask specific questions and receive detailed, AI-generated responses tailored to your needs.

## Installation

### Prerequisites

- **Python 3.8+**
- **Git**
- **Pinecone Account**
- **OpenAI API Key**
- **Google Maps API Key**
- **Snowflake Account**

### Steps

1. **Clone the Repository**

   ```bash
   git clone https://github.com/BigDataIA-Fall2024-TeamA3/damg7245_final_project
   cd damg7245_final_project
	```
2. **To run the Airflow
	```bash
   cd Airflow
   docker-compose up --build
	```
3. **To run the Application
	```bash
   cd Application
   docker-compose up --build
   
	```
### Project Directories
```
├── damg7245_final_project
│   ├── Airflow
│   │   ├── Dockerfile
│   │   ├── dags
│   │   │   ├── embeddings.py
│   │   │   ├── pdf.py
│   │   │   └── places.py
│   │   ├── docker-compose.yaml
│   │   └── requirements.txt
│   ├── Application
│   │   ├── Dockerfile
│   │   ├── docker-compose.yaml
│   │   ├── fastapi
│   │   │   ├── Dockerfile
│   │   │   ├── config.py
│   │   │   ├── database_connection.py
│   │   │   ├── main.py
│   │   │   ├── models.py
│   │   │   ├── requirements.txt
│   │   │   ├── requirements1.txt
│   │   │   └── utils
│   │   │       ├── __init__.py
│   │   │       ├── get_news.py
│   │   │       ├── s3_utils.py
│   │   │       └── snowflake_client.py
│   │   └── streamlit
│   │       ├── Dockerfile
│   │       ├── app.py
│   │       ├── pages
│   │       ├── pagess
│   │       │   ├── home.py
│   │       │   ├── login.py
│   │       │   ├── qn.py
│   │       │   ├── regulations.py
│   │       │   ├── restaurants.py
│   │       │   └── sample_data
│   │       │       └── sample_news_response.json
│   │       └── requirements.txt
│   └── README.md
└── project_tree.txt
```

## GitHub Projects - [Link](https://github.com/BigDataIA-Fall2024-TeamA3/damg7245_final_project) 

## References

- https://developers.google.com/maps/documentation
- https://platform.openai.com/docs/api-reference/introduction
- https://cloud.google.com
- https://app.snowflake.com/

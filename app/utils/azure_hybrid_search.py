# # app/utils/azure_hybrid_search.py
# # for lookup after the vectors are created

# import os
# import requests
# from openai import AzureOpenAI

# AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
# AZURE_OPENAI_KEY = os.getenv("AZURE_OPENAI_KEY")
# EMBEDDING_DEPLOYMENT = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-ada-002") #to be changed to cohere

# AZURE_SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT")
# AZURE_SEARCH_KEY = os.getenv("AZURE_SEARCH_KEY")
# AZURE_SEARCH_INDEX = os.getenv("AZURE_SEARCH_INDEX")
# VECTOR_FIELD = os.getenv("AZURE_SEARCH_VECTOR_FIELD", "contentVector")
# TOP_K = int(os.getenv("AZURE_SEARCH_TOP_K", "3"))

# client = AzureOpenAI(
#     api_key=AZURE_OPENAI_KEY,
#     api_version="2023-07-01-preview",
#     azure_endpoint=AZURE_OPENAI_ENDPOINT     # )


# def search_similar_responses(question: str, top_k: int = TOP_K) -> list[dict]:
#     embedding_response = client.embeddings.create(
#         input=question,
#         model=EMBEDDING_DEPLOYMENT
#     )
#     embedding_vector = embedding_response.data[0].embedding

#     search_url = f"{AZURE_SEARCH_ENDPOINT}/indexes/{AZURE_SEARCH_INDEX}/docs/search?api-version=2023-07-01-Preview"
#     headers = {
#         "Content-Type": "application/json",
#         "api-key": AZURE_SEARCH_KEY
#     }

#     payload = {
#         "search": question,
#         "top": top_k,
#         "vector": {
#             "value": embedding_vector,
#             "fields": VECTOR_FIELD,
#             "k": top_k
#         }

#     }

#     response = requests.post(search_url, headers=headers, json=payload)

#     if response.status_code == 200:
#         return response.json().get("value", [])
#     else:
#         raise RuntimeError(f"Hybrid search failed: {response.status_code} {response.text}")
                                 
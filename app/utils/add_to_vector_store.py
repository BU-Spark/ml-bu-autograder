import random

from azure.core.credentials import AzureKeyCredential
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import SearchField, SimpleField, SearchFieldDataType
from azure.search.documents.indexes.models import SearchIndex
from azure.search.documents.indexes.models import VectorSearch, VectorSearchProfile, HnswAlgorithmConfiguration

# Define fields for the index
fields = [
    SimpleField(name="id", type=SearchFieldDataType.String, key=True),  # primary key field
    SimpleField(name="file_path", type=SearchFieldDataType.String, filterable=True),
    SearchField(
        name="content_vector",
        type=SearchFieldDataType.Collection(SearchFieldDataType.Single),  # collection of Edm.Single (floats)
        searchable=True,  # True because we want to run similarity searches on this field
        vector_search_dimensions=1536,  # e.g. vector length 1536 for embeddings
        vector_search_profile_name="my-vector-profile"  # link to a vector search profile (defined next)
    )
]

# Define vector search algorithm and profile
vector_search = VectorSearch(
    profiles=[
        VectorSearchProfile(
            name="my-vector-profile",  # profile name (matches field)
            algorithm_configuration_name="my-hnsw-config"  # refers to the algorithm config below
        )
    ],
    algorithms=[
        HnswAlgorithmConfiguration(
            name="my-hnsw-config"  # algorithm name (matches profile reference)
            # You can optionally specify parameters like 'kind="hnsw"', 'metric="cosine"', m, efConstruction, efSearch, etc.
            # If not specified, defaults for HNSW are used.
        )
    ]
)

# Set up the client for your search service
endpoint = "https://autograder-search.search.windows.net"
admin_key = ""  # doesnt work in env for some reason
index_client = SearchIndexClient(endpoint=endpoint, credential=AzureKeyCredential(admin_key))

# Create the SearchIndex with the defined fields and vector search settings
index_name = "assignment2lookup2"
search_index = SearchIndex(name=index_name, fields=fields, vector_search=vector_search)

# Create or update the index in the service
index_client.create_or_update_index(search_index)
print(f"Index '{index_name}' created successfully.")

from azure.search.documents import SearchClient

# Assume we have a SearchClient for the index and a function to get embeddings
search_client = SearchClient(endpoint=endpoint, index_name=index_name, credential=AzureKeyCredential(admin_key))

# Example document
text_content = "q9UWEDH QWAUIEFHWEDFUIH WAP9UIFHWIPAUOEFHDCIUH"
embedding = [random.uniform(-1, 1) for _ in range(1536)]  # some dummy embedding to be changed later
doc = {
    "id": "2",
    "file_path": "/path/to/file1.txt",
    "content_vector": embedding  # include the embedding list in the document
}
result = search_client.upload_documents(documents=[doc])
if result[0].succeeded:
    print(f"Document {doc['id']} uploaded successfully.")
else:
    print(f"Failed to upload document {doc['id']}: {result[0].error_message}")

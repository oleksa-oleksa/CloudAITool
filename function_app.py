import os
import logging
import azure.functions as func
from azure.storage.blob import BlobServiceClient
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
from azure.cosmos import CosmosClient
import openai
from azure.search.documents import SearchClient
from azure.search.documents.indexes.models import SearchIndex, Field, SimpleField, SearchFieldDataType
from azure.search.documents.indexes import SearchIndexClient
from azure.core.credentials import AzureKeyCredential

app = func.FunctionApp()

@app.blob_trigger(arg_name="myblob", path="requirements/{name}", connection="AzureWebJobsStorage")
def BlobTriggerPDF(myblob: func.InputStream):
    logging.info(f"Python blob trigger function processed blob\n"
                f"Name: {myblob.name}\n"
                f"Blob Size: {myblob.length} bytes")

    # Only process PDF files
    if not myblob.name.endswith('.pdf'):
        logging.info("Not a PDF file, skipping processing.")
        return

    # Load PDF from blob
    pdf_bytes = myblob.read()
    process_pdf_and_create_chunks(pdf_bytes, myblob.name)

# Initialize global variables
connection_string = os.getenv("AzureWebJobsStorage")
cosmos_db_endpoint = os.getenv("CosmosDBEndpoint")
cosmos_db_primary_key = os.getenv("CosmosDBPrimaryKey")
database_id = os.getenv("DatabaseId")
graph_id = os.getenv("GraphId")
doc_intelligence_api_key = os.getenv("DocIntelligenceApiKey")
doc_intelligence_endpoint = os.getenv("DocIntelligenceEndpoint")
openai_api_key = os.getenv("OpenAIApiKey")
openai_endpoint = os.getenv("OpenAIEndpoint")

# Initialize OpenAI
openai.api_key = openai_api_key
openai.api_base = openai_endpoint

# Connect to Cosmos DB
cosmos_client = CosmosClient(cosmos_db_endpoint, cosmos_db_primary_key)
database = cosmos_client.get_database_client(database_id)
container = database.get_container_client(graph_id)

# Initialize Document Analysis client
doc_analysis_client = DocumentAnalysisClient(endpoint=doc_intelligence_endpoint, credential=AzureKeyCredential(doc_intelligence_api_key))

def process_pdf_and_create_chunks(pdf_bytes, blob_name):
    # Analyze document layout
    poller = doc_analysis_client.begin_analyze_document(
        model="prebuilt-layout", document=pdf_bytes)
    layout_result = poller.result()

    # Process layout result (semantic chunking)
    semantic_chunks = []
    for page in layout_result.pages:
        for element in page.tables + page.lines + page.selection_marks:
            semantic_chunks.append(element.content)

    generate_embeddings(semantic_chunks, blob_name)

def generate_embeddings(chunks, blob_name):
    embeddings = []
    for chunk in chunks:
        response = openai.Embedding.create(
            model="text-embedding-ada-002",
            input=chunk
        )
        embedding = response['data'][0]['embedding']
        embeddings.append({
            "chunk": chunk,
            "embedding": embedding
        })

    store_embeddings_in_cognitive_search(embeddings, blob_name)

def store_embeddings_in_cognitive_search(embeddings, blob_name):
    search_service_endpoint = os.getenv("SearchServiceEndpoint")
    search_service_key = os.getenv("SearchServiceKey")
    search_index_name = "documentchunks"

    credential = AzureKeyCredential(search_service_key)
    search_client = SearchClient(
        endpoint=search_service_endpoint, 
        index_name=search_index_name, 
        credential=credential
    )

    documents = [
        {
            "id": f"{blob_name}_{i}",
            "chunk": embedding["chunk"],
            "embedding": embedding["embedding"],
            "metadata_storage_path": f"https://{os.getenv('STORAGE_ACCOUNT_NAME')}.blob.core.windows.net/requirements/{blob_name}"
        } for i, embedding in enumerate(embeddings)
    ]

    result = search_client.upload_documents(documents=documents)
    logging.info(f"Upload result: {result}")

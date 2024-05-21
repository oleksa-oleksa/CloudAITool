import os
import logging
import azure.functions as func
from azure.storage.blob import BlobServiceClient
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
from azure.cosmos import CosmosClient
import openai
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential

app = func.FunctionApp()

@app.blob_trigger(arg_name="myblob", path="requirements/{name}", connection="AzureWebJobsStorage")
def BlobTriggerPDF(myblob: func.InputStream):

    logging.info(f"LOG: Triggered! Init")
    
    # Initialize global variables
    connection_string = os.getenv("AzureWebJobsStorage")
    # Connect to Blob Storage
    blob_service_client = BlobServiceClient.from_connection_string(connection_string)
    blob_client = blob_service_client.get_blob_client(container="requirements", blob=myblob.name)
    blob_properties = blob_client.get_blob_properties()


    doc_intelligence_api_key = os.getenv("DocIntelligenceApiKey")
    doc_intelligence_endpoint = os.getenv("DocIntelligenceEndpoint")

    # Initialize OpenAI
    openai.api_key = os.getenv("OpenAIApiKey")
    openai.base_url = os.getenv("OpenAIEndpoint")

    
    ###### PROCESS PDF ON TRIGGER #############
    logging.info(f"LOG: BLOB Trigger: Processed blob\n"
                f"Name: {myblob.name}\n"
                f"Blob Size: {blob_properties.size} bytes")

    # Only process PDF files
    if not myblob.name.endswith('.pdf'):
        logging.info("Not a PDF file, skipping processing.")
        return

    # Load PDF from blob
    pdf_bytes = myblob.read()

    ###### PROCESS PDF AND CREATE CHUNKS #######
    doc_intelligence_api_key = os.getenv("DocIntelligenceApiKey")
    doc_intelligence_endpoint = os.getenv("DocIntelligenceEndpoint")

    doc_analysis_client = DocumentAnalysisClient(
        endpoint=doc_intelligence_endpoint,
        credential=AzureKeyCredential(doc_intelligence_api_key)
    )
    logging.info("LOG: Document Intelligence init done")

    # Analyze document layout
    poller = doc_analysis_client.begin_analyze_document(
        model="prebuilt-layout", document=pdf_bytes)
    layout_result = poller.result()

    # Process layout result (semantic chunking)
    semantic_chunks = []
    for page in layout_result.pages:
        for element in page.tables + page.lines + page.selection_marks:
            semantic_chunks.append(element.content)
    logging.info("LOG: Chunks are created")

    ####### GENERATE EMBEDDINGS #############
    embeddings = []
    for chunk in semantic_chunks:
        response = openai.Embedding.create(
            model="text-embedding-ada-002",
            input=chunk
        )
        embedding = response['data'][0]['embedding']
        embeddings.append({
            "chunk": chunk,
            "embedding": embedding
        })
    logging.info("LOG: Embeddings are created")

    ##### STORE EMBEDDINGS IN AI SEARCH ##########
    search_service_endpoint = os.getenv("SearchServiceEndpoint")
    search_service_key = os.getenv("SearchServiceKey")
    search_index_name = "documentchunks"

    credential = AzureKeyCredential(search_service_key)
    search_client = SearchClient(
        endpoint=search_service_endpoint, 
        index_name=search_index_name, 
        credential=credential
    )
    logging.info("LOG: AI Search init done")


    documents = [
        {
            "id": f"{myblob.name}_{i}",
            "chunk": embedding["chunk"],
            "embedding": embedding["embedding"],
            "metadata_storage_path": f"https://{os.getenv('STORAGE_ACCOUNT_NAME')}.blob.core.windows.net/requirements/{myblob.name}"
        } for i, embedding in enumerate(embeddings)
    ]
    logging.info("LOG: Stored to AI Search")

    result = search_client.upload_documents(documents=documents)
    logging.info(f"LOG: Upload result: {result}")

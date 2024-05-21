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
    logging.info(myblob.name)

    # Initialize global variables    
    doc_intelligence_api_key = os.getenv("DocIntelligenceApiKey")
    doc_intelligence_endpoint = os.getenv("DocIntelligenceEndpoint")

    # Initialize OpenAI
    openai.api_key = os.getenv("OpenAIApiKey")
    openai.base_url = os.getenv("OpenAIEndpoint")

    logging.info(f"LOG: Got environment variables")

    ###### PROCESS PDF ON TRIGGER #############

    logging.info(f"Python blob trigger function processed blob\n"
                f"Name: {myblob.name}\n"
                f"Blob Size: {myblob.length} bytes")
    
    # Only process PDF files
    if not myblob.name.endswith('.pdf'):
        logging.info("Not a PDF file, skipping processing.")
        return

    # Load PDF from blob
    logging.info(f"LOG: Start myblob.read()")
    pdf_bytes = myblob.read()
    logging.info(f"LOG: Finish myblob.read()")

    ###### PROCESS PDF AND CREATE CHUNKS #######
    doc_intelligence_api_key = os.getenv("DocIntelligenceApiKey")
    doc_intelligence_endpoint = os.getenv("DocIntelligenceEndpoint")

    doc_analysis_client = DocumentAnalysisClient(endpoint=doc_intelligence_endpoint, credential=AzureKeyCredential(doc_intelligence_api_key))
    logging.info("LOG: Document Intelligence init done")

    # Analyze document layout
    # Analyze document layout
    poller = doc_analysis_client.begin_analyze_document(model_id="prebuilt-layout", document=pdf_bytes)
    layout_result = poller.result()

    # Process layout result (semantic chunking)
    semantic_chunks = []
    for page in layout_result.pages:
        for line in page.lines:
            semantic_chunks.append(line.content)
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

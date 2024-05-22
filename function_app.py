import os
import logging
import azure.functions as func
from azure.storage.blob import BlobServiceClient
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
from azure.cosmos import CosmosClient
import openai
from langchain_openai import OpenAIEmbeddings


from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential

app = func.FunctionApp()

@app.blob_trigger(arg_name="myblob", path="requirements/{name}", connection="AzureWebJobsStorage")
def BlobTriggerPDF(myblob: func.InputStream):

    logging.info(f"LOG: Function triggered, starting...")
    logging.info(myblob.name)

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

    ###### ANALYSE PDF CONTENT WITH DOCUMENT INTELLIGENCE #######
    doc_intelligence_api_key = os.getenv("DocIntelligenceApiKey")
    doc_intelligence_endpoint = os.getenv("DocIntelligenceEndpoint")
    doc_analysis_client = DocumentAnalysisClient(endpoint=doc_intelligence_endpoint, credential=AzureKeyCredential(doc_intelligence_api_key))
    logging.info("LOG: Document Intelligence init done")

    # Analyze document layout
    poller = doc_analysis_client.begin_analyze_document(model_id="prebuilt-layout", document=pdf_bytes)
    layout_result = poller.result()

    ###### CREATE CHUNKS #######
    # Process layout result (semantic chunking)
    semantic_chunks = []
    for page in layout_result.pages:
        for line in page.lines:
            semantic_chunks.append(line.content)
    logging.info("LOG: Chunks are created")

    ####### GENERATE EMBEDDINGS WITH AZURE OPEN AI #############
    # Configure Azure OpenAI Service API
    openai.api_type = "azure"
    openai.api_version = os.getenv('OPENAI_API_VERSION')
    openai.base_url = os.getenv('OpenAIEndpoint') 
    openai.api_key = os.getenv("OPENAI_API_KEY")

    # Initialize embedding model
    embed_open_ai = OpenAIEmbeddings(model= os.getenv("OPEN_AI_EMBEDDINGS_MODEL"),
                                  api_version=openai.api_version,
                                  base_url=openai.base_url,
                                  api_key=openai.api_key,
                                  chunk_size=1)

    embeddings = []
    for chunk in semantic_chunks:
        response = embed_open_ai.embed_query(chunk)

        embeddings.append({
            "chunk": chunk,
            "embedding": response
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

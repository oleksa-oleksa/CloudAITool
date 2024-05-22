import os
import logging
import azure.functions as func
from azure.storage.blob import BlobServiceClient
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
from azure.cosmos import CosmosClient
from openai import AzureOpenAI
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
import requests
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

    token_provider = get_bearer_token_provider(
        DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default"
    )

    client = AzureOpenAI(
        api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
        azure_endpoint=os.getenv("AZURE_OPENAI_API_VERSION"),
        azure_ad_token_provider=token_provider
    )
    # Construct the embedding URL
    openai_endpoint = os.getenv('AZURE_OPENAI_ENDPOINT')
    deployment_id = os.getenv('OPEN_AI_EMBEDDINGS_MODEL')
    api_version = os.getenv("AZURE_OPENAI_API_VERSION")
    openai_api_key = os.getenv('AZURE_OPENAI_API_KEY')
    embedding_url = f"{openai_endpoint}//openai/deployments/{deployment_id}/embeddings?api-version={api_version}"
    #embedding_url = "https://openai/deployments//subscriptions/d41f65a5-e9ed-4ef4-b968-93a24decf7a3/resourceGroups/DCE___Germany___C_M___Digital_Customer-RG-TB900/providers/Microsoft.CognitiveServices/accounts/UserStoryCreator/deployments/text-embedding-ada-002/embeddings?api-version=2023-05-15"
    
    headers = {
        'Content-Type': 'application/json',
        'api-key': openai_api_key
    }

    # Initialize embedding model
    embeddings = []
    for chunk in semantic_chunks:
        try:
            data = {
                "input": chunk
            }
            response = requests.post(embedding_url, headers=headers, json=data)
            response.raise_for_status()
            embedding = response.json()['data'][0]['embedding']  # Extract the embedding

            embeddings.append({
                "chunk": chunk,
                "embedding": embedding
            })

        except requests.exceptions.RequestException as e:
            logging.error(f"Failed to create embedding for chunk '{chunk}': {str(e)}")
            logging.error(f"Response: {e.response.text if e.response else 'No response'}")

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

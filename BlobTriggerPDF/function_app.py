import os
import logging
import azure.functions as func
from azure.storage.blob import BlobServiceClient
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
from azure.cosmos import CosmosClient
import openai

app = func.FunctionApp()

@app.blob_trigger(arg_name="myblob", path="requirements/{name}",
                               connection="AzureWebJobsStorage") 
def BlobTriggerPDF(myblob: func.InputStream):
    logging.info(f"Python blob trigger function processed blob"
                f"Name: {myblob.name}"
                f"Blob Size: {myblob.length} bytes")

    # Only process PDF files
    if not myblob.name.endswith('.pdf'):
        logging.info("Not a PDF file, skipping processing.")
        return
    
    # Pass the blob to the next function for processing
    process_pdf(myblob.read(), myblob.name)
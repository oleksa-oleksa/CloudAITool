import logging
import os
import azure.functions as func
from azure.cosmos import CosmosClient, exceptions

# Define the Azure Cosmos DB details
COSMOS_DB_URL = os.getenv("COSMOS_DB_URL")
COSMOS_DB_KEY = os.getenv("COSMOS_DB_KEY")
COSMOS_DB_DATABASE_NAME = os.getenv("COSMOS_DB_DATABASE_NAME")
COSMOS_DB_CONTAINER_NAME = os.getenv("COSMOS_DB_CONTAINER_NAME")

# Initialize Cosmos client
client = CosmosClient(COSMOS_DB_URL, COSMOS_DB_KEY)
database = client.get_database_client(COSMOS_DB_DATABASE_NAME)
container = database.get_container_client(COSMOS_DB_CONTAINER_NAME)

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    try:
        # Retrieve the predefined prompt
        prompt_id = req.params.get('id')
        if not prompt_id:
            return func.HttpResponse(
                "Please pass a prompt id on the query string or in the request body",
                status_code=400
            )
        
        prompt_role = req.params.get("role")
        if not prompt_role:
            return func.HttpResponse(
                "Please pass a prompt role on the query string or in the request body",
                status_code=400
            )

        prompt_content = req.params.get('content')
        if not prompt_content:
            return func.HttpResponse(
                "Please pass the prompt content on the query string or in the request body",
                status_code=400
            )

        # Construct the prompt document
        prompt_document = {
            "id": prompt_id,
            "role": prompt_role,
            "content": prompt_content
        }

        # Insert the document into Cosmos DB
        container.create_item(body=prompt_document)

        return func.HttpResponse(
            f"Prompt with ID {prompt_id} has been saved successfully.",
            status_code=200
        )

    except exceptions.CosmosHttpResponseError as e:
        logging.error(f"An error occurred: {e.message}")
        return func.HttpResponse(
            f"An error occurred while saving the prompt: {e.message}",
            status_code=500
        )

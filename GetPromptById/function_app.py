import os
import logging
import azure.functions as func
from azure.cosmos import CosmosClient, exceptions

# Initialize Cosmos Client
cosmos_url = os.getenv('COSMOS_DB_URL')
cosmos_key = os.getenv('COSMOS_DB_KEY')
database_name = os.getenv('COSMOS_DB_DATABASE_NAME')
container_name = os.getenv('COSMOS_DB_CONTAINER_NAME')

cosmos_client = CosmosClient(cosmos_url, cosmos_key)
database = cosmos_client.get_database_client(database_name)
container = database.get_container_client(container_name)

app = func.FunctionApp()

@app.function_name(name="GetPromptById")
@app.route(route="prompt/{id}", methods=["GET"])
def GetPromptById(req: func.HttpRequest, id: str) -> func.HttpResponse:
    logging.info(f"Fetching prompt with ID: {id}")

    try:
        # Query the Cosmos DB to get the document by ID
        prompt_document = container.read_item(item=id, partition_key=id)
        logging.info(f"Retrieved prompt: {prompt_document}")

        return func.HttpResponse(
            body=str(prompt_document),
            mimetype="application/json",
            status_code=200
        )
    except exceptions.CosmosResourceNotFoundError:
        logging.error(f"Prompt with ID {id} not found")
        return func.HttpResponse(
            f"Prompt with ID {id} not found",
            status_code=404
        )
    except Exception as e:
        logging.error(f"An error occurred: {str(e)}")
        return func.HttpResponse(
            f"An error occurred: {str(e)}",
            status_code=500
        )

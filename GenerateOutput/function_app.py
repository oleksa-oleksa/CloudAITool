import os
import logging
import azure.functions as func
from azure.cosmos import CosmosClient, exceptions
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
from openai import OpenAI

# Initialize clients
cosmos_endpoint = os.getenv('COSMOS_DB_ENDPOINT')
cosmos_key = os.getenv('COSMOS_DB_KEY')
database_name = 'PromptDatabase'
container_name = 'Prompts'
search_service_endpoint = os.getenv("SearchServiceEndpoint")
search_service_key = os.getenv("SearchServiceKey")
search_index_name = "processed_requirement_document"
openai_api_key = os.getenv('OPENAI_API_KEY')

cosmos_client = CosmosClient(cosmos_endpoint, cosmos_key)
database = cosmos_client.get_database_client(database_name)
container = database.get_container_client(container_name)

search_credential = AzureKeyCredential(search_service_key)
search_client = SearchClient(endpoint=search_service_endpoint, index_name=search_index_name, credential=search_credential)

openai = OpenAI(api_key=openai_api_key)

def get_prompt(prompt_id):
    try:
        prompt_item = container.read_item(item=prompt_id, partition_key=prompt_id)
        return prompt_item['content']
    except exceptions.CosmosResourceNotFoundError:
        logging.error(f'Prompt with id {prompt_id} not found')
        return None

def get_document_chunks(document_id):
    results = search_client.search(search_text="", filter=f"id eq '{document_id}'")
    for result in results:
        return result

def generate_user_story(prompt, document_text, chunks, model="gpt-35-turbo"):
    combined_text = f"{prompt}\n\nOriginal Text:\n{document_text}\n\nChunks:\n" + "\n".join(chunk['chunk'] for chunk in chunks)
    
    response = openai.ChatCompletion.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are a helpful assistant that creates user stories based on software requirements."},
            {"role": "user", "content": combined_text}
        ],
        max_tokens=200
    )
    
    return response['choices'][0]['message']['content']

@app.function_name(name="GenerateUserStory")
@app.route(route="generate_user_story")
def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Generating user story')

    document_id = req.params.get('document_id')
    prompt_id = req.params.get('prompt_id')
    model = req.params.get('model', 'gpt-35-turbo')  # Default to gpt-35-turbo if model is not specified

    if not document_id or not prompt_id:
        return func.HttpResponse(
            "Please pass document_id and prompt_id in the query string",
            status_code=400
        )

    prompt_content = get_prompt(prompt_id)
    if not prompt_content:
        return func.HttpResponse(
            f"Prompt with id {prompt_id} not found",
            status_code=404
        )

    document_chunks = get_document_chunks(document_id)
    if not document_chunks:
        return func.HttpResponse(
            f"Document with id {document_id} not found",
            status_code=404
        )

    original_text = document_chunks['original_text']
    chunks = document_chunks['chunks']
    user_story = generate_user_story(prompt_content, original_text, chunks, model=model)

    return func.HttpResponse(user_story, status_code=200)

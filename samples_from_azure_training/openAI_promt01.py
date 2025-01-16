  
import os  
import base64
from openai import AzureOpenAI  
from azure.identity import DefaultAzureCredential, get_bearer_token_provider  
        
endpoint = os.getenv("ENDPOINT_URL", "https://fghfghfghfgft.openai.azure.com/")  
deployment = os.getenv("DEPLOYMENT_NAME", "gpt-35-turbo-16k")  
      
# Initialize Azure OpenAI Service client with Entra ID authentication
token_provider = get_bearer_token_provider(  
    DefaultAzureCredential(),  
    "https://cognitiveservices.azure.com/.default"  
)  
  
client = AzureOpenAI(  
    azure_endpoint=endpoint,  
    azure_ad_token_provider=token_provider,  
    api_version="2024-05-01-preview",  
)  
  

chat_prompt = [
    {
        "role": "system",
        "content": "You are an AI assistant that helps people find information."
    },
    {
        "role": "user",
        "content": "You are a professional software developer. Explain me shortly what is variable in programming."
    },
    {
        "role": "assistant",
        "content": "In programming, a variable is a named storage location that holds a value. It is used to store and manipulate data during the execution of a program. Variables can have different data types, such as integers, floating-point numbers, characters, or strings, and their values can change throughout the program. They provide a way to refer to and work with data in a flexible and dynamic manner."
    }
] 
    
# Include speech result if speech is enabled  
messages = chat_prompt 

completion = client.chat.completions.create(  
    model=deployment,  
    messages=messages,
    max_tokens=800,  
    temperature=0.7,  
    top_p=0.95,  
    frequency_penalty=0,  
    presence_penalty=0,
    stop=None,  
    stream=False  
)  
  
print(completion.to_json())  

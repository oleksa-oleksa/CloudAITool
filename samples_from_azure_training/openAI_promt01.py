  
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
    },
    {
        "role": "user",
        "content": "You are a professional software developer that has a child and loves to talk to children. Explain shortly to a child 5-7 years old what is variable in programming."
    },
    {
        "role": "assistant",
        "content": "Imagine you have a special box that can hold different things like toys, books, or even snacks. This box is called a variable in programming. Just like you can put different things in the box, in programming, a variable is a special place where we can store different types of information, like numbers or words. We give the variable a name, like \"favoriteToy\" or \"age,\" so we can easily remember what's inside. And just like you can change what's in the box, in programming, we can change the value stored in a variable whenever we want. So variables help us keep track of important information while we're making cool programs!"
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

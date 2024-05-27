# RAG Implementation

## Chunks

Chunks in this context refer to dividing the input documents (PDFs) into smaller, more manageable sections or units of information. Each chunk represents a distinct part of the document, such as a paragraph, sentence, or page.
Breaking down the input documents into chunks allows for more focused analysis and processing by the AI model. It helps in isolating individual segments of input text, making it easier for the model to understand and generate output based on each chunk separately.

## Embeddings
    
Embeddings are numerical representations of text data that capture semantic meaning and relationships between words, phrases, or sentences. These representations encode the underlying context and structure of the text in a lower-dimensional space.

Embeddings serve as input features for the AI model to understand the content of the input documents and generate corresponding output. By converting the text data into embeddings, the AI model can analyze the semantic relationships between different input data and generate coherent output that align with the document's content.

## Consumption Plan for Azure Functions
 Azure Functions offer a Consumption Plan pricing model where you are charged based on the number of executions and resource consumption (e.g., memory and execution time). You pay only for the resources used during function execution.

##  Azure Cognitive Search
   Index both unstructured and structured data to facilitate efficient retrieval.

## Azure Functions
Orchestrate the workflow: process incoming PDFs, extract knowledge, augment with context, and invoke the generative model.

## Azure OpenAI Service
 Generate output from the augmented input.

## Trigger: New PDF file uploaded to Azure Blob Storage.
- Action: Chunks and Embeddings are created and stored to the Azure AI Search
-   Action: Extract text knowledge from the PDF store the extracted text in an Azure Queue (TBD)

## Trigger: Message added to Azure Queue (containing extracted knowledge base).
-   Action: Combine the extracted knowledge with the prompt creation guidelines to form an augmented prompt. Store the augmented prompt in another queue or directly call the generative model.

## Trigger: Message added to the queue with the augmented prompt.
-   Action: Use Azure OpenAI Service to generate output based on the augmented prompt and store the generated output back in Azure Blob Storage or another data store.
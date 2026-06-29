import os
from dotenv import load_dotenv
load_dotenv()
from groq import Groq
api_key=os.getenv("api_key")
GROQ_MODEL= "llama-3.3-70b-versatile"
client=Groq(api_key=api_key)

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

CONFIG_PATH = PROJECT_ROOT / "config" / "v2_config.json"
VECTOR_DB = PROJECT_ROOT / "Storage" / "sindhu_db"
LOG_FILE = PROJECT_ROOT / "logs" / "sindhu_rag.log"
CONVERSATION_PATH = PROJECT_ROOT / "Storage" / "conversation" / "conversation_history.json"

import json
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings.sentence_transformer import SentenceTransformerEmbeddings

# For Api Rate limiting
import logging
from tenacity import (
     retry,  # Decorator that wraps a function with retry logic
    stop_after_attempt,  # Stop after N total attempts
    wait_exponential,  # Wait 1s, 2s, 4s, 8s between retries
    before_sleep_log, 

)


logging.basicConfig(
    level=logging.INFO,
    filename=LOG_FILE,
    filemode="w",

)

logger = logging.getLogger(__name__)
attempt_counter={"n":0}


# Declaring some important variable 
Embendding_Model_Name='thenlper/gte-large'
Chroma_Path=str(VECTOR_DB)
        
Top_k=3# retrieving only 3 chunks because of api costs
collection="sindh-10k-collection"
embeddings=SentenceTransformerEmbeddings(model_name=Embendding_Model_Name)

vectore_Store=Chroma(
    collection_name=collection,
    persist_directory=Chroma_Path,
    embedding_function=embeddings
)
# declaring the retreiver
retriever=vectore_Store.as_retriever(
    search_type="similarity",
    search_kwargs={"k":Top_k}
)



# function for retreiving the chunks and returing it in the format of list of dictionaries
def retrieve_chunks(user_query,retriever):
    docs=retriever.invoke(user_query)
    retreived=[]
    for i,doc in enumerate(docs):
        retreived.append({
            "Index":i,
            "Text":doc.page_content,
            "Metadata":doc.metadata
        })
    return retreived




def loading_bundle(path):
    with open(path,"r") as f:
        dict=json.load(f)
    return dict

path=CONFIG_PATH
bundle=loading_bundle(path)

def loading_prompt(bundle):
    system_path=PROJECT_ROOT/Path(bundle["prompt"])
    with open(system_path,"r") as f:
        p=f.read()
    return p




# --- Configuration ---
HISTORY_FILE = CONVERSATION_PATH
MAX_MESSAGE=1


# --- Helper functions for managing conversation history ---
def load_conversation_history():
   
    with open(CONVERSATION_PATH, 'r') as f:
        history = json.load(f)
    print(f"Loaded conversation history from {CONVERSATION_PATH}. Current turns: {max(0, len(history)-1)}")
    

    # If history is shorter than or equal to MAX_MESSAGE, return as-is.
    if len(history) <= MAX_MESSAGE:
        return history

    # Keep only the last `MAX_MESSAGE` entries.
    kept = history[-MAX_MESSAGE:]
    return kept




# Building the system Prompt
SYSTEM_MESSAGE = loading_prompt(bundle).strip()
# building the context text from the retreived chunks
def build_context_block(retrieve_chunks):
    parts=[]
    for chunk in retrieve_chunks:
        parts.append(chunk["Text"])

    return "\n\n".join(parts)
# building the user query from the by atatching the context 
def build_user_message(user_query,retrieve_chunks):
    context_text=build_context_block(retrieve_chunks)
    conversation_history=load_conversation_history()

    return f"###Question\n{user_query}\n###Conversation history\n{conversation_history}\n###context\n{context_text}"




# Generating the answers:

@retry(
    stop=stop_after_attempt(4),
    wait=wait_exponential(multiplier=1,min=1,max=10),
    before_sleep=before_sleep_log(logger,logging.WARNING)
)
def generate_answer(user_message,system_message):
    response = client.chat.completions.create(
                    model=bundle["model"],
                    messages=[
                        {"role":"system","content":system_message},
                        {"role":"user","content":user_message}
                    ],
                     )

    return response.choices[0].message.content.strip()





# will use this function in case want to see the metadata for inquiry
def rag_answer(user_query, retriever):
    """End-to-end: retrieve → build messages → generate → return audit bundle."""
    retrieved = retrieve_chunks
    user_message = build_user_message(user_query, retrieved)
    answer = generate_answer(SYSTEM_MESSAGE)
    return {"answer": answer, "retrieved_chunks": retrieved, "user_message": user_message}


def save_conversation_history(history):
    """Saves the current conversation history to a JSON file."""
    with open(HISTORY_FILE, 'w') as f:
        json.dump(history, f, indent=2)
    print(f"Conversation history saved to {HISTORY_FILE}.")




# --- Multi-turn RAG interaction loop ---

def main():

    conversation_history = load_conversation_history()
    turn_count = 0
    MAX_STEPS = 5
    STOP_WORDS = ["exit", "quit", "stop"]

    print("\n--- Starting Multi-Turn RAG Chat ---")
    print("Type 'exit', 'quit', or 'stop' to end the conversation.")
    print(f"Maximum {MAX_STEPS} turns allowed per session (excluding system message and previous turns).")



    while turn_count < MAX_STEPS:
        user_input = input(f"\n[{turn_count + 1}/{MAX_STEPS}] You: ")

        if user_input.lower() in STOP_WORDS:
            print("Exiting chat. Goodbye!")
            break

        # 1. Retrieve relevant documents from Vector DB
        print("--> Retrieving documents for context...")
        context =retrieve_chunks(user_input,retriever)
        user_message_content = build_user_message(user_input, context)
        SYSTEM_MESSAGE = loading_prompt(bundle).strip()

        # 2. Append the user's message (with context) to history
        conversation_history.append({'role': 'user', 'content': user_message_content})

        # 3. Call the LLM with the entire history
        try:
            print("--> Calling LLM...")

            assistant_response = generate_answer(user_message_content,SYSTEM_MESSAGE)

        except Exception as e:
            assistant_response = f'Sorry, I encountered the following error: \n {e}'
            print(f"LLM Error: {e}")

        # 4. Append the LLM's response to history
        conversation_history.append({'role': 'assistant', 'content': assistant_response})

        # 5. Save the updated history
        save_conversation_history(conversation_history)

        print(f"Assistant: {assistant_response}")
        turn_count += 1

    if turn_count == MAX_STEPS:
        print(f"\nMaximum turns ({MAX_STEPS}) reached. Chat session ended.")

main()
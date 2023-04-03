import json
import re
import datetime
import os
import pinecone
from uuid import uuid4
import openai

from config.api_keys import (openai_api_key, openai_model_engine, openai_max_tokens, pinecone_api_key,
                      pinecone_enviroment, slack_app_token, slack_bot_token)

# OpenAI Key
openai.api_key = openai_api_key

# Ensure Pinecone is initialized and vdb is set
pinecone.init(api_key= pinecone_api_key, environment = pinecone_enviroment)
vdb = pinecone.Index("craphound")

# GPT-3 Embedding
def gpt3_embedding(content, engine='text-embedding-ada-002'):
    content = content.encode(encoding='ASCII',errors='ignore').decode()  # fix any UNICODE errors
    response = openai.Embedding.create(input=content,engine=engine)
    vector = response['data'][0]['embedding']  # this is a normal list
    return vector

def parse_chat_log(file_path):
    with open(file_path, 'r') as f:
        chat_log = f.read()

    messages = []
    current_message = {"username": "", "content": ""}

    for line in chat_log.splitlines():
        if re.match(r"^(AI|assistant|crapbot6000|eric):", line, re.IGNORECASE):
            if current_message["username"] and current_message["content"]:
                messages.append(current_message)
                current_message = {"username": "", "content": ""}

            username = re.match(r"^(AI|assistant|crapbot6000|eric):", line, re.IGNORECASE).group(1)
            current_message["username"] = "assistant" if username.lower() in ["ai", "assistant", "crapbot6000"] else "eric"
            current_message["content"] = re.sub(r"^(AI|assistant|crapbot6000|eric):", "", line, flags=re.IGNORECASE).strip()

        else:
            current_message["content"] += "\n" + line.strip()

    if current_message["username"] and current_message["content"]:
        messages.append(current_message)

    return messages

def save_user_prompt_to_directory(metadata, directory):
    date_str = datetime.date.today().strftime("%Y-%m-%d")
    log_filename = f"{directory}/{metadata['uuid']}.json"

    if not os.path.exists(directory):
        os.makedirs(directory)

    log_entry = {
        "timestamp": metadata["time"],
        "username": metadata["username"],
        "message": metadata["message"]["text"],
        "uuid": metadata["uuid"]
    }

    with open(log_filename, "w") as f:
        json.dump(log_entry, f, indent=4)

def upload_to_pinecone(metadata, vdb):
    # Process the metadata as needed
    print("Message: " + str(metadata["message"]["text"]))
    vector = gpt3_embedding(metadata["message"]["text"])

    # Print the vector value
    print(f"Vector value: {vector}")
    payload = list()
    payload.append((metadata["uuid"], vector, {"username": metadata["username"], "time": datetime.datetime.now().isoformat()}))

    # Upload the processed data to Pinecone using `vdb.upsert()`
    vdb.upsert(payload)


def process_chat_log(chat_log_file, output_directory, vdb):
    messages = parse_chat_log(chat_log_file)

    for message in messages:
        unique_id = str(uuid4())
        timestamp = datetime.datetime.now().isoformat()
        metadata = {
            "uuid": unique_id,
            "time": timestamp,
            "username": message["username"],
            "message": {"text": message["content"]}
        }

        # Save the JSON object to the directory
        save_user_prompt_to_directory(metadata, output_directory)

        # Upload the JSON object to Pinecone
        upload_to_pinecone(metadata, vdb)


chat_log_file = "_archive/messages.txt"
output_directory = "nexus"



process_chat_log(chat_log_file, output_directory, vdb)
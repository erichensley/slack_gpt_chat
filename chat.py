import datetime
import logging
import os
from uuid import uuid4

import openai
import pinecone
import tiktoken
import re
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from config.api_keys import (openai_api_key, openai_model_engine, openai_max_tokens, pinecone_api_key,
                      pinecone_enviroment, slack_app_token, slack_bot_token)

from utils.file_handler import read_from_file, load_json
from utils.conversation_handler import load_conversation, load_history, save_user_prompt
from utils.gpt3_helpers import num_tokens_from_string, gpt3_embedding, generate_response_from_gpt3, replace_user_ids_with_names

phrases = read_from_file("config/phrases.txt").strip()

conversation_lines = read_from_file("config/conversation_content.txt").splitlines()

personality = read_from_file("config/personality.txt").replace("{phrases}", phrases)

# Chatbot Options
convo_length = 5  # Number of relevant messages to load

prompt = [{"role": "system", "content": personality}]
prompt_context = [{"role": "user", "content": line.strip()} for line in conversation_lines if line.strip()]
prompt = prompt + prompt_context

# Pinecone
pinecone.init(api_key= pinecone_api_key, environment = pinecone_enviroment)
vdb = pinecone.Index("craphound")

# OpenAI
openai.api_key = openai_api_key
token_limit = 4000
model_engine = "text-davinci-003"

# Slack
os.environ["SLACK_APP_TOKEN"] = slack_app_token
os.environ["SLACK_BOT_TOKEN"] = slack_bot_token
client = WebClient(token=os.environ["SLACK_BOT_TOKEN"])
app = App(token=os.environ["SLACK_BOT_TOKEN"])

# Initialize logging
logging.basicConfig(filename="log/openai_chatbot.log", level=logging.INFO)


@app.event("app_mention")
def handle_app_mention_events(body, logger):
  # Create a logger object
  logger = logging.getLogger(__name__)
  with open("messages.txt", "a") as log_file:
    logger.info(str(body) + "\n")
    log_file.write(str(body) + "\n")

@app.message(".*")
def feed_message_to_openai(message, say, ack):
    print("Feed message to OpenAI called")
    logger = logging.getLogger(__name__)
    ack()
    payload = list()
    with open("messages.txt", "a") as log_file:
        user = replace_user_ids_with_names(message["user"], members)
        print(message["user"])
        user_id = str(message["user"])
        print(user_id)
        text = message["text"]
        vector = gpt3_embedding(message["text"])
        unique_id = str(uuid4())
        user_metadata = {'username': user, 'time': datetime.datetime.now().isoformat(), 'message': message, 'uuid': unique_id}
        payload.append((unique_id, vector, {"username": user, "time": datetime.datetime.now().isoformat()}))
        
        # Search for relevant messages and generate a response
        results = vdb.query(vector=vector, top_k=convo_length)
        print("Pinecone DB: " + str(results))
        related = load_conversation(results)
        print("Related: " + str(related))

        response_text = generate_response_from_gpt3(message, user, related, prompt)
        response_text = re.sub(r"^(Crapbot6001|Assistant):", "", response_text, flags=re.IGNORECASE | re.MULTILINE)
        response_text = re.sub(r"^[A-Za-z]+: ", "", response_text, flags=re.IGNORECASE)
        response_text = response_text.replace("crapbot6001: ", "")
        vdb.upsert(payload)
        log_file.write(user + ": " + text + "\n")
        log_file.write("AI: " + response_text + "\n")
        save_user_prompt(user_metadata)
        print("OpenAI Response: " + (str(response_text)))
        response_unique_id = str(uuid4())
        response_metadata = {'username': "assistant", 'time': datetime.datetime.now().isoformat(), 'message': {'text': str(response_text)}, 'uuid': response_unique_id}
        response_vector = gpt3_embedding(str(response_text))
        payload.append((response_unique_id, response_vector, {"username": "assistant", "time": datetime.datetime.now().isoformat()}))
        vdb.upsert(payload)
        save_user_prompt(response_metadata)
    say(response_text)


if __name__ == "__main__":
    response = app.client.users_list()
    members = response["members"]
    handler = SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"])
    handler.start()

import openai
import re
import logging
import tiktoken
from transformers import GPT2TokenizerFast

from utils.conversation_handler import load_history
from config.api_keys import (openai_api_key, openai_model_engine, pinecone_api_key,
                      pinecone_enviroment, slack_app_token, slack_bot_token)

tokenizer = GPT2TokenizerFast.from_pretrained("gpt2")

# Return the number of tokens
def num_tokens_from_string(string: str, encoding_name: str) -> int:
    """Returns the number of tokens in a text string."""
    encoding = tiktoken.get_encoding(encoding_name)
    num_tokens = len(encoding.encode(string))
    return num_tokens

# GPT-3 Embedding
def gpt3_embedding(content, engine='text-embedding-ada-002'):
    content = content.encode(encoding='ASCII',errors='ignore').decode()  # fix any UNICODE errors
    response = openai.Embedding.create(input=content,engine=engine)
    vector = response['data'][0]['embedding']  # this is a normal list
    return vector

def generate_response_from_gpt3(message, username, previous_messages, prompt, max_tokens=3072):
    message_text = message['text']
    content = f"{username}: {message_text}"
    history = load_history()

    # Combine previous messages with the new message
    messages = prompt + previous_messages + history + [{"role": "user", "content": content}]
    print("Prompt : " + str(prompt))
    print("Previous Messages: " + str(previous_messages))
    print("History: "+ str(history))
    conversation_history = "\n".join([msg["content"] for msg in messages])

    # Calculate tokens
    tokens = len(tokenizer.encode(conversation_history))

    if tokens > max_tokens:
        tokens_to_remove = tokens - max_tokens

        # Iterate through messages in reverse order, removing tokens until the limit is reached
        while tokens_to_remove > 0:
            msg = history.pop()  # Remove the message from history instead of messages
            msg_tokens = len(tokenizer.encode(msg["content"]))
            tokens_to_remove -= msg_tokens

        # Rebuild messages and conversation_history after truncating history
        messages = prompt + previous_messages + history + [{"role": "user", "content": content}]
        conversation_history = "\n".join([msg["content"] for msg in messages])

        # Recalculate tokens for the new conversation_history
        tokens = len(tokenizer.encode(conversation_history))

    # Use the OpenAI GPT-3 model to generate a response to the message
    response = openai.Completion.create(
        engine=openai_model_engine,
        prompt=conversation_history,
        max_tokens=1024,
        top_p=0.3,
        presence_penalty=0.5,
        frequency_penalty=0.5,
        temperature=0.5,
        stop=None
    )

    # Get the generated response text
    response_text = response.choices[0].text.strip()

    return response_text

# Replace the Slack's user id their display name
def replace_user_ids_with_names(message, members):
    print("Replace User IDs Called")
    # Iterate through the list of users
    for member in members:
        # Get the user's id
        user_id = member["id"]
        # Get the user's display name
        user_name = member["profile"]["display_name"]
        # Replace the user's id with their display name
        message = re.sub(user_id, user_name, message)

    return message
import openai
import re
import logging
import tiktoken
import requests
import os
import shutil
from uuid

import replicate
from slack_sdk import WebClient
from config.api_keys import slack_bot_token, replicate_api_key
from transformers import GPT2TokenizerFast
from utils.conversation_handler import load_history
from utils.file_handler import get_config_file_path, get_images_path, generate_image_url
from config.api_keys import (openai_api_key, openai_model_engine, pinecone_api_key,
                      pinecone_enviroment, slack_app_token, slack_bot_token)

tokenizer = GPT2TokenizerFast.from_pretrained("gpt2")
client = WebClient(token=slack_bot_token)
rep = replicate.Client(api_token=replicate_api_key)

# Return the number of tokens
def num_tokens_from_string(string: str, encoding_name: str) -> int:
    """Returns the number of tokens in a text string."""
    encoding = tiktoken.get_encoding(encoding_name)
    num_tokens = len(encoding.encode(string))
    return num_tokens

# Get word weights
def load_word_weights():
    word_weights = {}
    with open(get_config_file_path("word_weights.txt"), "r") as f:
        for line in f:
            token, weight = line.strip().split(",")
            weight = int(weight)

            word_weights[token] = weight
            word_weights[' ' + token] = weight
            word_weights[token.lower()] = weight
            word_weights[token.upper()] = weight

            # Add variations with punctuation marks
            punctuations = ['!', '.', ',', '?', ';', ':']
            for punc in punctuations:
                word_weights[token + punc] = weight
                word_weights[' ' + token + punc] = weight
                word_weights[token.lower() + punc] = weight
                word_weights[token.upper() + punc] = weight

    return word_weights

# Build weights
def build_logit_bias(tokenizer, word_weights):
    logit_bias = {}
    for word, weight in word_weights.items():
        token_id = tokenizer.encode(word)[0]
        logit_bias[token_id] = weight
    return logit_bias


# GPT-3 Embedding
def gpt3_embedding(content, engine='text-embedding-ada-002'):
    content = content.encode(encoding='ASCII',errors='ignore').decode()  # fix any UNICODE errors
    response = openai.Embedding.create(input=content,engine=engine)
    vector = response['data'][0]['embedding']  # this is a normal list
    return vector

def generate_response_from_gpt3(message, username, previous_messages, prompt, max_tokens=4000):
    message_text = message['text']
    content = f"{username}: {message_text}"
    history = load_history()

    # Combine previous messages with the new message
    messages = prompt + previous_messages + history + [{"role": "user", "content": content}]
    #messages = prompt + [{"role": "user", "content": content}]
    # print("Prompt : " + str(prompt))
    # print("Previous Messages: " + str(previous_messages))
    # print("History: "+ str(history))
    conversation_history = "\n".join([msg["content"] for msg in messages])
    print("**** GPT-3 Prompt ****\n" + conversation_history)
    #Filter Words
    conversation_history = re.sub(r'(?i)AL!', '', conversation_history)
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
    print(build_logit_bias(tokenizer, load_word_weights()))
    #Use Max tokens
    tokens_left = max_tokens - tokens
    # Use the OpenAI GPT-3 model to generate a response to the message
    response = openai.Completion.create(
        engine=openai_model_engine,
        prompt=conversation_history,
        max_tokens=tokens_left,
        top_p=0.3,
        presence_penalty=0.6,
        frequency_penalty=0.0,
        temperature=0.7,
        logit_bias = build_logit_bias(tokenizer, load_word_weights()),
        stop=None
    )

    # Get the generated response text
    response_text = response.choices[0].text.strip()

    return response_text

def generate_images_prompt_from_gpt3(message, username, prompt, max_tokens=3072):
    message_text = message['text']
    content = f"{username}: {message_text}"
    # History is the last X number of messages
    history = load_history(num_files=3)

    # Combine previous messages with the new message
    messages = prompt + history + [{"role": "user", "content": content}]
    print("Prompt : " + str(prompt))
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
        messages = prompt + history + [{"role": "user", "content": content}]
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
    #print(str(members))
    for member in members:
        # Get the user's id
        user_id = member["id"]
        # Get the user's display name
        user_name = member["profile"]["display_name"] if member["profile"]["display_name"] else member["name"]
        # Replace the user's id with their display name
        message = re.sub(user_id, user_name, message)

    return message

# Generate image from DALL-E
# def create_image(prompt):
#     response = openai.Image.create(
#         prompt=prompt,
#         n=1,
#         size="256x256",
#     )
#     image_url = response['data'][0]['url']
#     return image_url

# Trigger the modal
def trigger_modal(channel_id, image_url, title):  # Update the function parameters
    try:
        response = client.chat_postMessage(
            channel=channel_id,  # Use the channel_id here
            text="Here's your image:",
            blocks=[
                {
                    "type": "image",
                    "title": {"type": "plain_text", "text": title},
                    "image_url": image_url,
                    "alt_text": "Generated image",
                }
            ],
        )
    except Exception as e:
        print(f"Error opening modal: {e}")

# 
def create_image(prompt):
    output = rep.run(
        "cjwbw/kandinsky-2:65a15f6e3c538ee4adf5142411455308926714f7d3f5c940d9f7bc519e0e5c1a",
        input={"prompt": prompt}
    )
    url = generate_image_url(download_and_save_image(output))
    return url

def download_and_save_image(image_url):
    response = requests.get(image_url, stream=True)
    response.raise_for_status()

    file_extension = os.path.splitext(image_url)[-1]
    new_file_name = f"{uuid.uuid4()}{file_extension}"
    save_path = os.path.join(get_images_path, new_file_name)

    with open(save_path, "wb") as file:
        shutil.copyfileobj(response.raw, file)

    return new_file_name

import datetime
import logging
import os
import sys
from uuid import uuid4

import openai
import pinecone
import re
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from threading import Thread
from config.api_keys import (openai_api_key, openai_model_engine, openai_max_tokens, pinecone_api_key,
                      pinecone_enviroment, slack_app_token, slack_bot_token)

from utils.file_handler import read_from_file, load_json, get_messages_file_path, randomize_words
from utils.conversation_handler import load_conversation, load_history, save_user_prompt
from utils.gpt3_helpers import num_tokens_from_string, gpt3_embedding, generate_response_from_gpt3, replace_user_ids_with_names, create_image, trigger_modal, generate_images_prompt_from_gpt3

try:
    script_dir = os.path.dirname(os.path.realpath(sys.argv[0]))
    phrases = read_from_file("config/phrases.txt").strip()
    phrases = randomize_words(phrases)
    conversation_lines = read_from_file("config/conversation_content.txt").splitlines()

    personality = read_from_file("config/personality.txt").replace("{phrases}", phrases)

    # Chatbot Options
    convo_length = 2  # Number of relevant messages to load

    prompt = [{"role": "system", "content": personality}]
    prompt_context = [{"role": "user", "content": line.strip()} for line in conversation_lines if line.strip()]
    prompt = prompt + prompt_context

    prompt_image = [{"role": "system", "content": read_from_file("config/prompt_image.txt")}]

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
    logging.basicConfig(filename=os.path.join(script_dir, "log/openai_chatbot.log"), level=logging.INFO)

    @app.event("app_mention")
    def handle_app_mention_events(body, logger):
    # Create a logger object
        logger = logging.getLogger(__name__)
        with open(get_messages_file_path()) as log_file:
            logger.info(str(body) + "\n")
            log_file.write(str(body) + "\n")

    # Make an image
    @app.command("/image")
    def make_image(ack, respond, command):
        ack()
        user_prompt = command["text"]
        channel_id = command["channel_id"]  # Get the channel ID from the command
        image_url = create_image(user_prompt)

        if image_url:
            # Send an initial message to the user
            respond(text="Processing your image, please wait...")

            # Trigger the modal after the image is ready
            trigger_modal(channel_id, image_url, f"{user_prompt} Image")  # Pass the channel_id here
        else:
            respond(text="Failed to create an image. Please try again.")

    @app.message(".*")
    def feed_message_to_openai(message, say, ack):
        print("Feed message to OpenAI called")
        logger = logging.getLogger(__name__)
        ack()
        payload = list()
        with open(get_messages_file_path(), "a") as log_file:
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

            # Generate Images Prompt
            # image_prompt = generate_images_prompt_from_gpt3(message, user, prompt_image)

            # print("Image Prompt:" + image_prompt)
            # # Create an image using the image prompt
            # #image_url=""
            # image_url = create_image(image_prompt)

            # # If the image creation is successful, send the image to the channel
            # if image_url:
            #     say({
            #         "blocks": [
            #             {
            #                 "type": "image",
            #                 "block_id": "image_block",
            #                 "title": {
            #                     "type": "plain_text",
            #                     "text": "image"
            #                 },
            #                 "image_url": image_url,
            #                 "alt_text": "image"
            #             }
            #         ]
            #     })
        say(response_text)

    @app.message(".*")
    def feed_message_to_openai(message, say, ack):
        print("Generate Image called")
        logger = logging.getLogger(__name__)
        ack()
        with open(get_messages_file_path(), "a") as log_file:
            user = replace_user_ids_with_names(message["user"], members)
            print(message["user"])
            user_id = str(message["user"])
            print(user_id)
            text = message["text"]
            # # Generate Images Prompt
            image_prompt = generate_images_prompt_from_gpt3(message, user, prompt_image)

            print("Image Prompt:" + image_prompt)
            # Create an image using the image prompt
            image_url = create_image(image_prompt)

            # If the image creation is successful, send the image to the channel
            if image_url:
                say({
                    "blocks": [
                        {
                            "type": "image",
                            "block_id": "image_block",
                            "title": {
                                "type": "plain_text",
                                "text": "image"
                            },
                            "image_url": image_url,
                            "alt_text": "image"
                        }
                    ]
                })
        say()


    if __name__ == "__main__":
        response = app.client.users_list()
        members = response["members"]
        handler = SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"])
        handler.start()

except Exception as e:
        print(f"An error occurred: {e}")

finally:
    input("Press Enter to close the script...")
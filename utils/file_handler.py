import json
import os
import random
from config.api_keys import image_host

def read_from_file(file_path):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    abs_path = os.path.join(script_dir, "..", file_path)
    with open(abs_path, "r") as file:
        content = file.read()
    return content


def load_json(filepath):
    with open(filepath, 'r', encoding='utf-8') as infile:
        return json.load(infile)

def get_messages_file_path():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    abs_messages_file = os.path.join(script_dir, "..", "log", "messages.txt")
    return abs_messages_file

def get_nexus_folder_path():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    abs_nexus_folder = os.path.join(script_dir, "..", "nexus")
    return abs_nexus_folder

def get_config_file_path(filename):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    abs_nexus_folder = os.path.join(script_dir, "..", "config")
    file_path = os.path.join(abs_nexus_folder, filename)
    return file_path

def get_images_path(filename):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    abs_nexus_folder = os.path.join(script_dir, "..", "images")
    file_path = os.path.join(abs_nexus_folder, filename)
    return file_path

def generate_image_url(file_name):
    return image_host + file_name

def randomize_words(text):
    # Split the text into words
    words = text.split()

    # Shuffle the words
    random.shuffle(words)

    # Join the words back together into a single string
    randomized_text = ' '.join(words)

    return randomized_text
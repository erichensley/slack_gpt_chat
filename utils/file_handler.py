import json
import os

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

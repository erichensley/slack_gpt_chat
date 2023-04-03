import json

def read_from_file(file_path):
    with open(file_path, "r") as f:
        content = f.read()
    return content

def load_json(filepath):
    with open(filepath, 'r', encoding='utf-8') as infile:
        return json.load(infile)

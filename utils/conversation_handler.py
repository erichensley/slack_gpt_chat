import json
import os
import datetime

from utils.file_handler import load_json

def load_conversation(results):
    result = list()
    for m in results['matches']:
        try:
            info = load_json('nexus/%s.json' % m['id'])
            result.append(info)
        except FileNotFoundError:
            print(f"File 'nexus/{m['id']}.json' not found, skipping.")
            continue

    result = [item for sublist in result for item in sublist]
    ordered = sorted(result, key=lambda d: d['timestamp'], reverse=False)  # sort them all chronologically

    return ordered

def load_history(folder_path='nexus/', num_files=20):
    # Get a list of all files in the folder and their modification times
    all_files = [(os.path.join(folder_path, f), os.path.getmtime(os.path.join(folder_path, f))) for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f))]
    
    # Sort the files by modification time, in descending order (most recent first)
    sorted_files = sorted(all_files, key=lambda x: x[1], reverse=True)
    
    # Load the specified number of most recent files
    result = []
    for file_path, _ in sorted_files[:num_files]:
        try:
            info = load_json(file_path)
            result.append(info)
        except FileNotFoundError:
            print(f"File '{file_path}' not found, skipping.")
            continue

    result = [item for sublist in result for item in sublist]
    ordered = sorted(result, key=lambda d: d['timestamp'], reverse=False)  # sort them all chronologically

    # Extract messages from the ordered list
    messages = [{"role": "assistant" if i["username"] == "Crapbot6001" else "user",
                 "content": f'{i["username"]}: {i["message"]}'} for i in ordered]

    return messages

# Save user prompt to daily log
def save_user_prompt(metadata):
    # print("Save User Prompt Called")
    date_str = datetime.date.today().strftime("%Y-%m-%d")
    log_filename = f"nexus/%s.json" % metadata["uuid"]

    try:
        with open(log_filename, "r") as f:
            logs = json.load(f)
    except FileNotFoundError:
        logs = []

    try:
        message_text = metadata["message"]["text"]
    except TypeError as e:
        print(f"Error while handling save_user_prompt: {e}")
        return

    log_entry = {
        "timestamp": metadata["time"],
        "username": metadata["username"],
        "message": message_text,
        "uuid": metadata["uuid"]
    }
    logs.append(log_entry)

    with open(log_filename, "w") as f:
        json.dump(logs, f, indent=4)

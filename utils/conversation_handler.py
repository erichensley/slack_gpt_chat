import json
import os
import datetime

from utils.file_handler import load_json, get_nexus_folder_path

def load_conversation(results):
    result = list()
    print(results)
    nexus_folder = get_nexus_folder_path()

    for m in results['matches']:
        try:
            info = load_json(os.path.join(nexus_folder, f'{m["id"]}.json'))
            result.append(info)
        except FileNotFoundError:
            print(f"File '{nexus_folder}/{m['id']}.json' not found, skipping.")
            continue

    print(result)
    #ordered = sorted(result, key=lambda d: d['timestamp'], reverse=False)  # sort them all chronologically

    ordered = sorted(result, key=lambda d: d[0]['timestamp'] if isinstance(d, list) else d['timestamp'], reverse=False)  # sort them all chronologically

    # Extract messages from the ordered list
    # messages = [{"role": "assistant" if i["username"] == "Crapbot6001" else "user",
    #              "content": f'{i["username"]}: {i["message"]}'} for i in ordered]

    messages = [{"role": "assistant" if (i[0]["username"] if isinstance(i, list) else i["username"]) == "Crapbot6001" else "user",
            "content": f'{i[0]["username"] if isinstance(i, list) else i["username"]}: {i[0]["message"] if isinstance(i, list) else i["message"]}'} for i in ordered] 
    print(messages)

    

    return messages




def load_history(folder_path=get_nexus_folder_path(), num_files=20):
    # Get a list of all files in the folder and their modification times
    all_files = [(os.path.join(folder_path, f), os.path.getmtime(os.path.join(folder_path, f))) for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f))]
    
    # Sort the files by modification time, in descending order (most recent first)
    sorted_files = sorted(all_files, key=lambda x: x[1], reverse=True)
    
    # Load the specified number of most recent files
    result = []
    for file_path, _ in sorted_files[:num_files]:
        try:
            info = load_json(file_path)
            if isinstance(info, list):
                result.extend(info)
            elif isinstance(info, dict):
                result.append(info)
        except FileNotFoundError:
            print(f"File '{file_path}' not found, skipping.")
            continue

    ordered = sorted(result, key=lambda d: d['timestamp'], reverse=False)  # sort them all chronologically

    # Extract messages from the ordered list
    messages = [{"role": "assistant" if i["username"] == "Crapbot6001" else "user",
                 "content": f'{i["username"]}: {i["message"]}'} for i in ordered]

    return messages


def save_user_prompt(metadata):
    # print("Save User Prompt Called")
    date_str = datetime.date.today().strftime("%Y-%m-%d")
    nexus_folder = get_nexus_folder_path()
    os.makedirs(nexus_folder, exist_ok=True)
    log_filename = os.path.join(nexus_folder, f"{metadata['uuid']}.json")

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

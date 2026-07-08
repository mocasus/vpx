import os, json

CRED_FILE = "/config/credentials.json"

def get_api_token():
    if os.path.exists(CRED_FILE):
        with open(CRED_FILE) as f:
            return json.load(f).get("api_token", "")
    return os.environ.get("API_TOKEN", "")

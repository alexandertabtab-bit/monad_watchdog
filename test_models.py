import os
import requests

# Make sure your API key is loaded in your environment
api_key = os.environ.get("GROQ_API_KEY")

headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}

response = requests.get("https://api.groq.com/openai/v1/models", headers=headers)
models = response.json()

print("Models you have access to:")
for model in models.get("data", []):
    print(f"- {model['id']}")

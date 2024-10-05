from flask import Blueprint, render_template, request, jsonify
import requests
import json

app = Blueprint('chat', __name__)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        user_message = request.form.get('message')
        bot_response = get_bot_response(user_message)
        return jsonify({'response': bot_response})
    return render_template('chat.html')

def get_bot_response(user_message):
    api_url = 'http://localhost:11434/api/generate'  # адрес Ollama API

    request_body = {
        "model": "qwen2:1.5b",  # модель Ollama
        "prompt": user_message,
        "stream": False
    }

    

    response = requests.post(api_url, json=request_body)
    response_data = response.json()

    if 'response' in response_data:
        return response_data['response']
    else:
        return "Извини, я не понял."
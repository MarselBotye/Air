from flask import Blueprint, request, jsonify, render_template
import base64
import json
import time
import requests
import io
from PIL import Image
from io import BytesIO

app = Blueprint('draw', __name__)

# Класс для работы с API Ollama
class OllamaAPI:
    def __init__(self, url):
        self.URL = url

    def improve_prompt(self, prompt):
        # Системный промпт
        system_prompt = "You are a helpful assistant. Improve the following prompt for generating an image: Enhance this prompt to vividly generate an image:. Only output the improved prompt, nothing else:"

        # Объединяем системный и пользовательский промпт
        combined_prompt = f"{system_prompt}\n\n{prompt}"

        # Ограничиваем длину до 1000 символов
        if len(combined_prompt) > 1000:
            combined_prompt = combined_prompt[:1000]

        data = {
            "model": "qwen2.5:1.5b",  # Используем модель LLaMA 3.1
            "prompt": combined_prompt,
            "stream": False  # Отключаем стриминг для получения полного ответа сразу
        }
        response = requests.post(self.URL, json=data)
        response_data = response.json()
        return response_data['response'].strip()

class Text2ImageAPI:
    def __init__(self, url, api_key, secret_key):
        self.URL = url
        self.AUTH_HEADERS = {
            'X-Key': f'Key {api_key}',
            'X-Secret': f'Secret {secret_key}',
        }

    def get_model(self):
        response = requests.get(self.URL + 'key/api/v1/models', headers=self.AUTH_HEADERS)
        data = response.json()
        return data[0]['id']

    def generate(self, prompt, model, images=1, width=1024, height=1024):
        params = {
            "type": "GENERATE",
            "numImages": images,
            "width": width,
            "height": height,
            "generateParams": {
                "query": f"{prompt}"
            }
        }

        data = {
            'model_id': (None, model),
            'params': (None, json.dumps(params), 'application/json')
        }
        response = requests.post(self.URL + 'key/api/v1/text2image/run', headers=self.AUTH_HEADERS, files=data)
        data = response.json()
        return data['uuid']

    def check_generation(self, request_id, attempts=10, delay=10):
        while attempts > 0:
            response = requests.get(self.URL + 'key/api/v1/text2image/status/' + request_id,
                                    headers=self.AUTH_HEADERS)
            data = response.json()
            if data['status'] == 'DONE':
                return data['images']

            attempts -= 1
            time.sleep(delay)


@app.route('/generate_image', methods=['POST'])
def generate_image():
    prompt = request.form.get('message') 

    ollama_api = OllamaAPI('http://localhost:11434/api/generate')
    improved_prompt = ollama_api.improve_prompt(prompt)
    print("Log impr_promt", improved_prompt)
    kandinsky_api = Text2ImageAPI('https://api-key.fusionbrain.ai/', "093A428AF977F2B0FB42EA032D86794BB",
                                  "1517F3B149148EEC852DEDC2CF0F9ACBB")
    model_id = kandinsky_api.get_model()
    uuid = kandinsky_api.generate(improved_prompt, model_id)
    images = kandinsky_api.check_generation(uuid)

    #  Декодируем  base64  изображение  в  байты
    image_bytes = base64.b64decode(images[0])

    #  Создаем  объект  изображения  из  байтов
    image = Image.open(BytesIO(image_bytes)) 

    # Преобразуем картинку в байты
    buffered = BytesIO()
    image.save(buffered, format="PNG")
    image_bytes = buffered.getvalue()

    # Кодируем изображение в base64
    image_base64 = base64.b64encode(image_bytes).decode('utf-8')

    # Возвращаем base64 в виде JSON ответа
    return jsonify({'image_data': image_base64})
from flask import Flask, render_template, request, jsonify, session # импортируем jsonify и session
from summ import app as summ_app, scrape # импортируем scrape из summ
from draw import app as draw_app
from chat import app as chat_app
import uuid
import time
import re
import requests

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Установи секретный ключ для сессий
app.config['CSRF_ENABLED'] = False

app.register_blueprint(summ_app, url_prefix='/summ')
app.register_blueprint(draw_app, url_prefix='/draw')
app.register_blueprint(chat_app, url_prefix='/chat')

# Словарь для хранения контекста каждого пользователя
user_contexts = {}

@app.route('/', methods=['GET', 'POST'])
def index():
    return render_template('index.html')

@app.route('/process_input', methods=['POST'])
def process_input():
    user_id = session.get('user_id')  # Используем session вместо request.session
    if user_id is None:
        # Если пользователь не аутентифицирован, создаем новый ID
        user_id = str(uuid.uuid4())
        session['user_id'] = user_id

    if user_id not in user_contexts:
        user_contexts[user_id] = {
            'last_interaction': time.time(),
            'conversation_history': []
        }

    user_message = request.form.get('message')

    # Определение интента (пока упрощенно)
    if 'суммируй' in user_message.lower() or 'резюмируй' in user_message.lower():
        intent = 'summarize'
    elif 'нарисуй' in user_message.lower() or 'сгенерируй картинку' in user_message.lower():
        intent = 'generate_image'
    elif any(word in user_message.lower() for word in ['прочитай', 'ocr', 'текст']):
        intent = 'ocr'
    else:
        intent = 'chat'

    if intent == 'summarize':
        # Парсинг ссылки из сообщения
        url = extract_url(user_message)
        if url:
            try:
                result = scrape(url)
                summary = result['summary']
                user_contexts[user_id]['conversation_history'].append(
                    {'user': user_message, 'bot': summary})
                return jsonify({'response': summary})
            except Exception as e:
                return jsonify({'response': f"Ошибка при обработке ссылки: {str(e)}"})
        else:
            return jsonify({'response': "Пожалуйста, предоставьте ссылку для суммаризации."})

    elif intent == 'generate_image':
        # Отправляем запрос на генерацию изображения в draw.py
        response = requests.post('http://127.0.0.1:5000/draw/generate_image', data={'message': user_message})
        
        # Проверяем статус ответа
        if response.status_code == 200: 
            response_data = response.json()
            
            if 'image_data' in response_data:
                image_data = response_data['image_data']
                bot_response = f'<img src="data:image/png;base64,{image_data}" alt="Сгенерированное изображение">'
            else:
                bot_response = "Ошибка при генерации изображения: неверный формат ответа."
        else:
            bot_response = f"Ошибка при генерации изображения: код ответа {response.status_code}"
    
        user_contexts[user_id]['conversation_history'].append(
            {'user': user_message, 'bot': bot_response})
        return jsonify({'response': bot_response})
        
    elif intent == 'ocr':
        # OCR распознавание
        # ... (код для OCR распознавания)
        pass
    elif intent == 'chat':
        # Обработка чат-сообщения
        bot_response = get_bot_response(user_message, user_contexts[user_id]['conversation_history'])
        user_contexts[user_id]['conversation_history'].append({'user': user_message, 'bot': bot_response})
        return jsonify({'response': bot_response})


def get_bot_response(user_message, conversation_history):
    # Добавляем историю чата в промпт
    context = "История разговора:\n" + "\n".join(
        [f"Пользователь: {message['user']}\nБот: {message['bot']}" for message in conversation_history]
    )

    api_url = 'http://localhost:11434/api/generate'
    request_body = {
        "model": "qwen2.5:1.5b",
        "prompt": f"{context}\nПользователь: {user_message}\nБот:",
        "stream": True
    }

    response = requests.post(api_url, json=request_body)
    response_data = response.json()

    if 'response' in response_data:
        return response_data['response']
    else:
        return "Извини, я не понял."

def extract_url(text):
    url_pattern = re.compile(r'https?://\S+')
    match = url_pattern.search(text)
    return match.group(0) if match else None

if __name__ == '__main__':
    app.run(debug=True)
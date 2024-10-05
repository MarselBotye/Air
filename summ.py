from flask import Flask, request, render_template, Blueprint # импортируем Blueprint
import requests
from bs4 import BeautifulSoup
import json

app = Blueprint('summ', __name__) # создаем blueprint summ

# Функция для парсинга страницы
def scrape(url):
    result = {
        'title': '',
        'images': [],
        'summary': ''
    }

    response = requests.get(url)
    if response.status_code != 200:
        raise Exception(f"Ошибка статуса: {response.status_code} {response.reason}")

    soup = BeautifulSoup(response.content, 'html.parser')

    # Извлечение заголовка
    title = soup.select_one('.tm-article-presenter__content')
    if title:
        result['title'] = title.get_text(strip=True)

    # Извлечение изображений
    images = soup.select('.tm-article-presenter__content img')
    result['images'] = [img['src'] for img in images if img.has_attr('src')]

    # Получение суммаризации текста
    try:
        result['summary'] = get_summary(result['title'])
    except Exception as e:
        result['summary'] = f"Ошибка суммаризации: {str(e)}"

    return result

# Функция для получения суммаризации через API Ollama
def get_summary(text):
    api_url = "http://localhost:11434/api/chat"

    request_body = {
        'model': 'qwen2:1.5b',
        'messages': [
            {
                'role': 'user',
                'content': f"Суммаризируй следующий текст: {text}"
            }
        ],
        'stream': False
    }

    headers = {'Content-Type': 'application/json'}

    response = requests.post(api_url, headers=headers, data=json.dumps(request_body))
    if response.status_code != 200:
        raise Exception(f"Ошибка запроса к API Ollama: {response.status_code} {response.reason}")

    response_data = response.json()
    return response_data['message']['content']


@app.route('/', methods=['GET', 'POST'])
def index():
    title = ''
    images = []
    summary = ''
    if request.method == 'POST':
        url = request.form.get('url')
        try:
            result = scrape(url)
            title = result['title']
            images = result['images']
            summary = result['summary']
        except Exception as e:
            return f"Ошибка: {str(e)}", 500
    # Передаем переменные даже при GET-запросе
    return render_template('summ.html', title=title, images=images, summary=summary)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
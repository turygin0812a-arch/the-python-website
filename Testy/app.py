from flask import Flask, render_template, request, redirect, url_for, session
from weather_app import weather_bp
from dotenv import load_dotenv
import os

# 1. Загружаем переменные один раз здесь
load_dotenv('key.env')

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

# Регистрация модуля погоды
app.register_blueprint(weather_bp, url_prefix='/weather')


@app.after_request
def add_header(response):
    # 2. ИСПРАВЛЕНО: Добавлен домен ://weatherapi.com (откуда идут иконки)
    # и исправлен заголовок для корректной работы API
    response.headers['Content-Security-Policy'] = "img-src 'self' https://://weatherapi.com https://weatherapi.com;"
    return response


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == 'admin' and password == 'admin':
            session['user_role'] = 'admin'
            session['username'] = 'Администратор'
        else:
            session['user_role'] = 'guest'
            session['username'] = username
        return redirect(url_for('home'))
    return render_template('login.html')


@app.route('/')
def home():
    if 'user_role' not in session:
        return redirect(url_for('login'))
    return render_template('index.html', role=session['user_role'], name=session['username'])


@app.route('/skills')
def skills():
    if 'user_role' not in session or session['user_role'] != 'admin':
        return "<h1>Доступ запрещен</h1>", 403
    return render_template('skills.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/contact')
def contact():
    return render_template('contact.html')


if __name__ == '__main__':
    # Проверка ключа в консоли при запуске
    if not os.getenv("API_KEY"):
        print("ВНИМАНИЕ: API_KEY не найден! Проверьте переменные окружения или файл key.env")

    # Читаем динамический порт, который выделяет сервер Amvera
    port = int(os.environ.get("PORT", 8080))

    # Запускаем Flask на хосте 0.0.0.0 и нужном порту
    app.run(host='0.0.0.0', port=port, debug=False)

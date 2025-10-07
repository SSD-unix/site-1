from flask import Flask, render_template_string, request, redirect, url_for, make_response, session, jsonify
import g4f
import json
import hashlib
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this-in-production'

users_db = {}

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# --- HTML шаблоны ---
LOGIN_TEMPLATE = '''<html>...твой HTML код для логина и регистрации...</html>'''  # вставь весь LOGIN_TEMPLATE из твоего кода
MAIN_TEMPLATE = '''<html>...твой HTML код для главной страницы...</html>'''  # вставь весь MAIN_TEMPLATE из твоего кода

# --- Маршруты ---
@app.route('/')
def index():
    username = request.cookies.get('username')
    if username and username in users_db:
        return redirect(url_for('home'))
    return render_template_string(LOGIN_TEMPLATE)

@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')
    remember = request.form.get('remember')
    if username in users_db:
        if users_db[username]['password'] == hash_password(password):
            session['username'] = username
            resp = make_response(redirect(url_for('home')))
            if remember:
                resp.set_cookie('username', username, max_age=30*24*60*60)
            return resp
        else:
            return render_template_string(LOGIN_TEMPLATE, error='Неверный пароль')
    else:
        return render_template_string(LOGIN_TEMPLATE, error='Пользователь не найден')

@app.route('/register', methods=['POST'])
def register():
    username = request.form.get('username')
    password = request.form.get('password')
    password_confirm = request.form.get('password_confirm')
    if password != password_confirm:
        return render_template_string(LOGIN_TEMPLATE, error='Пароли не совпадают')
    if username in users_db:
        return render_template_string(LOGIN_TEMPLATE, error='Пользователь уже существует')
    users_db[username] = {'password': hash_password(password), 'history': []}
    session['username'] = username
    resp = make_response(redirect(url_for('home')))
    resp.set_cookie('username', username, max_age=30*24*60*60)
    return resp

@app.route('/home')
def home():
    username = session.get('username')
    if not username or username not in users_db:
        return redirect(url_for('index'))
    history = users_db[username].get('history', [])
    return render_template_string(MAIN_TEMPLATE, username=username, history=history)

@app.route('/ask', methods=['POST'])
def ask():
    username = session.get('username')
    if not username:
        return jsonify({'success': False, 'error': 'Не авторизован'})
    data = request.json
    question = data.get('question')
    language = data.get('language', 'russian')
    lang_prompts = {
        'russian': 'Ответь на русском языке: ',
        'english': 'Answer in English: ',
        'armenian': 'Պատասխանիր հայերեն: '
    }
    prompt = lang_prompts.get(language, '') + question
    try:
        from g4f.client import Client
        client = Client()
        response_obj = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}]
        )
        response = response_obj.choices[0].message.content
        users_db[username]['history'].append({
            'question': question,
            'answer': response,
            'language': language,
            'timestamp': datetime.now().isoformat()
        })
        return jsonify({'success': True, 'answer': response})
    except Exception as e:
        try:
            response = g4f.ChatCompletion.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}]
            )
            users_db[username]['history'].append({
                'question': question,
                'answer': response,
                'language': language,
                'timestamp': datetime.now().isoformat()
            })
            return jsonify({'success': True, 'answer': response})
        except Exception as e2:
            return jsonify({'success': False, 'error': f'Ошибка: {str(e2)}. Попробуй обновить g4f: pip install -U g4f'})

@app.route('/logout', methods=['POST'])
def logout():
    session.pop('username', None)
    resp = make_response(redirect(url_for('index')))
    resp.set_cookie('username', '', expires=0)
    return resp

# --- Запуск ---
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host='0.0.0.0', port=port)

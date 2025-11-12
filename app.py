from flask import Flask, render_template, request, jsonify, send_from_directory, session, redirect, url_for
import os
import json
import uuid
from werkzeug.utils import secure_filename
import fitz
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import re
from config import Config
from auth_utils import auth_manager, login_required
from ai_checker import AIAnswerChecker
from dataclasses import asdict
from flask import send_from_directory

AI_AVAILABLE = False
checker = None

# Функция для получения checker
def get_ai_checker():
    """
    Возвращает экземпляр AI checker, инициализируя его
    с актуальным API ключом и моделью из конфигурации.
    """
    global checker, AI_AVAILABLE
    from ai_config import AIConfig

    # Принудительно загружаем самые свежие настройки из файла
    AIConfig.load_from_file()
    
    try:
        # Передаем ключ и модель из настроек напрямую
        checker = AIAnswerChecker(provider="gemini", api_key=AIConfig.GEMINI_API_KEY)
        AI_AVAILABLE = True
    except (ValueError, Exception) as e:
        checker = None
        AI_AVAILABLE = False
        # Не выводим ошибку здесь, чтобы не спамить в консоль при каждом запросе
        
    return checker
    

app = Flask(__name__)
app.config.from_object(Config)
app.secret_key = app.config['SECRET_KEY']

Config.create_directories()
# Дополнительно создаем папку для логов, если ее нет
# Загружаем настройки AI при старте, чтобы ключ был доступен
from ai_config import AIConfig
AIConfig.load_from_file()

LOGS_DIR = os.path.join(Config.BASE_DIR, 'logs')
if not os.path.exists(LOGS_DIR):
    os.makedirs(LOGS_DIR)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS

def convert_pdf_to_images(pdf_path, output_dir):
    """Конвертация PDF в PNG изображения с использованием PyMuPDF и передача масштаба для полей"""
    image_data = []
    base_name = os.path.splitext(os.path.basename(pdf_path))[0]

    try:
        doc = fitz.open(pdf_path)
        zoom = Config.PDF_DPI / 72.0
        matrix = fitz.Matrix(zoom, zoom)

        for i, page in enumerate(doc):
            pix = page.get_pixmap(matrix=matrix)
            image_filename = f"{base_name}_page_{i+1}.png"
            image_path = os.path.join(output_dir, image_filename)
            pix.save(image_path)

            image_data.append({
                'filename': image_filename,
                'width': pix.width,
                'height': pix.height,
                'page_width': page.rect.width,
                'page_height': page.rect.height,
                'zoom': zoom
            })

        doc.close()
        return image_data
    except Exception as e:
        print(f"Ошибка конвертации PDF (PyMuPDF): {e}")
        return None

def save_to_google_sheets(sheet_url, student_data):
    """Сохранение результатов в Google Таблицы"""
    try:
        creds_path = os.path.join(Config.CREDENTIALS_FOLDER, 'credentials.json')
        if not os.path.exists(creds_path):
            return {"error": "Файл credentials.json не найден"}

        creds = Credentials.from_service_account_file(creds_path, scopes=Config.GOOGLE_SHEETS_SCOPES)
        client = gspread.authorize(creds)
        sheet = client.open_by_url(sheet_url)

        try:
            worksheet = sheet.worksheet("Результаты")
        except gspread.WorksheetNotFound:
            worksheet = sheet.add_worksheet(title="Результаты", rows=1000, cols=10)
            worksheet.append_row(['ФИО', 'Класс', 'Дата', 'Время', 'Правильных ответов', 'Всего вопросов', 'Процент'])

        now = datetime.now()
        date_str = now.strftime('%d.%m.%Y')
        time_str = now.strftime('%H:%M:%S')

        total_questions = student_data['total_questions']
        correct_answers = student_data['correct_answers']
        percentage = round((correct_answers / total_questions * 100), 1) if total_questions > 0 else 0

        row_data = [
            student_data['name'],
            student_data['class'],
            date_str,
            time_str,
            correct_answers,
            total_questions,
            f"{percentage}%"
        ]

        worksheet.append_row(row_data)
        return {"success": True}

    except Exception as e:
        return {"error": str(e)}


@app.route('/ai-settings')
@login_required
def ai_settings_page():
    """Страница настроек AI"""
    return render_template('ai_settings.html', login=session.get('login'))


@app.route('/api/ai/settings', methods=['GET', 'POST'])
@login_required
def ai_settings():
    """API для работы с настройками AI"""
    settings_file = os.path.join(Config.BASE_DIR, 'ai_settings.json')
    
    if request.method == 'GET':
        # Чтение настроек
        try:
            if os.path.exists(settings_file):
                with open(settings_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
            else:
                # Настройки по умолчанию из ai_config.py
                from ai_config import AIConfig
                settings = {
                    'ai_enabled': AIConfig.AI_CHECKING_ENABLED,
                    'similarity_threshold': AIConfig.SIMILARITY_THRESHOLD,
                    'api_key': 'YOUR_API_KEY_HERE',
                    'ai_model': AIConfig.GEMINI_MODEL,
                    'temperature': AIConfig.GENERATION_CONFIG['temperature'],
                    'max_tokens': AIConfig.GENERATION_CONFIG['max_output_tokens'],
                    'top_p': AIConfig.GENERATION_CONFIG['top_p'],
                    'system_prompt': AIConfig.SYSTEM_PROMPT,
                    'cache_enabled': AIConfig.CACHE_AI_RESPONSES,
                    'cache_duration': AIConfig.CACHE_DURATION,
                    'logging_enabled': AIConfig.LOG_AI_REQUESTS,
                    'log_file': AIConfig.AI_LOG_FILE
                }
            
            return jsonify({'success': True, 'config': settings})
        
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    elif request.method == 'POST':
        # Сохранение настроек
        try:
            settings = request.get_json()
            
            # Сохраняем в файл
            with open(settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, ensure_ascii=False, indent=2)
            
            # Обновляем конфигурацию в памяти
            from ai_config import AIConfig
            AIConfig.AI_CHECKING_ENABLED = settings.get('ai_enabled', True)
            AIConfig.SIMILARITY_THRESHOLD = settings.get('similarity_threshold', 0.8)
            
            if settings.get('api_key') and not settings['api_key'].startswith('***'):
                AIConfig.GEMINI_API_KEY = settings['api_key']
            
            AIConfig.GEMINI_MODEL = settings.get('ai_model', 'gemini-pro')
            AIConfig.GENERATION_CONFIG['temperature'] = settings.get('temperature', 0.1)
            AIConfig.GENERATION_CONFIG['max_output_tokens'] = settings.get('max_tokens', 200)
            AIConfig.GENERATION_CONFIG['top_p'] = settings.get('top_p', 0.95)
            AIConfig.SYSTEM_PROMPT = settings.get('system_prompt', AIConfig.SYSTEM_PROMPT)
            AIConfig.CACHE_AI_RESPONSES = settings.get('cache_enabled', True)
            AIConfig.CACHE_DURATION = settings.get('cache_duration', 3600)
            AIConfig.LOG_AI_REQUESTS = settings.get('logging_enabled', True)
            AIConfig.AI_LOG_FILE = settings.get('log_file', 'logs/ai_checks.log')
            
            return jsonify({'success': True, 'message': 'Настройки сохранены'})
        
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/ai/test', methods=['POST'])
@login_required
def test_ai():
    """Тестирование AI проверки"""
    global checker
    
    try:
        if not checker:
            return jsonify({
                'success': False, 
                'error': "AI Checker недоступен. Проверьте API ключ в переменной GOOGLE_API_KEY."
            }), 500
               
        tests = [
            {
                'name': 'Точное совпадение',
                'student_answer': 'Астана',
                'correct_answer': 'Астана',
                'expected': True
            },
            {
                'name': 'Регистр',
                'student_answer': 'астана',
                'correct_answer': 'Астана',
                'expected': True
            },
            {
                'name': 'Синоним',
                'student_answer': 'столица Казахстана',
                'correct_answer': 'Астана',
                'expected': True
            },
            {
                'name': 'Опечатка',
                'student_answer': 'Астан',
                'correct_answer': 'Астана',
                'expected': True
            },
            {
                'name': 'Неправильный ответ',
                'student_answer': 'Караганда',
                'correct_answer': 'Астана',
                'expected': False
            }
        ]

        results = []
        for test in tests:
            result = checker.check_answer(
                student_answer=test['student_answer'],
                correct_variants=[test['correct_answer']],
                question_context=f"Тест: {test['name']}"
            )
            
            result_dict = asdict(result)
            
            test_result = {
                'name': test['name'],
                'student_answer': test['student_answer'],
                'correct_answer': test['correct_answer'],
                'result': result_dict.get('is_correct', False),
                'expected': test['expected'],
                'passed': result_dict.get('is_correct') == test['expected'],
                'ai_confidence': result_dict.get('confidence', 0.0),
                'ai_explanation': result_dict.get('explanation', '')
            }
            
            results.append(test_result)
            
        return jsonify({'success': True, 'tests': results})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    


@app.route('/api/ai/status')
@login_required
def ai_status():
    """Статус AI системы"""
    try:
        from ai_config import AIConfig
        
        status = {
            'available': AI_AVAILABLE,
            'enabled': AIConfig.AI_CHECKING_ENABLED,
            'api_key_configured': AIConfig.GEMINI_API_KEY != 'YOUR_API_KEY_HERE',
            'model': AIConfig.GEMINI_MODEL
        }
        
        if not status['available']:
            status['error'] = 'AI модуль не загружен'
        elif not status['api_key_configured']:
            status['error'] = 'API ключ не настроен'
        
        return jsonify(status)
    
    except Exception as e:
        return jsonify({
            'available': False,
            'error': str(e)
        }), 500


@app.route('/api/ai/stats')
@login_required
def ai_stats():
    """Статистика AI проверок"""
    try:
        from ai_config import AIConfig
        
        stats = {
            'total_checks': 0,
            'ai_checks': 0,
            'cache_size': 0,
            'success_rate': 0
        }
        
        # Читаем логи для статистики
        if os.path.exists(AIConfig.AI_LOG_FILE):
            with open(AIConfig.AI_LOG_FILE, 'r', encoding='utf-8') as f:
                logs = [json.loads(line) for line in f if line.strip()]
                
                stats['total_checks'] = len(logs)
                stats['ai_checks'] = len(logs)  # Все записи в логах - это AI проверки
                
                if logs:
                    success_count = sum(1 for log in logs if log.get('success'))
                    stats['success_rate'] = round((success_count / len(logs)) * 100, 1)
        
        # Размер кэша
        try:
            from ai_checker_0 import get_ai_checker
            checker = get_ai_checker()
            if hasattr(checker, 'cache') and checker.cache:
                stats['cache_size'] = len(checker.cache)
        except:
            pass
        
        return jsonify({'success': True, **stats})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/ai/logs')
@login_required
def ai_logs():
    """Получение логов AI"""
    try:
        from ai_config import AIConfig
        
        logs = []
        if os.path.exists(AIConfig.AI_LOG_FILE):
            with open(AIConfig.AI_LOG_FILE, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        try:
                            logs.append(json.loads(line))
                        except:
                            continue
        
        return jsonify({'success': True, 'logs': logs})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/ai/logs/clear', methods=['POST'])
@login_required
def clear_ai_logs():
    """Очистка логов AI"""
    try:
        from ai_config import AIConfig
        
        if os.path.exists(AIConfig.AI_LOG_FILE):
            # Создаем бэкап перед очисткой
            backup_file = AIConfig.AI_LOG_FILE + f'.backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
            os.rename(AIConfig.AI_LOG_FILE, backup_file)
            
            # Создаем новый пустой файл
            with open(AIConfig.AI_LOG_FILE, 'w', encoding='utf-8') as f:
                pass
        
        return jsonify({'success': True, 'message': 'Логи очищены (создан бэкап)'})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/ai/cache/clear', methods=['POST'])
@login_required
def clear_ai_cache():
    """Очистка кэша AI"""
    try:
        from ai_checker_0 import get_ai_checker
        checker = get_ai_checker()
        
        cleared_items = 0
        if hasattr(checker, 'cache') and checker.cache:
            cleared_items = len(checker.cache)
            checker.cache.clear()
        
        return jsonify({
            'success': True,
            'cleared_items': cleared_items,
            'message': f'Очищено записей: {cleared_items}'
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/user/info')
@login_required
def user_info():
    """Информация о текущем пользователе"""
    return jsonify({
        'username': session.get('login', 'Гость'),
        'logged_in': session.get('logged_in', False)
    })


# ==========================
# КОНЕЦ API ЭНДПОИНТОВ
# ==========================


@app.route('/')
def home():
    """Новая главная страница для выбора роли."""
    return render_template('index.html')

@app.route('/editor')
@login_required
def editor_page():
    return render_template('editor.html', login=session.get('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('logged_in'):
        return redirect(url_for('editor_page'))

    error = None
    if request.method == 'POST':
        login_val = request.form.get('login')
        password_val = request.form.get('password')

        result = auth_manager.authenticate_user(login_val, password_val)

        if result['success']:
            session['logged_in'] = True
            session['login'] = result['login']
            next_url = request.args.get('next') or url_for('editor_page')
            return redirect(next_url)
        else:
            error = result['error']

    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    session.pop('login', None)
    return redirect(url_for('login'))

@app.route('/student')
def student():
    return render_template('student.html')

# Файл: app.py

# ... (другие импорты, например, os, json) ...

@app.route('/get_template_list')
@login_required
def get_template_list():
    """
    Возвращает список доступных шаблонов для редактора.
    """
    try:
        templates_dir = Config.TEMPLATES_FOLDER
        template_files = [f for f in os.listdir(templates_dir) if f.endswith('.json')]
        
        template_list = []
        for filename in template_files:
            try:
                filepath = os.path.join(templates_dir, filename)
                with open(filepath, 'r', encoding='utf-8') as f:
                    template_data = json.load(f)
                
                template_list.append({
                    'id': filename,
                    'name': template_data.get('name', filename.replace('.json', ''))
                })
            except Exception as e:
                print(f"Ошибка чтения файла шаблона {filename}: {e}")
                
        return jsonify(template_list)
        
    except FileNotFoundError:
        return jsonify({'error': 'Папка с шаблонами не найдена или недоступна'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500



@app.route('/upload', methods=['POST'])
@login_required
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'Файл не выбран'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Файл не выбран'}), 400

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(Config.UPLOAD_FOLDER, filename)
        file.save(file_path)

        if filename.lower().endswith('.pdf'):
            image_data = convert_pdf_to_images(file_path, Config.UPLOAD_FOLDER)
            if image_data:
                return jsonify({
                    'success': True,
                    'files': [item['filename'] for item in image_data],
                    'images_data': image_data,
                    'type': 'pdf'
                })
            else:
                return jsonify({'error': 'Ошибка конвертации PDF'}), 500
        else:
            return jsonify({
                'success': True,
                'files': [filename],
                'type': 'image'
            })

    return jsonify({'error': 'Неподдерживаемый формат файла'}), 400

@app.route('/load_template/<template_id>')
def load_template(template_id):
    """
    УНИВЕРСАЛЬНАЯ функция загрузки шаблона.
    Работает как с filename.json, так и с template_id.
    Используется как редактором, так и студентом.
    """
    try:
        # Определяем имя файла
        if template_id.endswith('.json'):
            # Если передан полный filename
            safe_filename = secure_filename(template_id)
            filepath = os.path.join(Config.TEMPLATES_FOLDER, safe_filename)
        else:
            # Если передан template_id
            filepath = os.path.join(Config.TEMPLATES_FOLDER, f"{template_id}.json")

        # Проверяем существование файла
        if not os.path.exists(filepath):
            return jsonify({'error': f'Шаблон не найден'}), 404

        # Читаем и возвращаем содержимое
        with open(filepath, 'r', encoding='utf-8') as f:
            template_data = json.load(f)

        return jsonify(template_data)

    except Exception as e:
        print(f"Ошибка при загрузке шаблона {template_id}: {e}")
        return jsonify({'error': 'Внутренняя ошибка сервера при чтении шаблона'}), 500

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    """
    Обслуживает запросы к загруженным файлам (изображениям) из папки UPLOAD_FOLDER.
    """
    # app.config['UPLOAD_FOLDER'] берется из Config.UPLOAD_FOLDER в config.py
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


@app.route('/save_template', methods=['POST'])
@login_required
def save_template():
    """
    Сохранение шаблона в JSON файл.
    """
    try:
        data = request.get_json()

        # Генерация ID если не указан
        if 'template_id' not in data or not data['template_id']:
            data['template_id'] = f"tpl_{uuid.uuid4().hex[:8]}"

        # Формирование имени файла
        filename = f"{data['template_id']}.json"
        filepath = os.path.join(Config.TEMPLATES_FOLDER, filename)

        # Сохранение
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return jsonify({'success': True, 'template_id': data['template_id']})

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    

@app.route('/list_templates')
def list_templates():
    """
    Возвращает список всех шаблонов для студента.
    """
    try:
        templates = []
        if os.path.exists(Config.TEMPLATES_FOLDER):
            for filename in os.listdir(Config.TEMPLATES_FOLDER):
                if filename.endswith('.json'):
                    filepath = os.path.join(Config.TEMPLATES_FOLDER, filename)
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            templates.append({
                                'id': data.get('template_id', filename[:-5]),
                                'name': data.get('name', filename[:-5])
                            })
                    except Exception as e:
                        print(f"Ошибка чтения шаблона {filename}: {e}")
                        continue

        return jsonify(templates)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

def calculate_similarity(s1, s2):
    """
    Вычисляет схожесть двух строк (расстояние Левенштейна)
    Возвращает значение от 0 до 1, где 1 - полное совпадение
    """
    if s1 == s2:
        return 1.0
    
    len1, len2 = len(s1), len(s2)
    if len1 == 0 or len2 == 0:
        return 0.0
    
    # Матрица расстояний
    matrix = [[0] * (len2 + 1) for _ in range(len1 + 1)]
    
    for i in range(len1 + 1):
        matrix[i][0] = i
    for j in range(len2 + 1):
        matrix[0][j] = j
    
    for i in range(1, len1 + 1):
        for j in range(1, len2 + 1):
            cost = 0 if s1[i-1] == s2[j-1] else 1
            matrix[i][j] = min(
                matrix[i-1][j] + 1,      # удаление
                matrix[i][j-1] + 1,      # вставка
                matrix[i-1][j-1] + cost  # замена
            )
    
    distance = matrix[len1][len2]
    max_len = max(len1, len2)
    similarity = 1 - (distance / max_len)
    
    return similarity

# Замените маршрут /check_answers в app.py на этот код:

# Замените функцию check_answers в app.py на эту версию:

@app.route('/check_answers', methods=['POST'])
def check_answers():
    try:
        # Загружаем актуальные настройки перед каждой проверкой
        from ai_config import AIConfig
        AIConfig.load_from_file()
        
        data = request.get_json()
        template_id = data.get('template_id')
        answers = data.get('answers', {})
        student_info = data.get('student_info', {})
        sheet_url = data.get('sheet_url')

        # Загружаем шаблон
        template_path = os.path.join(Config.TEMPLATES_FOLDER, f"{template_id}.json")
        if not os.path.exists(template_path):
            return jsonify({"success": False, "error": "Шаблон не найден"}), 404

        # КРИТИЧНО: Явно указываем кодировку UTF-8 при чтении
        with open(template_path, 'r', encoding='utf-8') as f:
            template = json.load(f)

        template_name = template.get("name", template_id)
        fields = template.get('fields', [])

        # Получаем AI checker
        ai_checker = get_ai_checker()

        correct_count = 0
        total_count = len(fields)
        detailed_results = []
        student_answers_list = []
        question_headers = []
        ai_check_count = 0

        for i, field in enumerate(fields):
            field_id = field['id']
            correct_variants = [v.strip().lower() for v in field.get('variants', [])]
            student_answer = answers.get(field_id, "").strip()
            student_answer_lower = student_answer.lower()

            # Инициализируем переменные для каждого поля
            is_correct = False
            checked_by_ai = False
            ai_confidence = 0.0
            ai_explanation = ""
            ai_error = None
            check_method = "none"
            
            if correct_variants:
                # 1. Точное совпадение (с учетом регистра)
                if student_answer_lower in correct_variants:
                    is_correct = True
                    checked_by_ai = False
                    check_method = "exact"
                    
                # 2. Проверка без пробелов и знаков препинания (для числовых ответов)
                elif any(
                    student_answer_lower.replace(' ', '').replace(',', '').replace('.', '') == 
                    variant.replace(' ', '').replace(',', '').replace('.', '')
                    for variant in correct_variants
                ):
                    is_correct = True
                    checked_by_ai = False
                    check_method = "numeric_sequence"
                    
                # 3. Проверка начала строки (если ответ студента - начало правильного)
                elif any(
                    len(student_answer) >= 3 and 
                    variant.startswith(student_answer_lower)
                    for variant in correct_variants
                ):
                    is_correct = True
                    checked_by_ai = False
                    check_method = "partial_match"
                    
                # 4. Проверка с допуском опечаток (расстояние Левенштейна)
                elif any(
                    len(student_answer) > 3 and 
                    calculate_similarity(student_answer_lower, variant) > 0.85
                    for variant in correct_variants
                ):
                    is_correct = True
                    checked_by_ai = False
                    check_method = "similarity_85"
                    
                # 5. AI проверка - только если все предыдущие методы не сработали
                elif ai_checker and student_answer and len(student_answer) > 1:
                    try:
                        question_context = correct_variants[0] if correct_variants else ""
                        
                        print(f"🤖 AI проверка для поля {field_id}:")
                        print(f"   Ответ студента: '{student_answer}'")
                        print(f"   Правильные варианты: {correct_variants}")
                        
                        check_result = ai_checker.check_answer(
                            student_answer=student_answer,
                            correct_variants=correct_variants,
                            question_context=question_context,
                            system_prompt=AIConfig.SYSTEM_PROMPT,
                            model_name=AIConfig.GEMINI_MODEL
                        )
                        
                        result_dict = asdict(check_result)
                        
                        print(f"   ✅ Результат: {result_dict}")
                        
                        is_correct = result_dict.get('is_correct', False)
                        checked_by_ai = True
                        ai_confidence = result_dict.get('confidence', 0.0)
                        
                        # КРИТИЧНО: Получаем explanation с правильной кодировкой
                        ai_explanation = result_dict.get('explanation', 'Нет объяснения от AI')
                        
                        # Убеждаемся что explanation в UTF-8
                        if isinstance(ai_explanation, bytes):
                            ai_explanation = ai_explanation.decode('utf-8')
                        
                        check_method = "ai"
                        
                        if is_correct:
                            ai_check_count += 1

                        # === ЛОГИРОВАНИЕ AI ПРОВЕРКИ ===
                        if AIConfig.LOG_AI_REQUESTS:
                            log_entry = {
                                "timestamp": datetime.now().isoformat(),
                                "template_id": template_id,
                                "field_id": field_id,
                                "question_number": i + 1,
                                "student_answer": student_answer,
                                "correct_variants": correct_variants,
                                "question_context": question_context,
                                "ai_provider": result_dict.get('ai_provider', 'unknown'),
                                "is_correct": is_correct,
                                "confidence": ai_confidence,
                                "explanation": ai_explanation,
                                "success": True
                            }
                            
                            log_file_path = os.path.join(Config.BASE_DIR, AIConfig.AI_LOG_FILE)
                            os.makedirs(os.path.dirname(log_file_path), exist_ok=True)
                            
                            # КРИТИЧНО: Явно указываем кодировку UTF-8 при записи
                            with open(log_file_path, 'a', encoding='utf-8') as log_f:
                                log_f.write(json.dumps(log_entry, ensure_ascii=False, indent=None) + '\n')

                    except Exception as ai_err:
                        ai_error = str(ai_err)
                        is_correct = False
                        checked_by_ai = True
                        ai_explanation = f"Ошибка вызова AI: {ai_error}"
                        check_method = "ai_error"
                        print(f"⚠️ Ошибка AI проверки для поля {field_id}: {ai_err}")
                        
                        # Выводим полный traceback для отладки
                        import traceback
                        traceback.print_exc()
                        
                        # === ЛОГИРОВАНИЕ ОШИБКИ AI ===
                        if AIConfig.LOG_AI_REQUESTS:
                            log_entry = {
                                "timestamp": datetime.now().isoformat(),
                                "template_id": template_id,
                                "field_id": field_id,
                                "question_number": i + 1,
                                "student_answer": student_answer,
                                "correct_variants": correct_variants,
                                "error": ai_error,
                                "error_traceback": traceback.format_exc(),
                                "success": False
                            }
                            
                            log_file_path = os.path.join(Config.BASE_DIR, AIConfig.AI_LOG_FILE)
                            os.makedirs(os.path.dirname(log_file_path), exist_ok=True)
                            
                            # КРИТИЧНО: UTF-8 кодировка
                            with open(log_file_path, 'a', encoding='utf-8') as log_f:
                                log_f.write(json.dumps(log_entry, ensure_ascii=False, indent=None) + '\n')

            if is_correct:
                correct_count += 1

            # Подготовка детального результата
            detail = {
                "field_id": field_id,
                "student_answer": student_answer,
                "correct_variants": correct_variants,
                "is_correct": is_correct,
                "checked_by_ai": checked_by_ai,
                "ai_confidence": ai_confidence,
                "ai_explanation": ai_explanation if checked_by_ai else None,
                "check_method": check_method
            }
            
            if ai_error:
                detail["ai_error"] = ai_error
            
            detailed_results.append(detail)
            student_answers_list.append(student_answer)

            # Формирование заголовков
            if correct_variants:
                base_header = correct_variants[0]
                clean_header = re.sub(r'[^\w\s\-а-яёА-ЯЁ]', '', base_header)
                clean_header = clean_header[:30].strip()

                if not clean_header:
                    clean_header = f"Вопрос {i+1}"

                header = clean_header
                if clean_header in question_headers:
                    header = f"{clean_header} ({i+1})"
            else:
                header = f"Вопрос {i+1}"

            question_headers.append(header)

        percentage = round((correct_count / total_count) * 100, 2) if total_count else 0

        # Запись в Google Sheets
        sheets_result = None
        if sheet_url:
            try:
                creds_path = os.path.join(Config.CREDENTIALS_FOLDER, 'credentials.json')
                if not os.path.exists(creds_path):
                    raise Exception("Файл credentials.json не найден")

                creds = Credentials.from_service_account_file(
                    creds_path, 
                    scopes=Config.GOOGLE_SHEETS_SCOPES
                )
                client = gspread.authorize(creds)
                sheet = client.open_by_url(sheet_url)
                worksheet_title = template_name

                try:
                    worksheet = sheet.worksheet(worksheet_title)
                except gspread.WorksheetNotFound:
                    worksheet = sheet.add_worksheet(
                        title=worksheet_title, 
                        rows=1000, 
                        cols=30
                    )

                existing_data = worksheet.get_all_values()

                base_headers = [
                    "Название шаблона",
                    "ФИО",
                    "Класс",
                    "Дата",
                    "Время",
                    "Правильных ответов",
                    "Всего вопросов",
                    "Процент",
                    "AI проверок"
                ]

                all_headers = base_headers + question_headers

                if not existing_data or existing_data[0] != all_headers:
                    worksheet.clear()
                    worksheet.append_row(all_headers)

                now = datetime.now()
                
                student_name = student_info.get("studentName") or student_info.get("name", "")
                student_class = student_info.get("studentClass") or student_info.get("class", "")
                
                base_row_data = [
                    template_name,
                    student_name,
                    student_class,
                    now.strftime("%d.%m.%Y"),
                    now.strftime("%H:%M:%S"),
                    correct_count,
                    total_count,
                    f"{percentage}%",
                    ai_check_count
                ]

                complete_row_data = base_row_data + student_answers_list
                worksheet.append_row(complete_row_data)

                sheets_result = {
                    "success": True,
                    "message": f"Результаты сохранены во вкладку '{worksheet_title}'."
                }

            except Exception as e:
                sheets_result = {
                    "success": False, 
                    "error": f"Ошибка Google Sheets: {str(e)}"
                }

        # КРИТИЧНО: Формируем JSON ответ с ensure_ascii=False для правильной кодировки
        return app.response_class(
            response=json.dumps({
                "success": True,
                "correct_count": correct_count,
                "total_count": total_count,
                "percentage": percentage,
                "details": detailed_results,
                "sheets_result": sheets_result,
                "ai_check_count": ai_check_count,
                "ai_available": AI_AVAILABLE
            }, ensure_ascii=False, indent=2),
            status=200,
            mimetype='application/json; charset=utf-8'
        )

    except Exception as e:
        print(f"❌ Ошибка в check_answers: {e}")
        import traceback
        traceback.print_exc()
        
        return app.response_class(
            response=json.dumps({
                "success": False, 
                "error": str(e)
            }, ensure_ascii=False),
            status=500,
            mimetype='application/json; charset=utf-8'
        )

@app.route('/static/classes.json')
def get_classes():
    try:
        classes_path = os.path.join(Config.STATIC_FOLDER, 'classes.json')
        with open(classes_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        default_classes = [
            "1А", "1Б", "1В",
            "2А", "2Б", "2В",
            "3А", "3Б", "3В",
            "4А", "4Б", "4В",
            "5А", "5Б", "5В",
            "6А", "6Б", "6В",
            "7А", "7Б", "7В",
            "8А", "8Б", "8В",
            "9А", "9Б", "9В",
            "10А", "10Б",
            "11А", "11Б"
        ]

        os.makedirs(Config.STATIC_FOLDER, exist_ok=True)
        classes_path = os.path.join(Config.STATIC_FOLDER, 'classes.json')
        with open(classes_path, 'w', encoding='utf-8') as f:
            json.dump(default_classes, f, ensure_ascii=False, indent=2)

        return jsonify(default_classes)

if __name__ == '__main__':
    app.run(debug=Config.DEBUG)
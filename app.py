from flask import Flask, render_template, request, jsonify, send_from_directory, session, redirect, url_for, abort
import os
import json
import uuid
from werkzeug.utils import secure_filename
import fitz
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, date
import re
from config import Config
from auth_utils import auth_manager, login_required, superuser_required
from ai_checker import AIAnswerChecker
from dataclasses import asdict
from flask import send_from_directory
from models import SessionLocal, User, Template, AuditLog, Subject, SubjectClass
from validators import ValidationError, validate_teacher_data, validate_topic, validate_topic_slug, validate_subject_classes
from utils import generate_username, generate_username_from_name, generate_topic_slug, generate_random_password, sanitize_username

AI_AVAILABLE = False
checker = None

try:
    from ai_cache import cache_manager
    CACHE_MANAGER_AVAILABLE = True
except ImportError:
    CACHE_MANAGER_AVAILABLE = False

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
    
    # Если checker уже создан, возвращаем его
    if checker is not None:
        return checker
    
    try:
        # Создаем новый экземпляр только если его нет
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
from answer_scorer import preload_model, score_answer
AIConfig.load_from_file()
# Прогреваем локальные модели (spaCy + sentence-transformers)
try:
    preload_model()
except Exception as preload_err:
    print(f"⚠️ Не удалось прогреть локальные модели: {preload_err}")

#LOGS_DIR = os.path.join(Config.BASE_DIR, 'logs')
#if not os.path.exists(LOGS_DIR):
 #   os.makedirs(LOGS_DIR)


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


@app.route('/api/user/info')
@login_required
def user_info():
    """Информация о текущем пользователе"""
    return jsonify({
        'username': session.get('login', 'Гость'),
        'role': session.get('role'),
        'logged_in': session.get('logged_in', False)
    })


# ==========================
# ФУНКЦИИ ДЛЯ ЛОГИРОВАНИЯ
# ==========================

def log_audit_action(action, target_type=None, target_id=None, details=None):
    """
    Логирование действия в audit_log.
    
    Args:
        action: Тип действия (create_teacher, update_teacher, delete_teacher, etc.)
        target_type: Тип объекта (teacher, test)
        target_id: ID объекта
        details: Дополнительные детали (dict)
    """
    try:
        db = SessionLocal()
        log_entry = AuditLog(
            user_id=session.get('user_id'),
            username=session.get('login'),
            action=action,
            target_type=target_type,
            target_id=target_id,
            details=details or {},
            ip_address=request.remote_addr,
            created_at=datetime.utcnow()
        )
        db.add(log_entry)
        db.commit()
        db.close()
    except Exception as e:
        print(f"Ошибка при логировании действия: {e}")


# ==========================
# HTML СТРАНИЦЫ ДЛЯ АДМИНИСТРИРОВАНИЯ
# ==========================

@app.route('/admin/teachers')
@superuser_required
def admin_teachers_page():
    """Страница управления учителями"""
    return render_template('admin_teachers.html', login=session.get('login'))

@app.route('/admin/subjects')
@superuser_required
def admin_subjects_page():
    """Страница управления предметами"""
    return render_template('admin_subjects.html', login=session.get('login'))

# ==========================
# API ДЛЯ УПРАВЛЕНИЯ УЧИТЕЛЯМИ
# ==========================

@app.route('/api/admin/teachers', methods=['GET'])
@superuser_required
def list_teachers():
    """Список всех учителей (только для супер-пользователя)"""
    try:
        db = SessionLocal()
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        username_filter = request.args.get('username')  # Для фильтрации по username
        
        # Получение всех учителей
        query = db.query(User).filter(User.role == 'teacher')
        
        # Фильтр по username если указан
        if username_filter:
            query = query.filter(User.username == username_filter)
        
        # Подсчет общего количества
        total = query.count()
        
        # Пагинация
        teachers = query.order_by(User.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()
        
        # Подсчет количества тестов для каждого учителя
        teachers_data = []
        for teacher in teachers:
            tests_count = db.query(Template).filter(
                Template.created_by_username == teacher.username
            ).count()
            
            teachers_data.append({
                'id': teacher.id,
                'username': teacher.username,
                'first_name': teacher.first_name,
                'last_name': teacher.last_name,
                'email': teacher.email,
                'city': teacher.city,
                'city_code': teacher.city_code,
                'school': teacher.school,
                'school_code': teacher.school_code,
                'is_active': teacher.is_active,
                'expiration_date': teacher.expiration_date.isoformat() if teacher.expiration_date else None,
                'max_tests_limit': teacher.max_tests_limit,
                'tests_count': tests_count,
                'created_at': teacher.created_at.isoformat() if teacher.created_at else None
            })
        
        db.close()
        
        return jsonify({
            'success': True,
            'teachers': teachers_data,
            'total': total,
            'page': page,
            'per_page': per_page
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/teacher/info')
@login_required
def get_teacher_info():
    """Получение данных текущего учителя (для использования в редакторе)"""
    try:
        username = session.get('username') or session.get('login')
        if not username:
            return jsonify({'success': False, 'error': 'Пользователь не авторизован'}), 401
        
        db = SessionLocal()
        teacher = db.query(User).filter(User.username == username).first()
        
        if not teacher:
            db.close()
            return jsonify({'success': False, 'error': 'Учитель не найден'}), 404
        
        teacher_data = {
            'username': teacher.username,
            'city': teacher.city,
            'city_code': teacher.city_code,
            'school': teacher.school,
            'school_code': teacher.school_code
        }
        
        db.close()
        
        return jsonify({'success': True, 'teacher': teacher_data})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/admin/teachers', methods=['POST'])
@superuser_required
def create_teacher():
    """Создание нового учителя"""
    try:
        data = request.get_json()
        
        # Валидация данных
        validate_teacher_data(data)
        
        db = SessionLocal()
        
        # Генерация или использование логина
        if 'username' in data and data['username'] and data['username'].strip():
            # Использовать предоставленный логин
            username = sanitize_username(data['username'].strip())
            if not username:
                db.close()
                return jsonify({
                    'success': False,
                    'error': 'Логин не может быть пустым'
                }), 400
        else:
            # Автогенерация логина из имени
            existing_usernames = [u[0] for u in db.query(User.username).all()]
            username = generate_username_from_name(
                data['last_name'],
                data['first_name'],
                existing_usernames
            )
        
        # Проверка уникальности логина
        existing_user = db.query(User).filter(User.username == username).first()
        if existing_user:
            db.close()
            return jsonify({
                'success': False,
                'error': f'Пользователь с логином "{username}" уже существует'
            }), 400
        
        # Проверка уникальности email
        existing_email = db.query(User).filter(User.email == data['email'].strip()).first()
        if existing_email:
            db.close()
            return jsonify({
                'success': False,
                'error': f'Пользователь с email "{data["email"]}" уже существует'
            }), 400
        
        # Генерация пароля
        if data.get('generate_password', False):
            password = generate_random_password(12)
        else:
            password = data.get('password')
            if not password:
                db.close()
                return jsonify({
                    'success': False,
                    'error': 'Пароль не указан'
                }), 400
        
        # Парсинг даты истечения
        expiration_date = None
        if data.get('expiration_date'):
            try:
                expiration_date = datetime.strptime(data['expiration_date'], '%Y-%m-%d').date()
            except ValueError:
                db.close()
                return jsonify({
                    'success': False,
                    'error': 'Неверный формат даты (ожидается YYYY-MM-DD)'
                }), 400
        
        # Создание пользователя
        result = auth_manager.create_user(
            username=username,
            password=password,
            role='teacher',
            first_name=data['first_name'].strip(),
            last_name=data['last_name'].strip(),
            email=data['email'].strip(),
            city=data['city'],
            city_code=data['city_code'],
            school=data['school'],
            school_code=data['school_code'],
            expiration_date=expiration_date,
            max_tests_limit=data.get('max_tests_limit'),
            is_active=True
        )
        
        db.close()
        
        if result['success']:
            # Логирование
            log_audit_action(
                action='create_teacher',
                target_type='teacher',
                target_id=result['user_id'],
                details={
                    'username': username,
                    'city': data['city'],
                    'school': data['school']
                }
            )
            
            return jsonify({
                'success': True,
                'teacher': {
                    'id': result['user_id'],
                    'username': username,
                    'password': password  # Показываем только при создании
                },
                'message': f'Учитель "{username}" успешно создан'
            }), 201
        else:
            return jsonify({
                'success': False,
                'error': result.get('error', 'Ошибка при создании учителя')
            }), 500
    
    except ValidationError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/admin/teachers/<int:teacher_id>', methods=['GET'])
@superuser_required
def get_teacher(teacher_id):
    """Получение данных учителя"""
    try:
        db = SessionLocal()
        teacher = db.query(User).filter(
            User.id == teacher_id,
            User.role == 'teacher'
        ).first()
        
        if not teacher:
            db.close()
            return jsonify({'success': False, 'error': 'Учитель не найден'}), 404
        
        tests_count = db.query(Template).filter(
            Template.created_by_username == teacher.username
        ).count()
        
        teacher_data = {
            'id': teacher.id,
            'username': teacher.username,
            'first_name': teacher.first_name,
            'last_name': teacher.last_name,
            'email': teacher.email,
            'city': teacher.city,
            'city_code': teacher.city_code,
            'school': teacher.school,
            'school_code': teacher.school_code,
            'is_active': teacher.is_active,
            'expiration_date': teacher.expiration_date.isoformat() if teacher.expiration_date else None,
            'max_tests_limit': teacher.max_tests_limit,
            'tests_count': tests_count,
            'created_at': teacher.created_at.isoformat() if teacher.created_at else None
        }
        
        db.close()
        
        return jsonify({'success': True, 'teacher': teacher_data})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/admin/teachers/<int:teacher_id>', methods=['PUT'])
@superuser_required
def update_teacher(teacher_id):
    """Обновление данных учителя"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'Данные не получены'}), 400
        
        # Базовая валидация обязательных полей
        if 'first_name' in data and not data['first_name']:
            return jsonify({'success': False, 'error': 'Имя не может быть пустым'}), 400
        if 'last_name' in data and not data['last_name']:
            return jsonify({'success': False, 'error': 'Фамилия не может быть пустой'}), 400
        if 'email' in data and not data['email']:
            return jsonify({'success': False, 'error': 'Email не может быть пустым'}), 400
        
        db = SessionLocal()
        
        teacher = db.query(User).filter(
            User.id == teacher_id,
            User.role == 'teacher'
        ).first()
        
        if not teacher:
            db.close()
            return jsonify({'success': False, 'error': 'Учитель не найден'}), 404
        
        # Обновление логина
        if 'username' in data and data['username']:
            new_username = sanitize_username(data['username'].strip())
            if not new_username:
                db.close()
                return jsonify({
                    'success': False,
                    'error': 'Логин не может быть пустым'
                }), 400
            # Проверка уникальности логина только если логин изменился
            if new_username != teacher.username:
                existing_username = db.query(User).filter(
                    User.username == new_username,
                    User.id != teacher_id
                ).first()
                if existing_username:
                    db.close()
                    return jsonify({
                        'success': False,
                        'error': f'Пользователь с логином "{new_username}" уже существует'
                    }), 400
                teacher.username = new_username
        
        # Обновление полей ФИО и email
        if 'first_name' in data:
            teacher.first_name = data['first_name'].strip()
        if 'last_name' in data:
            teacher.last_name = data['last_name'].strip()
        if 'email' in data:
            new_email = data['email'].strip()
            # Проверка уникальности email только если email изменился
            if new_email != teacher.email:
                existing_email = db.query(User).filter(
                    User.email == new_email,
                    User.id != teacher_id
                ).first()
                if existing_email:
                    db.close()
                    return jsonify({
                        'success': False,
                        'error': f'Пользователь с email "{new_email}" уже существует'
                    }), 400
                teacher.email = new_email
        
        # Обновление полей
        if 'city' in data:
            teacher.city = data['city']
        if 'city_code' in data:
            teacher.city_code = data['city_code']
        if 'school' in data:
            teacher.school = data['school']
        if 'school_code' in data:
            teacher.school_code = data['school_code']
        if 'is_active' in data:
            teacher.is_active = data['is_active']
        if 'expiration_date' in data:
            if data['expiration_date']:
                teacher.expiration_date = datetime.strptime(data['expiration_date'], '%Y-%m-%d').date()
            else:
                teacher.expiration_date = None
        if 'max_tests_limit' in data:
            teacher.max_tests_limit = data['max_tests_limit']
        
        teacher.updated_at = datetime.utcnow()
        
        try:
            db.commit()
            # Логирование
            log_audit_action(
                action='update_teacher',
                target_type='teacher',
                target_id=teacher_id,
                details=data
            )
            db.close()
            return jsonify({'success': True, 'message': 'Данные учителя обновлены'})
        except Exception as commit_error:
            db.rollback()
            db.close()
            print(f"Ошибка при коммите изменений учителя {teacher_id}: {commit_error}")
            return jsonify({'success': False, 'error': f'Ошибка при сохранении: {str(commit_error)}'}), 500
    
    except ValidationError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        import traceback
        print(f"Ошибка при обновлении учителя {teacher_id}: {e}")
        print(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/admin/teachers/<int:teacher_id>', methods=['DELETE'])
@superuser_required
def delete_teacher(teacher_id):
    """Удаление учителя (физическое удаление из БД)"""
    try:
        db = SessionLocal()
        
        teacher = db.query(User).filter(
            User.id == teacher_id,
            User.role == 'teacher'
        ).first()
        
        if not teacher:
            db.close()
            return jsonify({'success': False, 'error': 'Учитель не найден'}), 404
        
        # Сохраняем данные для логирования до удаления
        username = teacher.username
        teacher_data = {
            'username': username,
            'first_name': teacher.first_name,
            'last_name': teacher.last_name,
            'email': teacher.email
        }
        
        # Физическое удаление
        db.delete(teacher)
        db.commit()
        db.close()
        
        # Логирование (после закрытия сессии)
        log_audit_action(
            action='delete_teacher',
            target_type='teacher',
            target_id=teacher_id,
            details=teacher_data
        )
        
        return jsonify({'success': True, 'message': 'Учитель удален'})
    
    except Exception as e:
        db.rollback()
        db.close()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/admin/teachers/<int:teacher_id>/reset-password', methods=['POST'])
@superuser_required
def reset_teacher_password(teacher_id):
    """Сброс пароля учителя"""
    try:
        data = request.get_json()
        generate_new = data.get('generate', True)
        
        if generate_new:
            new_password = generate_random_password(12)
        else:
            new_password = data.get('password')
            if not new_password:
                return jsonify({
                    'success': False,
                    'error': 'Пароль не указан'
                }), 400
        
        result = auth_manager.update_user_password(teacher_id, new_password)
        
        if result['success']:
            # Логирование
            log_audit_action(
                action='reset_password',
                target_type='teacher',
                target_id=teacher_id
            )
            
            return jsonify({
                'success': True,
                'password': new_password,  # Показываем только при сбросе
                'message': 'Пароль успешно обновлен'
            })
        else:
            return jsonify({
                'success': False,
                'error': result.get('error', 'Ошибка при обновлении пароля')
            }), 500
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/admin/teachers/generate-password', methods=['POST'])
@superuser_required
def generate_password():
    """Генерация случайного пароля"""
    length = request.json.get('length', 12) if request.is_json else 12
    password = generate_random_password(length)
    return jsonify({'success': True, 'password': password})


@app.route('/admin/audit-logs', methods=['GET'])
@superuser_required
def get_audit_logs():
    """Получение логов действий (только для супер-пользователя)"""
    try:
        db = SessionLocal()
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        
        query = db.query(AuditLog)
        
        total = query.count()
        logs = query.order_by(AuditLog.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()
        
        logs_data = [{
            'id': log.id,
            'user_id': log.user_id,
            'username': log.username,
            'action': log.action,
            'target_type': log.target_type,
            'target_id': log.target_id,
            'details': log.details,
            'ip_address': log.ip_address,
            'created_at': log.created_at.isoformat() if log.created_at else None
        } for log in logs]
        
        db.close()
        
        return jsonify({
            'success': True,
            'logs': logs_data,
            'total': total,
            'page': page,
            'per_page': per_page
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ==========================
# API ДЛЯ ПОЛУЧЕНИЯ СПИСКОВ ГОРОДОВ И ШКОЛ
# ==========================

@app.route('/api/admin/cities', methods=['GET'])
@superuser_required
def get_cities():
    """Получить список уникальных городов из БД"""
    try:
        db = SessionLocal()
        cities = db.query(User.city).filter(
            User.city.isnot(None),
            User.city != ''
        ).distinct().order_by(User.city).all()
        
        cities_list = [city[0] for city in cities if city[0]]
        
        db.close()
        
        return jsonify({
            'success': True,
            'cities': cities_list
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/admin/schools', methods=['GET'])
@superuser_required
def get_schools():
    """Получить список уникальных школ из БД (с опциональным фильтром по городу)"""
    try:
        db = SessionLocal()
        city_filter = request.args.get('city')
        
        query = db.query(User.school).filter(
            User.school.isnot(None),
            User.school != ''
        )
        
        if city_filter:
            query = query.filter(User.city == city_filter)
        
        schools = query.distinct().order_by(User.school).all()
        
        schools_list = [school[0] for school in schools if school[0]]
        
        db.close()
        
        return jsonify({
            'success': True,
            'schools': schools_list
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ==========================
# API ДЛЯ УПРАВЛЕНИЯ ПРЕДМЕТАМИ
# ==========================

@app.route('/api/admin/subjects', methods=['GET'])
@superuser_required
def list_subjects():
    """Список всех предметов (только для супер-пользователя)"""
    try:
        db = SessionLocal()
        subjects = db.query(Subject).filter(Subject.is_active == True).order_by(Subject.name).all()
        
        subjects_data = []
        for s in subjects:
            # Получаем классы для предмета
            classes = db.query(SubjectClass.class_number).filter(
                SubjectClass.subject_id == s.id
            ).order_by(SubjectClass.class_number).all()
            classes_list = [c[0] for c in classes]
            
            subjects_data.append({
                'id': s.id,
                'name': s.name,
                'name_slug': s.name_slug,
                'description': s.description,
                'is_active': s.is_active,
                'classes': classes_list,
                'created_at': s.created_at.isoformat() if s.created_at else None
            })
        
        db.close()
        
        return jsonify({
            'success': True,
            'subjects': subjects_data
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/subjects', methods=['GET'])
def get_subjects():
    """Получение списка активных предметов (публичный API)"""
    try:
        db = SessionLocal()
        subjects = db.query(Subject).filter(Subject.is_active == True).order_by(Subject.name).all()
        
        subjects_data = [{
            'id': s.id,
            'name': s.name,
            'name_slug': s.name_slug
        } for s in subjects]
        
        db.close()
        
        return jsonify({
            'success': True,
            'subjects': subjects_data
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/admin/subjects', methods=['POST'])
@superuser_required
def create_subject():
    """Создание нового предмета"""
    try:
        data = request.get_json()
        
        if not data.get('name') or not data['name'].strip():
            return jsonify({
                'success': False,
                'error': 'Название предмета обязательно'
            }), 400
        
        # Валидация классов
        classes = data.get('classes', [])
        if not isinstance(classes, list):
            return jsonify({
                'success': False,
                'error': 'Классы должны быть массивом'
            }), 400
        
        try:
            validate_subject_classes(classes)
        except ValidationError as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 400
        
        name = data['name'].strip()
        name_slug = generate_topic_slug(name)  # Используем ту же функцию для генерации slug
        
        db = SessionLocal()
        
        # Проверка уникальности
        existing = db.query(Subject).filter(
            (Subject.name == name) | (Subject.name_slug == name_slug)
        ).first()
        
        if existing:
            db.close()
            return jsonify({
                'success': False,
                'error': f'Предмет с названием "{name}" уже существует'
            }), 400
        
        # Создание предмета
        subject = Subject(
            name=name,
            name_slug=name_slug,
            description=data.get('description', ''),
            is_active=True
        )
        
        db.add(subject)
        db.flush()  # Получаем ID предмета
        
        # Создание связей с классами
        for class_num in classes:
            subject_class = SubjectClass(
                subject_id=subject.id,
                class_number=class_num
            )
            db.add(subject_class)
        
        db.commit()
        subject_id = subject.id
        db.close()
        
        # Логирование
        log_audit_action(
            action='create_subject',
            target_type='subject',
            target_id=subject_id,
            details={'name': name, 'name_slug': name_slug}
        )
        
        return jsonify({
            'success': True,
            'subject': {
                'id': subject_id,
                'name': name,
                'name_slug': name_slug,
                'classes': classes
            },
            'message': f'Предмет "{name}" успешно создан'
        }), 201
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/admin/subjects/<int:subject_id>', methods=['PUT'])
@superuser_required
def update_subject(subject_id):
    """Обновление предмета"""
    try:
        data = request.get_json()
        db = SessionLocal()
        
        subject = db.query(Subject).filter(Subject.id == subject_id).first()
        
        if not subject:
            db.close()
            return jsonify({'success': False, 'error': 'Предмет не найден'}), 404
        
        # Обновление полей
        if 'name' in data and data['name']:
            new_name = data['name'].strip()
            new_slug = generate_topic_slug(new_name)
            
            # Проверка уникальности
            existing = db.query(Subject).filter(
                Subject.id != subject_id,
                ((Subject.name == new_name) | (Subject.name_slug == new_slug))
            ).first()
            
            if existing:
                db.close()
                return jsonify({
                    'success': False,
                    'error': f'Предмет с названием "{new_name}" уже существует'
                }), 400
            
            subject.name = new_name
            subject.name_slug = new_slug
        
        if 'description' in data:
            subject.description = data['description']
        
        if 'is_active' in data:
            subject.is_active = data['is_active']
        
        # Обновление классов
        if 'classes' in data:
            classes = data['classes']
            if not isinstance(classes, list):
                db.close()
                return jsonify({
                    'success': False,
                    'error': 'Классы должны быть массивом'
                }), 400
            
            try:
                validate_subject_classes(classes)
            except ValidationError as e:
                db.close()
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 400
            
            # Удаляем старые связи
            db.query(SubjectClass).filter(SubjectClass.subject_id == subject_id).delete()
            
            # Создаем новые связи
            for class_num in classes:
                subject_class = SubjectClass(
                    subject_id=subject_id,
                    class_number=class_num
                )
                db.add(subject_class)
        
        subject.updated_at = datetime.utcnow()
        
        db.commit()
        db.close()
        
        # Логирование
        log_audit_action(
            action='update_subject',
            target_type='subject',
            target_id=subject_id,
            details=data
        )
        
        return jsonify({'success': True, 'message': 'Предмет обновлен'})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/admin/subjects/<int:subject_id>', methods=['DELETE'])
@superuser_required
def delete_subject(subject_id):
    """Удаление предмета (мягкое удаление)"""
    try:
        db = SessionLocal()
        
        subject = db.query(Subject).filter(Subject.id == subject_id).first()
        
        if not subject:
            db.close()
            return jsonify({'success': False, 'error': 'Предмет не найден'}), 404
        
        # Мягкое удаление
        subject.is_active = False
        subject.updated_at = datetime.utcnow()
        
        db.commit()
        db.close()
        
        # Логирование
        log_audit_action(
            action='delete_subject',
            target_type='subject',
            target_id=subject_id,
            details={'name': subject.name}
        )
        
        return jsonify({'success': True, 'message': 'Предмет деактивирован'})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


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
    return render_template('editor.html', login=session.get('login'), role=session.get('role'))

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
            session['role'] = result.get('role', 'teacher')
            session['user_id'] = result.get('user_id')
            session['username'] = result['login']  # Для совместимости
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

@app.route('/test/<city_code>/<school_code>/<subject_slug>/<topic_slug>')
def test_by_link(city_code, school_code, subject_slug, topic_slug):
    """
    Публичный доступ к тесту по уникальной ссылке.
    Новый формат: /test/<city_code>/<school_code>/<subject_slug>/<topic_slug>
    """
    try:
        db = SessionLocal()
        
        # Поиск учителя по city_code и school_code
        username = generate_username(city_code, school_code)
        user = db.query(User).filter(User.username == username).first()
        
        if not user:
            db.close()
            return render_template('error.html', 
                error_code=404,
                error_message='Тест не найден',
                error_description='Учитель не найден. Проверьте правильность ссылки.'
            ), 404
        
        # Поиск предмета по slug
        subject = db.query(Subject).filter(
            Subject.name_slug == subject_slug,
            Subject.is_active == True
        ).first()
        
        if not subject:
            db.close()
            return render_template('error.html', 
                error_code=404,
                error_message='Тест не найден',
                error_description='Предмет не найден. Проверьте правильность ссылки.'
            ), 404
        
        # Поиск теста по username, subject_id и topic_slug
        template = db.query(Template).filter(
            Template.created_by_username == username,
            Template.subject_id == subject.id,
            Template.topic_slug == topic_slug,
            Template.is_active == True
        ).first()
        
        if not template:
            db.close()
            return render_template('error.html', 
                error_code=404,
                error_message='Тест не найден',
                error_description='Проверьте правильность ссылки или обратитесь к учителю.'
            ), 404
        
        # Проверка публичности теста
        if not template.is_public:
            db.close()
            return render_template('error.html',
                error_code=403,
                error_message='Доступ запрещен',
                error_description='Этот тест недоступен для публичного доступа.'
            ), 403
        
        # Увеличение счетчика прохождений
        template.access_count = (template.access_count or 0) + 1
        db.commit()
        db.close()
        
        # Загрузка данных шаблона из файла (для совместимости)
        template_path = os.path.join(Config.TEMPLATES_FOLDER, f"{template.template_id}.json")
        if os.path.exists(template_path):
            with open(template_path, 'r', encoding='utf-8') as f:
                template_data = json.load(f)
        else:
            # Если файла нет, создаем данные из БД
            template_data = {
                'template_id': template.template_id,
                'name': template.name,
                'topic': template.topic,
                'fields': template.fields or [],
                'files': template.images or []
            }
        
        # Передача данных в шаблон
        return render_template('student.html', 
            template_data=template_data,
            template_id=template.template_id,
            test_url=request.url
        )
    
    except Exception as e:
        print(f"Ошибка при загрузке теста: {e}")
        import traceback
        traceback.print_exc()
        return render_template('error.html',
            error_code=500,
            error_message='Внутренняя ошибка сервера',
            error_description='Произошла ошибка при загрузке теста. Попробуйте позже.'
        ), 500


@app.route('/student')
def student():
    """
    Страница студента - список доступных тестов или конкретный тест.
    """
    # Проверка, передан ли template_id в параметрах
    template_id = request.args.get('template_id')
    if template_id:
        # Загрузка конкретного теста по старому формату (для обратной совместимости)
        template_path = os.path.join(Config.TEMPLATES_FOLDER, f"{template_id}.json")
        if os.path.exists(template_path):
            with open(template_path, 'r', encoding='utf-8') as f:
                template_data = json.load(f)
            return render_template('student.html', 
                template_data=template_data,
                template_id=template_id
            )
    
    # Иначе показываем список доступных тестов
    return render_template('student.html')


# ==========================
# HEALTH CHECK & MONITORING
# ==========================

@app.route('/health')
def health_check():
    """Comprehensive health check endpoint."""
    from health import (
        get_system_health,
        check_ai_service,
        check_database,
        check_file_system,
        get_application_info
    )
    
    system = get_system_health()
    ai = check_ai_service()
    db = check_database()
    fs = check_file_system()
    app_info = get_application_info()
    
    # Determine overall status
    statuses = [system.get('status'), ai.get('status'), db.get('status'), fs.get('status')]
    if 'error' in statuses:
        overall_status = 'error'
    elif 'degraded' in statuses:
        overall_status = 'degraded'
    else:
        overall_status = 'healthy'
    
    return jsonify({
        'status': overall_status,
        'application': app_info,
        'system': system,
        'services': {
            'ai': ai,
            'database': db,
            'filesystem': fs
        }
    }), 200 if overall_status == 'healthy' else 503


@app.route('/health/live')
def liveness():
    """Kubernetes liveness probe - is the app running?"""
    return jsonify({'status': 'alive'}), 200


@app.route('/health/ready')
def readiness():
    """Kubernetes readiness probe - is the app ready to serve traffic?"""
    from health import check_ai_service, check_file_system
    
    ai = check_ai_service()
    fs = check_file_system()
    
    ready = (
        fs.get('status') == 'healthy' and
        ai.get('status') in ['healthy', 'degraded']  # AI can be degraded but still work
    )
    
    return jsonify({
        'status': 'ready' if ready else 'not_ready',
        'checks': {
            'ai': ai.get('status'),
            'filesystem': fs.get('status')
        }
    }), 200 if ready else 503


@app.route('/metrics')
def metrics():
    """Prometheus-compatible metrics endpoint."""
    from health import get_system_health
    
    system = get_system_health()
    
    if system.get('status') == 'error':
        return "# Error getting metrics\n", 500
    
    metrics_data = system.get('metrics', {})
    
    # Prometheus format
    output = []
    output.append('# HELP cpu_usage_percent CPU usage percentage')
    output.append('# TYPE cpu_usage_percent gauge')
    output.append(f'cpu_usage_percent {metrics_data.get("cpu_percent", 0)}')
    
    output.append('# HELP memory_usage_percent Memory usage percentage')
    output.append('# TYPE memory_usage_percent gauge')
    output.append(f'memory_usage_percent {metrics_data.get("memory_percent", 0)}')
    
    output.append('# HELP disk_usage_percent Disk usage percentage')
    output.append('# TYPE disk_usage_percent gauge')
    output.append(f'disk_usage_percent {metrics_data.get("disk_percent", 0)}')
    
    return '\n'.join(output) + '\n', 200, {'Content-Type': 'text/plain; charset=utf-8'}


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
        # Очистка template_id от .json если есть
        clean_template_id = template_id.replace('.json', '')
        
        # Сначала пытаемся загрузить из БД
        db = SessionLocal()
        template = db.query(Template).filter(Template.template_id == clean_template_id).first()
        
        if template:
            # Загружаем из файла для совместимости
            filepath = os.path.join(Config.TEMPLATES_FOLDER, f"{clean_template_id}.json")
            if os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8') as f:
                    template_data = json.load(f)
            else:
                # Если файла нет, создаем из БД
                template_data = {
                    'template_id': template.template_id,
                    'name': template.name,
                    'topic': template.topic,
                    'fields': template.fields or [],
                    'files': template.images or []
                }
            
            # Добавляем данные из БД
            template_data['class_number'] = template.class_number
            template_data['subject_id'] = template.subject_id
            template_data['topic'] = template.topic
            template_data['topic_slug'] = template.topic_slug
            
            db.close()
            return jsonify(template_data)
        
        # Если не найдено в БД, загружаем из файла (для обратной совместимости)
        if template_id.endswith('.json'):
            safe_filename = secure_filename(template_id)
            filepath = os.path.join(Config.TEMPLATES_FOLDER, safe_filename)
        else:
            filepath = os.path.join(Config.TEMPLATES_FOLDER, f"{clean_template_id}.json")

        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                template_data = json.load(f)
            db.close()
            return jsonify(template_data)
        
        db.close()
        return jsonify({'error': f'Шаблон не найден'}), 404

    except Exception as e:
        print(f"Ошибка при загрузке шаблона {template_id}: {e}")
        import traceback
        traceback.print_exc()
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
    Сохранение шаблона в JSON файл и БД.
    """
    try:
        data = request.get_json()
        username = session.get('username') or session.get('login')
        
        if not username:
            return jsonify({'error': 'Пользователь не авторизован'}), 401
        
        # Валидация темы
        topic = data.get('topic', '').strip()
        if not topic:
            return jsonify({'error': 'Тема теста обязательна для заполнения'}), 400
        
        try:
            validate_topic(topic)
        except ValidationError as e:
            return jsonify({'error': str(e)}), 400
        
        # Валидация класса
        class_number = data.get('class_number')
        if not class_number:
            return jsonify({'error': 'Класс обязателен для заполнения'}), 400
        
        try:
            class_number = int(class_number)
            if class_number < 1 or class_number > 11:
                return jsonify({'error': 'Класс должен быть от 1 до 11'}), 400
        except (ValueError, TypeError):
            return jsonify({'error': 'Некорректный номер класса'}), 400
        
        # Валидация предмета
        subject_id = data.get('subject_id')
        if not subject_id:
            return jsonify({'error': 'Предмет обязателен для заполнения'}), 400
        
        try:
            subject_id = int(subject_id)
        except (ValueError, TypeError):
            return jsonify({'error': 'Некорректный ID предмета'}), 400
        
        db = SessionLocal()
        
        # Проверка существования предмета
        subject = db.query(Subject).filter(
            Subject.id == subject_id,
            Subject.is_active == True
        ).first()
        
        if not subject:
            db.close()
            return jsonify({'error': 'Предмет не найден или неактивен'}), 400
        
        # Генерация topic_slug
        topic_slug = generate_topic_slug(topic)
        
        try:
            validate_topic_slug(topic_slug)
        except ValidationError as e:
            db.close()
            return jsonify({'error': f'Ошибка генерации slug: {str(e)}'}), 400
        
        # Генерация ID если не указан
        if 'template_id' not in data or not data['template_id']:
            data['template_id'] = f"tpl_{uuid.uuid4().hex[:8]}"
        
        # Проверка уникальности темы для данного учителя и предмета
        existing_template = db.query(Template).filter(
            Template.created_by_username == username,
            Template.subject_id == subject_id,
            Template.topic_slug == topic_slug
        ).first()
        
        if existing_template and str(existing_template.template_id) != data['template_id']:
            db.close()
            return jsonify({
                'error': f'Тест с темой "{topic}" по предмету "{subject.name}" для {class_number} класса уже существует. Выберите другое название темы.'
            }), 400
        
        # Проверка лимита на количество тестов
        user = auth_manager.get_user_by_username(username)
        if user and user.max_tests_limit:
            current_tests_count = db.query(Template).filter(
                Template.created_by_username == username
            ).count()
            
            if current_tests_count >= user.max_tests_limit:
                db.close()
                return jsonify({
                    'error': f'Достигнут лимит на количество тестов ({user.max_tests_limit})'
                }), 400
        
        # Получение данных учителя для формирования ссылки
        if not user:
            user = auth_manager.get_user_by_username(username)
        
        if not user or not user.city_code or not user.school_code:
            db.close()
            return jsonify({'error': 'У учителя не указаны город и школа. Обратитесь к администратору.'}), 400
        
        # Добавление полей в данные шаблона
        data['topic'] = topic
        data['topic_slug'] = topic_slug
        data['created_by_username'] = username
        data['class_number'] = class_number
        data['subject_id'] = subject_id
        
        # Формирование имени файла
        filename = f"{data['template_id']}.json"
        filepath = os.path.join(Config.TEMPLATES_FOLDER, filename)
        
        # Сохранение в файл
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        # Сохранение/обновление в БД
        template = db.query(Template).filter(
            Template.template_id == data['template_id']
        ).first()
        
        if template:
            # Обновление существующего шаблона
            template.name = data.get('name', template.name)
            template.topic = topic
            template.topic_slug = topic_slug
            template.created_by_username = username
            template.class_number = class_number
            template.subject_id = subject_id
            template.fields = data.get('fields', template.fields)
            template.images = data.get('files', template.images)
            template.is_active = data.get('is_active', True)
            template.is_public = data.get('is_public', True)
            template.updated_at = datetime.utcnow()
        else:
            # Создание нового шаблона
            template = Template(
                template_id=data['template_id'],
                name=data.get('name', 'Без названия'),
                description=data.get('description'),
                fields=data.get('fields', []),
                images=data.get('files', []),
                created_by=user.id if user else None,
                topic=topic,
                topic_slug=topic_slug,
                created_by_username=username,
                class_number=class_number,
                subject_id=subject_id,
                is_active=data.get('is_active', True),
                is_public=data.get('is_public', True)
            )
            db.add(template)
        
        db.commit()
        db.close()
        
        # Логирование создания теста
        log_audit_action(
            action='create_test' if not template.id else 'update_test',
            target_type='test',
            target_id=template.id if template.id else None,
            details={
                'template_id': data['template_id'],
                'topic': topic,
                'topic_slug': topic_slug,
                'class_number': class_number,
                'subject_id': subject_id
            }
        )
        
        # Формирование ссылки в новом формате
        base_url = request.host_url.rstrip('/')
        # Заменяем http://localhost:5000 на https://docquiz.predmet.kz если нужно
        if 'localhost' in base_url or '127.0.0.1' in base_url:
            base_url = 'https://docquiz.predmet.kz'
        test_url = f"{base_url}/test/{user.city_code}/{user.school_code}/{subject.name_slug}/{topic_slug}"
        
        return jsonify({
            'success': True,
            'template_id': data['template_id'],
            'topic': topic,
            'topic_slug': topic_slug,
            'class_number': class_number,
            'subject_id': subject_id,
            'subject_name': subject.name,
            'test_url': test_url,
            'message': 'Шаблон успешно сохранен'
        })
    
    except ValidationError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        print(f"Ошибка при сохранении шаблона: {e}")
        import traceback
        traceback.print_exc()
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

        thresholds = {
            "fuzzy_strict": AIConfig.FUZZY_STRICT,
            "fuzzy_soft": AIConfig.FUZZY_SOFT,
            "sem_threshold": AIConfig.SEM_THRESHOLD,
            "embed_max_tokens": AIConfig.EMBED_MAX_TOKENS,
        }

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
            fuzzy_score = 0.0
            semantic_sim = 0.0
            
            # Локальный скоринг
            local_result = {
                "is_correct": False,
                "method": "none",
                "fuzzy_score": 0.0,
                "semantic_sim": 0.0,
                "thresholds_used": thresholds,
                "from_cache": False
            }

            if AIConfig.LOCAL_SCORER_ENABLED and student_answer:
                local_result = score_answer(
                    student_answer=student_answer,
                    variants=correct_variants,
                    thresholds=thresholds,
                    template_id=template_id,
                    field_id=field_id,
                )
                is_correct = local_result.get("is_correct", False)
                fuzzy_score = local_result.get("fuzzy_score", 0.0)
                semantic_sim = local_result.get("semantic_sim", 0.0)
                check_method = local_result.get("method", "none")

            # AI fallback при отсутствии уверенности
            need_ai = (
                not is_correct
                and ai_checker
                and AIConfig.AI_CHECKING_ENABLED
                and student_answer
                and len(student_answer) > 1
            )

            if need_ai:
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

                    try:
                        if isinstance(ai_explanation, bytes):
                            ai_explanation = ai_explanation.decode('utf-8')
                    except UnicodeDecodeError:
                        ai_explanation = "Не удалось декодировать объяснение"

                    check_method = "ai_fallback" if check_method == "none" else check_method

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
                            "success": True,
                            "fuzzy_score": fuzzy_score,
                            "semantic_sim": semantic_sim,
                            "method": check_method,
                            "thresholds_used": thresholds,
                        }

                        log_file_path = os.path.join(Config.BASE_DIR, AIConfig.AI_LOG_FILE)
                        os.makedirs(os.path.dirname(log_file_path), exist_ok=True)

                        with open(log_file_path, 'a', encoding='utf-8') as log_f:
                            log_f.write(json.dumps(log_entry, ensure_ascii=False, indent=None) + '\n')

                except Exception as ai_err:
                    ai_error = str(ai_err)
                    is_correct = False
                    checked_by_ai = True
                    ai_explanation = f"Ошибка вызова AI: {ai_error}"
                    check_method = "ai_error"
                    print(f"⚠️ Ошибка AI проверки для поля {field_id}: {ai_err}")

                    import traceback
                    traceback.print_exc()

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
                            "success": False,
                            "fuzzy_score": fuzzy_score,
                            "semantic_sim": semantic_sim,
                            "method": check_method,
                            "thresholds_used": thresholds,
                        }

                        log_file_path = os.path.join(Config.BASE_DIR, AIConfig.AI_LOG_FILE)
                        os.makedirs(os.path.dirname(log_file_path), exist_ok=True)

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
                "check_method": check_method,
                "fuzzy_score": fuzzy_score,
                "semantic_sim": semantic_sim,
                "thresholds_used": thresholds
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

@app.route('/api/ai/cache/stats')
@login_required
def ai_cache_stats():
    """Статистика кэша"""
    try:
        if not CACHE_MANAGER_AVAILABLE:
            return jsonify({'success': False, 'error': 'Менеджер кэша недоступен'})
        
        stats = cache_manager.get_cache_stats()
        return jsonify({'success': True, 'stats': stats})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/ai/cache/clear', methods=['POST'])
@login_required
def clear_ai_cache():
    """Очистка кэша AI"""
    try:
        if not CACHE_MANAGER_AVAILABLE:
            return jsonify({'success': False, 'error': 'Менеджер кэша недоступен'})
        
        cleared_count = cache_manager.clear_expired_entries()
        return jsonify({
            'success': True,
            'cleared_count': cleared_count,
            'message': f'Очищено устаревших записей: {cleared_count}'
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ==========================
# ОБРАБОТЧИКИ ОШИБОК
# ==========================

@app.errorhandler(404)
def not_found_error(error):
    """Обработчик ошибки 404"""
    return render_template('error.html',
        error_code=404,
        error_message='Страница не найдена',
        error_description='Запрашиваемая страница не существует.'
    ), 404

@app.errorhandler(403)
def forbidden_error(error):
    """Обработчик ошибки 403"""
    return render_template('error.html',
        error_code=403,
        error_message='Доступ запрещен',
        error_description='У вас нет прав для доступа к этой странице.'
    ), 403

@app.errorhandler(500)
def internal_error(error):
    """Обработчик ошибки 500"""
    return render_template('error.html',
        error_code=500,
        error_message='Внутренняя ошибка сервера',
        error_description='Произошла непредвиденная ошибка. Попробуйте позже.'
    ), 500


if __name__ == '__main__':
    app.run(debug=Config.DEBUG)

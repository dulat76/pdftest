import os
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
from flask import session, redirect, url_for, request # Импортируем для декоратора
from config import Config
from functools import wraps

class AuthManager:
    """Менеджер авторизации, использующий Google Sheets для данных пользователей."""
    
    def __init__(self):
        # Инициализация gspread клиента
        self.client = None
        self.sheet = None
        
        # 🔑 1. Определяем путь к локальному файлу credentials.json
        # Используем абсолютный путь из config.py
        self.creds_path = os.path.join(Config.CREDENTIALS_FOLDER, 'credentials.json')

        # 2. Проверяем наличие файла. Если файл отсутствует, показываем ошибку.
        if not os.path.exists(self.creds_path):
            print("FATAL ERROR: credentials.json not found for AuthManager at path:", self.creds_path)
            print("СИСТЕМА АВТОРИЗАЦИИ ТРЕБУЕТ НАСТРОЙКИ! Создайте файл и вставьте JSON.")
            return

        try:
            # 3. Авторизация клиента с помощью ЛОКАЛЬНОГО ФАЙЛА (Правильный метод для PythonAnywhere)
            creds = Credentials.from_service_account_file(self.creds_path, scopes=Config.GOOGLE_SHEETS_SCOPES)
            self.client = gspread.authorize(creds)
            
            # 4. Открытие таблицы
            self.sheet = self.client.open_by_url(Config.USERS_SHEET_URL).sheet1
        except Exception as e:
            print(f"Error connecting to Google Sheets for Auth: {e}")
            self.client = None

    # УДАЛЕНА ФУНКЦИЯ _get_credentials_from_env, поскольку мы читаем данные с диска.
    
    def _fetch_users_data(self):
        """Получает данные пользователей из Google Таблицы."""
        if not self.sheet:
            return None

        # Ожидаемые заголовки: Login, Password, Expiration Date (в формате YYYY-MM-DD)
        try:
            # Получаем все записи как список словарей
            records = self.sheet.get_all_records()
            return records
        except Exception as e:
            print(f"Error fetching data from Google Sheets: {e}")
            return None

    def authenticate_user(self, login, password):
        # ⚠️ Проверяем инициализацию клиента
        if not self.client:
            return {"success": False, "error": "Ошибка подключения к Google Sheets. Проверьте credentials.json."}

        users_data = self._fetch_users_data()
        if users_data is None:
            return {"success": False, "error": "Не удалось загрузить данные пользователей."}
        # print(f"Loaded users data: {users_data}") 

        for user in users_data:
            # Проверка соответствия ключей заголовкам в вашей таблице
            user_login = user.get('Login')  
            user_password = user.get('Password')
            expiry_date_str = user.get('Expiration Date')
            
            if user_login == login and user_password == password:
                # Проверка срока действия
                days_left = None
                try:
                    expiry_date = datetime.strptime(expiry_date_str, '%Y-%m-%d').date()
                    today = datetime.now().date()
                    
                    if today > expiry_date:
                        return {"success": False, "error": f"Срок действия учетной записи истек ({expiry_date_str})."}
                    
                    days_left = (expiry_date - today).days

                except (ValueError, TypeError):
                    # Если формат даты неверен или отсутствует, считаем бессрочным
                    days_left = "Бессрочно"

                return {"success": True, "login": login, "days_left": days_left}
        
        return {"success": False, "error": "Неверный логин или пароль"}

auth_manager = AuthManager()

def login_required(f):
    """Декоратор для защиты маршрутов, требующих авторизации."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Проверяем, есть ли пользователь в сессии
        if session.get('logged_in') != True:
            # Сохраняем запрошенный URL для перенаправления после входа
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function
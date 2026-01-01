# -*- coding: utf-8 -*-
import os

class Config:
    DEBUG = True
    SECRET_KEY = "super-secret-key"

    SESSION_TIMEOUT_HOURS = 2
    PDF_DPI = 200

    # 1. Определение базового пути (ДОЛЖНО ИДТИ ПЕРЕД ДРУГИМИ ПУТЯМИ)
    # BASE_DIR - это абсолютный путь к папке pdftest_app
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

    # 2. Настройка всех путей (используем абсолютные пути)
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
    TEMPLATES_FOLDER = os.path.join(BASE_DIR, "templates_json")
    STATIC_FOLDER = os.path.join(BASE_DIR, "static")
    # КРИТИЧЕСКИ ВАЖНАЯ СТРОКА: папка для ключей авторизации
    CREDENTIALS_FOLDER = os.path.join(BASE_DIR, "credentials") 

    # Google Sheets API
    GOOGLE_SHEETS_SCOPES = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]

    # ссылка на Google Sheets
    USERS_SHEET_URL = "https://docs.google.com/spreadsheets/d/1yI_73HFTwXFuG2-2nwxqodoGCM0gDC6uDDp16t3aLa8/edit?gid=0#gid=0"

    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf'}


    @staticmethod
    def create_directories():
        """Создает все необходимые папки, если они не существуют."""
        import os
        for folder in [
            Config.UPLOAD_FOLDER,  
            Config.TEMPLATES_FOLDER,  
            Config.STATIC_FOLDER,
            Config.CREDENTIALS_FOLDER, # <--- Добавленная папка для ключей
            os.path.join(Config.BASE_DIR, 'logs')  # Папка для логов
            # Папка templates не нужна, так как Flask ищет ее сам в корне проекта
        ]:
            # exist_ok=True предотвращает ошибку, если папка уже есть
            os.makedirs(folder, mode=0o755, exist_ok=True)

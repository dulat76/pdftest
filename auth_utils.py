import os
from datetime import datetime, date
from werkzeug.security import check_password_hash, generate_password_hash
from flask import session, redirect, url_for, request
from config import Config
from functools import wraps
from models import SessionLocal, User

class AuthManager:
    """Менеджер авторизации, использующий PostgreSQL для данных пользователей."""
    
    def __init__(self):
        pass  # Сессия создается для каждого запроса
    
    def authenticate_user(self, login, password):
        """
        Аутентификация пользователя по логину и паролю.
        
        Args:
            login: Логин пользователя
            password: Пароль пользователя
            
        Returns:
            dict: Результат аутентификации
        """
        db = None
        try:
            db = SessionLocal()
            
            # Поиск пользователя по логину
            user = db.query(User).filter(User.username == login).first()
            
            if not user:
                return {"success": False, "error": "Неверный логин или пароль"}
            
            # Проверка активности аккаунта
            if not user.is_active:
                return {"success": False, "error": "Учетная запись деактивирована"}
            
            # Проверка пароля
            if not check_password_hash(user.password_hash, password):
                return {"success": False, "error": "Неверный логин или пароль"}
            
            # Проверка срока действия
            days_left = None
            if user.expiration_date:
                today = date.today()
                if today > user.expiration_date:
                    return {
                        "success": False,
                        "error": f"Срок действия учетной записи истек ({user.expiration_date.strftime('%Y-%m-%d')})."
                    }
                days_left = (user.expiration_date - today).days
            else:
                days_left = "Бессрочно"
            
            result = {
                "success": True,
                "login": user.username,
                "role": user.role,
                "user_id": user.id,
                "days_left": days_left
            }
            return result
        
        except Exception as e:
            import traceback
            error_msg = str(e)
            error_type = type(e).__name__
            print(f"Error authenticating user: {error_type}: {error_msg}")
            traceback.print_exc()
            return {
                "success": False, 
                "error": "Ошибка при аутентификации"
            }
        finally:
            if db:
                try:
                    db.close()
                except:
                    pass
    
    def get_user_by_username(self, username):
        """
        Получить пользователя по логину.
        
        Args:
            username: Логин пользователя
            
        Returns:
            User object or None
        """
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.username == username).first()
            db.close()
            return user
        except Exception as e:
            print(f"Error getting user: {e}")
            db.close()
            return None
    
    def get_user_by_id(self, user_id):
        """
        Получить пользователя по ID.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            User object or None
        """
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            db.close()
            return user
        except Exception as e:
            print(f"Error getting user: {e}")
            db.close()
            return None
    
    def create_user(self, username, password, role='teacher', **kwargs):
        """
        Создать нового пользователя.
        
        Args:
            username: Логин пользователя
            password: Пароль (будет захеширован)
            role: Роль пользователя ('superuser' или 'teacher')
            **kwargs: Дополнительные поля (city, city_code, school, school_code, expiration_date, etc.)
            
        Returns:
            dict: Результат создания
        """
        db = SessionLocal()
        try:
            # Проверка существования пользователя
            existing_user = db.query(User).filter(User.username == username).first()
            if existing_user:
                db.close()
                return {"success": False, "error": f"Пользователь с логином '{username}' уже существует"}
            
            # Хеширование пароля
            password_hash = generate_password_hash(password)
            
            # Создание пользователя
            user = User(
                username=username,
                password_hash=password_hash,
                role=role,
                first_name=kwargs.get('first_name', ''),
                last_name=kwargs.get('last_name', ''),
                email=kwargs.get('email', ''),
                city=kwargs.get('city'),
                city_code=kwargs.get('city_code'),
                school=kwargs.get('school'),
                school_code=kwargs.get('school_code'),
                expiration_date=kwargs.get('expiration_date'),
                max_tests_limit=kwargs.get('max_tests_limit'),
                is_active=kwargs.get('is_active', True),
                is_admin=(role == 'superuser')
            )
            
            db.add(user)
            db.commit()
            user_id = user.id
            db.close()
            
            return {"success": True, "user_id": user_id, "user": user}
        
        except Exception as e:
            db.rollback()
            db.close()
            print(f"Error creating user: {e}")
            return {"success": False, "error": f"Ошибка при создании пользователя: {str(e)}"}
    
    def update_user_password(self, user_id, new_password):
        """
        Обновить пароль пользователя.
        
        Args:
            user_id: ID пользователя
            new_password: Новый пароль
            
        Returns:
            dict: Результат обновления
        """
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                db.close()
                return {"success": False, "error": "Пользователь не найден"}
            
            user.password_hash = generate_password_hash(new_password)
            user.updated_at = datetime.utcnow()
            
            db.commit()
            db.close()
            
            return {"success": True, "message": "Пароль успешно обновлен"}
        
        except Exception as e:
            db.rollback()
            db.close()
            print(f"Error updating password: {e}")
            return {"success": False, "error": f"Ошибка при обновлении пароля: {str(e)}"}

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


def superuser_required(f):
    """Декоратор для защиты маршрутов, требующих прав супер-пользователя."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Проверяем авторизацию
        if session.get('logged_in') != True:
            return redirect(url_for('login', next=request.url))
        
        # Проверяем роль супер-пользователя
        if session.get('role') != 'superuser':
            from flask import abort
            abort(403)  # Forbidden
        
        return f(*args, **kwargs)
    return decorated_function
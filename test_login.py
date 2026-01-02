#!/usr/bin/env python3
"""
Скрипт для тестирования входа с реальными паролями
Использование: python3 test_login.py <username> <password>
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from auth_utils import auth_manager

if len(sys.argv) < 3:
    print("Использование: python3 test_login.py <username> <password>")
    print("Пример: python3 test_login.py dulat ваш_пароль")
    sys.exit(1)

username = sys.argv[1]
password = sys.argv[2]

print(f"🔐 Тестирование входа для пользователя: {username}\n")

result = auth_manager.authenticate_user(username, password)

if result['success']:
    print("✅ АУТЕНТИФИКАЦИЯ УСПЕШНА!")
    print(f"   Логин: {result['login']}")
    print(f"   Роль: {result['role']}")
    print(f"   ID: {result['user_id']}")
    print(f"   Срок действия: {result['days_left']}")
else:
    print(f"❌ АУТЕНТИФИКАЦИЯ НЕУДАЧНА")
    print(f"   Ошибка: {result['error']}")


# Команды для установки обучающего материала на сервер

## Шаг 1: Подключение к серверу
```bash
ssh ubuntu@your-server-ip
```

## Шаг 2: Переход в директорию проекта
```bash
cd ~/predmet_kz/flask_app
```

## Шаг 3: Активация виртуального окружения
```bash
source venv/bin/activate
```

## Шаг 4: Получение изменений из Git
```bash
git pull origin master
```

## Шаг 5: Проверка изменений
Убедитесь, что файлы обновились:
```bash
ls -la templates/tutorial.html
```

## Шаг 6: Перезапуск приложения Flask
```bash
sudo systemctl restart flask_app
```

## Шаг 7: Проверка статуса сервиса
```bash
sudo systemctl status flask_app
```

## Шаг 8: Проверка логов (опционально)
```bash
sudo journalctl -u flask_app -n 50 --no-pager
```

## Проверка работы
Откройте в браузере:
- `https://docquiz.predmet.kz/tutorial` - обучающий материал
- Проверьте, что ссылки на обучающий материал появились на главной странице и в справке

## Если возникли проблемы

### Проблема: Git pull требует stash
```bash
git stash
git pull origin master
git stash pop
```

### Проблема: Приложение не запускается
```bash
# Проверьте логи
sudo journalctl -u flask_app -n 100 --no-pager

# Проверьте синтаксис Python
python3 -m py_compile templates/tutorial.html  # Это не сработает для HTML, но можно проверить app.py
python3 -m py_compile app.py
```

### Проблема: Изменения не отображаются
```bash
# Очистите кэш браузера или откройте в режиме инкогнито
# Проверьте, что файл существует
ls -la templates/tutorial.html

# Проверьте права доступа
chmod 644 templates/tutorial.html
```



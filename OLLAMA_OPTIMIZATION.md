# Оптимизация Ollama для высокой нагрузки

## Рекомендуемые настройки для docker-compose.yml

Добавьте следующие переменные окружения в секцию `ollama`:

```yaml
ollama:
  image: ollama/ollama:latest
  container_name: ollama
  restart: always
  ports:
    - "11434:11434"
  volumes:
    - ollama_data:/root/.ollama
  networks:
    - app-network
  environment:
    - OLLAMA_NUM_PARALLEL=3        # Оптимально для 2 CPU
    - OLLAMA_MAX_LOADED_MODELS=1   # Одна модель в памяти
    - OLLAMA_NUM_THREAD=2          # Соответствует количеству CPU
    - OLLAMA_HOST=0.0.0.0:11434
    - OLLAMA_KEEP_ALIVE=5m         # Держать модель в памяти 5 минут
    - OLLAMA_MAX_QUEUE=15          # Очередь для пиковых нагрузок
  deploy:
    resources:
      limits:
        memory: 3G                 # Лимит памяти для Ollama
        cpus: '2.0'                # 2 CPU ядра
      reservations:
        memory: 2G
        cpus: '1.0'
```

## Объяснение параметров

### OLLAMA_NUM_PARALLEL=3
- **Рекомендуется**: 3 параллельных запроса
- **Максимум**: 4 (для 2 CPU)
- **Не рекомендуется**: 5+ (перегрузка CPU)

### OLLAMA_MAX_QUEUE=15
- **Рекомендуется**: 15 запросов в очереди
- **Максимум**: 20 (при достаточной памяти)
- **Минимум**: 10 (для базовой нагрузки)

### OLLAMA_NUM_THREAD=2
- Соответствует количеству CPU ядер
- Не превышайте количество доступных CPU

### OLLAMA_KEEP_ALIVE=5m
- Держит модель в памяти 5 минут после последнего запроса
- Ускоряет последующие запросы
- Увеличьте до 10m при высокой нагрузке

## Мониторинг производительности

### Проверка использования ресурсов
```bash
docker stats ollama --no-stream
```

### Проверка производительности
```bash
# Тест одного запроса
time curl -X POST http://localhost:11434/api/generate \
  -d '{"model": "qwen2.5:1.5b", "prompt": "test", "stream": false}'

# Тест параллельных запросов (3 одновременно)
for i in {1..3}; do
  curl -X POST http://localhost:11434/api/generate \
    -d '{"model": "qwen2.5:1.5b", "prompt": "test", "stream": false}' &
done
wait
```

### Проверка логов на ошибки
```bash
docker logs ollama --tail 50 | grep -i error
```

## Оптимизация для разных сценариев

### Низкая нагрузка (< 5 одновременных студентов)
```yaml
environment:
  - OLLAMA_NUM_PARALLEL=2
  - OLLAMA_MAX_QUEUE=10
```

### Средняя нагрузка (5-15 одновременных студентов)
```yaml
environment:
  - OLLAMA_NUM_PARALLEL=3
  - OLLAMA_MAX_QUEUE=15
```

### Высокая нагрузка (15+ одновременных студентов)
```yaml
environment:
  - OLLAMA_NUM_PARALLEL=4
  - OLLAMA_MAX_QUEUE=20
```
⚠️ **Внимание**: При высокой нагрузке убедитесь, что сервер имеет достаточно ресурсов (4+ CPU, 8+ GB RAM)

## Предупреждения

1. **Не превышайте OLLAMA_NUM_PARALLEL=4** для 2 CPU ядер
2. **Мониторьте использование памяти** - модель занимает ~1GB
3. **Проверяйте логи** на ошибки таймаутов
4. **Тестируйте изменения** перед применением в продакшене

## Интеграция с Flask

Flask приложение автоматически использует параллельную обработку через `ThreadPoolExecutor` с максимум 3 потоками, что соответствует `OLLAMA_NUM_PARALLEL=3`.

Это обеспечивает оптимальную производительность без перегрузки сервера.


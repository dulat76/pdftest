// AI Settings Web Interface

// Промпты пресеты
const promptPresets = {
    default: `Ты - профессиональный проверяющий учебных заданий. 
Твоя задача - определить, является ли ответ ученика правильным, учитывая эталонные ответы.

ПРАВИЛА ПРОВЕРКИ:
1. Учитывай возможные опечатки и грамматические ошибки
2. Синонимы и перефразирования правильных ответов засчитывай как верные
3. Игнорируй регистр букв и лишние пробелы
4. Для числовых ответов учитывай математическую эквивалентность
5. Для сокращений проверяй их соответствие полным формам
6. Будь строгим к фактическим ошибкам

ФОРМАТ ОТВЕТА:
Отвечай ТОЛЬКО одним словом:
- "ВЕРНО" - если ответ правильный
- "НЕВЕРНО" - если ответ неправильный`,

    strict: `Ты - строгий экзаменатор. Проверяй ответы максимально точно.

ПРАВИЛА:
1. НЕ принимай опечатки и грамматические ошибки
2. Принимай только точные формулировки
3. Синонимы НЕ засчитывай
4. Числа должны совпадать точно
5. Будь максимально строгим

ФОРМАТ ОТВЕТА:
- "ВЕРНО" - только если ответ абсолютно точен
- "НЕВЕРНО" - в остальных случаях`,

    lenient: `Ты - добрый и понимающий проверяющий. Оценивай понимание сути, а не форму.

ПРАВИЛА:
1. Принимай опечатки, если понятен смысл
2. Засчитывай синонимы и перефразирования
3. Принимай неполные, но правильные ответы
4. Игнорируй незначительные ошибки
5. Оценивай понимание концепции

ФОРМАТ ОТВЕТА:
- "ВЕРНО" - если ученик понял суть
- "НЕВЕРНО" - только при полном непонимании`
};

// Загрузка настроек при старте
document.addEventListener('DOMContentLoaded', function() {
    loadSettings();
    loadStatistics();
    checkAIStatus();
});

// Обновление значения порога схожести
function updateThresholdValue(value) {
    document.getElementById('thresholdValue').textContent = value + '%';
}

// Обновление значения температуры
function updateTempValue(value) {
    const temp = (value / 100).toFixed(2);
    document.getElementById('tempValue').textContent = temp;
}

// Обновление статуса AI
function updateAIStatus() {
    const enabled = document.getElementById('aiEnabled').checked;
    const badge = document.getElementById('aiStatusBadge');
    
    if (enabled) {
        badge.textContent = 'Активна';
        badge.className = 'status-badge active';
    } else {
        badge.textContent = 'Выключена';
        badge.className = 'status-badge inactive';
    }
}

// Применение пресета настроек
function applyPreset(preset) {
    const presets = {
        strict: {
            threshold: 95,
            temperature: 5,
            description: 'Строгие настройки для точных наук'
        },
        balanced: {
            threshold: 80,
            temperature: 10,
            description: 'Сбалансированные настройки'
        },
        flexible: {
            threshold: 60,
            temperature: 20,
            description: 'Гибкие настройки для гуманитарных наук'
        }
    };

    const config = presets[preset];
    if (config) {
        document.getElementById('similarityThreshold').value = config.threshold;
        updateThresholdValue(config.threshold);
        
        document.getElementById('temperature').value = config.temperature;
        updateTempValue(config.temperature);
        
        showAlert('info', `Применен пресет: ${config.description}`);
    }
}

// Загрузка пресета промпта
function loadPromptPreset(preset) {
    const promptText = promptPresets[preset] || promptPresets.default;
    document.getElementById('systemPrompt').value = promptText;
    showAlert('success', 'Промпт загружен');
}

// Сохранение настроек
async function saveSettings() {
    const settings = {
        ai_enabled: document.getElementById('aiEnabled').checked,
        similarity_threshold: parseInt(document.getElementById('similarityThreshold').value) / 100,
        api_key: document.getElementById('apiKey').value,
        ai_model: document.getElementById('aiModel').value,
        temperature: parseInt(document.getElementById('temperature').value) / 100,
        max_tokens: parseInt(document.getElementById('maxTokens').value),
        top_p: parseFloat(document.getElementById('topP').value),
        system_prompt: document.getElementById('systemPrompt').value,
        cache_enabled: document.getElementById('cacheEnabled').checked,
        cache_duration: parseInt(document.getElementById('cacheDuration').value),
        logging_enabled: document.getElementById('loggingEnabled').checked,
        log_file: document.getElementById('logFile').value
    };

    try {
        const response = await fetch('/api/ai/settings', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(settings)
        });

        const result = await response.json();
        
        if (result.success) {
            showAlert('success', '✅ Настройки успешно сохранены!');
        } else {
            showAlert('error', '❌ Ошибка сохранения: ' + result.error);
        }
    } catch (error) {
        showAlert('error', '❌ Ошибка: ' + error.message);
    }
}

// Загрузка настроек
async function loadSettings() {
    try {
        const response = await fetch('/api/ai/settings');
        const settings = await response.json();

        if (settings.success) {
            const config = settings.config;
            
            document.getElementById('aiEnabled').checked = config.ai_enabled;
            updateAIStatus();
            
            document.getElementById('similarityThreshold').value = Math.round(config.similarity_threshold * 100);
            updateThresholdValue(Math.round(config.similarity_threshold * 100));
            
            if (config.api_key && config.api_key !== 'YOUR_API_KEY_HERE') {
                document.getElementById('apiKey').value = '***' + config.api_key.slice(-8);
            }
            
            document.getElementById('aiModel').value = config.ai_model;
            
            document.getElementById('temperature').value = Math.round(config.temperature * 100);
            updateTempValue(Math.round(config.temperature * 100));
            
            document.getElementById('maxTokens').value = config.max_tokens;
            document.getElementById('topP').value = config.top_p;
            document.getElementById('systemPrompt').value = config.system_prompt;
            document.getElementById('cacheEnabled').checked = config.cache_enabled;
            document.getElementById('cacheDuration').value = config.cache_duration;
            document.getElementById('loggingEnabled').checked = config.logging_enabled;
            document.getElementById('logFile').value = config.log_file;

            showAlert('success', 'Настройки загружены');
        }
    } catch (error) {
        console.error('Ошибка загрузки настроек:', error);
        // Загружаем значения по умолчанию
        loadPromptPreset('default');
    }
}

// Тест AI
async function testAI() {
    showModal('Тест AI', '<p>Выполняется тест AI проверки...</p>');

    try {
        const response = await fetch('/api/ai/test', {
            method: 'POST'
        });

        const result = await response.json();
        
        if (result.success) {
            let html = '<div style="font-family: monospace; font-size: 13px;">';
            
            result.tests.forEach((test, index) => {
                const icon = test.passed ? '✅' : '❌';
                const color = test.passed ? '#27ae60' : '#e74c3c';
                
                html += `
                    <div style="padding: 10px; margin: 5px 0; background: #f8f9fa; border-left: 4px solid ${color}; border-radius: 4px;">
                        <strong>${icon} Тест ${index + 1}: ${test.name}</strong><br>
                        Ответ студента: "${test.student_answer}"<br>
                        Правильный ответ: "${test.correct_answer}"<br>
                        Результат: ${test.result ? 'Верно' : 'Неверно'}
                        ${test.checked_by_ai ? ' (AI)' : ' (Обычная проверка)'}
                        ${test.ai_confidence ? `<br>Уверенность: ${Math.round(test.ai_confidence * 100)}%` : ''}
                    </div>
                `;
            });
            
            const passed = result.tests.filter(t => t.passed).length;
            const total = result.tests.length;
            const percentage = Math.round((passed / total) * 100);
            
            html += `
                <div style="margin-top: 20px; padding: 15px; background: ${percentage >= 80 ? '#d4edda' : '#f8d7da'}; border-radius: 6px; text-align: center;">
                    <strong>Результат: ${passed}/${total} тестов пройдено (${percentage}%)</strong>
                </div>
            `;
            
            html += '</div>';
            
            showModal('Результаты теста AI', html);
        } else {
            showModal('Ошибка', `<p>Ошибка теста: ${result.error}</p>`);
        }
    } catch (error) {
        showModal('Ошибка', `<p>Ошибка: ${error.message}</p>`);
    }
}

// Сброс настроек
function resetSettings() {
    if (confirm('Вы уверены, что хотите сбросить все настройки к значениям по умолчанию?')) {
        document.getElementById('aiEnabled').checked = true;
        updateAIStatus();
        
        document.getElementById('similarityThreshold').value = 80;
        updateThresholdValue(80);
        
        document.getElementById('apiKey').value = '';
        document.getElementById('aiModel').value = 'gemini-pro';
        
        document.getElementById('temperature').value = 10;
        updateTempValue(10);
        
        document.getElementById('maxTokens').value = 200;
        document.getElementById('topP').value = 0.95;
        loadPromptPreset('default');
        
        document.getElementById('cacheEnabled').checked = true;
        document.getElementById('cacheDuration').value = 3600;
        document.getElementById('loggingEnabled').checked = true;
        document.getElementById('logFile').value = 'logs/ai_checks.log';
        
        showAlert('success', 'Настройки сброшены к значениям по умолчанию');
    }
}

// Очистка кэша
async function clearCache() {
    if (confirm('Очистить весь кэш AI проверок?')) {
        try {
            const response = await fetch('/api/ai/cache/clear', {
                method: 'POST'
            });
            
            const result = await response.json();
            
            if (result.success) {
                showAlert('success', `Кэш очищен (${result.cleared_items} записей)`);
                loadStatistics();
            } else {
                showAlert('error', 'Ошибка очистки кэша: ' + result.error);
            }
        } catch (error) {
            showAlert('error', 'Ошибка: ' + error.message);
        }
    }
}

// Просмотр логов
async function viewLogs() {
    try {
        const response = await fetch('/api/ai/logs');
        const result = await response.json();
        
        if (result.success) {
            let html = '<div style="max-height: 400px; overflow-y: auto; font-family: monospace; font-size: 12px;">';
            
            result.logs.slice(-50).reverse().forEach(log => {
                const time = new Date(log.timestamp).toLocaleString('ru-RU');
                const statusIcon = log.success ? '✅' : '❌';
                
                html += `
                    <div style="padding: 10px; margin: 5px 0; background: #f8f9fa; border-radius: 4px; border-left: 3px solid ${log.success ? '#27ae60' : '#e74c3c'}">
                        <div style="color: #666; font-size: 10px;">${statusIcon} ${time}</div>
                        <div><strong>Ответ:</strong> "${log.student_answer}"</div>
                        <div><strong>Правильно:</strong> ${log.correct_variants.join(', ')}</div>
                        <div><strong>AI:</strong> ${log.ai_result || 'N/A'}</div>
                    </div>
                `;
            });
            
            html += '</div>';
            showModal('Логи AI проверок (последние 50)', html);
        } else {
            showModal('Ошибка', `<p>Не удалось загрузить логи: ${result.error}</p>`);
        }
    } catch (error) {
        showModal('Ошибка', `<p>Ошибка: ${error.message}</p>`);
    }
}

// Очистка логов
async function clearLogs() {
    if (confirm('Очистить все логи AI проверок?')) {
        try {
            const response = await fetch('/api/ai/logs/clear', {
                method: 'POST'
            });
            
            const result = await response.json();
            
            if (result.success) {
                showAlert('success', 'Логи очищены');
                loadStatistics();
            } else {
                showAlert('error', 'Ошибка очистки логов: ' + result.error);
            }
        } catch (error) {
            showAlert('error', 'Ошибка: ' + error.message);
        }
    }
}

// Загрузка статистики
async function loadStatistics() {
    try {
        const response = await fetch('/api/ai/stats');
        const stats = await response.json();
        
        if (stats.success) {
            document.getElementById('totalChecks').textContent = stats.total_checks || 0;
            document.getElementById('aiChecks').textContent = stats.ai_checks || 0;
            document.getElementById('cacheSize').textContent = stats.cache_size || 0;
            document.getElementById('successRate').textContent = (stats.success_rate || 0) + '%';
        }
    } catch (error) {
        console.error('Ошибка загрузки статистики:', error);
    }
}

// Проверка статуса AI
async function checkAIStatus() {
    try {
        const response = await fetch('/api/ai/status');
        const status = await response.json();
        
        if (!status.available) {
            showAlert('warning', '⚠️ AI проверка недоступна: ' + (status.error || 'Неизвестная ошибка'));
        } else if (!status.api_key_configured) {
            showAlert('warning', '⚠️ API ключ не настроен. Введите ключ для активации AI проверки.');
        }
    } catch (error) {
        console.error('Ошибка проверки статуса:', error);
    }
}

// Показ уведомления
function showAlert(type, message) {
    const container = document.getElementById('alertContainer');
    const icons = {
        success: '✅',
        error: '❌',
        warning: '⚠️',
        info: 'ℹ️'
    };
    
    const alert = document.createElement('div');
    alert.className = `alert ${type}`;
    alert.innerHTML = `<span>${icons[type]}</span><span>${message}</span>`;
    
    container.innerHTML = '';
    container.appendChild(alert);
    
    setTimeout(() => {
        alert.style.opacity = '0';
        alert.style.transition = 'opacity 0.5s';
        setTimeout(() => alert.remove(), 500);
    }, 5000);
}

// Модальное окно
function showModal(title, content) {
    document.getElementById('modalTitle').textContent = title;
    document.getElementById('modalBody').innerHTML = content;
    document.getElementById('modal').style.display = 'block';
}

function closeModal() {
    document.getElementById('modal').style.display = 'none';
}

// Закрытие модального окна по клику вне его
window.onclick = function(event) {
    const modal = document.getElementById('modal');
    if (event.target === modal) {
        closeModal();
    }
}

// Загрузка имени пользователя
async function loadUserInfo() {
    try {
        const response = await fetch('/api/user/info');
        const data = await response.json();
        if (data.username) {
            document.getElementById('username').textContent = data.username;
        }
    } catch (error) {
        console.error('Ошибка загрузки информации о пользователе:', error);
    }
}

loadUserInfo();
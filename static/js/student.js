// student.js - Полная версия с правильным позиционированием и AI

let currentTemplate = null;
let currentPage = 0;
let studentAnswers = {};
let studentInfo = {};

// ====================================================================
//                             ИНИЦИАЛИЗАЦИЯ
// ====================================================================

document.addEventListener('DOMContentLoaded', function() {
    loadClasses();
    loadTemplateList();
    setupModal();

    const templateSelect = document.getElementById('templateSelect');
    if (templateSelect) {
        templateSelect.addEventListener('change', loadClasses);
    }
});

function setupModal() {
    const modal = document.getElementById('modal');
    const closeBtn = document.querySelector('.close');

    if (!modal || !closeBtn) return;

    closeBtn.onclick = function() {
        modal.style.display = 'none';
    };

    window.onclick = function(event) {
        if (event.target === modal) {
            modal.style.display = 'none';
        }
    };
}

function showModal(message) {
    const modalText = document.getElementById('modalText');
    const modal = document.getElementById('modal');
    if (modalText && modal) {
        modalText.textContent = message;
        modal.style.display = 'block';
    } else {
        alert(message);
    }
}

// ====================================================================
//                             ЗАГРУЗКА КЛАССОВ
// ====================================================================

async function loadClasses() {
    try {
        const templateSelect = document.getElementById('templateSelect');
        const selectedTemplateId = templateSelect ? templateSelect.value : null;

        if (selectedTemplateId) {
            const response = await fetch(`/load_template/${selectedTemplateId}`);
            const template = await response.json();

            if (response.ok && template.classes && template.classes.length > 0) {
                populateClassSelect(template.classes);
                return;
            }
        }

        const response = await fetch('/static/classes.json');
        const classes = await response.json();
        populateClassSelect(classes);

    } catch (error) {
        console.error('Ошибка загрузки классов:', error);
        const defaultClasses = ["5А", "5Б", "6А", "6Б", "7А", "7Б", "8А", "8Б", "9А", "9Б", "10А", "10Б", "11А", "11Б"];
        populateClassSelect(defaultClasses);
    }
}

function populateClassSelect(classes) {
    const select = document.getElementById('studentClass');
    if (!select) return;

    select.innerHTML = '<option value="">Выберите класс...</option>';

    classes.forEach(className => {
        const option = document.createElement('option');
        option.value = className;
        option.textContent = className;
        select.appendChild(option);
    });
}

// ====================================================================
//                             ЗАГРУЗКА ШАБЛОНОВ
// ====================================================================

async function loadTemplateList() {
    try {
        const response = await fetch('/list_templates');
        if (!response.ok) {
            throw new Error('Не удалось загрузить шаблоны');
        }

        const templates = await response.json();
        const select = document.getElementById('templateSelect');

        if (!select) return;

        select.innerHTML = '<option value="">Выберите задание...</option>';
        templates.forEach(t => {
            const opt = document.createElement('option');
            opt.value = t.id;
            opt.textContent = t.name || t.id;
            select.appendChild(opt);
        });

    } catch (error) {
        console.error('Ошибка загрузки шаблонов:', error);
        showModal('Ошибка при загрузке списка заданий');
    }
}

// ====================================================================
//                             НАЧАЛО ТЕСТА
// ====================================================================

async function startTest() {
    const name = document.getElementById('studentName').value.trim();
    const studentClass = document.getElementById('studentClass').value;
    const templateId = document.getElementById('templateSelect').value;

    if (!name) {
        showModal('Введите ФИО');
        return;
    }

    if (!studentClass) {
        showModal('Выберите класс');
        return;
    }

    if (!templateId) {
        showModal('Выберите задание');
        return;
    }

    try {
        const response = await fetch(`/load_template/${templateId}`);
        const template = await response.json();

        if (response.ok) {
            currentTemplate = template;
            currentPage = 0;
            studentAnswers = {};
            studentInfo = {
                name: name,
                class: studentClass,
                templateId: templateId,
                sheetUrl: template.sheet_url
            };

            document.getElementById('studentForm').style.display = 'none';
            document.getElementById('testArea').style.display = 'block';
            
            // Показываем имя и класс если есть элементы
            const displayName = document.getElementById('displayName');
            const displayClass = document.getElementById('displayClass');
            if (displayName) displayName.textContent = name;
            if (displayClass) displayClass.textContent = studentClass;

            loadTestDocument();
            updateProgress();

        } else {
            showModal('Ошибка загрузки задания: ' + template.error);
        }
    } catch (error) {
        showModal('Ошибка: ' + error.message);
    }
}

// ====================================================================
//                             ОТРИСОВКА ДОКУМЕНТА
// ====================================================================

function loadTestDocument() {
    const viewer = document.getElementById('documentViewer');
    if (!viewer) return;

    viewer.innerHTML = '';

    if (!currentTemplate?.files?.length) {
        viewer.innerHTML = '<div class="placeholder">Файлы документа не найдены</div>';
        return;
    }

    const pageDiv = document.createElement('div');
    pageDiv.className = 'document-page';
    pageDiv.id = `test-page-${currentPage}`;
    pageDiv.style.position = 'relative';
    pageDiv.style.display = 'inline-block';

    const img = document.createElement('img');
    img.src = `/uploads/${currentTemplate.files[currentPage]}`;
    img.style.maxWidth = '100%';
    img.style.height = 'auto';
    img.style.display = 'block';

    img.onload = function() {
        if (!currentTemplate.width) {
            currentTemplate.width = img.naturalWidth;
            currentTemplate.height = img.naturalHeight;
        }
        renderFieldsForPage(currentPage);
        updatePageNavigation();
    };

    img.onerror = function() {
        pageDiv.innerHTML = '<div class="placeholder">Ошибка загрузки изображения</div>';
    };

    pageDiv.appendChild(img);
    viewer.appendChild(pageDiv);
}

function renderFieldsForPage(pageIndex) {
    const viewer = document.getElementById('documentViewer');
    viewer.innerHTML = '';

    const page = document.createElement('div');
    page.className = 'document-page';
    page.style.position = 'relative';

    const img = document.createElement('img');
    img.src = `/uploads/${currentTemplate.files[pageIndex]}`;
    img.style.width = '100%';
    img.style.display = 'block';

    img.onload = function() {
        drawFields(page, img, pageIndex);
    };

    page.appendChild(img);
    viewer.appendChild(page);
}

function drawFields(page, img, pageIndex) {
    // Убираем старые поля
    page.querySelectorAll('.student-field-wrapper').forEach(el => el.remove());

    // Берем размеры из PDF (в points) и зум
    const pageData = currentTemplate.images_data?.[pageIndex];
    const pdfW = pageData?.page_width || currentTemplate.width;
    const pdfH = pageData?.page_height || currentTemplate.height;
    const zoom = pageData?.zoom || 1;

    // Вычисляем коэффициент масштабирования: пиксели экрана / PDF points
    const scaleX = img.clientWidth / pdfW;
    const scaleY = img.clientHeight / pdfH;

    currentTemplate.fields
        .filter(f => f.page === pageIndex)
        .forEach(f => {
            // 1. Инвертируем Y: из PDF-координат (Y_bottom) в веб-координаты (Y_top)
            const webPointsY = pdfH - f.y - f.h;

            // 2. Преобразуем PDF points в экранные пиксели
            const screenX = f.x * scaleX;
            const screenY = webPointsY * scaleY;
            const screenW = f.w * scaleX;
            const screenH = f.h * scaleY;

            const wrapper = document.createElement('div');
            wrapper.className = 'student-field-wrapper';
            wrapper.style.position = 'absolute';
            wrapper.style.left = screenX + 'px';
            wrapper.style.top = screenY + 'px';
            wrapper.style.width = screenW + 'px';
            wrapper.style.height = screenH + 'px';

            const input = document.createElement('input');
            input.type = 'text';
            input.className = 'student-field';
            input.dataset.fieldId = f.id;
            if (studentAnswers[f.id] !== undefined) input.value = studentAnswers[f.id];

            input.addEventListener('input', e => {
                studentAnswers[f.id] = e.target.value;
                updateProgress();
            });

            input.addEventListener('blur', e => {
                studentAnswers[f.id] = e.target.value.trim();
            }, { passive: true });

            wrapper.appendChild(input);
            page.appendChild(wrapper);

            // Фокус только если поле уже было заполнено
            if (studentAnswers[f.id]) {
                requestAnimationFrame(() => input.focus());
            }
        });
}

// ====================================================================
//                             НАВИГАЦИЯ ПО СТРАНИЦАМ
// ====================================================================

function updatePageNavigation() {
    const nav = document.getElementById('pageNavigation');
    const pageInfo = document.getElementById('pageInfo');
    const prevBtn = document.getElementById('prevBtn');
    const nextBtn = document.getElementById('nextBtn');

    if (!nav || !pageInfo) return;

    if (currentTemplate.files && currentTemplate.files.length > 1) {
        nav.style.display = 'flex';
        pageInfo.textContent = `${currentPage + 1} / ${currentTemplate.files.length}`;
        if (prevBtn) prevBtn.disabled = currentPage === 0;
        if (nextBtn) nextBtn.disabled = currentPage === currentTemplate.files.length - 1;
    } else {
        nav.style.display = 'none';
    }
}

function prevPage() {
    if (currentPage > 0) {
        saveCurrentPageAnswers();
        currentPage--;
        loadTestDocument();
    }
}

function nextPage() {
    if (currentPage < currentTemplate.files.length - 1) {
        saveCurrentPageAnswers();
        currentPage++;
        loadTestDocument();
    }
}

function saveCurrentPageAnswers() {
    document.querySelectorAll('.student-field').forEach(input => {
        const fieldId = input.dataset.fieldId;
        if (fieldId) {
            studentAnswers[fieldId] = input.value.trim();
        }
    });
}

function updateProgress() {
    const totalFields = currentTemplate?.fields?.length || 0;
    const filledFields = Object.values(studentAnswers).filter(v => v.trim() !== '').length;

    const progressElement = document.getElementById('progress');
    const totalFieldsElement = document.getElementById('totalFields');

    if (progressElement) progressElement.textContent = filledFields;
    if (totalFieldsElement) totalFieldsElement.textContent = totalFields;
}

// ====================================================================
//                             ПРОВЕРКА ОТВЕТОВ
// ====================================================================

async function checkAnswers() {
    saveCurrentPageAnswers();

    const totalFields = currentTemplate.fields.length;
    const filledFields = Object.values(studentAnswers).filter(v => v.trim() !== '').length;

    if (filledFields < totalFields) {
        if (!confirm(`Заполнено ${filledFields} из ${totalFields} вопросов. Продолжить проверку?`)) {
            return;
        }
    }

    const submitBtn = document.getElementById('submitBtn');
    if (submitBtn) {
        submitBtn.innerHTML = `
            <span style="display: flex; align-items: center; justify-content: center;">
                <span style="
                    border: 2px solid rgba(255, 255, 255, 0.3);
                    border-top: 2px solid #fff;
                    border-radius: 50%;
                    width: 16px;
                    height: 16px;
                    margin-right: 8px;
                    animation: spin 1s linear infinite;
                "></span>
                Проверка с помощью ИИ...
            </span>
        `;
        submitBtn.disabled = true;

        if (!document.getElementById('spin-animation')) {
            const style = document.createElement('style');
            style.id = 'spin-animation';
            style.textContent = `@keyframes spin { to { transform: rotate(360deg); } }`;
            document.head.appendChild(style);
        }
    }

    try {
        const response = await fetch('/check_answers', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                template_id: studentInfo.templateId,
                answers: studentAnswers,
                student_info: {
                    studentName: studentInfo.name,
                    studentClass: studentInfo.class
                },
                sheet_url: studentInfo.sheetUrl
            })
        });

        const result = await response.json();
        if (result.success) {
            showResults(result);
        } else {
            showModal('Ошибка проверки: ' + result.error);
        }
    } catch (error) {
        showModal('Ошибка: ' + error.message);
    } finally {
        if (submitBtn) {
            submitBtn.textContent = 'Завершить и проверить';
            submitBtn.disabled = false;
        }
    }
}

// ====================================================================
//                             РЕЗУЛЬТАТЫ
// ====================================================================

function showResults(result) {
    document.getElementById('testArea').style.display = 'none';
    document.getElementById('results').style.display = 'block';

    const percentage = Math.round((result.correct_count / result.total_count) * 100);

    const scorePercent = document.getElementById('scorePercent');
    const correctCount = document.getElementById('correctCount');
    const totalCount = document.getElementById('totalCount');

    if (scorePercent) scorePercent.textContent = percentage + '%';
    if (correctCount) correctCount.textContent = result.correct_count;
    if (totalCount) totalCount.textContent = result.total_count;

    const scoreCircle = document.querySelector('.score-circle');
    if (scoreCircle) {
        scoreCircle.style.backgroundColor =
            percentage >= 80 ? '#27ae60' :
            percentage >= 60 ? '#f39c12' : '#e74c3c';
    }

    // Статус Google Sheets
    const sheetsStatus = document.getElementById('sheetsStatus');
    if (sheetsStatus) {
        if (result.sheets_result?.success) {
            sheetsStatus.innerHTML = "💾 Результаты и ответы сохранены в Google Таблице";
            sheetsStatus.style.color = "#27ae60";

            if (result.sheets_result.message) {
                const detailSpan = document.createElement('div');
                detailSpan.style.fontSize = '12px';
                detailSpan.style.marginTop = '5px';
                detailSpan.textContent = result.sheets_result.message;
                sheetsStatus.appendChild(detailSpan);
            }
        } else {
            sheetsStatus.textContent = "❌ Не удалось сохранить в Google Таблицу: " + (result.sheets_result?.error || "");
            sheetsStatus.style.color = "#e74c3c";
        }
    }

    // Детальный обзор ответов
    const answerReview = document.getElementById('answerReview');
    if (answerReview && result.details) {
        answerReview.innerHTML = '<h3>Результаты по вопросам:</h3>';
        result.details.forEach((detail, index) => {
            const isCorrect = detail.is_correct;
            const icon = isCorrect ? '✅' : '❌';
            
            // Метод проверки для отладки
            let methodInfo = '';
            if (detail.check_method && detail.check_method !== 'exact' && detail.check_method !== 'none') {
                const methodNames = {
                    'boolean': '🔢 Логическое значение',
                    'numeric_sequence': '🔢 Числовая последовательность',
                    'keywords': '🔑 Ключевые слова',
                    'ai': '🤖 ИИ',
                    'ai_error': '⚠️ Ошибка ИИ'
                };
                
                let methodName = methodNames[detail.check_method] || detail.check_method;
                if (detail.check_method.startsWith('similarity_')) {
                    methodName = `📊 Схожесть ${detail.check_method.split('_')[1]}`;
                }
                
                methodInfo = `<small style="color: #666; display: block; margin-top: 4px;">Метод: ${methodName}</small>`;
            }
            
            let aiInfo = '';
            if (detail.checked_by_ai) {
                const aiIcon = isCorrect ? '🤖✅' : '🤖❌';
                const confidence = detail.ai_confidence ? `${(detail.ai_confidence * 100).toFixed(1)}%` : 'N/A';
                aiInfo = `
                    <div style="margin-top: 8px; padding: 8px; background: #f0f0f0; border-radius: 4px; font-size: 12px;">
                        <strong>${aiIcon} Проверено ИИ | Уверенность: ${confidence}</strong>
                        ${detail.ai_error ? `<p style="color: #e74c3c; margin: 4px 0 0 0;">⚠️ ${detail.ai_error}</p>` : ''}
                    </div>
                `;
            }
            
            const div = document.createElement('div');
            div.innerHTML = `
                <div style="margin: 10px 0; padding: 10px; border-radius: 5px;
                           background: ${isCorrect ? '#d4edda' : '#f8d7da'};
                           border: 1px solid ${isCorrect ? '#c3e6cb' : '#f5c6cb'};">
                    <strong>Вопрос ${index + 1}: ${icon}</strong><br>
                    Ваш ответ: "${detail.student_answer || '—'}"<br>
                    Правильно: ${detail.correct_variants.join(', ') || '—'}
                    ${methodInfo}
                    ${aiInfo}
                </div>
            `;
            answerReview.appendChild(div);
        });
    }

    // Информация об AI проверках
    if (result.ai_check_count > 0) {
        const aiInfo = document.createElement('div');
        aiInfo.style.marginTop = '15px';
        aiInfo.style.padding = '12px';
        aiInfo.style.background = '#e3f2fd';
        aiInfo.style.borderRadius = '6px';
        aiInfo.style.textAlign = 'center';
        aiInfo.innerHTML = `<strong>🤖 ИИ проверил ${result.ai_check_count} из ${result.total_count} ответов</strong>`;
        
        if (answerReview) {
            answerReview.appendChild(aiInfo);
        }
    }
}

function resetTest() {
    currentTemplate = null;
    currentPage = 0;
    studentAnswers = {};
    studentInfo = {};

    document.getElementById('results').style.display = 'none';
    document.getElementById('testArea').style.display = 'none';
    document.getElementById('studentForm').style.display = 'block';

    document.getElementById('studentName').value = '';
    document.getElementById('studentClass').value = '';
    document.getElementById('templateSelect').value = '';
}

// ====================================================================
//                             АДАПТИВНОСТЬ
// ====================================================================

// Обработчик ориентации для мобильных
window.addEventListener('orientationchange', function() {
    if (currentTemplate) {
        saveCurrentPageAnswers();
        setTimeout(() => {
            renderFieldsForPage(currentPage);
        }, 800);
    }
});

console.log('Student.js загружен полностью');
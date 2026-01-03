// student.js - Полная версия с правильным позиционированием и AI

let currentTemplate = null;
let currentPage = 0;
let studentAnswers = {};
let studentInfo = {};

// Переменные для фильтрации
let filterState = {
    cityCode: null,
    schoolCode: null,
    selectedClass: null,
    selectedSubjectId: null,
    selectedTopic: null,
    currentStep: 1  // 1=класс, 2=предмет, 3=тема, 4=тест
};

// ====================================================================
//                             ИНИЦИАЛИЗАЦИЯ
// ====================================================================

document.addEventListener('DOMContentLoaded', function() {
    setupModal();
    
    // Проверяем, есть ли city_code и school_code в URL
    const pathParts = window.location.pathname.split('/').filter(p => p);
    if (pathParts.length >= 3 && pathParts[0] === 'student' && pathParts[1] && pathParts[2]) {
        filterState.cityCode = pathParts[1];
        filterState.schoolCode = pathParts[2];
        initFilterFlow();
    } else {
        // Старый режим - показываем форму выбора теста (скрываем формы фильтрации)
        ['stepClassForm', 'stepSubjectForm', 'stepTopicForm', 'stepTestForm'].forEach(id => {
            const el = document.getElementById(id);
            if (el) el.style.display = 'none';
        });
        const progressDiv = document.getElementById('filterProgress');
        if (progressDiv) progressDiv.style.display = 'none';
        
        // Показываем старую форму (если она есть)
        const oldForm = document.getElementById('studentForm');
        if (oldForm) {
            oldForm.style.display = 'block';
            loadClasses();
            loadTemplateList();
        }
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
//                             ФИЛЬТРАЦИЯ ТЕСТОВ
// ====================================================================

async function initFilterFlow() {
    // Показываем индикатор прогресса
    const progressDiv = document.getElementById('filterProgress');
    if (progressDiv) {
        progressDiv.style.display = 'block';
        updateStepIndicator(1);
    }
    
    // Загружаем классы для школы
    await loadClassesForSchool();
}

async function loadClassesForSchool() {
    try {
        const response = await fetch(`/api/classes/by-school/${filterState.cityCode}/${filterState.schoolCode}`);
        const result = await response.json();
        
        if (result.success && result.classes.length > 0) {
            displayClasses(result.classes);
        } else {
            showModal('Для вашей школы пока нет доступных тестов');
        }
    } catch (error) {
        console.error('Ошибка загрузки классов:', error);
        showModal('Ошибка загрузки классов');
    }
}

function displayClasses(classes) {
    const select = document.getElementById('classSelect');
    if (!select) return;
    
    // Очищаем и заполняем select
    select.innerHTML = '<option value="">Выберите класс...</option>';
    
    // Сортируем классы по возрастанию
    const sortedClasses = [...classes].sort((a, b) => a - b);
    
    sortedClasses.forEach(classNum => {
        const option = document.createElement('option');
        option.value = classNum;
        option.textContent = `${classNum} класс`;
        select.appendChild(option);
    });
    
    // Обработчик изменения выбора
    select.onchange = function() {
        if (this.value) {
            selectClass(parseInt(this.value));
        }
    };
    
    // Показываем форму выбора класса
    document.getElementById('stepClassForm').style.display = 'block';
}

function selectClass(classNum) {
    filterState.selectedClass = classNum;
    filterState.currentStep = 2;
    
    // Скрываем форму класса, показываем форму предмета
    document.getElementById('stepClassForm').style.display = 'none';
    document.getElementById('stepSubjectForm').style.display = 'block';
    updateStepIndicator(2);
    
    // Загружаем предметы для выбранного класса
    loadSubjectsForClass(classNum);
}

async function loadSubjectsForClass(classNum) {
    try {
        const response = await fetch(`/api/subjects?class_level=${classNum}`);
        const result = await response.json();
        
        if (result.success && result.subjects.length > 0) {
            displaySubjects(result.subjects);
        } else {
            showModal('Для выбранного класса пока нет доступных предметов');
            goBack();
        }
    } catch (error) {
        console.error('Ошибка загрузки предметов:', error);
        showModal('Ошибка загрузки предметов');
    }
}

function displaySubjects(subjects) {
    const container = document.getElementById('subjectsContainer');
    if (!container) return;
    
    container.innerHTML = '';
    
    subjects.forEach(subject => {
        const btn = document.createElement('button');
        btn.className = 'btn';
        btn.style.cssText = 'padding: 15px; font-size: 1.1em; min-width: 120px;';
        btn.textContent = subject.name;
        btn.onclick = () => selectSubject(subject.id, subject.name);
        container.appendChild(btn);
    });
}

function selectSubject(subjectId, subjectName) {
    filterState.selectedSubjectId = subjectId;
    filterState.currentStep = 3;
    
    // Скрываем форму предмета, показываем форму темы
    document.getElementById('stepSubjectForm').style.display = 'none';
    document.getElementById('stepTopicForm').style.display = 'block';
    updateStepIndicator(3);
    
    // Загружаем темы для выбранного предмета и класса
    loadTopicsForSubject();
}

async function loadTopicsForSubject() {
    try {
        const params = new URLSearchParams({
            city_code: filterState.cityCode,
            school_code: filterState.schoolCode,
            class_level: filterState.selectedClass,
            subject_id: filterState.selectedSubjectId
        });
        
        const response = await fetch(`/api/topics/by-school?${params}`);
        const result = await response.json();
        
        if (result.success && result.topics.length > 0) {
            displayTopics(result.topics);
        } else {
            showModal('Для выбранного предмета пока нет доступных тем');
            goBack();
        }
    } catch (error) {
        console.error('Ошибка загрузки тем:', error);
        showModal('Ошибка загрузки тем');
    }
}

function displayTopics(topics) {
    const container = document.getElementById('topicsContainer');
    if (!container) return;
    
    container.innerHTML = '';
    
    topics.forEach(topic => {
        const btn = document.createElement('button');
        btn.className = 'btn';
        btn.style.cssText = 'padding: 15px; font-size: 1.1em; min-width: 150px;';
        btn.textContent = topic;
        btn.onclick = () => selectTopic(topic);
        container.appendChild(btn);
    });
}

function selectTopic(topic) {
    filterState.selectedTopic = topic;
    filterState.currentStep = 4;
    
    // Скрываем форму темы, показываем форму выбора теста
    document.getElementById('stepTopicForm').style.display = 'none';
    document.getElementById('stepTestForm').style.display = 'block';
    updateStepIndicator(4);
    
    // Очищаем поле класса - оно будет заполнено при выборе теста
    const classSelect = document.getElementById('studentClass');
    if (classSelect) {
        classSelect.innerHTML = '<option value="">Выберите тест, затем класс...</option>';
    }
    
    // Загружаем тесты для выбранных параметров
    loadTestsForSelection();
}

async function loadTestsForSelection() {
    try {
        const params = new URLSearchParams({
            city_code: filterState.cityCode,
            school_code: filterState.schoolCode,
            class_level: filterState.selectedClass,
            subject_id: filterState.selectedSubjectId,
            topic: filterState.selectedTopic
        });
        
        const response = await fetch(`/api/templates/filter?${params}`);
        const result = await response.json();
        
        if (result.success && result.templates.length > 0) {
            populateTestSelect(result.templates);
        } else {
            showModal('Для выбранных параметров пока нет доступных тестов');
            goBack();
        }
    } catch (error) {
        console.error('Ошибка загрузки тестов:', error);
        showModal('Ошибка загрузки тестов');
    }
}

function populateTestSelect(templates) {
    const select = document.getElementById('templateSelect');
    if (!select) return;
    
    select.innerHTML = '<option value="">Выберите тест...</option>';
    
    templates.forEach(template => {
        const option = document.createElement('option');
        option.value = template.id;
        option.textContent = template.name || template.id;
        option.dataset.templateId = template.id;
        select.appendChild(option);
    });
    
    // Добавляем обработчик изменения выбора теста
    select.onchange = function() {
        const selectedTemplateId = this.value;
        if (selectedTemplateId) {
            loadClassesForSelectedTemplate(selectedTemplateId);
        } else {
            // Очищаем список классов если тест не выбран
            const classSelect = document.getElementById('studentClass');
            if (classSelect) {
                classSelect.innerHTML = '<option value="">Выберите класс...</option>';
            }
        }
    };
}

async function loadClassesForSelectedTemplate(templateId) {
    try {
        const response = await fetch(`/load_template/${templateId}`);
        const template = await response.json();
        
        if (response.ok && template.classes && template.classes.length > 0) {
            populateClassSelect(template.classes);
        } else {
            // Если классов нет в шаблоне, используем выбранный класс из фильтрации
            const classSelect = document.getElementById('studentClass');
            if (classSelect) {
                classSelect.innerHTML = '<option value="">Выберите класс...</option>';
                const option = document.createElement('option');
                option.value = `${filterState.selectedClass} класс`;
                option.textContent = `${filterState.selectedClass} класс`;
                option.selected = true;
                classSelect.appendChild(option);
            }
        }
    } catch (error) {
        console.error('Ошибка загрузки классов из шаблона:', error);
        // Fallback: используем выбранный класс из фильтрации
        const classSelect = document.getElementById('studentClass');
        if (classSelect) {
            classSelect.innerHTML = '<option value="">Выберите класс...</option>';
            const option = document.createElement('option');
            option.value = `${filterState.selectedClass} класс`;
            option.textContent = `${filterState.selectedClass} класс`;
            option.selected = true;
            classSelect.appendChild(option);
        }
    }
}

function updateStepIndicator(step) {
    for (let i = 1; i <= 4; i++) {
        const stepEl = document.getElementById(`step${i}`);
        if (stepEl) {
            if (i <= step) {
                stepEl.classList.add('active');
                stepEl.style.color = '#27ae60';
                stepEl.style.fontWeight = 'bold';
            } else {
                stepEl.classList.remove('active');
                stepEl.style.color = '#999';
                stepEl.style.fontWeight = 'normal';
            }
        }
    }
}

function goBack() {
    if (filterState.currentStep > 1) {
        filterState.currentStep--;
        
        // Скрываем все формы
        ['stepClassForm', 'stepSubjectForm', 'stepTopicForm', 'stepTestForm'].forEach(id => {
            const el = document.getElementById(id);
            if (el) el.style.display = 'none';
        });
        
        // Показываем нужную форму
        if (filterState.currentStep === 1) {
            document.getElementById('stepClassForm').style.display = 'block';
            filterState.selectedClass = null;
            loadClassesForSchool();
        } else if (filterState.currentStep === 2) {
            document.getElementById('stepSubjectForm').style.display = 'block';
            filterState.selectedSubjectId = null;
            loadSubjectsForClass(filterState.selectedClass);
        } else if (filterState.currentStep === 3) {
            document.getElementById('stepTopicForm').style.display = 'block';
            filterState.selectedTopic = null;
            loadTopicsForSubject();
        }
        
        updateStepIndicator(filterState.currentStep);
    }
}

function goToTestSelection() {
    // Сбрасываем все и возвращаемся к началу фильтрации
    currentTemplate = null;
    currentPage = 0;
    studentAnswers = {};
    studentInfo = {};
    
    document.getElementById('results').style.display = 'none';
    document.getElementById('testArea').style.display = 'none';
    
    // Если есть фильтрация, возвращаемся к началу
    if (filterState.cityCode && filterState.schoolCode) {
        filterState.selectedClass = null;
        filterState.selectedSubjectId = null;
        filterState.selectedTopic = null;
        filterState.currentStep = 1;
        
        // Показываем форму выбора класса
        ['stepSubjectForm', 'stepTopicForm', 'stepTestForm'].forEach(id => {
            const el = document.getElementById(id);
            if (el) el.style.display = 'none';
        });
        document.getElementById('stepClassForm').style.display = 'block';
        
        // Показываем индикатор прогресса
        const progressDiv = document.getElementById('filterProgress');
        if (progressDiv) progressDiv.style.display = 'block';
        updateStepIndicator(1);
        
        // Перезагружаем классы
        loadClassesForSchool();
    } else {
        // Старый режим - перезагружаем страницу
        window.location.href = '/student';
    }
}

// ====================================================================
//                             ЗАГРУЗКА КЛАССОВ (старый режим)
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
//                             ЗАГРУЗКА ШАБЛОНОВ (старый режим)
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
    const studentClassInput = document.getElementById('studentClass');
    const studentClass = studentClassInput ? studentClassInput.value : filterState.selectedClass;
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

            // Скрываем все формы фильтрации
            ['stepClassForm', 'stepSubjectForm', 'stepTopicForm', 'stepTestForm'].forEach(id => {
                const el = document.getElementById(id);
                if (el) el.style.display = 'none';
            });
            
            // Скрываем индикатор прогресса
            const progressDiv = document.getElementById('filterProgress');
            if (progressDiv) progressDiv.style.display = 'none';
            
            document.getElementById('testArea').style.display = 'block';
            
            // Показываем имя и класс если есть элементы
            const submitBtn = document.getElementById('submitBtn');
            if (submitBtn) submitBtn.disabled = true;

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

    // Активируем кнопку, только если все поля заполнены
    const submitBtn = document.getElementById('submitBtn');
    if (submitBtn) {
        submitBtn.disabled = filledFields !== totalFields;
    }
}

// ====================================================================
//                             ПРОВЕРКА ОТВЕТОВ
// ====================================================================

async function checkAnswers() {
    const submitBtn = document.getElementById('submitBtn');
    saveCurrentPageAnswers();

    const totalFields = currentTemplate.fields.length;
    const filledFields = Object.values(studentAnswers).filter(v => v.trim() !== '').length;

    if (filledFields < totalFields) {
        if (!confirm(`Заполнено ${filledFields} из ${totalFields} вопросов. Продолжить проверку?`)) {
            return;
        }
    }

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
            submitBtn.innerHTML = '✅ Завершить и проверить';
            submitBtn.disabled = false;
        }
    }
}

// ====================================================================
//                             РЕЗУЛЬТАТЫ
// ====================================================================
// Замените функцию showResults в student.js на эту версию:

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
        } else if (result.sheets_result) {
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
            
            // Определяем метод проверки для отображения
            let methodBadge = '';
            if (detail.check_method) {
                const methodNames = {
                    'exact': '🎯 Точное совпадение',
                    'numeric_sequence': '🔢 Числовая последовательность',
                    'partial_match': '📝 Частичное совпадение',
                    'similarity_85': '📊 Схожесть 85%',
                    'ai': '🤖 Проверено AI',
                    'ai_error': '⚠️ Ошибка AI',
                    'none': '❓ Не проверено'
                };
                
                let methodName = methodNames[detail.check_method] || detail.check_method;
                
                const bgColor = detail.check_method === 'ai' ? '#e3f2fd' : 
                               detail.check_method === 'ai_error' ? '#ffebee' : 
                               detail.check_method === 'exact' ? '#e8f5e9' : '#f5f5f5';
                
                methodBadge = `
                    <div style="
                        display: inline-block;
                        margin-top: 6px;
                        padding: 4px 8px;
                        background: ${bgColor};
                        border-radius: 4px;
                        font-size: 11px;
                        font-weight: 500;
                    ">
                        ${methodName}
                    </div>
                `;
            }
            
            // AI информация
            let aiInfo = '';
            if (detail.checked_by_ai) {
                const aiIcon = detail.check_method === 'ai_error' ? '⚠️' : '🤖';
                const confidence = detail.ai_confidence ? `${(detail.ai_confidence * 100).toFixed(1)}%` : 'N/A';
                
                const bgColor = detail.check_method === 'ai_error' ? '#ffebee' : '#e3f2fd';
                const textColor = detail.check_method === 'ai_error' ? '#c62828' : '#1565c0';
                
                aiInfo = `
                    <div style="
                        margin-top: 10px;
                        padding: 10px;
                        background: ${bgColor};
                        border-left: 3px solid ${textColor};
                        border-radius: 4px;
                        font-size: 12px;
                    ">
                        <div style="font-weight: 600; color: ${textColor}; margin-bottom: 4px;">
                            ${aiIcon} AI Проверка | Уверенность: ${confidence}
                        </div>
                        ${detail.ai_explanation ? `
                            <div style="
                                color: #555;
                                line-height: 1.4;
                                font-size: 11px;
                                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                            ">
                                ${detail.ai_explanation}
                            </div>
                        ` : ''}
                    </div>
                `;
            }
            
            const div = document.createElement('div');
            div.style.margin = '15px 0';
            div.style.padding = '15px';
            div.style.borderRadius = '8px';
            div.style.background = isCorrect ? '#d4edda' : '#f8d7da';
            div.style.border = `2px solid ${isCorrect ? '#c3e6cb' : '#f5c6cb'}`;
            div.style.transition = 'all 0.3s ease';
            
            div.innerHTML = `
                <div style="font-weight: 600; font-size: 14px; margin-bottom: 8px;">
                    Вопрос ${index + 1}: ${icon}
                </div>
                <div style="margin: 6px 0;">
                    <strong>Ваш ответ:</strong> 
                    <span style="
                        background: white;
                        padding: 2px 6px;
                        border-radius: 3px;
                        font-family: monospace;
                    ">${detail.student_answer || '—'}</span>
                </div>
                <div style="margin: 6px 0;">
                    <strong>Правильно:</strong> 
                    ${detail.correct_variants.map(v => `
                        <span style="
                            background: white;
                            padding: 2px 6px;
                            border-radius: 3px;
                            font-family: monospace;
                            margin-right: 4px;
                        ">${v}</span>
                    `).join('') || '—'}
                </div>
                ${methodBadge}
                ${aiInfo}
            `;
            
            answerReview.appendChild(div);
        });
    }

    // Информация об AI проверках
    if (result.ai_check_count > 0 || result.ai_available) {
        const aiSummary = document.createElement('div');
        aiSummary.style.marginTop = '20px';
        aiSummary.style.padding = '15px';
        aiSummary.style.background = 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)';
        aiSummary.style.borderRadius = '8px';
        aiSummary.style.color = 'white';
        aiSummary.style.textAlign = 'center';
        aiSummary.style.boxShadow = '0 4px 6px rgba(0,0,0,0.1)';
        
        if (result.ai_check_count > 0) {
            aiSummary.innerHTML = `
                <div style="font-size: 16px; font-weight: 600; margin-bottom: 5px;">
                    🤖 Искусственный интеллект проверил
                </div>
                <div style="font-size: 24px; font-weight: 700;">
                    ${result.ai_check_count} из ${result.total_count} ответов
                </div>
                <div style="font-size: 12px; opacity: 0.9; margin-top: 5px;">
                    Остальные проверены автоматически по точному совпадению
                </div>
            `;
        } else {
            aiSummary.innerHTML = `
                <div style="font-size: 14px;">
                    ✅ Все ответы проверены автоматически по точному совпадению
                </div>
            `;
        }
        
        if (answerReview) {
            answerReview.appendChild(aiSummary);
        }
    }
    
    // Добавляем кнопку "Показать логи" для отладки (опционально)
    if (console && result.details) {
        console.log('Детальные результаты проверки:', result);
    }
}

function resetTest() {
    currentTemplate = null;
    currentPage = 0;
    studentAnswers = {};
    studentInfo = {};

    document.getElementById('results').style.display = 'none';
    document.getElementById('testArea').style.display = 'none';
    
    // Если есть фильтрация, возвращаемся к началу
    if (filterState.cityCode && filterState.schoolCode) {
        // Сбрасываем состояние фильтрации
        filterState.selectedClass = null;
        filterState.selectedSubjectId = null;
        filterState.selectedTopic = null;
        filterState.currentStep = 1;
        
        // Показываем форму выбора класса
        ['stepSubjectForm', 'stepTopicForm', 'stepTestForm'].forEach(id => {
            const el = document.getElementById(id);
            if (el) el.style.display = 'none';
        });
        document.getElementById('stepClassForm').style.display = 'block';
        
        // Показываем индикатор прогресса
        const progressDiv = document.getElementById('filterProgress');
        if (progressDiv) progressDiv.style.display = 'block';
        updateStepIndicator(1);
        
        // Перезагружаем классы
        loadClassesForSchool();
    } else {
        // Старый режим
        const studentForm = document.getElementById('studentForm');
        if (studentForm) studentForm.style.display = 'block';
    }

    const nameInput = document.getElementById('studentName');
    const classInput = document.getElementById('studentClass');
    const templateSelect = document.getElementById('templateSelect');
    
    if (nameInput) nameInput.value = '';
    if (classInput && !classInput.readOnly) classInput.value = '';
    if (templateSelect) templateSelect.value = '';
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
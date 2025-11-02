// mobile.js - минимальная версия без вмешательства в клавиатуру
class MobileUX {
    constructor() {
        this.init();
    }

    init() {
        this.setupViewport();
        this.preventDoubleTabZoom();
    }

    setupViewport() {
        const viewport = document.querySelector('meta[name="viewport"]');
        if (viewport) {
            viewport.setAttribute('content',
                'width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no');
        }
    }

    preventDoubleTabZoom() {
        // Только предотвращаем двойной тап для зума
        // НЕ блокируем события на input полях!
        let lastTouchEnd = 0;

        document.addEventListener('touchend', (event) => {
            // Пропускаем все input элементы
            if (event.target.tagName === 'INPUT' ||
                event.target.tagName === 'TEXTAREA' ||
                event.target.closest('.student-field-wrapper')) {
                return;
            }

            const now = Date.now();
            if (now - lastTouchEnd <= 300) {
                event.preventDefault();
            }
            lastTouchEnd = now;
        }, { passive: false });
    }

}



// Инициализация только на мобильных устройствах
if (window.innerWidth <= 768 ||
    /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent)) {
    document.addEventListener('DOMContentLoaded', () => {
        window.mobileUX = new MobileUX();
        console.log('Mobile UX initialized (minimal version)');
    });
}
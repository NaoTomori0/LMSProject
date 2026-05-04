document.addEventListener('DOMContentLoaded', () => {
    const signInForm = document.querySelector('form');
    const passwordInput = document.getElementById('password-field');
    const usernameInput = document.getElementById('username');
    const emailInput = document.getElementById('email');

    if (!signInForm || !passwordInput) return;

    signInForm.addEventListener('submit', (event) => {
        let isValid = true;

        // Если поле уже подсвечено серверной ошибкой, не трогаем его
        if (usernameInput && !usernameInput.classList.contains('is-invalid')) {
            const val = usernameInput.value.trim();
            if (val.length < 3 || val.length > 30) {
                usernameInput.classList.add('is-invalid');
                const fb = usernameInput.parentNode.querySelector('.invalid-feedback');
                if (fb) fb.textContent = 'Имя должно быть от 3 до 30 символов.';
                isValid = false;
            }
        }

        if (emailInput && !emailInput.classList.contains('is-invalid')) {
            const pattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            if (!pattern.test(emailInput.value.trim())) {
                emailInput.classList.add('is-invalid');
                const fb = emailInput.parentNode.querySelector('.invalid-feedback');
                if (fb) fb.textContent = 'Введите корректный email.';
                isValid = false;
            }
        }

        if (!passwordInput.classList.contains('is-invalid')) {
            const pattern = /^[a-zA-Z0-9!@#$%^&*()_+\-=\[\]{}|;':",./<>?`~\\ ]{8,20}$/;
            if (!pattern.test(passwordInput.value)) {
                passwordInput.classList.add('is-invalid');
                const fb = passwordInput.parentNode.querySelector('.invalid-feedback');
                if (fb) {
                    const len = passwordInput.value.length;
                    if (len < 8 || len > 20) {
                        fb.textContent = 'Длина пароля должна быть от 8 до 20 символов.';
                    } else {
                        fb.textContent = 'Разрешена только латиница, цифры и спецсимволы.';
                    }
                }
                isValid = false;
            }
        }

        if (!isValid) {
            event.preventDefault();
            const firstInvalid = document.querySelector('.is-invalid');
            if (firstInvalid) firstInvalid.focus();
        }
    });

    // Сброс подсветки при вводе
    [usernameInput, emailInput, passwordInput].forEach(input => {
        if (!input) return;
        input.addEventListener('input', () => {
            input.classList.remove('is-invalid');
        });
    });
});
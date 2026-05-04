document.addEventListener('DOMContentLoaded', () => {
    const signInForm = document.querySelector('form');
    const usernameInput = document.getElementById('username');
    const emailInput = document.getElementById('email');
    const passwordInput = document.getElementById('password-field');

    if (!signInForm || !passwordInput) return;

    signInForm.addEventListener('submit', (event) => {
        let isValid = true;

        // Проверка имени пользователя (если поле есть)
        if (usernameInput) {
            const username = usernameInput.value.trim();
            if (username.length < 3 || username.length > 30) {
                isValid = false;
                usernameInput.classList.add('is-invalid');
                const err = usernameInput.parentNode.querySelector('.invalid-feedback');
                if (err) err.textContent = 'Имя должно быть от 3 до 30 символов.';
            } else {
                usernameInput.classList.remove('is-invalid');
            }
        }

        // Проверка email
        if (emailInput) {
            const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            if (!emailPattern.test(emailInput.value.trim())) {
                isValid = false;
                emailInput.classList.add('is-invalid');
                const err = emailInput.parentNode.querySelector('.invalid-feedback');
                if (err) err.textContent = 'Введите корректный email.';
            } else {
                emailInput.classList.remove('is-invalid');
            }
        }

        // Проверка пароля
        const finalPattern = /^[a-zA-Z0-9!@#$%^&*()_+\-=\[\]{}|;':",./<>?`~\\ ]{8,20}$/;
        if (!finalPattern.test(passwordInput.value)) {
            isValid = false;
            passwordInput.classList.add('is-invalid');
            const err = passwordInput.parentNode.querySelector('.invalid-feedback');
            if (err) {
                const len = passwordInput.value.length;
                if (len < 8 || len > 20) {
                    err.textContent = 'Длина пароля должна быть от 8 до 20 символов.';
                } else {
                    err.textContent = 'Разрешена только латиница, цифры и спецсимволы.';
                }
            }
        } else {
            passwordInput.classList.remove('is-invalid');
        }

        if (!isValid) {
            event.preventDefault();
            // Фокусируем первое поле с ошибкой
            const firstInvalid = document.querySelector('.is-invalid');
            if (firstInvalid) firstInvalid.focus();
        }
    });

    // Снятие подсветки при вводе
    [usernameInput, emailInput, passwordInput].forEach(input => {
        if (!input) return;
        input.addEventListener('input', () => {
            input.classList.remove('is-invalid');
        });
    });
});
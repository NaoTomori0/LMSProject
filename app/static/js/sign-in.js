signInForm.addEventListener('submit', (event) => {
    let isValid = true;

    // Валидация username (всегда)
    if (usernameInput) {
        const val = usernameInput.value.trim();
        if (val.length < 3 || val.length > 30) {
            usernameInput.classList.add('is-invalid');
            const fb = usernameInput.parentNode.querySelector('.invalid-feedback');
            if (fb) fb.textContent = 'Имя должно быть от 3 до 30 символов.';
            isValid = false;
        } else {
            usernameInput.classList.remove('is-invalid');
        }
    }

    // Валидация email (всегда)
    if (emailInput) {
        const pattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!pattern.test(emailInput.value.trim())) {
            emailInput.classList.add('is-invalid');
            const fb = emailInput.parentNode.querySelector('.invalid-feedback');
            if (fb) fb.textContent = 'Введите корректный email.';
            isValid = false;
        } else {
            emailInput.classList.remove('is-invalid');
        }
    }

    // Валидация пароля (всегда)
    if (passwordInput) {
        const pattern = /^[a-zA-Z0-9!@#$%^&*()_+\-=[\]{}|;':",./<>?`~\\ ]{8,20}$/;
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
        } else {
            passwordInput.classList.remove('is-invalid');
        }
    }

    if (!isValid) {
        event.preventDefault();
        const firstInvalid = document.querySelector('.is-invalid');
        if (firstInvalid) firstInvalid.focus();
    }
});
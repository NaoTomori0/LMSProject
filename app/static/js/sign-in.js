document.addEventListener('DOMContentLoaded', () => {
    const signInForm = document.querySelector('form');
    const passwordInput = document.getElementById('password-field');
    const errorDiv = document.getElementById('password-error');

    if (signInForm && passwordInput) {
        signInForm.addEventListener('submit', (event) => {
            const finalPattern = /^[a-zA-Z0-9!@#$%^&*()_+=\-\[\]{}|;':",./<>?`~\\ ]{8,20}$/;

            if (!finalPattern.test(passwordInput.value)) {
                event.preventDefault();
                passwordInput.classList.add('is-invalid');

                if (errorDiv) {
                    const len = passwordInput.value.length;
                    if (len < 8 || len > 20) {
                        errorDiv.textContent = 'Длина пароля должна быть от 8 до 20 символов.';
                    } else {
                        errorDiv.textContent = 'Разрешена только латиница, цифры и спецсимволы.';
                    }
                    errorDiv.style.display = 'block';
                }
                passwordInput.focus();
            }
        });

        passwordInput.addEventListener('input', () => {
            passwordInput.classList.remove('is-invalid');
            if (errorDiv) errorDiv.style.display = 'none';
        });
    }
});

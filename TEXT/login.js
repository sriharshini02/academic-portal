import { loginUser } from './auth.js';

document.addEventListener('DOMContentLoaded', () => {
    const loginForm = document.getElementById('loginForm');
    const errorMessage = document.getElementById('errorMessage');

    loginForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const username = document.getElementById('username').value;
        const password = document.getElementById('password').value;

        try {
            const user = loginUser(username, password);
            // Clear any previous error messages
            errorMessage.textContent = '';
            errorMessage.style.display = 'none';

            // Redirect based on role
            if (user.role === 'teacher') {
                window.location.href = 'teacher-dashboard.html';
            } else {
                window.location.href = 'student-dashboard.html';
            }
        } catch (error) {
            // Display error message
            errorMessage.textContent = error.message;
            errorMessage.style.display = 'block';
        }
    });
}); 
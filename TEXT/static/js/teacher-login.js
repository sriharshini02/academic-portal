document.addEventListener('DOMContentLoaded', () => {
    const loginForm = document.getElementById('teacherLoginForm');
    const registerForm = document.getElementById('teacherRegisterForm');
    
    // Function to show message
    function showMessage(message, type) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `alert alert-${type}`;
        messageDiv.textContent = message;
        
        // Remove any existing alerts
        const existingAlerts = document.querySelectorAll('.alert');
        existingAlerts.forEach(alert => alert.remove());
        
        // Insert the message at the top of the form
        const form = document.querySelector('.register-container');
        form.insertBefore(messageDiv, form.firstChild);
        
        // Auto-dismiss success messages after 3 seconds
        if (type === 'success') {
            setTimeout(() => {
                messageDiv.remove();
            }, 3000);
        }
    }

    // Handle Teacher Login
    if (loginForm) {
        loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const teacherId = document.getElementById('teacherId').value;
            const password = document.getElementById('password').value;

            // Basic validation
            if (!teacherId || !password) {
                showMessage('Please fill in all fields', 'error');
                return;
            }

            try {
                const response = await fetch('/teacher/login', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ teacherId, password })
                });

                const data = await response.json();

                if (response.ok) {
                    showMessage('Login successful!', 'success');
                    setTimeout(() => {
                        window.location.href = '/teacher/dashboard';
                    }, 1000);
                } else {
                    showMessage(data.message || 'Invalid credentials', 'error');
                }
            } catch (error) {
                showMessage('An error occurred during login', 'error');
            }
        });
    }

    // Handle Teacher Registration
    if (registerForm) {
        registerForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const teacherId = document.getElementById('teacherId').value;
            const fullName = document.getElementById('fullName').value;
            const department = document.getElementById('department').value;
            const specialization = document.getElementById('specialization').value;
            const password = document.getElementById('password').value;

            // Basic validation
            if (!teacherId || !fullName || !department || !specialization || !password) {
                showMessage('Please fill in all fields', 'error');
                return;
            }

            try {
                const response = await fetch('/teacher/register', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        teacherId,
                        fullName,
                        department,
                        specialization,
                        password
                    })
                });

                const data = await response.json();

                if (response.ok) {
                    showMessage('Registration successful! Redirecting to login...', 'success');
                    setTimeout(() => {
                        window.location.href = '/teacher/login';
                    }, 2000);
                } else {
                    showMessage(data.message || 'Registration failed', 'error');
                }
            } catch (error) {
                showMessage('An error occurred during registration', 'error');
            }
        });
    }
}); 
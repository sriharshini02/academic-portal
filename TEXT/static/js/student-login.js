document.addEventListener('DOMContentLoaded', () => {
    const loginForm = document.getElementById('studentLoginForm');
    const registerForm = document.getElementById('studentRegisterForm');
    
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

    // Handle Student Login
    if (loginForm) {
        loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const studentId = document.getElementById('studentId').value;
            const password = document.getElementById('password').value;

            // Basic validation
            if (!studentId || !password) {
                showMessage('Please fill in all fields', 'error');
                return;
            }

            try {
                const response = await fetch('/student/login', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ studentId, password })
                });

                const data = await response.json();

                if (response.ok) {
                    showMessage('Login successful!', 'success');
                    setTimeout(() => {
                        window.location.href = '/student/dashboard';
                    }, 1000);
                } else {
                    showMessage(data.message || 'Invalid credentials', 'error');
                }
            } catch (error) {
                showMessage('An error occurred during login', 'error');
            }
        });
    }

    // Handle Student Registration
    if (registerForm) {
        registerForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const studentId = document.getElementById('studentId').value;
            const fullName = document.getElementById('fullName').value;
            const department = document.getElementById('department').value;
            const password = document.getElementById('password').value;

            // Basic validation
            if (!studentId || !fullName || !department || !password) {
                showMessage('Please fill in all fields', 'error');
                return;
            }

            try {
                const response = await fetch('/student/register', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        studentId,
                        fullName,
                        department,
                        password
                    })
                });

                const data = await response.json();

                if (response.ok) {
                    showMessage('Registration successful! Redirecting to login...', 'success');
                    setTimeout(() => {
                        window.location.href = '/student/login';
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
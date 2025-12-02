// Authentication JavaScript
console.log("🔥 auth.js LOADED");
// Form validation rules
const validationRules = {
    email: {
        required: true,
        pattern: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
        message: 'Please enter a valid email address'
    },
    password: {
        required: true,
        minLength: 6,
        message: 'Password must be at least 6 characters long'
    },
    username: {
        required: true,
        minLength: 2,
        message: 'Name must be at least 2 characters long'
    }
};

function getCSRFToken() {
    const name = 'csrftoken';
    const cookies = document.cookie.split(';');
    for (let cookie of cookies) {
        cookie = cookie.trim();
        if (cookie.startsWith(name + '=')) {
            return cookie.substring(name.length + 1);
        }
    }
    return null;
}


// Initialize authentication page
function initAuth() {
    setupFormListeners();
    checkAlreadyLoggedIn();
}

// Check if user is already logged in
function checkAlreadyLoggedIn() {
    const userData = sessionStorage.getItem('currentUser');
    if (userData) {
        window.location.href = '/dashboard';
    }
}

// Setup form event listeners
function setupFormListeners() {
    const loginForm = document.getElementById('loginForm');
    const registerForm = document.getElementById('registerForm');
    
    if (loginForm) {
        loginForm.addEventListener('submit', handleLogin);
    }
    
    if (registerForm) {
        registerForm.addEventListener('submit', handleRegister);
    }
    
    // Add real-time validation
    setupRealTimeValidation();
}

/// LOGIN
async function handleLogin(e) {
    e.preventDefault();

    const form = e.target;
    const formData = new FormData(form);

    const loginData = {
        login: formData.get("email"),   // username or email
        password: formData.get("password")
    };

    console.log("➡️ LOGIN DATA RECEIVED:", loginData);

    // --- validation ---
    if (!loginData.login || loginData.login.length < 3) {
        showAlert("Enter valid email or username", "error");
        return;
    }
    if (!loginData.password || loginData.password.length < 3) {
        showAlert("Password required", "error");
        return;
    }

    try {
        const response = await fetch("/api/accounts/login/", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": getCSRFToken()
            },
            body: JSON.stringify(loginData)
        });

        const data = await response.json();
        console.log("➡️ LOGIN RESPONSE:", data);

        if (!response.ok) {
            showAlert("Invalid login", "error");
            return;
        }

        sessionStorage.setItem("currentUser", JSON.stringify(data.user));
        sessionStorage.setItem("accessToken", data.access);

        window.location.href = "/dashboard";

    } catch (err) {
        console.error("Login error:", err);
        showAlert("Login error occurred", "error");
    }
}

// Handle register form submission
async function handleRegister(e) {
    e.preventDefault();
    
    const form = e.target;
    const formData = new FormData(form);
    const registerData = {
        username: formData.get('name'), 
        email: formData.get('email'),
        password: formData.get('password')
    };

    if (!validateRegisterForm(registerData)) return;

    const submitBtn = form.querySelector('button[type="submit"]');
    const originalText = submitBtn.textContent;
    submitBtn.textContent = 'Creating Account...';
    submitBtn.disabled = true;

    try {
        const response = await fetch('/api/accounts/register/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken(),
            },
            body: JSON.stringify(registerData)
        });


        const data = await response.json();

        if (response.ok) {
            showAlert('Account created successfully! Redirecting...', 'success');

            form.reset();

            setTimeout(() => {
                window.location.href = '/api/accounts/login-page/';
            }, 1500);
        } else {
            showAlert(JSON.stringify(data) || 'Registration failed', 'error');
        }

    } catch (error) {
        console.error('Registration error:', error);
        showAlert('An error occurred during registration.', 'error');
    } finally {
        submitBtn.textContent = originalText;
        submitBtn.disabled = false;
    }
}

// Validate login form
function validateLoginForm(data) {
    const errors = [];

    // Allow BOTH email OR username
    const isEmail = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(data.email);
    const isUsername = data.email.length >= 3;  // minimum username length

    if (!isEmail && !isUsername) {
        errors.push("Enter a valid email or username");
    }

    if (!validateField('password', data.password)) {
        errors.push('Password required');
    }

    if (errors.length > 0) {
        showAlert(errors.join('. '), 'error');
        return false;
    }
    return true;
}


// Validate register form
function validateRegisterForm(data) {
    const errors = [];

    if (!validateField('username', data.username)) {
        errors.push(validationRules.username.message);
    }
    if (!validateField('email', data.email)) {
        errors.push(validationRules.email.message);
    }
    if (!validateField('password', data.password)) {
        errors.push(validationRules.password.message);
    }

    if (errors.length > 0) {
        showAlert(errors.join('. '), 'error');
        return false;
    }
    return true;
}

// Validate individual field
function validateField(fieldName, value) {
    const rule = validationRules[fieldName];
    if (!rule) return true;

    if (rule.required && (!value || value.trim() === '')) return false;
    if (rule.minLength && value.length < rule.minLength) return false;
    if (rule.pattern && !rule.pattern.test(value)) return false;

    return true;
}

// Real-time validation
function setupRealTimeValidation() {
    const inputs = document.querySelectorAll('.form-control');

    inputs.forEach(input => {
        input.addEventListener('blur', function() {
            validateInputField(this);
        });

        input.addEventListener('input', function() {
            clearInputError(this);
        });
    });
}

function validateInputField(input) {
    const fieldName = input.name;
    const value = input.value;

    if (validateField(fieldName, value)) {
        input.classList.remove('is-invalid');
        input.classList.add('is-valid');
    } else {
        input.classList.remove('is-valid');
        input.classList.add('is-invalid');
    }
}

function clearInputError(input) {
    input.classList.remove('is-invalid', 'is-valid');
}

// Alerts
function showAlert(message, type = 'info') {
    const existingAlerts = document.querySelectorAll('.alert');
    existingAlerts.forEach(alert => alert.remove());

    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type}`;
    alertDiv.innerHTML = `
        <span>${message}</span>
        <button type="button" class="alert-close" onclick="this.parentElement.remove()">&times;</button>
    `;

    const formContainer = document.querySelector('.auth-right') || document.querySelector('.container');
    if (formContainer) {
        formContainer.insertBefore(alertDiv, formContainer.firstChild);

        setTimeout(() => {
            if (alertDiv.parentNode) alertDiv.parentNode.removeChild(alertDiv);
        }, 5000);
    }
}

// Initialize
document.addEventListener('DOMContentLoaded', function() {
    initAuth();
});

window.AuthApp = {
    initAuth,
    handleLogin,
    handleRegister,
    showAlert,
    togglePassword
};

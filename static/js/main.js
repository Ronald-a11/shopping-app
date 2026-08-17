// Main JavaScript for Zimbabwe Supermarket

document.addEventListener('DOMContentLoaded', function() {
    // Initialize cart count
    updateCartCount();
    
    // Add smooth scrolling to all links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
    
    // Add animation classes on scroll
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };
    
    const observer = new IntersectionObserver(function(entries) {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('fade-in');
            }
        });
    }, observerOptions);
    
    // Observe all cards and sections
    document.querySelectorAll('.card, .feature-card, .product-card').forEach(card => {
        observer.observe(card);
    });
    
    // Cart functionality
    initializeCart();
    
    // Form validation
    initializeFormValidation();

    // Quantity input validation
    initializeQuantityInputs();
});

// Cart functionality
function initializeCart() {
    // Add to cart forms
    document.querySelectorAll('form[action*="add_to_cart"]').forEach(form => {
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const formData = new FormData(this);
            const productId = this.action.split('/').slice(-2, -1)[0];
            const quantity = formData.get('quantity') || 1;
            
            addToCart(productId, quantity, this);
        });
    });
    
    // Update cart item forms
    document.querySelectorAll('form[action*="update_cart_item"]').forEach(form => {
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const formData = new FormData(this);
            const quantity = formData.get('quantity');
            
            if (quantity <= 0) {
                if (confirm('Are you sure you want to remove this item from your cart?')) {
                    this.submit();
                }
                return;
            }
            
            this.submit();
        });
    });
}

// Add to cart function
function addToCart(productId, quantity, form) {
    const button = form.querySelector('button[type="submit"]');
    const originalText = button.innerHTML;
    
    // Show loading state
    button.innerHTML = '<span class="spinner"></span>';
    button.disabled = true;
    
    fetch(form.action, {
        method: 'POST',
        body: new FormData(form),
        headers: {
            'X-CSRFToken': getCookie('csrftoken'),
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(response => response.json().catch(() => ({
        success: response.ok,
        message: response.ok ? null : 'Error adding product to cart'
    })))
    .then(data => {
        if (data.success) {
            // Show success message
            showNotification(data.message || 'Product added to cart!', 'success');

            // Update cart count
            if (typeof data.count === 'number') {
                setCartCount(data.count);
            } else {
                updateCartCount();
            }

            // Add animation to button
            button.classList.add('btn-success');
            setTimeout(() => {
                button.classList.remove('btn-success');
            }, 1000);
        } else {
            showNotification(data.message || 'Error adding product to cart', 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showNotification('Error adding product to cart', 'error');
    })
    .finally(() => {
        // Restore button state
        button.innerHTML = originalText;
        button.disabled = false;
    });
}

// Render a cart count into the navbar badge
function setCartCount(count) {
    const cartCount = document.getElementById('cart-count');
    if (cartCount) {
        cartCount.textContent = count || 0;
        cartCount.style.display = count > 0 ? 'flex' : 'none';
    }
}

// Update cart count
function updateCartCount() {
    fetch('/cart-count/', {
        method: 'GET',
        headers: {
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(response => response.json())
    .then(data => setCartCount(data.count))
    .catch(error => {
        console.error('Error updating cart count:', error);
    });
}

// Form validation
function initializeFormValidation() {
    const forms = document.querySelectorAll('form');
    
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            if (!validateForm(this)) {
                e.preventDefault();
            }
        });
    });
}

// Validate form
function validateForm(form) {
    let isValid = true;
    const requiredFields = form.querySelectorAll('[required]');
    
    requiredFields.forEach(field => {
        if (!field.value.trim()) {
            showFieldError(field, 'This field is required');
            isValid = false;
        } else {
            clearFieldError(field);
        }
    });
    
    // Email validation
    const emailFields = form.querySelectorAll('input[type="email"]');
    emailFields.forEach(field => {
        if (field.value && !isValidEmail(field.value)) {
            showFieldError(field, 'Please enter a valid email address');
            isValid = false;
        }
    });
    
    // Phone validation
    const phoneFields = form.querySelectorAll('input[type="tel"], input[name*="phone"]');
    phoneFields.forEach(field => {
        if (field.value && !isValidPhone(field.value)) {
            showFieldError(field, 'Please enter a valid phone number');
            isValid = false;
        }
    });
    
    return isValid;
}

// Show field error
function showFieldError(field, message) {
    clearFieldError(field);
    
    field.classList.add('is-invalid');
    
    const errorDiv = document.createElement('div');
    errorDiv.className = 'invalid-feedback';
    errorDiv.textContent = message;
    
    field.parentNode.appendChild(errorDiv);
}

// Clear field error
function clearFieldError(field) {
    field.classList.remove('is-invalid');
    
    const errorDiv = field.parentNode.querySelector('.invalid-feedback');
    if (errorDiv) {
        errorDiv.remove();
    }
}

// Email validation
function isValidEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
}

// Phone validation (Zimbabwe format)
function isValidPhone(phone) {
    const phoneRegex = /^(\+263|0)[0-9]{9}$/;
    return phoneRegex.test(phone.replace(/\s/g, ''));
}

// Quantity input validation
function initializeQuantityInputs() {
    const quantityInputs = document.querySelectorAll('input[name="quantity"]');
    
    quantityInputs.forEach(input => {
        input.addEventListener('change', function() {
            const value = parseInt(this.value);
            const max = parseInt(this.getAttribute('max')) || 999;
            const min = parseInt(this.getAttribute('min')) || 1;
            
            if (value < min) {
                this.value = min;
            } else if (value > max) {
                this.value = max;
                showNotification(`Maximum quantity available: ${max}`, 'warning');
            }
        });
    });
}

// Show notification
function showNotification(message, type = 'info') {
    // Remove existing notifications
    const existingNotifications = document.querySelectorAll('.notification');
    existingNotifications.forEach(notification => notification.remove());
    
    const notification = document.createElement('div');
    notification.className = `notification alert alert-${type === 'error' ? 'danger' : type} alert-dismissible fade show`;
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        z-index: 9999;
        min-width: 300px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    `;
    
    notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(notification);
    
    // Auto remove after 5 seconds
    setTimeout(() => {
        if (notification.parentNode) {
            notification.remove();
        }
    }, 5000);
}

// Get CSRF token
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// Format currency
function formatCurrency(amount, currency = 'USD') {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: currency
    }).format(amount);
}

// Format Zimbabwe Dollars
function formatZWD(amount) {
    return new Intl.NumberFormat('en-ZW', {
        style: 'currency',
        currency: 'ZWD'
    }).format(amount);
}

// Lazy loading for images
function initializeLazyLoading() {
    const images = document.querySelectorAll('img[data-src]');
    
    const imageObserver = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const img = entry.target;
                img.src = img.dataset.src;
                img.classList.remove('lazy');
                imageObserver.unobserve(img);
            }
        });
    });
    
    images.forEach(img => imageObserver.observe(img));
}

// Initialize lazy loading
document.addEventListener('DOMContentLoaded', initializeLazyLoading);

// Back to top button
function initializeBackToTop() {
    const backToTopButton = document.createElement('button');
    backToTopButton.innerHTML = '<i class="fas fa-arrow-up"></i>';
    backToTopButton.className = 'btn btn-success btn-floating';
    backToTopButton.style.cssText = `
        position: fixed;
        bottom: 20px;
        right: 20px;
        z-index: 1000;
        width: 50px;
        height: 50px;
        border-radius: 50%;
        display: none;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    `;
    
    document.body.appendChild(backToTopButton);
    
    window.addEventListener('scroll', () => {
        if (window.pageYOffset > 300) {
            backToTopButton.style.display = 'block';
        } else {
            backToTopButton.style.display = 'none';
        }
    });
    
    backToTopButton.addEventListener('click', () => {
        window.scrollTo({
            top: 0,
            behavior: 'smooth'
        });
    });
}

// Initialize back to top button
document.addEventListener('DOMContentLoaded', initializeBackToTop);

// Product image zoom
function initializeImageZoom() {
    const productImages = document.querySelectorAll('.product-card img, .product-detail img');
    
    productImages.forEach(img => {
        img.addEventListener('click', function() {
            // Create modal for image zoom
            const modal = document.createElement('div');
            modal.className = 'modal fade';
            modal.innerHTML = `
                <div class="modal-dialog modal-lg modal-dialog-centered">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">Product Image</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body text-center">
                            <img src="${this.src}" class="img-fluid" alt="${this.alt}">
                        </div>
                    </div>
                </div>
            `;
            
            document.body.appendChild(modal);
            
            const bsModal = new bootstrap.Modal(modal);
            bsModal.show();
            
            modal.addEventListener('hidden.bs.modal', () => {
                modal.remove();
            });
        });
        
        img.style.cursor = 'pointer';
    });
}

// Initialize image zoom
document.addEventListener('DOMContentLoaded', initializeImageZoom);

/**
 * HKHC Community Discussion Platform - Client Interactivity
 */

// CSRF Cookie Helper
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

// Automatically configure HTMX with CSRF token for all requests
document.addEventListener('htmx:configRequest', function (evt) {
    const csrfToken = getCookie('csrftoken') || (document.querySelector('[name=csrfmiddlewaretoken]') ? document.querySelector('[name=csrfmiddlewaretoken]').value : '');
    if (csrfToken) {
        evt.detail.headers['X-CSRFToken'] = csrfToken;
    }
});

// Auto-scroll to newly appended reply after HTMX swap
document.addEventListener('htmx:afterSwap', function (evt) {
    if (evt.detail.target && evt.detail.target.id === 'replies-container') {
        const lastCard = evt.detail.target.lastElementChild;
        if (lastCard) {
            lastCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            lastCard.classList.add('highlight-pulse');
        }
        const textarea = document.querySelector('#main-reply-form textarea');
        if (textarea) textarea.value = '';
    }
});

// Toggle nested reply box
function toggleNestedReplyForm(replyId) {
    const formEl = document.getElementById('reply-form-' + replyId);
    if (formEl) {
        const isHidden = formEl.classList.contains('hidden');
        document.querySelectorAll('.nested-reply-form').forEach(el => el.classList.add('hidden'));
        if (isHidden) {
            formEl.classList.remove('hidden');
            const textarea = formEl.querySelector('textarea');
            if (textarea) textarea.focus();
        }
    }
}

// Confirmation helper for destructive actions
function confirmAction(message) {
    return confirm(message || 'Are you sure you want to proceed with this action?');
}

// Mobile navigation menu toggle
document.addEventListener('DOMContentLoaded', function () {
    const menuToggle = document.getElementById('mobile-menu-toggle');
    const mobileMenu = document.getElementById('mobile-menu');
    if (menuToggle && mobileMenu) {
        menuToggle.addEventListener('click', function () {
            mobileMenu.classList.toggle('hidden');
        });
    }

    // Auto-dismiss alerts after 6 seconds
    const alerts = document.querySelectorAll('.alert-auto-dismiss');
    alerts.forEach(function (alert) {
        setTimeout(function () {
            alert.style.transition = 'opacity 0.5s ease';
            alert.style.opacity = '0';
            setTimeout(function () {
                alert.remove();
            }, 500);
        }, 6000);
    });

    // Identity mode toggle explanation update
    const postModeRadios = document.querySelectorAll('input[name="post_mode"]');
    const privacyNotice = document.getElementById('identity-mode-notice');
    if (postModeRadios.length > 0 && privacyNotice) {
        postModeRadios.forEach(function (radio) {
            radio.addEventListener('change', function () {
                if (this.value === 'anonymous') {
                    privacyNotice.classList.remove('hidden');
                } else {
                    privacyNotice.classList.add('hidden');
                }
            });
        });
    }
});

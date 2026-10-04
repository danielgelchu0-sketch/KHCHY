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

// Client interactivity on DOM ready
document.addEventListener('DOMContentLoaded', function () {
    // Mobile navigation drawer toggle
    const menuToggle = document.getElementById('mobile-menu-toggle');
    const drawer = document.getElementById('mobile-drawer');
    const backdrop = document.getElementById('mobile-drawer-backdrop');
    const drawerClose = document.getElementById('mobile-drawer-close');

    function openDrawer() {
        if (!drawer || !backdrop) return;
        drawer.classList.remove('hidden');
        backdrop.classList.remove('hidden');
        // Force reflow for CSS transition
        void drawer.offsetWidth;
        drawer.classList.add('open');
        backdrop.classList.add('open');
        document.body.style.overflow = 'hidden';
        if (menuToggle) menuToggle.setAttribute('aria-expanded', 'true');
        if (drawerClose) drawerClose.focus();
    }

    function closeDrawer() {
        if (!drawer || !backdrop) return;
        drawer.classList.remove('open');
        backdrop.classList.remove('open');
        document.body.style.overflow = '';
        if (menuToggle) menuToggle.setAttribute('aria-expanded', 'false');
        setTimeout(function () {
            if (drawer && !drawer.classList.contains('open')) {
                drawer.classList.add('hidden');
            }
            if (backdrop && !backdrop.classList.contains('open')) {
                backdrop.classList.add('hidden');
            }
        }, 280);
        if (menuToggle) menuToggle.focus();
    }

    if (menuToggle) {
        menuToggle.addEventListener('click', function () {
            if (drawer && drawer.classList.contains('open')) {
                closeDrawer();
            } else {
                openDrawer();
            }
        });
    }

    if (drawerClose) {
        drawerClose.addEventListener('click', closeDrawer);
    }

    if (backdrop) {
        backdrop.addEventListener('click', closeDrawer);
    }

    // Close drawer on Escape key press
    document.addEventListener('keydown', function (evt) {
        if (evt.key === 'Escape' && drawer && drawer.classList.contains('open')) {
            closeDrawer();
        }
    });

    // Close automatically if viewport resized to desktop breakpoint
    window.addEventListener('resize', function () {
        if (window.innerWidth > 900 && drawer && drawer.classList.contains('open')) {
            closeDrawer();
        }
    });

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

    // Password Visibility Toggle (Show / Hide Password)
    const toggleButtons = document.querySelectorAll('.btn-toggle-password');
    toggleButtons.forEach(function (btn) {
        btn.addEventListener('click', function () {
            const targetId = btn.getAttribute('data-target');
            let input = null;
            if (targetId) {
                input = document.getElementById(targetId);
            }
            if (!input) {
                input = btn.closest('.password-input-wrapper')?.querySelector('input');
            }
            if (!input) return;

            const iconShow = btn.querySelector('.icon-eye-show');
            const iconHide = btn.querySelector('.icon-eye-hide');

            if (input.type === 'password') {
                input.type = 'text';
                btn.setAttribute('title', 'Hide password');
                btn.setAttribute('aria-label', 'Hide password');
                if (iconShow) iconShow.classList.add('hidden');
                if (iconHide) iconHide.classList.remove('hidden');
            } else {
                input.type = 'password';
                btn.setAttribute('title', 'Show password');
                btn.setAttribute('aria-label', 'Show password');
                if (iconShow) iconShow.classList.remove('hidden');
                if (iconHide) iconHide.classList.add('hidden');
            }
        });
    });
});

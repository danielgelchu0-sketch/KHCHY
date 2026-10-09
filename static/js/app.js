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

    // =========================================================================
    // HKHC Real-Time Notification & Web Push System (Telegram-Inspired)
    // =========================================================================

    const isAuthenticated = document.querySelector('meta[name="is-authenticated"]')?.content === 'true';
    const pollUrl = document.querySelector('meta[name="poll-notifications-url"]')?.content;
    const vapidPublicKey = document.querySelector('meta[name="vapid-public-key"]')?.content;
    const subscribeUrl = document.querySelector('meta[name="push-subscribe-url"]')?.content;

    // 1. Audio Sound Player with Mute Toggle
    const soundToggleBtn = document.getElementById('nav-sound-toggle');
    const soundIconUnmuted = document.getElementById('sound-icon-unmuted');
    const soundIconMuted = document.getElementById('sound-icon-muted');

    function isSoundMuted() {
        return localStorage.getItem('hkhc_sound_muted') === 'true';
    }

    function updateSoundToggleUI() {
        if (!soundToggleBtn) return;
        const muted = isSoundMuted();
        if (muted) {
            soundIconUnmuted?.classList.add('hidden');
            soundIconMuted?.classList.remove('hidden');
            soundToggleBtn.setAttribute('title', 'Notification Sound: Muted (Click to Unmute)');
            soundToggleBtn.setAttribute('aria-label', 'Notification Sound: Muted (Click to Unmute)');
        } else {
            soundIconUnmuted?.classList.remove('hidden');
            soundIconMuted?.classList.add('hidden');
            soundToggleBtn.setAttribute('title', 'Notification Sound: Active (Click to Mute)');
            soundToggleBtn.setAttribute('aria-label', 'Notification Sound: Active (Click to Mute)');
        }
    }

    function playNotificationSound() {
        if (isSoundMuted()) return;
        try {
            const chime = new Audio('/static/sounds/notification.wav');
            chime.volume = 0.85;
            chime.play().catch(function (e) {
                // Browser autoplay policies may restrict playback until user interaction
                console.log('Audio playback waiting for user gesture:', e);
            });
        } catch (err) {
            console.error('Error playing notification sound:', err);
        }
    }

    if (soundToggleBtn) {
        updateSoundToggleUI();
        soundToggleBtn.addEventListener('click', function () {
            const currentlyMuted = isSoundMuted();
            localStorage.setItem('hkhc_sound_muted', currentlyMuted ? 'false' : 'true');
            updateSoundToggleUI();
            if (currentlyMuted) {
                playNotificationSound();
            }
        });
    }

    // 2. Telegram-Style Floating Toast Banner
    const toastContainer = document.getElementById('toast-container');

    function showNotificationToast(item) {
        if (!toastContainer) return;

        const card = document.createElement('div');
        card.className = 'toast-card';
        card.setAttribute('role', 'alert');

        const iconSymbol = item.notification_type === 'new_discussion' ? '📢' : '💬';

        card.innerHTML = `
            <div class="toast-icon" aria-hidden="true">${iconSymbol}</div>
            <div class="toast-content">
                <div class="toast-title">${escapeHTML(item.title)}</div>
                <div class="toast-message">${escapeHTML(item.message)}</div>
                <div class="toast-time">${item.created_at || 'Just now'}</div>
            </div>
            <button type="button" class="toast-close-btn" aria-label="Close notification">&times;</button>
        `;

        // Card navigation on click
        card.addEventListener('click', function (e) {
            if (e.target.closest('.toast-close-btn')) {
                dismissToast(card);
                return;
            }
            if (item.link) {
                window.location.href = item.link;
            }
        });

        // Close button
        const closeBtn = card.querySelector('.toast-close-btn');
        closeBtn?.addEventListener('click', function (e) {
            e.stopPropagation();
            dismissToast(card);
        });

        toastContainer.appendChild(card);
        playNotificationSound();

        // Auto-dismiss after 6.5 seconds
        setTimeout(function () {
            dismissToast(card);
        }, 6500);
    }

    function dismissToast(card) {
        if (!card || card.classList.contains('fade-out')) return;
        card.classList.add('fade-out');
        setTimeout(function () {
            card.remove();
        }, 300);
    }

    function escapeHTML(str) {
        if (!str) return '';
        const p = document.createElement('p');
        p.textContent = str;
        return p.innerHTML;
    }

    // 3. Near Real-Time Notification Polling (Active Tabs)
    let lastSeenNotificationId = parseInt(sessionStorage.getItem('hkhc_last_notif_id') || '0', 10);
    let pollInterval = null;

    function updateBadge(count) {
        const badge = document.getElementById('nav-notification-badge');
        if (!badge) return;
        if (count > 0) {
            badge.textContent = count;
            badge.classList.remove('hidden');
        } else {
            badge.textContent = '0';
            badge.classList.add('hidden');
        }
    }

    function checkLiveNotifications() {
        if (!isAuthenticated || !pollUrl) return;

        const url = lastSeenNotificationId > 0
            ? `${pollUrl}?since_id=${lastSeenNotificationId}`
            : pollUrl;

        fetch(url, { credentials: 'same-origin' })
            .then(function (res) {
                if (!res.ok) throw new Error('Poll failed');
                return res.json();
            })
            .then(function (data) {
                if (typeof data.unread_count === 'number') {
                    updateBadge(data.unread_count);
                }

                if (typeof data.total_members === 'number') {
                    document.querySelectorAll('.js-total-members-count').forEach(function (el) {
                        el.textContent = data.total_members;
                    });
                }

                if (Array.isArray(data.notifications) && data.notifications.length > 0) {

                    let highestId = lastSeenNotificationId;

                    data.notifications.forEach(function (notif) {
                        if (notif.id > lastSeenNotificationId) {
                            showNotificationToast(notif);
                            if (notif.id > highestId) {
                                highestId = notif.id;
                            }
                        }
                    });

                    if (highestId > lastSeenNotificationId) {
                        lastSeenNotificationId = highestId;
                        sessionStorage.setItem('hkhc_last_notif_id', highestId.toString());
                    }
                }
            })
            .catch(function (err) {
                // Silently handle occasional offline or network blips
                console.debug('Notification poll status:', err);
            });
    }

    if (isAuthenticated) {
        // Initial fetch after 2 seconds
        setTimeout(checkLiveNotifications, 2000);
        // Near real-time interval every 12 seconds
        pollInterval = setInterval(checkLiveNotifications, 12000);
    }

    // 4. Web Push Notifications (Service Worker + VAPID)
    function urlBase64ToUint8Array(base64String) {
        const padding = '='.repeat((4 - base64String.length % 4) % 4);
        const base64 = (base64String + padding)
            .replace(/\-/g, '+')
            .replace(/_/g, '/');
        const rawData = window.atob(base64);
        const outputArray = new Uint8Array(rawData.length);
        for (let i = 0; i < rawData.length; ++i) {
            outputArray[i] = rawData.charCodeAt(i);
        }
        return outputArray;
    }

    const pushCard = document.getElementById('push-permission-card');
    const btnEnablePush = document.getElementById('btn-enable-push');
    const btnDismissPush = document.getElementById('btn-dismiss-push');

    if (isAuthenticated && 'serviceWorker' in navigator && 'PushManager' in window && vapidPublicKey) {
        // Register the root service worker
        navigator.serviceWorker.register('/sw.js', { scope: '/' })
            .then(function (registration) {
                return registration.pushManager.getSubscription().then(function (sub) {
                    // Check if already subscribed
                    if (sub) {
                        // Keep subscription in sync
                        sendSubscriptionToServer(sub);
                    } else if (Notification.permission === 'default' && !sessionStorage.getItem('hkhc_push_dismissed')) {
                        // Show friendly bilingual card for non-tech users
                        setTimeout(function () {
                            pushCard?.classList.remove('hidden');
                        }, 2500);
                    }
                });
            })
            .catch(function (err) {
                console.debug('ServiceWorker registration note:', err);
            });

        // User clicked Enable Alerts
        btnEnablePush?.addEventListener('click', function () {
            playNotificationSound(); // Also unlocks audio autoplay for page

            Notification.requestPermission().then(function (permission) {
                pushCard?.classList.add('hidden');
                if (permission === 'granted') {
                    navigator.serviceWorker.ready.then(function (registration) {
                        const subscribeOptions = {
                            userVisibleOnly: true,
                            applicationServerKey: urlBase64ToUint8Array(vapidPublicKey)
                        };
                        return registration.pushManager.subscribe(subscribeOptions);
                    }).then(function (subscription) {
                        return sendSubscriptionToServer(subscription);
                    }).then(function () {
                        showNotificationToast({
                            title: 'Alerts Activated! / ማሳወቂያዎች ተከፍተዋል!',
                            message: 'You will receive instant alerts for community replies.',
                            notification_type: 'new_discussion'
                        });
                    }).catch(function (err) {
                        console.error('Push subscribe error:', err);
                    });
                }
            });
        });

        // User clicked Later
        btnDismissPush?.addEventListener('click', function () {
            pushCard?.classList.add('hidden');
            sessionStorage.setItem('hkhc_push_dismissed', 'true');
        });
    }

    function sendSubscriptionToServer(subscription) {
        if (!subscribeUrl) return Promise.resolve();
        const csrfToken = getCookie('csrftoken') || '';

        return fetch(subscribeUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify(subscription)
        });
    }
});


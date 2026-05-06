(function() {
  'use strict';

  var CONFIG = window.GOFORAI_CONFIG || {};
  var navbar = document.getElementById('navbar');
  var mobileMenuBtn = document.getElementById('mobileMenuBtn');
  var mobileMenu = document.getElementById('mobileMenu');
  var videoModal = document.getElementById('videoModal');
  var videoFrame = document.getElementById('videoFrame');
  var modalTitle = document.getElementById('modalTitle');
  var modalClose = videoModal.querySelector('.modal-close');
  var modalBackdrop = videoModal.querySelector('.modal-backdrop');
  var contactForm = document.getElementById('contactForm');
  var toast = document.getElementById('toast');

  // ── Auth Elements ──
  var authModal = document.getElementById('authModal');
  var phoneForm = document.getElementById('phoneForm');
  var authPhone = document.getElementById('authPhone');

  // ── Payment Elements ──
  var paymentModal = document.getElementById('paymentModal');
  var paymentLoading = document.getElementById('paymentLoading');
  var paymentDetails = document.getElementById('paymentDetails');
  var paymentStatusDisplay = document.getElementById('paymentStatusDisplay');
  var paymentPollTimer = null;

  // ── State ──
  var isLoggedIn = CONFIG.isLoggedIn || false;
  var hasPaid = CONFIG.hasPaid || false;

  // ── Navbar ──
  window.addEventListener('scroll', function() {
    navbar.style.boxShadow = window.pageYOffset > 50 ? '0 1px 4px rgba(0,0,0,.06)' : 'none';
  }, { passive: true });

  // ── Mobile Menu ──
  mobileMenuBtn.addEventListener('click', function() {
    mobileMenu.classList.toggle('active');
  });
  mobileMenu.querySelectorAll('a, button').forEach(function(el) {
    el.addEventListener('click', function() { mobileMenu.classList.remove('active'); });
  });

  // ── Module Accordion ──
  document.querySelectorAll('.module-header').forEach(function(header) {
    header.addEventListener('click', function(e) {
      e.stopPropagation();
      header.parentElement.classList.toggle('expanded');
    });
  });
  var first = document.querySelector('.module-card');
  if (first) first.classList.add('expanded');

  // ── Video Modal ──
  document.querySelectorAll('.btn-play:not(.btn-disabled)').forEach(function(btn) {
    btn.addEventListener('click', function(e) {
      e.stopPropagation();
      openModal(btn.dataset.video, btn.dataset.title);
    });
  });

  function openModal(videoId, title) {
    videoFrame.src = 'https://www.youtube.com/embed/' + videoId + '?autoplay=1&rel=0';
    modalTitle.textContent = title || 'Lecture vidéo';
    videoModal.classList.add('active');
    document.body.style.overflow = 'hidden';
  }

  function closeVideoModal() {
    videoModal.classList.remove('active');
    videoFrame.src = '';
    document.body.style.overflow = '';
  }

  modalClose.addEventListener('click', closeVideoModal);
  modalBackdrop.addEventListener('click', closeVideoModal);
  document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
      if (videoModal.classList.contains('active')) closeVideoModal();
      if (authModal.classList.contains('active')) closeAuthModal();
      if (paymentModal.classList.contains('active')) closePaymentModal();
    }
  });

  // ── Contact Form ──
  if (contactForm) {
    contactForm.addEventListener('submit', function(e) {
      e.preventDefault();
      var btn = contactForm.querySelector('button[type="submit"]');
      var btnText = btn.querySelector('.btn-text');
      var loader = btn.querySelector('.btn-loader');
      btn.disabled = true;
      btnText.style.display = 'none';
      loader.style.display = 'block';

      fetch('/api/contact', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: document.getElementById('name').value,
          email: document.getElementById('email').value,
          message: document.getElementById('message').value
        })
      })
      .then(function(r) { return r.json(); })
      .then(function(res) {
        if (res.success) {
          showToast(res.message || 'Message envoyé !');
          contactForm.reset();
        } else {
          showToast(res.error || 'Erreur.', true);
        }
      })
      .catch(function() { showToast('Erreur réseau.', true); })
      .finally(function() {
        btn.disabled = false;
        btnText.style.display = '';
        loader.style.display = 'none';
      });
    });
  }

  // ── Toast ──
  var toastTimer;
  function showToast(message, isError) {
    var msg = toast.querySelector('.toast-msg');
    msg.textContent = message;
    msg.style.color = isError ? '#e74c3c' : '#27ae60';
    toast.classList.add('active');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function() { toast.classList.remove('active'); }, 3500);
  }

  // ── Smooth scroll ──
  document.querySelectorAll('a[href^="#"]').forEach(function(anchor) {
    anchor.addEventListener('click', function(e) {
      e.preventDefault();
      var target = document.querySelector(this.getAttribute('href'));
      if (target) {
        var top = target.getBoundingClientRect().top + window.pageYOffset - 70;
        window.scrollTo({ top: top, behavior: 'smooth' });
      }
    });
  });

  // ═══════════════════════════════════════════════════════════════════════
  //  AUTH FLOW
  // ═══════════════════════════════════════════════════════════════════════

  function openAuthModal() {
    if (phoneForm) phoneForm.reset();
    authModal.classList.add('active');
    document.body.style.overflow = 'hidden';
    setTimeout(function() { authPhone.focus(); }, 150);
  }

  function closeAuthModal() {
    authModal.classList.remove('active');
    document.body.style.overflow = '';
  }

  document.querySelectorAll('#btnLogin, #btnLoginMobile, #btnLoginFromLock').forEach(function(btn) {
    if (btn) btn.addEventListener('click', function(e) {
      e.preventDefault();
      openAuthModal();
    });
  });

  // Close auth modal via backdrop
  var authBackdrop = authModal.querySelector('.modal-backdrop');
  if (authBackdrop) authBackdrop.addEventListener('click', closeAuthModal);
  var authCloseBtn = authModal.querySelector('.modal-close');
  if (authCloseBtn) authCloseBtn.addEventListener('click', closeAuthModal);

  // Phone form submit → login direct
  if (phoneForm) {
    phoneForm.addEventListener('submit', function(e) {
      e.preventDefault();
      var phone = authPhone.value.trim();
      if (!phone || phone.length < 8) {
        showToast('Numéro invalide (min 8 chiffres).', true);
        return;
      }
      setBtnLoading('btnLoginSubmit', true);

      fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ phone: phone })
      })
      .then(function(r) { return r.json(); })
      .then(function(res) {
        setBtnLoading('btnLoginSubmit', false);
        if (res.success) {
          isLoggedIn = true;
          hasPaid = res.data.has_paid;
          closeAuthModal();
          showToast('Connecté !');
          location.reload();
        } else {
          showToast(res.error || 'Erreur.', true);
        }
      })
      .catch(function() {
        setBtnLoading('btnLoginSubmit', false);
        showToast('Erreur réseau.', true);
      });
    });
  }

  // Phone input formatting
  if (authPhone) {
    authPhone.addEventListener('input', function() {
      this.value = this.value.replace(/[^0-9+\-\s]/g, '');
    });
  }

  // Logout buttons
  function doLogout() {
    fetch('/api/auth/logout', { method: 'POST' })
      .then(function() {
        isLoggedIn = false;
        hasPaid = false;
        location.reload();
      })
      .catch(function() {
        location.reload();
      });
  }

  document.querySelectorAll('#btnLogout, #btnLogoutMobile').forEach(function(btn) {
    if (btn) btn.addEventListener('click', doLogout);
  });

  // ═══════════════════════════════════════════════════════════════════════
  //  PAYMENT FLOW
  // ═══════════════════════════════════════════════════════════════════════

  // Payment success check (redirected back from MaxelPay)
  function checkPaymentSuccess() {
    var params = new URLSearchParams(window.location.search);
    if (params.get('payment') === 'success') {
      window.history.replaceState({}, document.title, window.location.pathname);
      showToast('Paiement en cours de verification...');
      startPaymentPolling();
    }
  }

  function openPaymentModal() {
    if (!isLoggedIn) {
      showToast('Connectez-vous d\'abord.', true);
      openAuthModal();
      return;
    }
    paymentLoading.style.display = '';
    paymentDetails.style.display = 'none';
    paymentStatusDisplay.innerHTML = '<span class="payment-status-pending">⏳ Redirection vers le paiement...</span>';
    paymentModal.classList.add('active');
    document.body.style.overflow = 'hidden';
    createPayment();
  }

  function closePaymentModal() {
    if (paymentPollTimer) clearInterval(paymentPollTimer);
    paymentPollTimer = null;
    paymentModal.classList.remove('active');
    document.body.style.overflow = '';
  }

  var paymentBackdrop = paymentModal.querySelector('.modal-backdrop');
  if (paymentBackdrop) paymentBackdrop.addEventListener('click', closePaymentModal);
  var paymentCloseBtn = paymentModal.querySelector('.modal-close');
  if (paymentCloseBtn) paymentCloseBtn.addEventListener('click', closePaymentModal);

  function createPayment() {
    fetch('/api/payment/create', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    })
    .then(function(r) { return r.json(); })
    .then(function(res) {
      if (res.success) {
        var data = res.data;
        if (data.checkout_url) {
          window.location.href = data.checkout_url;
        } else {
          paymentLoading.innerHTML = '<p style="color:#e74c3c">Erreur: URL de paiement non disponible.</p>';
        }
      } else {
        var errMsg = res.error || 'Erreur creation paiement.';
        paymentLoading.innerHTML = '<p style="color:#e74c3c">' + errMsg + '</p>';
        console.error('[GoForAI Payment]', errMsg);
      }
    })
    .catch(function() {
      paymentLoading.innerHTML = '<p style="color:#e74c3c">Erreur reseau. Reessayez.</p>';
    });
  }

  function startPaymentPolling() {
    var attempts = 0;
    var maxAttempts = 120; // 10 minutes
    if (paymentPollTimer) clearInterval(paymentPollTimer);
    paymentPollTimer = setInterval(function() {
      attempts++;
      if (attempts > maxAttempts) {
        clearInterval(paymentPollTimer);
        paymentPollTimer = null;
        paymentStatusDisplay.innerHTML = '<span class="payment-status-expired">⏰ Délai expiré. Rechargez la page.</span>';
        return;
      }
      fetch('/api/payment/status')
        .then(function(r) { return r.json(); })
        .then(function(res) {
          if (res.success && res.data.paid) {
            clearInterval(paymentPollTimer);
            paymentPollTimer = null;
            paymentStatusDisplay.innerHTML = '<span class="payment-status-confirmed">✅ Paiement confirmé ! Redirection...</span>';
            setTimeout(function() { location.reload(); }, 2000);
          }
        })
        .catch(function() {});
    }, 5000);
  }

  // Unlock buttons
  document.querySelectorAll('#btnUnlockAll, .unlock-trigger').forEach(function(btn) {
    if (btn) btn.addEventListener('click', function(e) {
      e.preventDefault();
      e.stopPropagation();
      openPaymentModal();
    });
  });

  function setBtnLoading(btnId, loading) {
    var btn = document.getElementById(btnId);
    if (!btn) return;
    var textEl = btn.querySelector('.btn-text');
    var loaderEl = btn.querySelector('.btn-loader');
    btn.disabled = loading;
    if (textEl) textEl.style.display = loading ? 'none' : '';
    if (loaderEl) loaderEl.style.display = loading ? 'inline-block' : 'none';
  }

  checkPaymentSuccess();

})();

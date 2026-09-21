/*
 * JKC Supermarket — interface behaviour. Plain JavaScript, no framework.
 *
 * Everything is driven by data attributes so templates stay declarative:
 *
 *   data-tabs / data-tab / data-tab-panel   tabbed content (data-tabs-hash keeps #tab in the URL)
 *   data-filter-group / data-filter / data-filter-item / data-filter-empty
 *                                          client-side filter tabs over a list
 *   data-add-to-cart                        <form> posts via fetch, shows toast + fly-to-cart
 *   data-confirm="Question?"                on a <form>, submit button or <a>; opens a confirm dialog
 *   data-confirm-title / data-confirm-ok    optional dialog title / confirm button text
 *   data-loading-text="Placing order…"      label while a submit button is busy
 *   data-no-loader                          on a <form>, skip the button spinner/progress bar
 *   data-post-url                           button that POSTs to the URL, then reloads
 *   data-post-redirect="/somewhere/"        …or goes to this URL instead of reloading
 *   data-qty (+ data-qty-dec / data-qty-inc) quantity stepper; data-qty-autosubmit submits on change
 *   data-password-toggle                    show/hide the password input in the same wrapper
 *   data-fill="Harare" data-fill-target="id_delivery_city"   click to fill an input
 *   data-lightbox                           click an <img> to view it enlarged
 *   data-count-to="500" data-count-suffix="+"  count-up number when scrolled into view
 *   data-reveal-stagger="80"                children fade up one after another; or class="reveal"
 *   data-dropdown / data-dropdown-toggle     header account menu
 */
(function () {
  'use strict';

  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => Array.from(root.querySelectorAll(selector));

  function getCookie(name) {
    const match = document.cookie.split(';').map((c) => c.trim()).find((c) => c.startsWith(name + '='));
    return match ? decodeURIComponent(match.slice(name.length + 1)) : null;
  }

  function csrfToken() {
    const meta = $('meta[name="csrf-token"]');
    return (meta && meta.content) || getCookie('csrftoken') || '';
  }

  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  function restartAnimation(el, className) {
    el.classList.remove(className);
    void el.offsetWidth; // force reflow so the animation plays again
    el.classList.add(className);
  }

  /* ------------------------------------------------------------ loaders */

  function hidePreloader() {
    const el = $('#preloader');
    if (!el) return;
    el.classList.add('is-hidden');
    try { sessionStorage.setItem('jkc-preloaded', '1'); } catch (e) { /* storage blocked */ }
    setTimeout(() => el.remove(), 600);
  }

  const progress = {
    get el() { return $('#page-progress'); },
    start() {
      const el = this.el;
      if (!el) return;
      el.classList.remove('is-done');
      void el.offsetWidth;
      el.classList.add('is-loading');
    },
    done() {
      const el = this.el;
      if (!el || !el.classList.contains('is-loading')) return;
      el.classList.remove('is-loading');
      el.classList.add('is-done');
    },
  };

  function setButtonLoading(btn, on) {
    if (!btn) return;
    if (on) {
      if (btn.dataset.busy === '1') return;
      btn.dataset.busy = '1';
      btn.dataset.originalHtml = btn.innerHTML;
      btn.style.minWidth = btn.offsetWidth + 'px';
      const text = btn.dataset.loadingText !== undefined ? btn.dataset.loadingText : btn.textContent.trim();
      btn.innerHTML = '<span class="spinner" aria-hidden="true"></span>' +
        (text ? '<span>' + escapeHtml(text) + '</span>' : '<span class="sr-only">Loading</span>');
      btn.setAttribute('aria-busy', 'true');
      if ('disabled' in btn) btn.disabled = true;
      else btn.classList.add('pointer-events-none', 'opacity-70');
    } else if (btn.dataset.busy === '1') {
      btn.innerHTML = btn.dataset.originalHtml;
      btn.style.minWidth = '';
      btn.removeAttribute('aria-busy');
      if ('disabled' in btn) btn.disabled = false;
      btn.classList.remove('pointer-events-none', 'opacity-70');
      delete btn.dataset.busy;
      delete btn.dataset.originalHtml;
    }
  }

  function resetBusyButtons() {
    $$('[data-busy="1"]').forEach((btn) => setButtonLoading(btn, false));
    $$('.qty.is-busy').forEach((wrap) => wrap.classList.remove('is-busy'));
  }

  /* ------------------------------------------------------------- toasts */

  const TOAST_ICONS = {
    success: 'fa-circle-check',
    error: 'fa-circle-exclamation',
    warning: 'fa-triangle-exclamation',
    info: 'fa-circle-info',
  };

  function dismissToast(el) {
    if (el.classList.contains('is-leaving')) return;
    el.classList.add('is-leaving');
    setTimeout(() => el.remove(), 300);
  }

  function armToast(el, duration) {
    const bar = $('.toast-progress', el);
    let remaining = duration;
    let startedAt = Date.now();
    let timer = setTimeout(() => dismissToast(el), remaining);
    if (bar) bar.style.animationDuration = duration + 'ms';

    $('.toast-close', el)?.addEventListener('click', () => dismissToast(el));
    el.addEventListener('mouseenter', () => {
      clearTimeout(timer);
      remaining -= Date.now() - startedAt;
      if (bar) bar.style.animationPlayState = 'paused';
    });
    el.addEventListener('mouseleave', () => {
      startedAt = Date.now();
      timer = setTimeout(() => dismissToast(el), Math.max(remaining, 800));
      if (bar) bar.style.animationPlayState = 'running';
    });
  }

  function showToast(message, type = 'info', duration = 5000) {
    if (type === 'danger') type = 'error';
    let root = $('#toast-root');
    if (!root) {
      root = document.createElement('div');
      root.id = 'toast-root';
      document.body.appendChild(root);
    }
    const el = document.createElement('div');
    el.className = 'toast toast-' + type;
    el.setAttribute('role', type === 'error' ? 'alert' : 'status');
    el.innerHTML =
      '<span class="toast-icon"><i class="fas ' + (TOAST_ICONS[type] || TOAST_ICONS.info) + '"></i></span>' +
      '<p class="toast-message"></p>' +
      '<button type="button" class="toast-close" aria-label="Dismiss"><i class="fas fa-xmark"></i></button>' +
      '<span class="toast-progress"></span>';
    $('.toast-message', el).textContent = message;
    root.appendChild(el);
    armToast(el, duration);
    return el;
  }

  /* ------------------------------------------------------ confirm dialog */

  function confirmDialog({ title, message, okText, tone }) {
    return new Promise((resolve) => {
      const danger = tone !== 'primary';
      const backdrop = document.createElement('div');
      backdrop.className = 'modal-backdrop';
      backdrop.innerHTML =
        '<div class="modal-panel" role="alertdialog" aria-modal="true" aria-labelledby="confirm-title" aria-describedby="confirm-message">' +
          '<div class="flex items-start gap-4">' +
            '<span class="grid size-12 shrink-0 place-items-center rounded-full ' + (danger ? 'bg-rose-100 text-rose-600' : 'bg-brand-100 text-brand-600') + ' animate-wiggle">' +
              '<i class="fas ' + (danger ? 'fa-triangle-exclamation' : 'fa-circle-question') + ' text-lg"></i>' +
            '</span>' +
            '<div class="min-w-0">' +
              '<h2 id="confirm-title" class="text-lg font-bold text-slate-900"></h2>' +
              '<p id="confirm-message" class="mt-1 text-sm text-slate-500"></p>' +
            '</div>' +
          '</div>' +
          '<div class="mt-6 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">' +
            '<button type="button" class="btn btn-secondary" data-cancel>Cancel</button>' +
            '<button type="button" class="btn ' + (danger ? 'btn-danger' : 'btn-primary') + '" data-ok></button>' +
          '</div>' +
        '</div>';
      $('#confirm-title', backdrop).textContent = title || 'Are you sure?';
      $('#confirm-message', backdrop).textContent = message || '';
      $('[data-ok]', backdrop).textContent = okText || 'Yes, continue';

      const previousFocus = document.activeElement;
      const close = (result) => {
        document.removeEventListener('keydown', onKey);
        backdrop.classList.add('is-leaving');
        setTimeout(() => backdrop.remove(), 200);
        if (previousFocus && previousFocus.focus) previousFocus.focus();
        resolve(result);
      };
      const onKey = (e) => {
        if (e.key === 'Escape') close(false);
      };
      backdrop.addEventListener('click', (e) => {
        if (e.target === backdrop || e.target.closest('[data-cancel]')) close(false);
        else if (e.target.closest('[data-ok]')) close(true);
      });
      document.addEventListener('keydown', onKey);
      document.body.appendChild(backdrop);
      $('[data-ok]', backdrop).focus();
    });
  }

  function confirmOptions(el, fallbackEl) {
    const src = el.dataset.confirm !== undefined ? el : fallbackEl;
    return {
      title: src.dataset.confirmTitle,
      message: src.dataset.confirm,
      okText: src.dataset.confirmOk,
      tone: src.dataset.confirmTone,
    };
  }

  /* ------------------------------------------------------------- header */

  function initHeader() {
    const header = $('.site-header');
    const backToTop = $('.back-to-top');
    let ticking = false;
    const update = () => {
      const y = window.scrollY;
      header?.classList.toggle('is-scrolled', y > 8);
      backToTop?.classList.toggle('is-visible', y > 480);
      ticking = false;
    };
    window.addEventListener('scroll', () => {
      if (!ticking) {
        requestAnimationFrame(update);
        ticking = true;
      }
    }, { passive: true });
    update();
    backToTop?.addEventListener('click', () => window.scrollTo({ top: 0, behavior: reduceMotion ? 'auto' : 'smooth' }));

    const toggle = $('[data-mobile-toggle]');
    const menu = $('[data-mobile-menu]');
    if (toggle && menu) {
      menu.inert = true;
      toggle.addEventListener('click', () => {
        const open = menu.classList.toggle('is-open');
        menu.inert = !open;
        toggle.classList.toggle('is-open', open);
        toggle.setAttribute('aria-expanded', String(open));
        toggle.setAttribute('aria-label', open ? 'Close menu' : 'Open menu');
      });
    }

    const closeDropdowns = (except) => {
      $$('[data-dropdown].is-open').forEach((dd) => {
        if (dd === except) return;
        dd.classList.remove('is-open');
        $('[data-dropdown-toggle]', dd)?.setAttribute('aria-expanded', 'false');
      });
    };
    $$('[data-dropdown]').forEach((dd) => {
      const btn = $('[data-dropdown-toggle]', dd);
      btn?.addEventListener('click', (e) => {
        e.stopPropagation();
        closeDropdowns(dd);
        const open = dd.classList.toggle('is-open');
        btn.setAttribute('aria-expanded', String(open));
      });
    });
    document.addEventListener('click', (e) => {
      if (!e.target.closest('[data-dropdown]')) closeDropdowns();
    });
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') closeDropdowns();
    });
  }

  /* --------------------------------------------------------------- tabs */

  function activeTab(list) {
    return $$(':scope > .tab', list).find((t) => t.getAttribute('aria-selected') === 'true' || t.classList.contains('is-active'));
  }

  function moveIndicator(list) {
    if (!list || !(list.classList.contains('tabs') || list.classList.contains('tabs-line'))) return;
    const active = activeTab(list);
    let indicator = $(':scope > .tab-indicator', list);
    if (!active || active.offsetParent === null) {
      if (indicator) indicator.style.opacity = '0';
      return;
    }
    if (!indicator) {
      indicator = document.createElement('span');
      indicator.className = 'tab-indicator';
      indicator.setAttribute('aria-hidden', 'true');
      indicator.style.transition = 'none';
      list.prepend(indicator);
      list.classList.add('has-indicator');
      requestAnimationFrame(() => requestAnimationFrame(() => { indicator.style.transition = ''; }));
    }
    indicator.style.opacity = '1';
    indicator.style.width = active.offsetWidth + 'px';
    // A wrapped strip puts its tabs on more than one row, so the pill has to
    // follow the active tab down as well as across. The underline variant
    // (.tabs-line) keeps its own height and stays on the bottom edge.
    if (list.classList.contains('tabs')) {
      indicator.style.height = active.offsetHeight + 'px';
      indicator.style.transform = 'translate(' + active.offsetLeft + 'px, ' + active.offsetTop + 'px)';
    } else {
      indicator.style.transform = 'translateX(' + active.offsetLeft + 'px)';
    }
  }

  function refreshIndicators() {
    $$('.tabs, .tabs-line').forEach(moveIndicator);
  }

  // Link tabs reload the page with the strip scrolled back to its start. On a
  // phone that can leave the active tab, the only sign of which filter is on,
  // out of sight. Kept out of the resize path: mobile browsers fire resize
  // whenever the URL bar hides, which would undo a strip the user had swiped.
  function revealActiveTab(list) {
    const active = activeTab(list);
    if (!active || active.offsetParent === null) return;
    const start = active.offsetLeft;
    const end = start + active.offsetWidth;
    if (start >= list.scrollLeft && end <= list.scrollLeft + list.clientWidth) return;
    list.scrollLeft = Math.max(0, start - (list.clientWidth - active.offsetWidth) / 2);
  }

  function initTabs() {
    $$('[data-tabs]').forEach((root, index) => {
      const own = (el) => el.closest('[data-tabs]') === root;
      const tabs = $$('[data-tab]', root).filter(own);
      const panels = $$('[data-tab-panel]', root).filter(own);
      if (!tabs.length) return;
      const list = tabs[0].parentElement;
      list.setAttribute('role', 'tablist');
      const prefix = root.id || 'tabs' + index;

      tabs.forEach((tab) => {
        tab.setAttribute('role', 'tab');
        tab.id = tab.id || prefix + '-tab-' + tab.dataset.tab;
        tab.setAttribute('aria-controls', prefix + '-panel-' + tab.dataset.tab);
        if (tab.tagName === 'BUTTON' && !tab.hasAttribute('type')) tab.type = 'button';
      });
      panels.forEach((panel) => {
        panel.setAttribute('role', 'tabpanel');
        panel.id = panel.id || prefix + '-panel-' + panel.dataset.tabPanel;
        panel.setAttribute('aria-labelledby', prefix + '-tab-' + panel.dataset.tabPanel);
      });

      const select = (id, { focus = false, animate = true } = {}) => {
        tabs.forEach((tab) => {
          const on = tab.dataset.tab === id;
          tab.setAttribute('aria-selected', String(on));
          tab.tabIndex = on ? 0 : -1;
          if (on && focus) tab.focus();
        });
        panels.forEach((panel) => {
          const on = panel.dataset.tabPanel === id;
          panel.hidden = !on;
          if (on && animate && !reduceMotion) restartAnimation(panel, 'animate-fade-up');
          // Tab bars nested in a panel can only be measured once it is visible.
          if (on) $$('.tabs, .tabs-line', panel).forEach(moveIndicator);
        });
        moveIndicator(list);
        if (root.hasAttribute('data-tabs-hash') && animate) history.replaceState(null, '', '#' + id);
      };

      tabs.forEach((tab, i) => {
        tab.addEventListener('click', (e) => {
          e.preventDefault();
          select(tab.dataset.tab);
        });
        tab.addEventListener('keydown', (e) => {
          const step = { ArrowRight: 1, ArrowDown: 1, ArrowLeft: -1, ArrowUp: -1 }[e.key];
          if (e.key === 'Home' || e.key === 'End' || step) {
            e.preventDefault();
            const next = e.key === 'Home' ? 0 : e.key === 'End' ? tabs.length - 1 : (i + step + tabs.length) % tabs.length;
            select(tabs[next].dataset.tab, { focus: true });
          }
        });
      });

      // Initial tab: one with form errors > URL hash > aria-selected > first.
      let initial = (tabs.find((t) => t.getAttribute('aria-selected') === 'true') || tabs[0]).dataset.tab;
      const hash = decodeURIComponent(location.hash.slice(1));
      if (hash && tabs.some((t) => t.dataset.tab === hash)) initial = hash;
      const errorPanel = panels.find((p) => p.querySelector('.field-error, .is-invalid'));
      if (errorPanel) initial = errorPanel.dataset.tabPanel;
      select(initial, { animate: false });
    });

    // Link tabs (server-side filters): slide the indicator before navigating.
    $$('.tabs > a.tab, .tabs-line > a.tab').forEach((link) => {
      link.addEventListener('click', (e) => {
        if (e.metaKey || e.ctrlKey || e.shiftKey) return;
        $$(':scope > .tab', link.parentElement).forEach((t) => t.classList.toggle('is-active', t === link));
        moveIndicator(link.parentElement);
      });
    });

    const revealActiveTabs = () => $$('.tabs, .tabs-line').forEach(revealActiveTab);
    refreshIndicators();
    revealActiveTabs();
    let resizeTimer;
    window.addEventListener('resize', () => {
      clearTimeout(resizeTimer);
      resizeTimer = setTimeout(refreshIndicators, 100);
    });
    // Tab widths change once the web font loads, so both are measured again.
    if (document.fonts && document.fonts.ready) {
      document.fonts.ready.then(() => {
        refreshIndicators();
        revealActiveTabs();
      });
    }
  }

  /* ----------------------------------------------------- filter tabs */

  function initFilters() {
    $$('[data-filter-group]').forEach((group) => {
      const buttons = $$('[data-filter]', group);
      const items = $$('[data-filter-item]', group);
      const empty = $('[data-filter-empty]', group);
      const matches = (item, key) => key === 'all' || item.dataset.filterItem.split(/\s+/).includes(key);

      buttons.forEach((btn) => {
        if (btn.tagName === 'BUTTON' && !btn.hasAttribute('type')) btn.type = 'button';
        const count = $('.tab-count', btn);
        if (count) count.textContent = items.filter((item) => matches(item, btn.dataset.filter)).length;
      });

      const apply = (key, animate) => {
        buttons.forEach((btn) => {
          const on = btn.dataset.filter === key;
          btn.classList.toggle('is-active', on);
          btn.setAttribute('aria-pressed', String(on));
        });
        let shown = 0;
        items.forEach((item) => {
          const on = matches(item, key);
          item.hidden = !on;
          if (on && animate && !reduceMotion) {
            item.style.animationDelay = Math.min(shown * 40, 400) + 'ms';
            restartAnimation(item, 'animate-fade-up');
          }
          if (on) shown += 1;
        });
        if (empty) empty.hidden = shown > 0;
        if (buttons[0]) moveIndicator(buttons[0].parentElement);
      };

      buttons.forEach((btn) => btn.addEventListener('click', () => apply(btn.dataset.filter, true)));
      const initial = buttons.find((b) => b.classList.contains('is-active'));
      apply(initial ? initial.dataset.filter : 'all', false);
    });
  }

  /* --------------------------------------------------------------- cart */

  function setCartCount(count) {
    $$('[data-cart-count]').forEach((badge) => {
      badge.textContent = count || 0;
      badge.hidden = !(count > 0);
    });
  }

  function bumpCart() {
    $$('[data-cart-count]').forEach((badge) => restartAnimation(badge, 'animate-bump'));
  }

  function flyToCart(fromEl) {
    const target = $$('[data-cart-icon]').find((el) => el.offsetParent !== null);
    if (!fromEl || !target || reduceMotion || !fromEl.animate) {
      bumpCart();
      return;
    }
    const a = fromEl.getBoundingClientRect();
    const b = target.getBoundingClientRect();
    const dot = document.createElement('div');
    dot.className = 'fly-dot';
    dot.innerHTML = '<i class="fas fa-basket-shopping"></i>';
    document.body.appendChild(dot);
    const sx = a.left + a.width / 2 - 16;
    const sy = a.top + a.height / 2 - 16;
    const ex = b.left + b.width / 2 - 16;
    const ey = b.top + b.height / 2 - 16;
    const anim = dot.animate([
      { transform: 'translate(' + sx + 'px,' + sy + 'px) scale(0.6)', opacity: 0 },
      { transform: 'translate(' + sx + 'px,' + (sy - 10) + 'px) scale(1.1)', opacity: 1, offset: 0.15 },
      { transform: 'translate(' + (sx + ex) / 2 + 'px,' + (Math.min(sy, ey) - 90) + 'px) scale(1)', opacity: 1, offset: 0.55 },
      { transform: 'translate(' + ex + 'px,' + ey + 'px) scale(0.35)', opacity: 0.4 },
    ], { duration: 800, easing: 'cubic-bezier(0.45, 0, 0.55, 1)' });
    anim.onfinish = () => {
      dot.remove();
      bumpCart();
    };
  }

  function flashAdded(btn) {
    if (!btn) return;
    const original = btn.innerHTML;
    const hasText = btn.textContent.trim().length > 0;
    btn.innerHTML = '<i class="fas fa-check animate-pop"></i>' + (hasText ? '<span>Added</span>' : '');
    btn.classList.add('!bg-brand-500');
    setTimeout(() => {
      btn.innerHTML = original;
      btn.classList.remove('!bg-brand-500');
    }, 1400);
  }

  async function submitAddToCart(form, submitter) {
    const btn = submitter || $('[type="submit"]', form);
    setButtonLoading(btn, true);
    let added = false;
    try {
      const response = await fetch(form.action, {
        method: 'POST',
        body: new FormData(form),
        credentials: 'same-origin',
        headers: { 'X-CSRFToken': csrfToken(), 'X-Requested-With': 'XMLHttpRequest' },
      });
      const data = await response.json().catch(() => ({ success: false }));
      if (data.success) {
        added = true;
        if (typeof data.count === 'number') setCartCount(data.count);
        showToast(data.message || 'Added to your cart', 'success', 3500);
        flyToCart(btn);
      } else {
        showToast(data.message || 'Could not add this item to your cart', 'error');
      }
    } catch (err) {
      showToast('Network problem, please try again', 'error');
    } finally {
      setButtonLoading(btn, false);
      if (added) flashAdded(btn);
    }
  }

  /* -------------------------------------------------------------- forms */

  const PHONE_RE = /^(\+?263|0)\d{9}$/;

  function fieldErrorFor(input) {
    return input.parentElement.querySelector(':scope > .field-error[data-client]');
  }

  function validatePhones(form) {
    let ok = true;
    $$('input[name*="phone"]', form).forEach((input) => {
      const existing = fieldErrorFor(input);
      if (input.value.trim() && !PHONE_RE.test(input.value.replace(/[\s-]/g, ''))) {
        ok = false;
        input.classList.add('is-invalid');
        if (!existing) {
          const error = document.createElement('p');
          error.className = 'field-error';
          error.dataset.client = '';
          error.innerHTML = '<i class="fas fa-circle-exclamation"></i> Enter a Zimbabwe number, e.g. 0771 234 567 or +263 771 234 567';
          input.insertAdjacentElement('afterend', error);
        }
      } else {
        input.classList.remove('is-invalid');
        existing?.remove();
      }
    });
    if (!ok) {
      const first = $('.is-invalid', form);
      // If the bad field sits in a hidden tab, switch to that tab so the error is visible.
      const panel = first.closest('[data-tab-panel]');
      if (panel && panel.hidden) {
        const root = panel.closest('[data-tabs]');
        const tab = root && $$('[data-tab]', root).find((t) => t.dataset.tab === panel.dataset.tabPanel);
        if (tab) tab.click();
      }
      first.focus();
      restartAnimation(first, 'animate-wiggle');
    }
    return ok;
  }

  function initForms() {
    document.addEventListener('submit', (e) => {
      const form = e.target;
      if (!(form instanceof HTMLFormElement) || e.defaultPrevented) return;
      const submitter = e.submitter && e.submitter.form === form ? e.submitter : null;

      if (!validatePhones(form)) {
        e.preventDefault();
        return;
      }

      const needsConfirm = (submitter && submitter.dataset.confirm !== undefined) || form.dataset.confirm !== undefined;
      if (needsConfirm && !form.dataset.confirmed) {
        e.preventDefault();
        confirmDialog(confirmOptions(submitter || form, form)).then((ok) => {
          if (!ok) return;
          form.dataset.confirmed = '1';
          if (submitter) form.requestSubmit(submitter);
          else form.requestSubmit();
        });
        return;
      }
      delete form.dataset.confirmed;

      if (form.hasAttribute('data-add-to-cart')) {
        e.preventDefault();
        submitAddToCart(form, submitter);
        return;
      }

      if (form.hasAttribute('data-no-loader') || form.target === '_blank') return;
      progress.start();
      const btn = submitter || $$('[type="submit"]', form).find((b) => b.offsetParent !== null);
      // Disable after the browser has collected the form data, so the
      // clicked button's name/value is still submitted.
      setTimeout(() => setButtonLoading(btn, true), 0);
    });

    // Clear a client-side phone error as soon as the user edits the field.
    document.addEventListener('input', (e) => {
      const input = e.target;
      if (input.classList && input.classList.contains('is-invalid')) {
        input.classList.remove('is-invalid');
        fieldErrorFor(input)?.remove();
      }
    });

    $$('[data-password-toggle]').forEach((btn) => {
      btn.addEventListener('click', () => {
        const input = btn.dataset.passwordToggle ? document.getElementById(btn.dataset.passwordToggle) : $('input', btn.parentElement);
        if (!input) return;
        const show = input.type === 'password';
        input.type = show ? 'text' : 'password';
        const icon = $('i', btn);
        if (icon) icon.className = 'fas ' + (show ? 'fa-eye-slash' : 'fa-eye');
        btn.setAttribute('aria-label', show ? 'Hide password' : 'Show password');
      });
    });

    $$('[data-fill]').forEach((chip) => {
      if (chip.tagName === 'BUTTON' && !chip.hasAttribute('type')) chip.type = 'button';
      chip.addEventListener('click', () => {
        const input = document.getElementById(chip.dataset.fillTarget);
        if (!input) return;
        input.value = chip.dataset.fill;
        input.dispatchEvent(new Event('input', { bubbles: true }));
        input.focus();
        $$('[data-fill-target="' + chip.dataset.fillTarget + '"]').forEach((c) => c.classList.toggle('is-active', c === chip));
      });
    });

    $$('[data-qty]').forEach((wrap) => {
      const input = $('input', wrap);
      if (!input) return;
      const min = parseInt(input.min, 10);
      const max = parseInt(input.max, 10);
      const lo = Number.isNaN(min) ? 1 : min;
      const hi = Number.isNaN(max) ? 999 : max;
      let submitTimer;

      const sync = () => {
        const value = parseInt(input.value, 10) || lo;
        const dec = $('[data-qty-dec]', wrap);
        const inc = $('[data-qty-inc]', wrap);
        if (dec) dec.disabled = value <= lo;
        if (inc) inc.disabled = value >= hi;
      };
      const set = (value) => {
        if (value > hi) showToast('Only ' + hi + ' available', 'warning', 3000);
        const clamped = Math.max(lo, Math.min(hi, value));
        if (String(clamped) !== input.value) {
          input.value = clamped;
          restartAnimation(input, 'animate-pop');
          input.dispatchEvent(new Event('change', { bubbles: true }));
        }
        sync();
      };

      $$('[data-qty-dec], [data-qty-inc]', wrap).forEach((btn) => {
        btn.type = 'button';
        btn.addEventListener('click', () => set((parseInt(input.value, 10) || lo) + (btn.hasAttribute('data-qty-inc') ? 1 : -1)));
      });
      input.addEventListener('change', () => {
        const value = parseInt(input.value, 10);
        if (Number.isNaN(value) || value < lo || value > hi) set(Number.isNaN(value) ? lo : value);
        sync();
        if (wrap.hasAttribute('data-qty-autosubmit') && input.form) {
          clearTimeout(submitTimer);
          submitTimer = setTimeout(() => {
            wrap.classList.add('is-busy');
            input.form.requestSubmit();
          }, 700);
        }
      });
      sync();
    });
  }

  /* ----------------------------------------------------- links & actions */

  function initLinks() {
    // Confirm on links, e.g. <a href="…" data-confirm="Cancel this order?">
    document.addEventListener('click', (e) => {
      const link = e.target.closest('a[data-confirm]');
      if (!link || e.defaultPrevented) return;
      e.preventDefault();
      confirmDialog(confirmOptions(link, link)).then((ok) => {
        if (!ok) return;
        progress.start();
        window.location.href = link.href;
      });
    });

    // Buttons that POST and reload, e.g. founder dashboard toggles.
    document.addEventListener('click', async (e) => {
      const btn = e.target.closest('[data-post-url]');
      if (!btn || e.defaultPrevented) return;
      e.preventDefault();
      setButtonLoading(btn, true);
      try {
        const response = await fetch(btn.dataset.postUrl, {
          method: 'POST',
          credentials: 'same-origin',
          headers: { 'X-CSRFToken': csrfToken(), 'X-Requested-With': 'XMLHttpRequest' },
        });
        if (!response.ok) throw new Error('HTTP ' + response.status);
        progress.start();
        if (btn.dataset.postRedirect) window.location.href = btn.dataset.postRedirect;
        else window.location.reload();
      } catch (err) {
        setButtonLoading(btn, false);
        showToast('That did not work, please try again', 'error');
      }
    });

    // Top progress bar for ordinary same-site navigation. Registered last so
    // handlers above can cancel the click first.
    document.addEventListener('click', (e) => {
      const link = e.target.closest('a[href]');
      if (!link || e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
      if ((link.target && link.target !== '_self') || link.hasAttribute('download') || link.hasAttribute('data-no-progress')) return;
      const url = new URL(link.href, window.location.href);
      if (url.origin !== window.location.origin) return;
      if (url.pathname === window.location.pathname && url.search === window.location.search) return;
      progress.start();
    });
  }

  /* ------------------------------------------------------------- images */

  function initImages() {
    $$('.img-frame > img').forEach((img) => {
      const frame = img.parentElement;
      const loaded = () => frame.classList.add('is-loaded');
      const failed = () => frame.classList.add('is-error');
      if (img.complete) {
        if (img.naturalWidth) loaded();
        else if (img.getAttribute('src')) failed();
      } else {
        img.addEventListener('load', loaded, { once: true });
        img.addEventListener('error', failed, { once: true });
      }
    });

    document.addEventListener('click', (e) => {
      const img = e.target.closest('img[data-lightbox]');
      if (!img) return;
      const backdrop = document.createElement('div');
      backdrop.className = 'modal-backdrop cursor-zoom-out';
      backdrop.innerHTML =
        '<button type="button" class="absolute top-4 right-4 grid size-11 place-items-center rounded-full bg-white/90 text-slate-700 shadow-lg transition hover:bg-white" aria-label="Close"><i class="fas fa-xmark text-lg"></i></button>' +
        '<img class="lightbox-img" alt="">';
      const big = $('img', backdrop);
      big.src = img.currentSrc || img.src;
      big.alt = img.alt;
      const close = () => {
        document.removeEventListener('keydown', onKey);
        backdrop.classList.add('is-leaving');
        setTimeout(() => backdrop.remove(), 200);
      };
      const onKey = (ev) => {
        if (ev.key === 'Escape') close();
      };
      backdrop.addEventListener('click', close);
      document.addEventListener('keydown', onKey);
      document.body.appendChild(backdrop);
    });
  }

  /* --------------------------------------------------------- animations */

  function finishReveal(el) {
    el.classList.remove('reveal', 'is-visible');
    el.style.removeProperty('--reveal-delay');
  }

  function initReveal() {
    $$('[data-reveal-stagger]').forEach((group) => {
      const step = parseInt(group.dataset.revealStagger, 10) || 80;
      Array.from(group.children).forEach((child, i) => {
        child.classList.add('reveal');
        child.style.setProperty('--reveal-delay', Math.min(i * step, 640) + 'ms');
      });
    });

    const items = $$('.reveal');
    if (reduceMotion || !('IntersectionObserver' in window)) {
      items.forEach(finishReveal);
      return;
    }
    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        const el = entry.target;
        observer.unobserve(el);
        el.classList.add('is-visible');
        // Drop the reveal transition afterwards so it can't delay hover effects.
        const delay = parseInt(el.style.getPropertyValue('--reveal-delay'), 10) || 0;
        setTimeout(() => finishReveal(el), delay + 750);
      });
    }, { threshold: 0.1, rootMargin: '0px 0px -40px 0px' });
    items.forEach((el) => observer.observe(el));
  }

  function initCounters() {
    const counters = $$('[data-count-to]');
    if (!counters.length || reduceMotion || !('IntersectionObserver' in window)) return;
    const animate = (el) => {
      const target = parseFloat(el.dataset.countTo);
      const suffix = el.dataset.countSuffix || '';
      const duration = 1400;
      const start = performance.now();
      const frame = (now) => {
        const t = Math.min((now - start) / duration, 1);
        const eased = 1 - Math.pow(1 - t, 3);
        el.textContent = Math.round(target * eased).toLocaleString() + suffix;
        if (t < 1) requestAnimationFrame(frame);
      };
      requestAnimationFrame(frame);
    };
    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        observer.unobserve(entry.target);
        animate(entry.target);
      });
    }, { threshold: 0.4 });
    counters.forEach((el) => {
      el.textContent = '0' + (el.dataset.countSuffix || '');
      observer.observe(el);
    });
  }

  /* --------------------------------------------------------------- boot */

  function init() {
    $$('#toast-root .toast').forEach((toast) => armToast(toast, 6000));
    initHeader();
    initTabs();
    initFilters();
    initForms();
    initLinks();
    initImages();
    initReveal();
    initCounters();
    setTimeout(hidePreloader, 1500);
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
  window.addEventListener('load', () => setTimeout(hidePreloader, 150));

  // Coming back via the browser's back button restores a frozen page:
  // clear any spinners and progress bar left from when we navigated away.
  window.addEventListener('pageshow', (e) => {
    if (e.persisted) {
      progress.done();
      resetBusyButtons();
    }
  });
  window.addEventListener('load', () => progress.done());

  // Small public API for page-specific scripts.
  window.JKC = { showToast, confirmDialog, setButtonLoading, setCartCount };
})();

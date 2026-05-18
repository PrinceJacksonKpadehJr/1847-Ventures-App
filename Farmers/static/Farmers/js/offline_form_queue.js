(function () {
  'use strict';

  const DB_NAME = '1847OfflineFormQueue';
  const STORE_NAME = 'requests';
  const DB_VERSION = 1;
  const LOGIN_PATH_FRAGMENT = '/login';
  const PANEL_POSITION_KEY = '1847-offline-queue-position';
  const PANEL_DISMISSED_KEY = '1847-offline-queue-dismissed';
  let dbPromise = null;
  let flushInProgress = false;
  let queuePanelHost = null;
  let queuePanelToggleHost = null;
  const queueObservers = [];

  function isValidPanelPosition(position) {
    return position === 'top-left' || position === 'top-right' || position === 'bottom-left' || position === 'bottom-right';
  }

  function getSavedPanelPosition() {
    const saved = window.localStorage.getItem(PANEL_POSITION_KEY);
    return isValidPanelPosition(saved) ? saved : 'bottom-left';
  }

  function applyPanelPosition(host, position) {
    const resolved = isValidPanelPosition(position) ? position : 'bottom-left';

    host.style.left = '';
    host.style.right = '';
    host.style.top = '';
    host.style.bottom = '';

    if (resolved.indexOf('left') !== -1) {
      host.style.left = '16px';
    } else {
      host.style.right = '16px';
    }

    if (resolved.indexOf('top') !== -1) {
      host.style.top = '16px';
    } else {
      host.style.bottom = '16px';
    }

    return resolved;
  }

  function setPanelPosition(position) {
    const host = ensureQueuePanel();
    const resolved = applyPanelPosition(host, position);
    window.localStorage.setItem(PANEL_POSITION_KEY, resolved);
    syncQueueTogglePosition(resolved);
    return resolved;
  }

  function isPanelDismissed() {
    return window.sessionStorage.getItem(PANEL_DISMISSED_KEY) === '1';
  }

  function setPanelDismissed(isDismissed) {
    if (isDismissed) {
      window.sessionStorage.setItem(PANEL_DISMISSED_KEY, '1');
      return;
    }
    window.sessionStorage.removeItem(PANEL_DISMISSED_KEY);
  }

  function ensureQueueToggleHost() {
    if (queuePanelToggleHost) {
      return queuePanelToggleHost;
    }

    queuePanelToggleHost = document.createElement('div');
    queuePanelToggleHost.id = 'offline-queue-panel-toggle';
    queuePanelToggleHost.style.position = 'fixed';
    queuePanelToggleHost.style.zIndex = '4901';
    queuePanelToggleHost.style.display = 'none';
    syncQueueTogglePosition(getSavedPanelPosition());
    document.body.appendChild(queuePanelToggleHost);
    return queuePanelToggleHost;
  }

  function syncQueueTogglePosition(position) {
    const host = queuePanelToggleHost;
    if (!host) {
      return;
    }

    host.style.left = '';
    host.style.right = '';
    host.style.top = '';
    host.style.bottom = '';

    const resolved = isValidPanelPosition(position) ? position : getSavedPanelPosition();
    if (resolved.indexOf('left') !== -1) {
      host.style.left = '16px';
    } else {
      host.style.right = '16px';
    }

    if (resolved.indexOf('top') !== -1) {
      host.style.top = '16px';
    } else {
      host.style.bottom = '16px';
    }
  }

  function renderQueueToggle(queueCount) {
    const host = ensureQueueToggleHost();
    const shouldShowToggle = queueCount > 0 && isPanelDismissed();
    if (!shouldShowToggle) {
      host.style.display = 'none';
      host.innerHTML = '';
      return;
    }

    host.style.display = 'block';
    host.innerHTML = [
      '<button type="button" id="offline-queue-show" style="border:1px solid rgba(18,58,35,0.22);border-radius:999px;padding:8px 12px;background:#ffffff;color:#123826;font:700 12px/1 Segoe UI, Arial, sans-serif;cursor:pointer;box-shadow:0 8px 18px rgba(0,0,0,0.14);">Show pending actions (', queueCount, ')</button>'
    ].join('');

    const showButton = document.getElementById('offline-queue-show');
    if (showButton) {
      showButton.addEventListener('click', function () {
        setPanelDismissed(false);
        notifyQueueObservers();
      });
    }
  }

  function openDb() {
    if (dbPromise) {
      return dbPromise;
    }

    dbPromise = new Promise(function (resolve, reject) {
      const request = window.indexedDB.open(DB_NAME, DB_VERSION);

      request.onupgradeneeded = function () {
        const db = request.result;
        if (!db.objectStoreNames.contains(STORE_NAME)) {
          db.createObjectStore(STORE_NAME, { keyPath: 'id' });
        }
      };

      request.onsuccess = function () {
        resolve(request.result);
      };

      request.onerror = function () {
        reject(request.error);
      };
    });

    return dbPromise;
  }

  function getStore(mode) {
    return openDb().then(function (db) {
      return db.transaction(STORE_NAME, mode).objectStore(STORE_NAME);
    });
  }

  function storeRequest(mode, operation) {
    return getStore(mode).then(function (store) {
      return new Promise(function (resolve, reject) {
        const request = operation(store);
        request.onsuccess = function () {
          resolve(request.result);
        };
        request.onerror = function () {
          reject(request.error);
        };
      });
    });
  }

  function getAllQueuedRequests() {
    return storeRequest('readonly', function (store) {
      return store.getAll();
    }).then(function (records) {
      return (records || []).sort(function (left, right) {
        return new Date(left.createdAt) - new Date(right.createdAt);
      });
    });
  }

  function subscribe(listener) {
    queueObservers.push(listener);
  }

  function notifyQueueObservers() {
    return getAllQueuedRequests().then(function (queue) {
      queueObservers.forEach(function (listener) {
        listener(queue);
      });
      return queue;
    }).catch(function () {
      return [];
    });
  }

  function putQueuedRequest(record) {
    return storeRequest('readwrite', function (store) {
      return store.put(record);
    }).then(function () {
      return notifyQueueObservers();
    });
  }

  function deleteQueuedRequest(id) {
    return storeRequest('readwrite', function (store) {
      return store.delete(id);
    }).then(function () {
      return notifyQueueObservers();
    });
  }

  function escapeHtml(value) {
    return String(value).replace(/[&<>"']/g, function (char) {
      return {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#39;'
      }[char];
    });
  }

  function formatTime(value) {
    try {
      return new Date(value).toLocaleString();
    } catch (error) {
      return value || '';
    }
  }

  function getRecordLabel(record) {
    return record.formName || record.label || record.url || 'Queued action';
  }

  function getGlobalNoticeHost() {
    let host = document.getElementById('offline-queue-global-notice');
    if (host) {
      return host;
    }

    host = document.createElement('div');
    host.id = 'offline-queue-global-notice';
    host.style.position = 'fixed';
    host.style.right = '16px';
    host.style.bottom = '16px';
    host.style.zIndex = '5000';
    host.style.maxWidth = '380px';
    host.style.width = 'calc(100vw - 32px)';
    document.body.appendChild(host);
    return host;
  }

  function renderGlobalNotice(message, tone) {
    const host = getGlobalNoticeHost();
    if (!message) {
      host.innerHTML = '';
      return;
    }

    const isError = tone === 'error';
    host.innerHTML = [
      '<div style="padding:12px 14px;border-radius:12px;box-shadow:0 10px 24px rgba(0,0,0,0.18);',
      'background:', isError ? '#fff1f1' : '#edf8f0', ';',
      'border:1px solid ', isError ? '#e4aaaa' : '#a7d8b4', ';',
      'color:', isError ? '#7a2121' : '#14552b', ';',
      'font:600 14px/1.45 Segoe UI, Arial, sans-serif;">',
      escapeHtml(message),
      '</div>'
    ].join('');
  }

  function getFormNoticeHost(form) {
    const selector = form.getAttribute('data-offline-notice-target');
    if (selector) {
      return document.querySelector(selector);
    }

    let host = form.querySelector('.offline-queue-form-notice');
    if (host) {
      return host;
    }

    host = document.createElement('div');
    host.className = 'offline-queue-form-notice';
    host.style.marginBottom = '12px';
    form.insertBefore(host, form.firstChild);
    return host;
  }

  function renderFormNotice(form, message, tone) {
    const host = getFormNoticeHost(form);
    if (!message) {
      host.innerHTML = '';
      return;
    }

    const isError = tone === 'error';
    host.innerHTML = '<div style="padding:10px 12px;border-radius:10px;border:1px solid ' +
      (isError ? '#e4aaaa' : '#a7d8b4') +
      ';background:' +
      (isError ? '#fff1f1' : '#edf8f0') +
      ';color:' +
      (isError ? '#7a2121' : '#14552b') +
      ';font:600 13px/1.45 Segoe UI, Arial, sans-serif;">' +
      escapeHtml(message) +
      '</div>';
  }

  function ensureQueuePanel() {
    if (queuePanelHost) {
      return queuePanelHost;
    }

    queuePanelHost = document.createElement('div');
    queuePanelHost.id = 'offline-queue-panel';
    queuePanelHost.style.position = 'fixed';
    queuePanelHost.style.zIndex = '4900';
    queuePanelHost.style.width = 'min(360px, calc(100vw - 32px))';
    queuePanelHost.style.display = 'none';
    applyPanelPosition(queuePanelHost, getSavedPanelPosition());
    document.body.appendChild(queuePanelHost);
    return queuePanelHost;
  }

  function renderQueuePanel(queue) {
    const host = ensureQueuePanel();
    const count = queue.length;

    renderQueueToggle(count);

    if (!count) {
      host.style.display = 'none';
      host.innerHTML = '';
      if (host.parentNode) {
        host.parentNode.removeChild(host);
      }
      queuePanelHost = null;

      if (queuePanelToggleHost) {
        queuePanelToggleHost.style.display = 'none';
        queuePanelToggleHost.innerHTML = '';
        if (queuePanelToggleHost.parentNode) {
          queuePanelToggleHost.parentNode.removeChild(queuePanelToggleHost);
        }
        queuePanelToggleHost = null;
      }
      return;
    }

    if (isPanelDismissed()) {
      host.style.display = 'none';
      host.innerHTML = '';
      return;
    }

    host.style.display = 'block';
    const activePosition = applyPanelPosition(host, getSavedPanelPosition());
    syncQueueTogglePosition(activePosition);
    const rows = queue.map(function (record) {
      return [
        '<div style="padding:10px 0;border-top:1px solid rgba(20,53,35,0.08);">',
        '<div style="display:flex;justify-content:space-between;gap:10px;align-items:flex-start;">',
        '<div style="min-width:0;">',
        '<div style="font-weight:700;color:#123826;font-size:13px;">', escapeHtml(getRecordLabel(record)), '</div>',
        '<div style="font-size:12px;color:#597063;margin-top:4px;">Queued ', escapeHtml(formatTime(record.createdAt)), '</div>',
        '</div>',
        '<button type="button" data-offline-remove="', escapeHtml(record.id), '" style="border:none;background:#fff1f1;color:#a02525;border-radius:999px;padding:6px 10px;cursor:pointer;font-weight:700;font-size:12px;">Cancel</button>',
        '</div>',
        '</div>'
      ].join('');
    }).join('');

    host.innerHTML = [
      '<div style="background:#ffffff;border:1px solid rgba(18,58,35,0.14);border-radius:16px;box-shadow:0 16px 32px rgba(0,0,0,0.16);overflow:hidden;">',
      '<div style="padding:12px 14px;background:linear-gradient(135deg,#edf8f0,#f8fbf8);display:flex;justify-content:space-between;align-items:center;gap:10px;">',
      '<div>',
      '<div style="font:700 14px/1.3 Segoe UI, Arial, sans-serif;color:#123826;">Pending Offline Actions</div>',
      '<div style="font:600 12px/1.4 Segoe UI, Arial, sans-serif;color:#597063;">', count, ' waiting to sync</div>',
      '</div>',
      '<div style="display:flex;align-items:center;gap:6px;">',
      '<button type="button" id="offline-queue-hide" title="Temporarily hide panel" style="border:1px solid #c7d7cd;background:#ffffff;border-radius:8px;padding:4px 8px;color:#123826;font:700 11px/1 Segoe UI, Arial, sans-serif;cursor:pointer;">Hide</button>',
      '<button type="button" data-offline-move="top-left" title="Move to top left" style="border:1px solid ', (activePosition === 'top-left' ? '#16482d' : '#c7d7cd'), ';background:', (activePosition === 'top-left' ? '#dceee2' : '#ffffff'), ';border-radius:8px;padding:4px 6px;color:#123826;font:700 11px/1 Segoe UI, Arial, sans-serif;cursor:pointer;">TL</button>',
      '<button type="button" data-offline-move="top-right" title="Move to top right" style="border:1px solid ', (activePosition === 'top-right' ? '#16482d' : '#c7d7cd'), ';background:', (activePosition === 'top-right' ? '#dceee2' : '#ffffff'), ';border-radius:8px;padding:4px 6px;color:#123826;font:700 11px/1 Segoe UI, Arial, sans-serif;cursor:pointer;">TR</button>',
      '<button type="button" data-offline-move="bottom-left" title="Move to bottom left" style="border:1px solid ', (activePosition === 'bottom-left' ? '#16482d' : '#c7d7cd'), ';background:', (activePosition === 'bottom-left' ? '#dceee2' : '#ffffff'), ';border-radius:8px;padding:4px 6px;color:#123826;font:700 11px/1 Segoe UI, Arial, sans-serif;cursor:pointer;">BL</button>',
      '<button type="button" data-offline-move="bottom-right" title="Move to bottom right" style="border:1px solid ', (activePosition === 'bottom-right' ? '#16482d' : '#c7d7cd'), ';background:', (activePosition === 'bottom-right' ? '#dceee2' : '#ffffff'), ';border-radius:8px;padding:4px 6px;color:#123826;font:700 11px/1 Segoe UI, Arial, sans-serif;cursor:pointer;">BR</button>',
      '<button type="button" id="offline-sync-now" ', (!count || !navigator.onLine ? 'disabled ' : ''), 'style="border:none;border-radius:999px;padding:8px 12px;background:', (!count || !navigator.onLine ? '#d6e2da' : '#16482d'), ';color:#fff;font:700 12px/1 Segoe UI, Arial, sans-serif;cursor:', (!count || !navigator.onLine ? 'default' : 'pointer'), ';">Sync now</button>',
      '</div>',
      '</div>',
      '<div style="padding:0 14px 12px;max-height:220px;overflow:auto;">', rows, '</div>',
      '</div>'
    ].join('');

    const syncButton = document.getElementById('offline-sync-now');
    if (syncButton && count && navigator.onLine) {
      syncButton.addEventListener('click', flushQueue);
    }

    const hideButton = document.getElementById('offline-queue-hide');
    if (hideButton) {
      hideButton.addEventListener('click', function () {
        setPanelDismissed(true);
        notifyQueueObservers();
      });
    }

    host.querySelectorAll('[data-offline-move]').forEach(function (button) {
      button.addEventListener('click', function () {
        setPanelPosition(button.getAttribute('data-offline-move'));
        renderQueuePanel(queue);
      });
    });

    host.querySelectorAll('[data-offline-remove]').forEach(function (button) {
      button.addEventListener('click', function () {
        deleteQueuedRequest(button.getAttribute('data-offline-remove')).then(function () {
          renderGlobalNotice('Queued action removed.', 'success');
        });
      });
    });
  }

  function serializeFormData(formData) {
    const entries = [];
    formData.forEach(function (value, key) {
      if (value instanceof File) {
        if (!value.name && value.size === 0) {
          return;
        }
        entries.push({
          key: key,
          type: 'file',
          file: value,
          filename: value.name,
          mimeType: value.type,
          lastModified: value.lastModified
        });
        return;
      }

      entries.push({ key: key, type: 'text', value: value });
    });
    return entries;
  }

  function deserializeFormData(serializedEntries) {
    const formData = new FormData();
    (serializedEntries || []).forEach(function (entry) {
      if (entry.type === 'file' && entry.file) {
        formData.append(entry.key, entry.file, entry.filename || 'upload.bin');
        return;
      }
      formData.append(entry.key, entry.value == null ? '' : entry.value);
    });
    return formData;
  }

  function setSubmittingState(form, isSubmitting) {
    const submitButtons = form.querySelectorAll('[type="submit"]');
    submitButtons.forEach(function (button) {
      if (!button.hasAttribute('data-offline-original-text')) {
        button.setAttribute('data-offline-original-text', button.textContent);
      }
      button.disabled = isSubmitting;
      button.textContent = isSubmitting ? (button.getAttribute('data-offline-loading-text') || 'Saving...') : button.getAttribute('data-offline-original-text');
    });
  }

  function buildRecord(base) {
    return Object.assign({
      id: 'req-' + Date.now() + '-' + Math.random().toString(36).slice(2),
      createdAt: new Date().toISOString(),
      pageUrl: window.location.pathname + window.location.search,
      method: 'POST',
      payloadType: 'form-data',
      headers: {},
      reloadOnSuccess: true,
      successMessage: 'Saved and synced successfully.',
      queueMessage: 'No network right now. This action was saved offline and will sync automatically.'
    }, base || {});
  }

  function enqueueRecord(record) {
    return putQueuedRequest(record).then(function (queue) {
      return { record: record, queueLength: queue.length };
    });
  }

  function enqueueFormSubmission(form) {
    const formData = new FormData(form);
    const record = buildRecord({
      url: form.getAttribute('action') || window.location.pathname,
      method: (form.getAttribute('method') || 'POST').toUpperCase(),
      payloadType: 'form-data',
      entries: serializeFormData(formData),
      enctype: form.getAttribute('enctype') || 'application/x-www-form-urlencoded',
      formName: form.getAttribute('data-offline-label') || form.getAttribute('aria-label') || form.getAttribute('action') || 'form',
      successMessage: form.getAttribute('data-offline-success-message') || 'Saved and synced successfully.',
      queueMessage: form.getAttribute('data-offline-queue-message') || 'No network right now. This form was saved offline and will sync automatically.',
      reloadOnSuccess: form.getAttribute('data-offline-reload-on-success') !== 'false'
    });

    return enqueueRecord(record);
  }

  function parseJsonResponse(response) {
    const contentType = response.headers.get('content-type') || '';
    if (contentType.indexOf('application/json') === -1) {
      return Promise.resolve(null);
    }
    return response.json().catch(function () { return null; });
  }

  function buildFetchOptions(record) {
    const headers = Object.assign({ 'X-Requested-With': 'XMLHttpRequest' }, record.headers || {});
    let body = null;

    if (!record.payloadType || record.payloadType === 'form-data') {
      body = deserializeFormData(record.entries);
    } else if (record.payloadType === 'json') {
      headers['Content-Type'] = 'application/json';
      body = record.jsonBody || '{}';
    } else if (record.payloadType === 'none') {
      body = null;
    }

    return {
      method: record.method || 'POST',
      body: body,
      headers: headers,
      credentials: 'same-origin'
    };
  }

  function submitSerializedRequest(record) {
    return fetch(record.url, buildFetchOptions(record)).then(function (response) {
      return parseJsonResponse(response).then(function (json) {
        return { response: response, json: json };
      });
    });
  }

  function responseMeansSuccess(result) {
    const response = result.response;
    const json = result.json;

    if (json && json.ok === true) {
      return true;
    }

    if (json && json.ok === false) {
      return false;
    }

    if (response.redirected) {
      try {
        const redirectedPath = new URL(response.url, window.location.origin).pathname;
        if (redirectedPath.indexOf(LOGIN_PATH_FRAGMENT) !== -1) {
          return false;
        }
      } catch (error) {
        return false;
      }
      return true;
    }

    return response.ok;
  }

  function clearValidationErrors(form) {
    Array.from(form.elements || []).forEach(function (field) {
      if (field.setCustomValidity) {
        field.setCustomValidity('');
      }
    });
  }

  function showValidationError(form, result) {
    const json = result.json || {};
    if (json.message) {
      renderFormNotice(form, json.message, 'error');
    }
    const errors = json.errors || {};
    Object.keys(errors).forEach(function (fieldName) {
      const field = form.elements.namedItem(fieldName);
      if (field && field.setCustomValidity) {
        field.setCustomValidity((errors[fieldName] || []).join(' '));
      }
    });
    const firstErrorFieldName = Object.keys(errors)[0];
    const firstErrorField = firstErrorFieldName ? form.elements.namedItem(firstErrorFieldName) : null;
    if (firstErrorField && firstErrorField.reportValidity) {
      firstErrorField.reportValidity();
    }
  }

  function replaceDocumentWithHtml(htmlText) {
    document.open();
    document.write(htmlText);
    document.close();
  }

  function handleImmediateSubmission(form) {
    clearValidationErrors(form);
    if (form.reportValidity && !form.reportValidity()) {
      return Promise.resolve(false);
    }

    setSubmittingState(form, true);

    if (!navigator.onLine) {
      return enqueueFormSubmission(form).then(function (queued) {
        renderFormNotice(form, (form.getAttribute('data-offline-queue-message') || 'Saved offline and waiting for connection.') + ' Pending queue: ' + queued.queueLength + '.', 'success');
        renderGlobalNotice(queued.record.formName + ' saved offline. It will sync automatically when the network returns.', 'success');
        if (form.getAttribute('data-offline-reset-on-queue') === 'true') {
          form.reset();
        }
        return true;
      }).finally(function () {
        setSubmittingState(form, false);
      });
    }

    const immediateRecord = buildRecord({
      url: form.getAttribute('action') || window.location.pathname,
      method: (form.getAttribute('method') || 'POST').toUpperCase(),
      payloadType: 'form-data',
      entries: serializeFormData(new FormData(form))
    });

    return submitSerializedRequest(immediateRecord).then(function (result) {
      if (responseMeansSuccess(result)) {
        const successMessage = (result.json && result.json.message) || form.getAttribute('data-offline-success-message') || 'Saved successfully.';
        renderFormNotice(form, successMessage, 'success');
        if (result.response.redirected) {
          window.location.assign(result.response.url);
          return true;
        }
        if (result.json && result.json.reload) {
          window.location.reload();
          return true;
        }
        return true;
      }

      if (result.json && result.json.errors) {
        showValidationError(form, result);
        return false;
      }

      return result.response.text().then(function (html) {
        replaceDocumentWithHtml(html);
        return false;
      });
    }).catch(function () {
      return enqueueFormSubmission(form).then(function (queued) {
        renderFormNotice(form, queued.record.queueMessage + ' Pending queue: ' + queued.queueLength + '.', 'success');
        renderGlobalNotice(queued.record.formName + ' saved offline after a network interruption.', 'success');
        if (form.getAttribute('data-offline-reset-on-queue') === 'true') {
          form.reset();
        }
        return true;
      });
    }).finally(function () {
      setSubmittingState(form, false);
    });
  }

  function runAction(options) {
    const record = buildRecord(options || {});

    if (!navigator.onLine) {
      return enqueueRecord(record).then(function (queued) {
        renderGlobalNotice((record.queueMessage || 'Action saved offline.') + ' Pending queue: ' + queued.queueLength + '.', 'success');
        return { queued: true, record: queued.record };
      });
    }

    return submitSerializedRequest(record).then(function (result) {
      if (!responseMeansSuccess(result)) {
        const error = new Error((result.json && (result.json.message || result.json.error)) || 'Request failed.');
        error.result = result;
        throw error;
      }
      if (typeof record.onImmediateSuccess === 'function') {
        record.onImmediateSuccess(result);
      }
      return { queued: false, result: result };
    }).catch(function (error) {
      if (error && error.result && error.result.json && (error.result.json.errors || error.result.json.error)) {
        if (typeof record.onImmediateError === 'function') {
          record.onImmediateError(error);
        }
        throw error;
      }

      return enqueueRecord(record).then(function (queued) {
        renderGlobalNotice((record.queueMessage || 'Action saved offline.') + ' Pending queue: ' + queued.queueLength + '.', 'success');
        return { queued: true, record: queued.record };
      });
    });
  }

  function runFormDataAction(options) {
    return runAction(Object.assign({}, options, {
      payloadType: 'form-data',
      entries: serializeFormData(options.formData || new FormData())
    }));
  }

  function runJsonAction(options) {
    return runAction(Object.assign({}, options, {
      payloadType: 'json',
      jsonBody: JSON.stringify(options.json || {})
    }));
  }

  function flushQueue() {
    if (flushInProgress || !navigator.onLine) {
      return Promise.resolve();
    }

    flushInProgress = true;

    return getAllQueuedRequests().then(function (queue) {
      if (!queue.length) {
        return null;
      }

      renderGlobalNotice('Connection restored. Syncing saved work...', 'success');
      let shouldReload = false;

      return queue.reduce(function (chain, record) {
        return chain.then(function () {
          return submitSerializedRequest(record).then(function (result) {
            if (!responseMeansSuccess(result)) {
              throw new Error((result.json && (result.json.message || result.json.error)) || 'Server did not accept queued submission.');
            }

            shouldReload = shouldReload || (record.reloadOnSuccess && record.pageUrl === (window.location.pathname + window.location.search));
            return deleteQueuedRequest(record.id);
          });
        });
      }, Promise.resolve()).then(function () {
        renderGlobalNotice('Offline submissions synced successfully.', 'success');
        if (shouldReload) {
          window.setTimeout(function () {
            window.location.reload();
          }, 600);
        }
      });
    }).catch(function (error) {
      renderGlobalNotice(error.message || 'Some offline submissions are still waiting to sync.', 'error');
    }).finally(function () {
      flushInProgress = false;
      notifyQueueObservers();
    });
  }

  function wireOfflineForms() {
    const forms = Array.from(document.querySelectorAll('form')).filter(function (form) {
      const method = (form.getAttribute('method') || '').toLowerCase();
      if (method !== 'post') {
        return false;
      }
      if (form.getAttribute('data-offline-queue') === 'false') {
        return false;
      }
      if (form.querySelector('input[type="password"]')) {
        return false;
      }
      if (form.querySelector('input[name="otp_code"]')) {
        return false;
      }
      return true;
    });

    forms.forEach(function (form) {
      form.addEventListener('submit', function (event) {
        event.preventDefault();
        handleImmediateSubmission(form);
      });
    });
  }

  function initialize() {
    subscribe(renderQueuePanel);
    wireOfflineForms();
    notifyQueueObservers().then(function (queue) {
      if (queue.length) {
        renderGlobalNotice(queue.length + ' offline action(s) are waiting to sync.', 'success');
      }
      if (navigator.onLine) {
        flushQueue();
      }
    }).catch(function () {
      renderGlobalNotice('Offline storage is unavailable in this browser session.', 'error');
    });
  }

  window.OfflineActionQueue = {
    runAction: runAction,
    runFormDataAction: runFormDataAction,
    runJsonAction: runJsonAction,
    flushQueue: flushQueue,
    getAllQueuedRequests: getAllQueuedRequests,
    cancelQueuedRequest: deleteQueuedRequest,
    subscribe: subscribe,
    refresh: notifyQueueObservers
  };

  window.addEventListener('online', flushQueue);
  window.addEventListener('offline', function () {
    renderGlobalNotice('You are offline. Supported actions will be saved on this device and sent automatically later.', 'error');
  });
  window.addEventListener('load', initialize);
})();

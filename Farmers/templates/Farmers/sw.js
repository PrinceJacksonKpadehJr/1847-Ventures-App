/* 1847 Ventures — Service Worker */
const CACHE_NAME = '1847-ventures-v4';
const PRECACHE_URLS = [
  '/',
  '/login/',
  '/static/Farmers/pwa/manifest.json',
  '/static/Farmers/homepage/logo-1847.png',
  '/static/Farmers/homepage/nimba-clusters.jpg',
  '/static/Farmers/homepage/agroforestry.jpg',
  '/static/Farmers/homepage/gari-sacks.jpg',
  '/static/Farmers/homepage/happy-farmers.jpg',
  '/static/Farmers/pwa/icons/icon-192-maskable.png',
  '/static/Farmers/pwa/icons/icon-512-maskable.png',
  '/static/Farmers/pwa/icons/icon-512-any.png',
  '/static/Farmers/pwa/icons/apple-touch-icon-180.png',
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => cache.addAll(PRECACHE_URLS))
  );
  self.skipWaiting();
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(
        keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k))
      )
    )
  );
  self.clients.claim();
});

self.addEventListener('message', event => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});

self.addEventListener('fetch', event => {
  const { request } = event;
  // Only handle GET requests and same-origin
  if (request.method !== 'GET') return;

  const url = new URL(request.url);
  if (url.origin !== location.origin) return;

  // Network-first for HTML navigation
  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request)
        .then(response => {
          if (response.ok) {
            const clone = response.clone();
            caches.open(CACHE_NAME).then(c => c.put(request, clone));
          }
          return response;
        })
        .catch(() => caches.match(request).then(r => r || caches.match('/')))
    );
    return;
  }

  // Cache-first for static assets and media used by the installed experience.
  if (url.pathname.startsWith('/static/') || url.pathname.startsWith('/media/')) {
    event.respondWith(
      caches.match(request).then(cached => {
        if (cached) return cached;
        return fetch(request).then(response => {
          if (response.ok) {
            const clone = response.clone();
            caches.open(CACHE_NAME).then(c => c.put(request, clone));
          }
          return response;
        });
      })
    );
    return;
  }

  // Stale-while-revalidate for other same-origin GET requests.
  event.respondWith(
    caches.match(request).then(cached => {
      const networkFetch = fetch(request)
        .then(response => {
          if (response.ok) {
            const clone = response.clone();
            caches.open(CACHE_NAME).then(c => c.put(request, clone));
          }
          return response;
        })
        .catch(() => cached);

      return cached || networkFetch;
    })
  );
});

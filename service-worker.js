const CACHE_NAME = 'tipikus-v1.0.0';
const RUNTIME_CACHE = 'tipikus-runtime';

// Fichiers à mettre en cache immédiatement
const STATIC_CACHE_URLS = [
  '/',
  '/static/css/style.css',
  '/static/js/theme.js',
  '/static/icons/icon-192x192.png',
  '/static/icons/icon-512x512.png'
];

// Installation : mise en cache des ressources statiques
self.addEventListener('install', event => {
  console.log('[SW] Installation...');
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        console.log('[SW] Mise en cache des ressources statiques');
        return cache.addAll(STATIC_CACHE_URLS);
      })
      .then(() => self.skipWaiting())
  );
});

// Activation : nettoyage des anciens caches
self.addEventListener('activate', event => {
  console.log('[SW] Activation...');
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cacheName => {
          if (cacheName !== CACHE_NAME && cacheName !== RUNTIME_CACHE) {
            console.log('[SW] Suppression ancien cache:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    }).then(() => self.clients.claim())
  );
});

// Fetch : stratégie Network First pour les données, Cache First pour les assets
self.addEventListener('fetch', event => {
  const { request } = event;
  const url = new URL(request.url);

  // Ignorer les requêtes non-GET et les requêtes externes
  if (request.method !== 'GET' || url.origin !== location.origin) {
    return;
  }

  // Stratégie Cache First pour les assets statiques (CSS, JS, images)
  if (request.url.includes('/static/')) {
    event.respondWith(
      caches.match(request).then(cachedResponse => {
        if (cachedResponse) {
          return cachedResponse;
        }
        return fetch(request).then(response => {
          return caches.open(RUNTIME_CACHE).then(cache => {
            cache.put(request, response.clone());
            return response;
          });
        });
      })
    );
    return;
  }

  // Stratégie Network First pour les pages et API
  event.respondWith(
    fetch(request)
      .then(response => {
        // Ne pas cacher les erreurs
        if (!response || response.status !== 200) {
          return response;
        }

        const responseClone = response.clone();
        caches.open(RUNTIME_CACHE).then(cache => {
          cache.put(request, responseClone);
        });

        return response;
      })
      .catch(() => {
        // Si le réseau échoue, utiliser le cache
        return caches.match(request).then(cachedResponse => {
          if (cachedResponse) {
            return cachedResponse;
          }
          // Page offline par défaut
          return caches.match('/');
        });
      })
  );
});

// Messages du client (pour forcer la mise à jour)
self.addEventListener('message', event => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});
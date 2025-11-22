// Basic Service Worker for MushGuard PWA

self.addEventListener('install', (event) => {
  console.log('Service Worker: Installed');
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  console.log('Service Worker: Activated');
});

// For now, just pass-through network requests
self.addEventListener('fetch', (event) => {
  event.respondWith(fetch(event.request));
});

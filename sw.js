// LED4YOU app: keep the app shell available offline (lights are often used where there is no internet)
const CACHE = 'led4you-v86';
const FILES = ['./', 'index.html', 'i18n.js?v=59', 'studio.js?v=59', 'layouts.js?v=41', 'scanner.js?v=28', 'manifest.webmanifest', 'icon-192.png', 'icon-512.png', 'gifs/pack.json'];
// cache: 'reload' skips the browser's HTTP cache, so a new version never mixes with old files
self.addEventListener('install', e => { e.waitUntil(caches.open(CACHE).then(c => c.addAll(FILES.map(f => new Request(f, { cache: 'reload' }))))); self.skipWaiting(); });
self.addEventListener('activate', e => { e.waitUntil(caches.keys().then(k => Promise.all(k.filter(n => n !== CACHE).map(n => caches.delete(n))))); self.clients.claim(); });
// network first (always asking the server if the file changed) so updates arrive, cache as fallback when offline
self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET' || new URL(e.request.url).origin !== location.origin) return;
  e.respondWith(fetch(e.request, { cache: 'no-cache' }).then(r => { const copy = r.clone(); caches.open(CACHE).then(c => c.put(e.request, copy)); return r; }).catch(() => caches.match(e.request)));
});

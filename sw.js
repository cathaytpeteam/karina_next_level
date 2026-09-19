const C = "locha-v5";
const FILES = ["./", "index.html", "manifest.webmanifest", "icon-192.png", "icon-512.png", "icon-maskable-192.png", "icon-maskable-512.png", "apple-touch-icon.png"];

self.addEventListener("install", e => {
  e.waitUntil(caches.open(C).then(c => c.addAll(FILES)));
  self.skipWaiting();
});

self.addEventListener("activate", e => {
  e.waitUntil(
    caches.keys().then(keys => Promise.all(keys.filter(k => k !== C).map(k => caches.delete(k))))
  );
  self.clients.claim();
});

// 先用快取立刻開啟（不等網路），同時在背景抓最新版存起來，下次開啟就是新版
self.addEventListener("fetch", e => {
  if (e.request.method !== "GET") return;
  e.respondWith(
    caches.match(e.request, { ignoreSearch: true }).then(cached => {
      const net = fetch(e.request)
        .then(r => {
          if (r && r.ok) { const copy = r.clone(); caches.open(C).then(c => c.put(e.request, copy)); }
          return r;
        })
        .catch(() => cached);
      return cached || net;
    })
  );
});

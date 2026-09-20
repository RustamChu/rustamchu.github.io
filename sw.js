/* RUSTAM.CHU service worker
   Стратегии:
   - навигация (index): network-first — публикации видны сразу, офлайн отдаём кэш;
   - статика с этого origin: stale-while-revalidate — повторные заходы
     мгновенны и тихо обновляются в фоне. Версия кэша = штамп сборки. */
const VERSION = "20.09-1323";
const CACHE = "rustamchu-" + VERSION;

self.addEventListener("install", e => {
  e.waitUntil(
    caches.open(CACHE).then(c => c.addAll(["/", "404.html"]).catch(() => {}))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", e => {
  e.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", e => {
  const req = e.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  if (url.origin !== location.origin) return; // чужие домены не трогаем

  if (req.mode === "navigate") {
    e.respondWith(
      fetch(req)
        .then(res => {
          const copy = res.clone();
          caches.open(CACHE).then(c => c.put(req, copy)).catch(() => {});
          return res;
        })
        .catch(() =>
          caches.match(req).then(hit => hit || caches.match("/"))
        )
    );
    return;
  }

  e.respondWith(
    caches.match(req).then(hit => {
      const refresh = fetch(req)
        .then(res => {
          if (res.ok) {
            const copy = res.clone();
            caches.open(CACHE).then(c => c.put(req, copy)).catch(() => {});
          }
          return res;
        })
        .catch(() => hit);
      return hit || refresh;
    })
  );
});

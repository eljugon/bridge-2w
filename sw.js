// Generado por build_bridge_2w.py. No editar a mano.
// Alcance ./ (solo este repo). Comparte origen con otras apps: solo usa y borra
// cachés cuyo nombre empieza por PREFIX.
const PREFIX = "bridge2w-";
const CACHE = "bridge2w-v1";
const SHELL = ["./", "./index.html"];

self.addEventListener("install", e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", e => {
  e.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(k => k.startsWith(PREFIX) && k !== CACHE).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

// Stale-while-revalidate: responde desde la caché propia y la refresca en segundo plano.
self.addEventListener("fetch", e => {
  const req = e.request;
  if (req.method !== "GET") return;
  if (!req.url.startsWith(self.registration.scope)) return;
  e.respondWith(
    caches.open(CACHE).then(c =>
      c.match(req, {ignoreSearch: true}).then(hit => {
        const net = fetch(req).then(res => {
          if (res && res.ok) c.put(req, res.clone());
          return res;
        });
        if (hit) { e.waitUntil(net.catch(() => {})); return hit; }
        return net.catch(() => c.match("./index.html").then(r => r || Response.error()));
      })
    )
  );
});

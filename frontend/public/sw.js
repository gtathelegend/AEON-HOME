const CACHE_NAME = "aeon-home-pwa-v1";
const STATIC_ASSETS = [
  "/",
  "/dashboard",
  "/manifest.webmanifest",
  "/aeon-logo.png",
  "/favicon.ico"
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(STATIC_ASSETS).catch((err) => console.log("SW Install cache note:", err));
    })
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))
      );
    })
  );
  self.clients.claim();
});

// IndexedDB helper for Background Sync
function openSyncDB() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open("aeon-sync-db", 1);
    request.onupgradeneeded = (e) => {
      e.target.result.createObjectStore("sync-queue", { keyPath: "id", autoIncrement: true });
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

async function addToSyncQueue(request) {
  const db = await openSyncDB();
  const tx = db.transaction("sync-queue", "readwrite");
  const body = await request.clone().text();
  tx.objectStore("sync-queue").add({
    url: request.url,
    method: request.method,
    headers: Array.from(request.headers.entries()),
    body,
    timestamp: Date.now()
  });
  return tx.complete;
}

async function replaySyncQueue() {
  const db = await openSyncDB();
  const tx = db.transaction("sync-queue", "readwrite");
  const store = tx.objectStore("sync-queue");
  const request = store.getAll();
  
  return new Promise((resolve) => {
    request.onsuccess = async () => {
      const items = request.result;
      for (const item of items) {
        try {
          const req = new Request(item.url, {
            method: item.method,
            headers: item.headers,
            body: item.body
          });
          await fetch(req);
          // Delete on success
          const delTx = db.transaction("sync-queue", "readwrite");
          delTx.objectStore("sync-queue").delete(item.id);
        } catch (err) {
          console.error("Background sync failed for", item.url, err);
        }
      }
      resolve();
    };
  });
}

self.addEventListener("sync", (event) => {
  if (event.tag === "aeon-background-sync") {
    event.waitUntil(replaySyncQueue());
  }
});

self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);
  
  // Intercept POST requests for background sync if offline
  if (event.request.method === "POST" && url.pathname.startsWith("/api/")) {
    if (!navigator.onLine) {
      event.respondWith(
        addToSyncQueue(event.request).then(() => {
          // Register background sync
          if (self.registration.sync) {
            self.registration.sync.register("aeon-background-sync");
          }
          return new Response(JSON.stringify({ queued: true }), {
            headers: { "Content-Type": "application/json" }
          });
        })
      );
      return;
    }
  }

  if (event.request.method !== "GET") return;
  
  // Ignore websocket and API endpoints for offline cache fallback
  if (url.pathname.startsWith("/ws/") || url.pathname.startsWith("/api/")) {
    return;
  }

  event.respondWith(
    caches.match(event.request).then((cachedResponse) => {
      if (cachedResponse) {
        // Fetch background update
        fetch(event.request)
          .then((networkResponse) => {
            if (networkResponse.status === 200) {
              caches.open(CACHE_NAME).then((cache) => cache.put(event.request, networkResponse));
            }
          })
          .catch(() => {});
        return cachedResponse;
      }
      return fetch(event.request).catch(() => {
        // Return fallback shell if offline
        return caches.match("/dashboard") || caches.match("/");
      });
    })
  );
});

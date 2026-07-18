/**
 * ÆON Home — Progressive Web App Service Worker
 *
 * Strategy:
 *   - App shell (HTML, CSS, JS, fonts) → Cache-First (installed once, served fast)
 *   - API calls (/api/*)               → Network-First with offline fallback JSON
 *   - Images / icons                   → Stale-While-Revalidate
 *   - Navigate requests                → Cache-First → offline shell fallback
 *
 * Caches:
 *   aeon-shell-v1   — app shell assets
 *   aeon-api-v1     — API response cache (fallback only)
 *   aeon-assets-v1  — images & fonts
 */

const SHELL_CACHE   = "aeon-shell-v1";
const API_CACHE     = "aeon-api-v1";
const ASSETS_CACHE  = "aeon-assets-v1";

const OFFLINE_URL   = "/offline.html";
const OFFLINE_API   = { status: "offline", message: "ÆON is running in offline mode." };

const SHELL_URLS = [
  "/",
  "/dashboard",
  "/dashboard/v2",
  "/offline.html",
  "/manifest.webmanifest",
  "/favicon.ico",
];

/* ── Install ──────────────────────────────────────────────────────────────── */
self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(SHELL_CACHE).then((cache) => cache.addAll(SHELL_URLS)).then(() => self.skipWaiting())
  );
});

/* ── Activate ─────────────────────────────────────────────────────────────── */
self.addEventListener("activate", (event) => {
  const keep = new Set([SHELL_CACHE, API_CACHE, ASSETS_CACHE]);
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => !keep.has(k)).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

/* ── Fetch ────────────────────────────────────────────────────────────────── */
self.addEventListener("fetch", (event) => {
  const { request } = event;
  const url = new URL(request.url);

  /* Skip non-GET and cross-origin */
  if (request.method !== "GET") return;
  if (url.origin !== location.origin && !url.hostname.includes("fonts.g")) return;

  /* ── API: Network-First ────────────────────────────────────────────────── */
  if (url.pathname.startsWith("/api/")) {
    event.respondWith(
      fetch(request)
        .then((res) => {
          if (res.ok) {
            const clone = res.clone();
            caches.open(API_CACHE).then((c) => c.put(request, clone));
          }
          return res;
        })
        .catch(async () => {
          const cached = await caches.match(request);
          if (cached) return cached;
          return new Response(JSON.stringify(OFFLINE_API), {
            status: 503,
            headers: { "Content-Type": "application/json", "X-ÆON-Offline": "true" },
          });
        })
    );
    return;
  }

  /* ── Google Fonts: Stale-While-Revalidate ─────────────────────────────── */
  if (url.hostname.includes("fonts.g")) {
    event.respondWith(
      caches.open(ASSETS_CACHE).then(async (cache) => {
        const cached = await cache.match(request);
        const networkPromise = fetch(request).then((res) => {
          cache.put(request, res.clone());
          return res;
        });
        return cached ?? networkPromise;
      })
    );
    return;
  }

  /* ── Navigate: Cache-First → offline shell ────────────────────────────── */
  if (request.mode === "navigate") {
    event.respondWith(
      caches.match(request)
        .then((cached) => cached ?? fetch(request))
        .catch(() => caches.match(OFFLINE_URL))
    );
    return;
  }

  /* ── Static assets: Cache-First ─────────────────────────────────────────── */
  event.respondWith(
    caches.match(request).then(
      (cached) =>
        cached ??
        fetch(request).then((res) => {
          if (res.ok && (url.pathname.match(/\.(js|css|woff2?|png|ico|webp|svg)$/) || url.pathname.startsWith("/assets/"))) {
            caches.open(SHELL_CACHE).then((c) => c.put(request, res.clone()));
          }
          return res;
        })
    )
  );
});

/* ── Background Sync — queue voice commands made offline ─────────────────── */
self.addEventListener("sync", (event) => {
  if (event.tag === "aeon-voice-queue") {
    event.waitUntil(flushVoiceQueue());
  }
});

async function flushVoiceQueue() {
  /* Reads queued text commands from IndexedDB and replays them when online */
  try {
    const { openDB } = await import("idb");
    const db = await openDB("aeon-offline-queue", 1);
    const tx = db.transaction("voice", "readwrite");
    const all = await tx.store.getAll();
    for (const item of all) {
      try {
        await fetch("/api/v1/voice/text", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text: item.text, user_id: item.userId }),
        });
        await tx.store.delete(item.id);
      } catch {
        /* will retry on next sync */
      }
    }
    await tx.done;
  } catch {
    /* idb not available — skip */
  }
}

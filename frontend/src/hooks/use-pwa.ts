/**
 * usePWA.ts — Progressive Web App lifecycle hooks
 *
 * Exports:
 *   usePWA()  — registers the service worker, tracks online/offline,
 *               and exposes SW update notification state
 */

import { useEffect, useState } from "react";

export interface PWAState {
  /** true when a new SW version is waiting to activate */
  updateAvailable: boolean;
  /** apply the waiting SW immediately (triggers page reload) */
  applyUpdate: () => void;
  /** current network status */
  isOnline: boolean;
  /** true once the SW has been registered */
  swRegistered: boolean;
}

export function usePWA(): PWAState {
  const [updateAvailable, setUpdateAvailable] = useState(false);
  const [waitingWorker, setWaitingWorker] = useState<ServiceWorker | null>(null);
  const [isOnline, setIsOnline] = useState(
    typeof navigator !== "undefined" ? navigator.onLine : true,
  );
  const [swRegistered, setSwRegistered] = useState(false);

  /* ── Service Worker registration ────────────────────────────────────── */
  useEffect(() => {
    if (!("serviceWorker" in navigator)) return;

    let registration: ServiceWorkerRegistration | null = null;

    navigator.serviceWorker
      .register("/sw.js", { scope: "/" })
      .then((reg) => {
        registration = reg;
        setSwRegistered(true);

        /* Detect a waiting (updated) SW */
        if (reg.waiting) {
          setWaitingWorker(reg.waiting);
          setUpdateAvailable(true);
        }

        reg.addEventListener("updatefound", () => {
          const newWorker = reg.installing;
          if (!newWorker) return;
          newWorker.addEventListener("statechange", () => {
            if (newWorker.state === "installed" && navigator.serviceWorker.controller) {
              setWaitingWorker(newWorker);
              setUpdateAvailable(true);
            }
          });
        });
      })
      .catch((err) => {
        console.warn("[ÆON PWA] SW registration failed:", err);
      });

    /* Reload page when new SW takes control */
    let refreshing = false;
    navigator.serviceWorker.addEventListener("controllerchange", () => {
      if (!refreshing) {
        refreshing = true;
        window.location.reload();
      }
    });

    /* Periodic update checks every 60 s */
    const interval = setInterval(() => {
      registration?.update().catch(() => {});
    }, 60_000);

    return () => clearInterval(interval);
  }, []);

  /* ── Online / offline ────────────────────────────────────────────────── */
  useEffect(() => {
    const online  = () => setIsOnline(true);
    const offline = () => setIsOnline(false);
    window.addEventListener("online",  online);
    window.addEventListener("offline", offline);
    return () => {
      window.removeEventListener("online",  online);
      window.removeEventListener("offline", offline);
    };
  }, []);

  /* ── Apply update ────────────────────────────────────────────────────── */
  const applyUpdate = () => {
    waitingWorker?.postMessage({ type: "SKIP_WAITING" });
  };

  return { updateAvailable, applyUpdate, isOnline, swRegistered };
}

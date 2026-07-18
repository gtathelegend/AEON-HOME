/**
 * PWAInstallPrompt.tsx
 *
 * Renders an "Install App" bottom-sheet prompt when the browser
 * fires `beforeinstallprompt`. Dismissible, persists choice in localStorage.
 */

import { useEffect, useState } from "react";
import { Download, X } from "lucide-react";

interface BeforeInstallPromptEvent extends Event {
  prompt(): Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
}

const DISMISSED_KEY = "aeon-pwa-install-dismissed";

export function PWAInstallPrompt() {
  const [prompt, setPrompt] = useState<BeforeInstallPromptEvent | null>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (localStorage.getItem(DISMISSED_KEY)) return;

    const handler = (e: Event) => {
      e.preventDefault();
      setPrompt(e as BeforeInstallPromptEvent);
      setVisible(true);
    };

    window.addEventListener("beforeinstallprompt", handler);
    return () => window.removeEventListener("beforeinstallprompt", handler);
  }, []);

  const handleInstall = async () => {
    if (!prompt) return;
    await prompt.prompt();
    const { outcome } = await prompt.userChoice;
    if (outcome === "accepted") {
      setVisible(false);
    }
    setPrompt(null);
  };

  const handleDismiss = () => {
    localStorage.setItem(DISMISSED_KEY, "1");
    setVisible(false);
  };

  if (!visible) return null;

  return (
    <div
      className="fixed inset-x-0 bottom-0 z-[100] lg:bottom-6 lg:left-auto lg:right-6 lg:inset-x-auto animate-in slide-in-from-bottom"
      style={{ paddingBottom: "env(safe-area-inset-bottom)" }}
    >
      <div className="glass-card mx-3 mb-3 flex items-center gap-3 rounded-3xl p-4 shadow-2xl lg:mx-0 lg:mb-0 lg:w-80">
        {/* Icon */}
        <div
          className="grid h-11 w-11 shrink-0 place-items-center rounded-2xl text-white"
          style={{ background: "var(--gradient-aeon)" }}
        >
          <span className="text-lg font-bold" style={{ fontFamily: "'Instrument Serif', serif" }}>
            Æ
          </span>
        </div>

        {/* Text */}
        <div className="min-w-0 flex-1">
          <p className="text-sm font-semibold">Install ÆON Home</p>
          <p className="text-xs text-muted-foreground truncate">
            Add to home screen for offline access
          </p>
        </div>

        {/* Actions */}
        <div className="flex shrink-0 items-center gap-1.5">
          <button
            onClick={handleInstall}
            className="flex items-center gap-1.5 rounded-xl bg-foreground px-3 py-2 text-xs font-semibold text-background transition hover:scale-[1.04] active:scale-95"
          >
            <Download className="h-3 w-3" />
            Install
          </button>
          <button
            onClick={handleDismiss}
            aria-label="Dismiss"
            className="grid h-8 w-8 place-items-center rounded-xl bg-foreground/6 text-muted-foreground transition hover:bg-foreground/10 active:scale-95"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>
    </div>
  );
}

import React, { createContext, useContext, useEffect, useState, ReactNode } from "react";
import { toast } from "sonner";

interface AutoDiscoveryContextType {
  backendUrl: string | null;
  wsUrl: string | null;
  isSearching: boolean;
}

const AutoDiscoveryContext = createContext<AutoDiscoveryContextType>({
  backendUrl: null,
  wsUrl: null,
  isSearching: true,
});

export const useAutoDiscovery = () => useContext(AutoDiscoveryContext);

export function AutoDiscoveryProvider({ children }: { children: ReactNode }) {
  const [backendUrl, setBackendUrl] = useState<string | null>(null);
  const [wsUrl, setWsUrl] = useState<string | null>(null);
  const [isSearching, setIsSearching] = useState(true);

  useEffect(() => {
    let mounted = true;

    async function discover() {
      // 1. Try local hostname first
      const hostname = window.location.hostname;
      const candidates = [
        `http://${hostname}:8000`, // Same machine
        "http://localhost:8000",
        // Common local subnets if PWA is loaded offline
        "http://192.168.1.100:8000",
        "http://192.168.1.2:8000",
        "http://10.0.0.2:8000"
      ];

      for (const url of candidates) {
        try {
          // Fast timeout to aggressively scan LAN
          const controller = new AbortController();
          const timeoutId = setTimeout(() => controller.abort(), 1000);
          
          const res = await fetch(`${url}/api/v1/health`, { signal: controller.signal });
          clearTimeout(timeoutId);

          if (res.ok && mounted) {
            setBackendUrl(url);
            setWsUrl(url.replace("http://", "ws://").replace("https://", "wss://").replace(":8000", ":8001"));
            setIsSearching(false);
            toast.success(`Discovered Edge Engine at ${url}`);
            return;
          }
        } catch (e) {
          // ignore and try next
        }
      }

      if (mounted) {
        setIsSearching(false);
        toast.error("Could not discover Snapdragon Edge Engine on LAN");
      }
    }

    discover();

    return () => {
      mounted = false;
    };
  }, []);

  return (
    <AutoDiscoveryContext.Provider value={{ backendUrl, wsUrl, isSearching }}>
      {children}
    </AutoDiscoveryContext.Provider>
  );
}

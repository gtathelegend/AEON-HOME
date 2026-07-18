import React, { useState, useEffect } from "react";
import Webcam from "react-webcam";
import { Html5Qrcode } from "html5-qrcode";
import { Button } from "../ui/button";
import { Camera, X } from "lucide-react";
import { toast } from "sonner";

export function CameraScanner({ onScan }: { onScan: (data: string) => void }) {
  const [active, setActive] = useState(false);

  useEffect(() => {
    let scanner: Html5Qrcode | null = null;
    if (active) {
      scanner = new Html5Qrcode("reader");
      scanner.start(
        { facingMode: "environment" },
        { fps: 10, qrbox: { width: 250, height: 250 } },
        (decodedText) => {
          onScan(decodedText);
          toast.success("Device paired successfully via QR code");
          setActive(false);
          scanner?.stop().catch(console.error);
        },
        () => {}
      ).catch((err) => {
        console.error("Camera error", err);
        toast.error("Could not access camera for QR scanning.");
        setActive(false);
      });
    }

    return () => {
      if (scanner && scanner.isScanning) {
        scanner.stop().catch(console.error);
      }
    };
  }, [active, onScan]);

  if (!active) {
    return (
      <Button variant="outline" onClick={() => setActive(true)} className="gap-2">
        <Camera className="h-4 w-4" />
        Scan Device QR
      </Button>
    );
  }

  return (
    <div className="relative overflow-hidden rounded-xl border border-border bg-black">
      <div id="reader" className="w-full max-w-sm h-[300px]" />
      <Button 
        variant="destructive" 
        size="icon" 
        className="absolute top-2 right-2 z-10 rounded-full"
        onClick={() => setActive(false)}
      >
        <X className="h-4 w-4" />
      </Button>
      <div className="absolute inset-x-0 bottom-4 text-center text-xs text-white/70">
        Point at device pairing QR
      </div>
    </div>
  );
}

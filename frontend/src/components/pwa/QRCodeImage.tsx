/**
 * QRCodeImage.tsx
 *
 * Renders a real QR code from a string payload using the `qrcode` library.
 * No fake CSS patterns — this is a scannable QR code.
 */
import { useEffect, useRef } from "react";
import QRCode from "qrcode";

interface Props {
  value: string;
  size?: number;
  className?: string;
}

export function QRCodeImage({ value, size = 176, className }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    if (!canvasRef.current || !value) return;
    QRCode.toCanvas(canvasRef.current, value, {
      width: size,
      margin: 2,
      color: {
        dark: "#1a1035",
        light: "#ffffff",
      },
      errorCorrectionLevel: "M",
    }).catch(() => {
      // On failure leave canvas blank — callers show fallback text
    });
  }, [value, size]);

  if (!value) {
    return (
      <div
        className={`flex items-center justify-center rounded-xl bg-slate-100 text-xs text-muted-foreground ${className ?? ""}`}
        style={{ width: size, height: size }}
      >
        No payload
      </div>
    );
  }

  return (
    <canvas
      ref={canvasRef}
      width={size}
      height={size}
      className={`rounded-xl ${className ?? ""}`}
      aria-label="Identity migration QR code"
    />
  );
}

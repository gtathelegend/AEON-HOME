import { useEffect, useState, type ElementType, type ReactNode } from "react";
import { useInView } from "@/hooks/use-in-view";

type Variant = "fade-up" | "fade" | "scale-in";

interface RevealProps {
  children: ReactNode;
  as?: ElementType;
  delay?: number;
  duration?: number;
  variant?: Variant;
  className?: string;
}

function usePrefersReducedMotion() {
  const [reduced, setReduced] = useState(false);
  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    setReduced(mq.matches);
    const onChange = () => setReduced(mq.matches);
    mq.addEventListener?.("change", onChange);
    return () => mq.removeEventListener?.("change", onChange);
  }, []);
  return reduced;
}

const hiddenClasses: Record<Variant, string> = {
  "fade-up": "opacity-0 translate-y-4",
  fade: "opacity-0",
  "scale-in": "opacity-0 scale-95",
};

const shownClasses = "opacity-100 translate-y-0 scale-100";

export function Reveal({
  children,
  as,
  delay = 0,
  duration = 700,
  variant = "fade-up",
  className = "",
}: RevealProps) {
  const Tag = (as ?? "div") as ElementType;
  const { ref, inView } = useInView<HTMLElement>();
  const reduced = usePrefersReducedMotion();

  const active = reduced || inView;
  const style = reduced
    ? undefined
    : { transitionDuration: `${duration}ms`, transitionDelay: `${delay}ms` };

  return (
    <Tag
      ref={ref as never}
      style={style}
      className={`will-change-transform transition-all ease-out ${
        active ? shownClasses : hiddenClasses[variant]
      } ${className}`}
    >
      {children}
    </Tag>
  );
}

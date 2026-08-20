import { useEffect, useRef } from "react";

interface DailyAutosaveOptions {
  enabled: boolean;
  dirty: boolean;
  onSave: () => void;
  delayMs?: number;
}

/** Saves only server-backed daily records after a quiet editing interval. */
export function useDailyAutosave({ enabled, dirty, onSave, delayMs = 1_500 }: DailyAutosaveOptions) {
  const saveRef = useRef(onSave);
  useEffect(() => { saveRef.current = onSave; }, [onSave]);

  useEffect(() => {
    if (!enabled || !dirty) return;
    const timeout = window.setTimeout(() => saveRef.current(), delayMs);
    return () => window.clearTimeout(timeout);
  }, [delayMs, dirty, enabled]);
}

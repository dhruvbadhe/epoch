"use client";
import { useEffect, useRef, useState } from "react";
import type { ApiResult } from "./types";
export function useResource<T>(
  key: string,
  fetcher: () => Promise<ApiResult<T>>,
  enabled = true,
) {
  const [result, setResult] = useState<ApiResult<T> | null>(null);
  const [loading, setLoading] = useState(enabled);
  const [error, setError] = useState<Error | null>(null);
  const [revision, setRevision] = useState(0);
  const latest = useRef(fetcher);
  latest.current = fetcher;
  useEffect(() => {
    if (!enabled) {
      setLoading(false);
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError(null);
    setResult(null);
    const timer = setTimeout(() => {
      latest
        .current()
        .then((value) => {
          if (!cancelled) setResult(value);
        })
        .catch((reason) => {
          if (!cancelled)
            setError(
              reason instanceof Error ? reason : new Error(String(reason)),
            );
        })
        .finally(() => {
          if (!cancelled) setLoading(false);
        });
    }, 150);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [key, revision, enabled]);
  return { result, loading, error, reload: () => setRevision((v) => v + 1) };
}

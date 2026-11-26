"use client";

import { useEffect, useState } from "react";
export type Study = { word: string; attempts: number; last: string };
export type Activity = {
  id: string;
  label: string;
  at: string;
  kind: "speech" | "prosody" | "talk" | "dictionary";
};

export function useStored<T>(key: string, initial: T) {
  const [entry, setEntry] = useState<{ key: string; value: T }>();
  useEffect(() => {
    try {
      const value = localStorage.getItem(key);
      setEntry({ key, value: value ? (JSON.parse(value) as T) : initial });
    } catch {
      setEntry({ key, value: initial });
    }
    // Defaults are used only on a key change.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);
  const value = entry?.key === key ? entry.value : initial;
  function save(next: T | ((previous: T) => T)) {
    setEntry((previous) => {
      const prior = previous?.key === key ? previous.value : initial;
      return { key, value: typeof next === "function" ? (next as (value: T) => T)(prior) : next };
    });
  }
  useEffect(() => {
    if (entry?.key !== key) return;
    try {
      localStorage.setItem(key, JSON.stringify(entry.value));
    } catch {
      /* The current tab can still be used. */
    }
  }, [entry, key]);
  return [value, save] as const;
}

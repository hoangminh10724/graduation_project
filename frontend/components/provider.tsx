"use client";

import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { ApiError, api } from "@/lib/api";
import { useStored, type Study, type Activity } from "@/lib/storage";

type Identity = { email: string; token: string; id: string; expiresAt: number };
type Profile = { name: string; level: "A2" | "B1" | "B2" };
const defaultProfile: Profile = { name: "", level: "A2" };

const keys = { account: "wordspeak-session", theme: "wordspeak-theme", motion: "wordspeak-motion" };
const sessionContext = createContext<ReturnType<typeof useAppState> | null>(null);

function identity(email: string, token: string): Identity {
  const claims = JSON.parse(atob(token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/"))) as {
    sub?: string;
    exp?: number;
  };
  if (!claims.sub || !claims.exp || claims.exp * 1000 <= Date.now())
    throw new Error("Phiên đăng nhập chưa hợp lệ.");
  return { email, token, id: String(claims.sub), expiresAt: claims.exp * 1000 };
}

function useAppState() {
  const [account, setAccount] = useState<Identity | null>(null);
  const [ready, setReady] = useState(false);
  const [theme, setTheme] = useStored<"light" | "dark">(keys.theme, "light");
  const [motion, setMotion] = useStored(keys.motion, false);
  const suffix = account ? `user-${account.id}` : "guest";
  const [profile, setProfile] = useStored<Profile>(`wordspeak-profile-${suffix}`, defaultProfile);
  const [study, setStudy] = useStored<Study[]>(`wordspeak-study-${suffix}`, []);
  const [activity, setActivity] = useStored<Activity[]>(`wordspeak-activity-${suffix}`, []);
  const [saved, setSaved] = useStored<string[]>(`wordspeak-words-${suffix}`, []);
  const [ratings, setRatings] = useStored<Record<string, number>>(`wordspeak-ratings-${suffix}`, {});

  function logout() {
    setAccount(null);
    try {
      sessionStorage.removeItem(keys.account);
    } catch {
      /* Restricted storage mode. */
    }
  }

  useEffect(() => {
    try {
      const value = JSON.parse(sessionStorage.getItem(keys.account) || "null") as Identity | null;
      if (value) setAccount(identity(value.email, value.token));
    } catch {
      logout();
    }
    setReady(true);
  }, []);

  useEffect(() => {
    if (!account) return;
    const timeout = setTimeout(
      logout,
      Math.min(2 ** 31 - 1, Math.max(0, account.expiresAt - Date.now())),
    );
    return () => clearTimeout(timeout);
  }, [account]);

  useEffect(() => {
    const root = document.documentElement;
    root.dataset.theme = theme;
    if (motion) root.dataset.motion = "reduced";
    else delete root.dataset.motion;
  }, [theme, motion]);

  async function authenticate(mode: "login" | "register", email: string, password: string) {
    try {
      const result = await api<{ access_token: string }>(`/auth/${mode}`, { data: { email, password } });
      const next = identity(email.toLowerCase(), result.access_token);
      setAccount(next);
      try {
        sessionStorage.setItem(keys.account, JSON.stringify(next));
      } catch {
        /* The session survives navigation in this tab. */
      }
    } catch (error) {
      if (error instanceof ApiError && mode === "register" && error.status === 409)
        throw new Error("Email này đã được đăng ký.");
      throw error;
    }
  }

  function log(label: string, kind: Activity["kind"], word?: string) {
    const at = new Date().toISOString();
    if (word)
      setStudy((previous) => {
        const earlier = previous.find((item) => item.word === word);
        return [
          { word, attempts: (earlier?.attempts ?? 0) + 1, last: at },
          ...previous.filter((item) => item.word !== word),
        ];
      });
    setActivity((previous) => [{ id: crypto.randomUUID(), label, at, kind }, ...previous].slice(0, 250));
  }

  function toggleSaved(word: string) {
    setSaved((previous) =>
      previous.includes(word) ? previous.filter((item) => item !== word) : [word, ...previous],
    );
  }

  return {
    account,
    ready,
    theme,
    setTheme,
    motion,
    setMotion,
    profile,
    setProfile,
    study,
    activity,
    saved,
    toggleSaved,
    ratings,
    setRatings,
    log,
    logout,
    authenticate,
  };
}

export function Provider({ children }: { children: ReactNode }) {
  return <sessionContext.Provider value={useAppState()}>{children}</sessionContext.Provider>;
}
export function useApp() {
  const context = useContext(sessionContext);
  if (!context) throw new Error("WordSpeak provider is missing");
  return context;
}

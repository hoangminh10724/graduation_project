"use client";

import { Suspense, useEffect } from "react";
import type { Section } from "@/lib/content";
import { stopSpeech } from "@/lib/voice";
import { Auth, Profile, Settings } from "./account";
import { Dashboard, History } from "./activity";
import { Dictionary } from "./dictionary";
import { Ipa, Practice } from "./practice";
import { Prosody } from "./prosody";
import { Talk } from "./talk";
import { Busy } from "./ui";
import { PracticeBanner } from "./practice-banner";

export function Screen({ section }: { section: Section }) {
  useEffect(() => () => stopSpeech(), [section]);
  switch (section) {
    case "dang-nhap":
      return <Auth />;
    case "dang-ky":
      return <Auth key="register" register />;
    case "ho-so":
      return <Profile />;
    case "cai-dat":
      return <Settings />;
    case "luyen-ngu-am":
      return (
        <>
          <PracticeBanner area="luyen-ngu-am" />
          <Suspense fallback={<Busy>Đang mở bài luyện…</Busy>}>
            <Practice />
          </Suspense>
        </>
      );
    case "ipa":
      return <Ipa />;
    case "luyen-ngu-dieu":
      return <Prosody />;
    case "tu-dien":
      return <Dictionary />;
    case "tu-da-luu":
      return <Dictionary key="saved" savedOnly />;
    case "talk":
      return <Talk />;
    case "tien-do":
      return <Dashboard />;
    case "lich-su":
      return <History />;
  }
}

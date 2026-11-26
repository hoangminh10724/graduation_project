"use client";

import { useEffect, useState } from "react";
import { ApiError, api, type Progress, type TalkSession, type Turn } from "@/lib/api";
import { useApp } from "./provider";
import { SpeakButton } from "./audio-controls";
import { Action, Button, Busy, Empty, Notice, Panel, Title } from "./ui";

const localDate = new Intl.DateTimeFormat("sv-SE", {
  timeZone: "Asia/Ho_Chi_Minh",
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
});
const displayDate = new Intl.DateTimeFormat("vi-VN", {
  timeZone: "Asia/Ho_Chi_Minh",
  dateStyle: "medium",
  timeStyle: "short",
});
function isoDay(date = new Date()) {
  return localDate.format(date);
}

function useRemote<T>(path: string | null) {
  const { account, logout } = useApp();
  const [refresh, setRefresh] = useState(0);
  const [result, setResult] = useState<{ key: string; data?: T; error?: string }>();
  const token = account?.token;
  const key = `${account?.id ?? ""}:${path ?? ""}:${refresh}`;
  useEffect(() => {
    if (!path || !token) return;
    const request = new AbortController();
    async function load() {
      try {
        const data = await api<T>(path!, { token, signal: request.signal });
        if (!request.signal.aborted) setResult({ key, data });
      } catch (error) {
        if (request.signal.aborted) return;
        if (error instanceof ApiError && error.status === 401) logout();
        setResult({ key, error: error instanceof Error ? error.message : "Không tải được dữ liệu." });
      }
    }
    void load();
    return () => request.abort();
    // Logging out is a stable state transition scoped to the captured account.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [path, token, key]);
  return {
    data: result?.key === key ? result.data : undefined,
    error: result?.key === key ? result.error : undefined,
    loading: Boolean(path && token && result?.key !== key),
    retry: () => setRefresh((value) => value + 1),
  };
}

function ActivityList({ kind }: { kind?: "speech" | "prosody" }) {
  const { activity } = useApp();
  const events = activity.filter((item) => !kind || item.kind === kind);
  return events.length ? (
    <div>
      {events.slice(0, 20).map((item) => (
        <div className="list-item" key={item.id}>
          <strong>{item.label}</strong>
          <small>{displayDate.format(new Date(item.at))}</small>
        </div>
      ))}
    </div>
  ) : (
    <p>Chưa có hoạt động trên thiết bị này.</p>
  );
}

export function Dashboard() {
  const { activity, study, account } = useApp();
  const remote = useRemote<Progress>("/progress?timezone_name=Asia%2FHo_Chi_Minh");
  const phonemes = Object.entries(remote.data?.phoneme_averages ?? {})
    .filter(([, score]) => Number.isFinite(score) && score >= 0 && score <= 100)
    .sort(([left], [right]) => left.localeCompare(right));
  const localDays = new Set(activity.map((item) => isoDay(new Date(item.at))));
  const days = new Set([
    ...Array.from(localDays),
    ...(remote.data?.daily ?? []).filter((day) => day.attempts > 0).map((day) => day.date),
  ]);
  const lastWeek = Array.from(
    { length: 7 },
    (_, index) => new Date(Date.now() - (6 - index) * 86400000),
  );
  let streak = 0;
  let date = Date.now();
  if (!days.has(isoDay(new Date(date)))) date -= 86400000;
  while (days.has(isoDay(new Date(date)))) {
    streak++;
    date -= 86400000;
  }
  return (
    <>
      <Title title="Tiến độ">Theo dõi từ đã học, số lần luyện và nhịp học của bạn.</Title>
      <div className="stack">
        <div className="grid cards">
          {[
            [study.length, "Từ đã học"],
            [activity.filter((item) => item.kind !== "dictionary").length, "Lượt luyện trên thiết bị"],
            [streak, "Ngày liên tiếp"],
          ].map(([value, label]) => (
            <Panel key={label} className="stack metric">
              <small>{label}</small>
              <strong>{value}</strong>
            </Panel>
          ))}
        </div>
        {days.size ? (
          <Panel className="stack">
            <h2>7 ngày gần đây</h2>
            <div className="row">
              {lastWeek.map((day) => (
                <span key={isoDay(day)} className="activity-day" data-active={days.has(isoDay(day))}>
                  <strong>
                    {day.toLocaleDateString("vi-VN", {
                      day: "2-digit",
                      month: "2-digit",
                      timeZone: "Asia/Ho_Chi_Minh",
                    })}
                  </strong>
                  <small>{days.has(isoDay(day)) ? "Có học" : "—"}</small>
                </span>
              ))}
            </div>
          </Panel>
        ) : (
          <Empty title="Chưa có hoạt động học" icon="chart">
            <Action href="/luyen-ngu-am" primary>
              Bắt đầu luyện
            </Action>
          </Empty>
        )}
        {account &&
          (remote.loading ? (
            <Busy>Đang tải số liệu máy chủ…</Busy>
          ) : remote.error ? (
            <Notice tone="error">
              {remote.error} <Button onClick={remote.retry}>Thử lại</Button>
            </Notice>
          ) : (
            <Panel className="stack">
              <h2>Số liệu tài khoản</h2>
              <p>{remote.data?.attempts ?? 0} lượt máy chủ đã ghi nhận</p>
              <h3>Điểm trung bình theo âm</h3>
              {phonemes.length ? (
                <div className="grid score-grid">
                  {phonemes.map(([ipa, score]) => (
                    <div key={ipa} className="score-row">
                      <strong>/{ipa}/</strong>
                      <meter
                        className="meter"
                        min="0"
                        max="100"
                        value={score}
                        aria-label={`Điểm âm ${ipa}`}
                      />
                      <small>{score}/100</small>
                    </div>
                  ))}
                </div>
              ) : (
                <p>Máy chủ chưa có điểm âm vị cho các lượt luyện.</p>
              )}
            </Panel>
          ))}
        <Panel className="stack">
          <h2>Hoạt động gần đây</h2>
          <ActivityList />
        </Panel>
      </div>
    </>
  );
}

export function History() {
  const { account, ready } = useApp();
  const [tab, setTab] = useState<"speech" | "prosody" | "talk">("talk");
  const [selected, setSelected] = useState<number>();
  const remote = useRemote<{ items: TalkSession[] }>(tab === "talk" ? "/sessions" : null);
  const session = remote.data?.items.find((item) => item.id === selected);
  const detail = useRemote<{ items: Turn[] }>(
    tab === "talk" && session ? `/sessions/${session.id}/turns` : null,
  );
  return (
    <>
      <Title title="Lịch sử">
        Xem lại các lần luyện và nghe nội dung đã được ghi nhận trong các cuộc hội thoại.
      </Title>
      <div className="stack">
        <div className="row" role="group" aria-label="Hoạt động">
          {(
            [
              ["talk", "Hội thoại AI"],
              ["speech", "Ngữ âm"],
              ["prosody", "Ngữ điệu"],
            ] as const
          ).map(([key, label]) => (
            <Button key={key} aria-pressed={key === tab} onClick={() => setTab(key)}>
              {label}
            </Button>
          ))}
        </div>
        {tab !== "talk" ? (
          <Panel className="stack">
            <h2>Lần luyện trên thiết bị</h2>
            <ActivityList kind={tab} />
          </Panel>
        ) : !ready || remote.loading ? (
          <Busy>Đang tải lịch sử hội thoại…</Busy>
        ) : !account ? (
          <Empty title="Đăng nhập để xem hội thoại" icon="talk">
            <Action href="/dang-nhap" primary>
              Đăng nhập
            </Action>
          </Empty>
        ) : remote.error ? (
          <Notice tone="error">
            {remote.error} <Button onClick={remote.retry}>Thử lại</Button>
          </Notice>
        ) : !remote.data?.items.length ? (
          <Empty title="Chưa có hội thoại" icon="talk">
            <Action href="/talk" primary>
              Mở phòng luyện
            </Action>
          </Empty>
        ) : (
          <div className="grid two">
            <Panel className="stack">
              <h2>Các phiên</h2>
              <div>
                {remote.data.items.map((item) => (
                  <div className="list-item" key={item.id}>
                    <div>
                      <strong>
                        Phiên {item.id} · {item.cefr_level}
                      </strong>
                      <p>
                        {item.topic.replace(/^Voice practice: use these learned words naturally: /, "")}
                      </p>
                    </div>
                    <Button aria-pressed={selected === item.id} onClick={() => setSelected(item.id)}>
                      Mở
                    </Button>
                  </div>
                ))}
              </div>
            </Panel>
            {detail.loading ? (
              <Busy>Đang tải lịch sử phiên…</Busy>
            ) : detail.error ? (
              <Notice tone="error">
                {detail.error} <Button onClick={detail.retry}>Thử lại</Button>
              </Notice>
            ) : (
              <Panel className="stack">
                <h2>{session ? `Phiên ${session.id}` : "Nội dung phiên"}</h2>
                {!session ? (
                  <p>Chọn một phiên để xem các lượt luyện.</p>
                ) : !detail.data?.items.length ? (
                  <p>Chưa ghi nhận lượt nói hoàn tất.</p>
                ) : (
                  <>
                    <small>
                      Trình duyệt đọc lại nội dung đã nhận dạng. Bản thu gốc không có trong lịch sử.
                    </small>
                    <div>
                      {detail.data.items.map((turn, index) => (
                        <div key={turn.id} className="list-item">
                          <strong>Lượt {index + 1}</strong>
                          <div className="row">
                            <SpeakButton text={turn.text} label="Nghe câu đã nói" />
                            <SpeakButton text={turn.reply} label="Nghe gia sư" />
                          </div>
                        </div>
                      ))}
                    </div>
                  </>
                )}
              </Panel>
            )}
          </div>
        )}
      </div>
    </>
  );
}

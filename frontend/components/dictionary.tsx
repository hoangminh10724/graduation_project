"use client";

import { useEffect, useRef, useState } from "react";
import { dictionaryCategories, entries, type Entry } from "@/lib/content";
import { stopSpeech } from "@/lib/voice";
import { useApp } from "./provider";
import { SpeakButton } from "./audio-controls";
import { Action, Button, Empty, Panel, Title } from "./ui";

function WordCard({ entry }: { entry: Entry }) {
  const { saved, toggleSaved, ratings, setRatings, study, log } = useApp();
  const selected = saved.includes(entry.word);
  const rating = ratings[entry.word] ?? 0;
  const learned = study.some((item) => item.word === entry.word);
  return (
    <article className="panel stack">
      <div className="row spread">
        <div>
          <h2 id="word-detail-heading" lang="en">
            {entry.word}
          </h2>
          <span className="muted">/{entry.ipa}/</span>
        </div>
        <span className="badge dim">{entry.kind}</span>
      </div>
      <p>
        <strong>{entry.meaning}</strong>
      </p>
      <p lang="en">{entry.example}</p>
      <div className="row">
        <SpeakButton text={entry.word} audioSrc={`/audio/dictionary/${entry.word}.wav`} />
        <SpeakButton
          text={entry.example}
          label="Nghe câu ví dụ"
          audioSrc={`/audio/dictionary/${entry.word}-example.wav`}
        />
      </div>
      <div className="row">
        <Button icon="bookmark" aria-pressed={selected} onClick={() => toggleSaved(entry.word)}>
          {selected ? "Đã lưu" : "Lưu từ"}
        </Button>
        {entry.sound && (
          <Action href={`/luyen-ngu-am?am=${encodeURIComponent(entry.sound)}`}>Kiểm tra phát âm</Action>
        )}
        <Button
          aria-pressed={learned}
          disabled={learned}
          onClick={() => {
            if (!learned) log(`Học từ ${entry.word}`, "dictionary", entry.word);
          }}
        >
          {learned ? "Đã học" : "Đánh dấu đã học"}
        </Button>
      </div>
      <details className="word-rating">
        <summary>Đánh giá {rating ? `· ${rating}/5` : ""}</summary>
        <small>Tự đánh giá mức ghi nhớ từ này.</small>
        <div className="rating" role="group" aria-label={`Đánh giá từ ${entry.word}`}>
          {[1, 2, 3, 4, 5].map((value) => (
            <Button
              key={value}
              aria-label={`${value} trên 5`}
              aria-pressed={rating === value}
              onClick={() => {
                setRatings((previous) => ({ ...previous, [entry.word]: value }));
                if (!learned) log(`Học từ ${entry.word}`, "dictionary", entry.word);
              }}
            >
              {value}
            </Button>
          ))}
        </div>
      </details>
    </article>
  );
}

function normalize(value: string) {
  return value
    .normalize("NFD")
    .replace(/\p{Diacritic}/gu, "")
    .toLowerCase()
    .replace(/đ/g, "d")
    .trim();
}

export function Dictionary({ savedOnly = false }: { savedOnly?: boolean }) {
  const { saved, study } = useApp();
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState("all");
  const [detail, setDetail] = useState<Entry>();
  const dialog = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    if (detail && !dialog.current?.open) dialog.current?.showModal();
  }, [detail]);
  const key = normalize(query);
  const matches = entries
    .filter(
      (entry) =>
        (!savedOnly || saved.includes(entry.word)) &&
        (filter === "all" || study.some((item) => item.word === entry.word)) &&
        (!key || normalize(`${entry.word} ${entry.meaning} ${entry.ipa}`).includes(key)),
    )
    .sort((left, right) => Number(normalize(right.word) === key) - Number(normalize(left.word) === key));
  return (
    <>
      <Title title={savedOnly ? "Từ đã lưu" : "Từ điển"}>
        {savedOnly
          ? "Nghe lại và xem cách dùng những từ bạn đã lưu trên thiết bị này."
          : "Tra nghĩa tiếng Việt, nghe cách đọc và học từ qua ví dụ."}
      </Title>
      <div className="stack">
        <Panel className="stack">
          <label className="field">
            Tìm từ hoặc nghĩa
            <input
              type="search"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Ví dụ: seat, chỗ ngồi"
            />
          </label>
          <div className="row spread">
            <small>
              {matches.length} mục · {savedOnly ? "Đã lưu trên thiết bị" : "Danh mục WordSpeak"} · Mẫu
              nghe giọng Anh-Mỹ tổng hợp
            </small>
            {savedOnly && (
              <Button
                aria-pressed={filter === "learned"}
                onClick={() => setFilter(filter === "all" ? "learned" : "all")}
              >
                Chỉ từ đã học
              </Button>
            )}
          </div>
        </Panel>
        {matches.length ? (
          <div className="stack word-groups" aria-live="polite">
            {dictionaryCategories.map(({ title, words }) => {
              const group = matches.filter((entry) => words.some((word) => word === entry.word));
              if (!group.length) return null;
              return (
                <section className="stack word-group" key={title} aria-label={title}>
                  <h2>{title}</h2>
                  <ul className="word-grid">
                    {group.map((entry) => (
                      <li key={entry.word} className="word-tile">
                        <strong lang="en">{entry.word}</strong>
                        <span className="muted">/{entry.ipa}/</span>
                        <Button aria-label={`Chi tiết: ${entry.word}`} onClick={() => setDetail(entry)}>
                          Chi tiết
                        </Button>
                      </li>
                    ))}
                  </ul>
                </section>
              );
            })}
          </div>
        ) : (
          <Empty
            title={savedOnly && saved.length === 0 ? "Chưa có từ đã lưu" : "Không tìm thấy từ phù hợp"}
            icon="book"
          >
            <p>
              {savedOnly && saved.length === 0
                ? "Lưu một từ trong từ điển để xem lại bất cứ lúc nào."
                : "Thử một từ hoặc nghĩa khác trong danh mục."}
            </p>
            {savedOnly && (
              <Action href="/tu-dien" primary>
                Mở từ điển
              </Action>
            )}
          </Empty>
        )}
      </div>
      <dialog
        ref={dialog}
        className="word-dialog"
        aria-labelledby="word-detail-heading"
        onClose={() => {
          stopSpeech();
          setDetail(undefined);
        }}
      >
        {detail && (
          <>
            <div className="word-dialog-actions">
              <Button onClick={() => dialog.current?.close()}>Đóng</Button>
            </div>
            <WordCard key={detail.word} entry={detail} />
          </>
        )}
      </dialog>
    </>
  );
}

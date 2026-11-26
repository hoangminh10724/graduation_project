"use client";

import Link from "next/link";
import type { ButtonHTMLAttributes, ReactNode } from "react";

const paths: Record<string, ReactNode> = {
  home: <path d="m3 10 9-7 9 7v10H3zm6 10v-7h6v7" />,
  mic: (
    <>
      <rect x="9" y="2" width="6" height="13" rx="3" />
      <path d="M5 11v1a7 7 0 0 0 14 0v-1m-7 8v3m-4 0h8" />
    </>
  ),
  wave: <path d="M3 12h2m3-5v10m4-14v18m4-14v10m3-5h2" />,
  grid: (
    <>
      <rect x="3" y="3" width="7" height="7" rx="1" />
      <rect x="14" y="3" width="7" height="7" rx="1" />
      <rect x="3" y="14" width="7" height="7" rx="1" />
      <rect x="14" y="14" width="7" height="7" rx="1" />
    </>
  ),
  book: <path d="M5 19V5a2 2 0 0 1 2-2h12v18H7a2 2 0 0 1 0-4h12M9 7h6m-6 4h6" />,
  bookmark: <path d="M6 21V4h12v17l-6-4z" />,
  talk: (
    <>
      <path d="M5 14v-2a7 7 0 0 1 14 0v2m-14 0h3v6H6a2 2 0 0 1-2-2v-2a2 2 0 0 1 1-2zm14 0h-3v6h2a2 2 0 0 0 2-2v-2a2 2 0 0 0-1-2Z" />
      <path d="M11 22h3l2-2" />
    </>
  ),
  chart: <path d="M3 3v18h18M7 16l4-5 4 2 5-7" />,
  history: <path d="M3 12a9 9 0 1 1 3 7m-3-7V6m0 6h6m3-5v5l3 2" />,
  user: (
    <>
      <circle cx="12" cy="7" r="4" />
      <path d="M4 21v-2a8 5 0 0 1 16 0v2" />
    </>
  ),
  settings: (
    <>
      <circle cx="12" cy="12" r="3" />
      <path d="m10 2-1 3-3 1-3 1 1 3-2 2 2 2-1 3 3 1 3 1 1 3h4l1-3 3-1 3-1-1-3 2-2-2-2 1-3-3-1-3-1-1-3z" />
    </>
  ),
  menu: <path d="M4 6h16M4 12h16M4 18h16" />,
  down: <path d="m6 9 6 6 6-6" />,
  sun: (
    <>
      <circle cx="12" cy="12" r="4" />
      <path d="M12 2v2m0 16v2M2 12h2m16 0h2M5 5l2 2m10 10 2 2m0-14-2 2M7 17l-2 2" />
    </>
  ),
  moon: <path d="M20 15a8 8 0 1 1-11-11 7 7 0 0 0 11 11Z" />,
  play: <path d="m8 5 12 7-12 7z" />,
  stop: <rect x="6" y="6" width="12" height="12" rx="2" />,
  info: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 11v6m0-10h.01" />
    </>
  ),
  eye: (
    <>
      <path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7-10-7-10-7Z" />
      <circle cx="12" cy="12" r="3" />
    </>
  ),
  check: <path d="m5 12 4 4L19 6" />,
  close: <path d="m6 6 12 12M18 6 6 18" />,
  volume: (
    <>
      <path d="M4 9h4l5-4v14l-5-4H4zm12 0a4 4 0 0 1 0 6m2-9a8 8 0 0 1 0 12" />
    </>
  ),
  search: (
    <>
      <circle cx="10" cy="10" r="6" />
      <path d="m15 15 5 5" />
    </>
  ),
};

export function Icon({ name, size = 20 }: { name: string; size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.65"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {paths[name] ?? paths.info}
    </svg>
  );
}

export function Button({
  icon,
  children,
  tone = "",
  className = "",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  icon?: string;
  tone?: "primary" | "soft" | "danger" | "";
}) {
  return (
    <button type="button" className={`button ${tone} ${className}`} {...props}>
      {icon && <Icon name={icon} />}
      {children}
    </button>
  );
}
export function Action({
  href,
  children,
  icon,
  primary = false,
}: {
  href: string;
  children: ReactNode;
  icon?: string;
  primary?: boolean;
}) {
  return (
    <Link href={href} className={`button ${primary ? "primary" : ""}`}>
      {icon && <Icon name={icon} />}
      {children}
    </Link>
  );
}
export function Panel({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <section className={`panel ${className}`}>{children}</section>;
}
export function Title({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <header className="page-title">
      <h1>{title}</h1>
      {children && <p>{children}</p>}
    </header>
  );
}
export function Notice({ children, tone = "" }: { children: ReactNode; tone?: "error" | "warn" | "" }) {
  return (
    <div className={`notice ${tone}`} role={tone === "error" ? "alert" : "status"}>
      <Icon name="info" />
      <div>{children}</div>
    </div>
  );
}
export function Empty({
  title,
  children,
  icon = "info",
}: {
  title: string;
  children: ReactNode;
  icon?: string;
}) {
  return (
    <Panel className="empty">
      <span className="tile">
        <Icon name={icon} />
      </span>
      <h2>{title}</h2>
      {children}
    </Panel>
  );
}
export function Busy({ children }: { children: ReactNode }) {
  return (
    <Panel className="stack">
      <span role="status">{children}</span>
      <div className="skeleton" />
      <div className="skeleton short" />
    </Panel>
  );
}

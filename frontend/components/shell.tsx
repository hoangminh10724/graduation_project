"use client";

import { useEffect, useState, type ReactNode } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { sections, type Section } from "@/lib/content";
import { Busy, Icon } from "./ui";
import { useApp } from "./provider";

const groups: { title: string; links: Section[] }[] = [
  { title: "Luyện tập", links: ["luyen-ngu-am", "luyen-ngu-dieu", "talk"] },
  { title: "Từ vựng", links: ["tu-dien", "tu-da-luu", "ipa"] },
  { title: "Cá nhân", links: ["tien-do", "lich-su", "ho-so", "cai-dat"] },
];
const mobile: [Section | "/", string, Section[]][] = [
  ["/", "Trang chủ", []],
  ["luyen-ngu-am", "Luyện tập", ["luyen-ngu-dieu", "talk"]],
  ["tu-dien", "Từ vựng", ["tu-da-luu", "ipa"]],
  ["ho-so", "Hồ sơ", ["cai-dat", "tien-do", "lich-su", "dang-nhap", "dang-ky"]],
];

export function Shell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { account, ready, theme, setTheme, profile, logout } = useApp();
  const [menu, setMenu] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  const [profileMenu, setProfileMenu] = useState(false);
  const section = pathname.slice(1) as Section;
  const title = sections[section]?.[0] ?? "Trang chủ";
  const dark = theme === "dark";
  const authPage = section === "dang-nhap" || section === "dang-ky";

  useEffect(() => {
    if (ready && !account && !authPage) router.replace("/dang-nhap");
  }, [account, authPage, ready, router]);

  if (authPage || !ready || !account) {
    return (
      <main id="main" className="auth-shell">
        <div className="auth-brand brand">
          <span className="brand-mark">
            <Icon name="wave" size={25} />
          </span>
          <span>
            Word<strong>Speak</strong>
          </span>
        </div>
        {authPage ? children : <Busy>Đang mở WordSpeak…</Busy>}
      </main>
    );
  }

  function nav(
    key: Section | "/",
    label?: string,
    active = pathname === (key === "/" ? "/" : `/${key}`),
  ) {
    const [text, icon] = key === "/" ? ["Trang chủ", "home"] : sections[key];
    return (
      <Link
        key={key}
        href={key === "/" ? "/" : `/${key}`}
        className={`nav-link ${active ? "active" : ""}`}
        aria-current={active ? "page" : undefined}
        title={text}
        onClick={() => {
          setMenu(false);
          setProfileMenu(false);
        }}
      >
        <Icon name={icon} />
        <span>{label ?? text}</span>
      </Link>
    );
  }

  return (
    <div className={`shell ${collapsed ? "collapsed" : ""}`}>
      <a className="skip" href="#main">
        Đến nội dung
      </a>
      {menu && (
        <button className="nav-scrim" aria-label="Đóng điều hướng" onClick={() => setMenu(false)} />
      )}
      <aside className={`sidebar ${menu ? "is-open" : ""}`} id="sidebar">
        <Link className="brand" href="/" onClick={() => setMenu(false)}>
          <span className="brand-mark">
            <Icon name="wave" size={25} />
          </span>
          <span>
            Word<strong>Speak</strong>
          </span>
        </Link>
        <nav className="side-nav" aria-label="Điều hướng chính">
          {nav("/")}
          {groups.map((group) => (
            <div className="nav-group" key={group.title}>
              <span>{group.title}</span>
              {group.links.map((key) => nav(key))}
            </div>
          ))}
        </nav>
      </aside>
      <div className="workspace">
        <header className="topbar">
          <button
            type="button"
            className="icon-button desktop-menu"
            aria-label="Thu hoặc mở thanh điều hướng"
            aria-controls="sidebar"
            aria-expanded={!collapsed}
            onClick={() => setCollapsed(!collapsed)}
          >
            <Icon name="menu" />
          </button>
          <button
            type="button"
            className="icon-button mobile-menu"
            aria-label="Thu hoặc mở thanh điều hướng"
            aria-controls="sidebar"
            aria-expanded={menu}
            onClick={() => setMenu(!menu)}
          >
            <Icon name="menu" />
          </button>
          <span className="top-title">{title}</span>
          <div className="top-actions">
            <button
              type="button"
              className="icon-button"
              aria-label={dark ? "Bật giao diện sáng" : "Bật giao diện tối"}
              onClick={() => setTheme(dark ? "light" : "dark")}
            >
              <Icon name={dark ? "sun" : "moon"} />
            </button>
            <div
              className="profile-menu"
              onKeyDown={(event) => {
                if (event.key === "Escape") setProfileMenu(false);
              }}
            >
              <button
                type="button"
                className="button"
                aria-expanded={profileMenu}
                aria-controls="profile-menu"
                aria-label="Menu hồ sơ"
                onClick={() => setProfileMenu(!profileMenu)}
              >
                <span className="avatar">
                  <Icon name="user" size={16} />
                </span>
                <span className="profile-label">{profile.name || "Tài khoản"}</span>
                <Icon name="down" size={15} />
              </button>
              {profileMenu && (
                <div id="profile-menu" className="menu stack">
                  {nav("ho-so")}
                  <button
                    className="button"
                    onClick={() => {
                      logout();
                      setProfileMenu(false);
                      router.replace("/dang-nhap");
                    }}
                  >
                    Đăng xuất
                  </button>
                </div>
              )}
            </div>
          </div>
        </header>
        <main id="main" className="main">
          {children}
        </main>
        <footer className="footer">
          WordSpeak <span>·</span> Luyện nói tiếng Anh
        </footer>
      </div>
      <nav className="bottom-nav" aria-label="Điều hướng điện thoại">
        {mobile.map(([key, label, children]) =>
          nav(key, label, pathname === (key === "/" ? "/" : `/${key}`) || children.includes(section)),
        )}
      </nav>
    </div>
  );
}

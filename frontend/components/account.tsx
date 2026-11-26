"use client";

import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";
import { ApiError } from "@/lib/api";
import { useApp } from "./provider";
import { Action, Button, Busy, Empty, Notice, Panel, Title } from "./ui";

export function Auth({ register = false }: { register?: boolean }) {
  const { account, ready, authenticate } = useApp();
  const [visible, setVisible] = useState(false);
  const [emailError, setEmailError] = useState("");
  const [passwordError, setPasswordError] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const router = useRouter();
  const title = register ? "Đăng ký" : "Đăng nhập";

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (loading) return;
    const form = event.currentTarget;
    const fields = new FormData(form);
    const email = String(fields.get("email") ?? "").trim();
    const password = String(fields.get("password") ?? "");
    const emailMessage = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email) ? "" : "Nhập địa chỉ email hợp lệ.";
    const passwordMessage =
      password.length < 8
        ? "Mật khẩu cần ít nhất 8 ký tự."
        : new TextEncoder().encode(password).length > 72
          ? "Mật khẩu quá dài (tối đa 72 byte)."
          : "";
    setEmailError(emailMessage);
    setPasswordError(passwordMessage);
    setError("");
    if (emailMessage || passwordMessage) {
      (form.elements.namedItem(emailMessage ? "email" : "password") as HTMLInputElement).focus();
      return;
    }
    setLoading(true);
    try {
      await authenticate(register ? "register" : "login", email, password);
      router.replace("/");
    } catch (error) {
      setError(
        error instanceof ApiError &&
          error.status === 0 &&
          ["localhost", "127.0.0.1"].includes(location.hostname)
          ? "Chưa kết nối được máy chủ. Hãy khởi động WordSpeak bằng scripts/local.py rồi thử lại."
          : error instanceof Error
            ? error.message
            : "Không xử lý được tài khoản.",
      );
    } finally {
      setLoading(false);
    }
  }
  return (
    <div className="auth">
      <Title title={title}>
        {register
          ? "Tạo tài khoản để luyện cùng gia sư và xem tiến độ."
          : "Tiếp tục luyện với tài khoản WordSpeak của bạn."}
      </Title>
      {!ready ? (
        <Busy>Đang kiểm tra phiên đăng nhập…</Busy>
      ) : account ? (
        <Empty title="Bạn đã đăng nhập" icon="user">
          <Action href="/" primary>
            Mở trang chủ
          </Action>
        </Empty>
      ) : (
        <Panel className="stack">
          <form onSubmit={(event) => void submit(event)} className="stack" noValidate>
            <label className="field">
              Email
              <input
                autoComplete="email"
                type="email"
                name="email"
                required
                maxLength={255}
                aria-invalid={Boolean(emailError)}
                aria-describedby={emailError ? "email-problem" : undefined}
                disabled={loading}
              />
              {emailError && (
                <small id="email-problem" className="field-error">
                  {emailError}
                </small>
              )}
            </label>
            <div className="input-action">
              <label className="field">
                Mật khẩu
                <input
                  autoComplete={register ? "new-password" : "current-password"}
                  name="password"
                  required
                  type={visible ? "text" : "password"}
                  aria-invalid={Boolean(passwordError)}
                  aria-describedby={passwordError ? "password-problem" : undefined}
                  disabled={loading}
                />
              </label>
              <Button
                icon="eye"
                aria-label={visible ? "Ẩn mật khẩu" : "Hiện mật khẩu"}
                aria-pressed={visible}
                onClick={() => setVisible(!visible)}
              />
            </div>
            {passwordError && (
              <small id="password-problem" className="field-error">
                {passwordError}
              </small>
            )}
            {error && <Notice tone="error">{error}</Notice>}
            <Button type="submit" tone="primary" disabled={loading}>
              {loading ? "Đang gửi…" : title}
            </Button>
          </form>
          <p className="row">
            {register ? "Đã có tài khoản?" : "Chưa có tài khoản?"}{" "}
            <Action href={register ? "/dang-nhap" : "/dang-ky"}>
              {register ? "Đăng nhập" : "Đăng ký"}
            </Action>
          </p>
        </Panel>
      )}
    </div>
  );
}

export function Profile() {
  const { account, ready, profile, setProfile, logout, study } = useApp();
  const [message, setMessage] = useState("");
  const router = useRouter();
  return (
    <>
      <Title title="Hồ sơ">Quản lý thông tin hiển thị và xem những từ bạn đã học.</Title>
      {!ready ? (
        <Busy>Đang tải hồ sơ…</Busy>
      ) : !account ? (
        <Empty title="Bạn đang ở chế độ khách" icon="user">
          <p>Đăng nhập hoặc tạo tài khoản để mở hồ sơ.</p>
          <div className="row">
            <Action href="/dang-nhap" primary>
              Đăng nhập
            </Action>
            <Action href="/dang-ky">Đăng ký</Action>
          </div>
        </Empty>
      ) : (
        <div className="grid two">
          <Panel className="stack">
            <h2>Thông tin cá nhân</h2>
            <p>{account.email}</p>
            <form
              className="stack"
              key={account.id + profile.name + profile.level}
              onSubmit={(event) => {
                event.preventDefault();
                const fields = new FormData(event.currentTarget);
                setProfile({
                  name: String(fields.get("name") ?? "").trim(),
                  level: fields.get("level") as typeof profile.level,
                });
                setMessage("Đã lưu hồ sơ trên thiết bị này.");
              }}
            >
              <label className="field">
                Tên hiển thị
                <input
                  name="name"
                  maxLength={60}
                  defaultValue={profile.name}
                  placeholder="Tên bạn muốn sử dụng"
                />
              </label>
              <label className="field">
                Trình độ
                <select name="level" defaultValue={profile.level}>
                  <option>A2</option>
                  <option>B1</option>
                  <option>B2</option>
                </select>
              </label>
              <div className="row">
                <Button type="submit" tone="primary">
                  Lưu hồ sơ
                </Button>
                <Button
                  onClick={() => {
                    logout();
                    router.replace("/dang-nhap");
                  }}
                >
                  Đăng xuất
                </Button>
              </div>
              {message && <p role="status">{message}</p>}
            </form>
          </Panel>
          <Panel className="stack metric">
            <h2>Học tập</h2>
            <strong>{study.length}</strong>
            <p>Từ đã học trên thiết bị</p>
            <div>
              <Action href="/tien-do">Xem tiến độ</Action>
            </div>
          </Panel>
        </div>
      )}
    </>
  );
}

export function Settings() {
  const { theme, setTheme, motion, setMotion } = useApp();
  return (
    <>
      <Title title="Cài đặt">Cá nhân hóa giao diện học trên thiết bị này.</Title>
      <div className="grid two">
        <Panel className="stack">
          <h2>Giao diện</h2>
          <div className="row" role="group" aria-label="Chế độ màu">
            <Button icon="sun" aria-pressed={theme === "light"} onClick={() => setTheme("light")}>
              Sáng
            </Button>
            <Button icon="moon" aria-pressed={theme === "dark"} onClick={() => setTheme("dark")}>
              Tối
            </Button>
          </div>
          <label className="row">
            <input
              type="checkbox"
              checked={motion}
              onChange={(event) => setMotion(event.target.checked)}
            />{" "}
            Giảm chuyển động
          </label>
        </Panel>
        <Panel className="stack">
          <h2>Ngôn ngữ và dữ liệu</h2>
          <p>Giao diện: Tiếng Việt</p>
          <p>Tên hiển thị, từ đã lưu và lần tự luyện được lưu trên trình duyệt này.</p>
          <p>Khi chọn Kiểm tra hoặc luyện Talk, audio được gửi đến dịch vụ WordSpeak để xử lý.</p>
          <div>
            <Action href="/ho-so">Mở hồ sơ</Action>
          </div>
        </Panel>
      </div>
    </>
  );
}

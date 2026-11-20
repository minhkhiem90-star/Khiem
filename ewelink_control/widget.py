"""Widget nhỏ trên màn hình + phím tắt toàn cục để bật/tắt thiết bị eWeLink.

    python widget.py          # chạy thật (cần config.json)
    python widget.py --demo   # xem thử với thiết bị giả
"""
from __future__ import annotations

import json
import queue
import sys
import threading
import tkinter as tk
from tkinter import messagebox

from ewelink_api import (BASE_DIR, Channel, DemoClient, EWeLinkClient, EWeLinkError,
                         NeedLogin, find_channel, load_config)

STATE_PATH = BASE_DIR / "widget_state.json"

BG = "#1e1f24"
CARD = "#2a2c33"
CARD_HOVER = "#33363f"
FG = "#f2f2f5"
MUTED = "#8c8f99"
ON = "#f5b83d"
OFF = "#4a4d57"
DANGER = "#e5534b"
FONT = ("Segoe UI", 10) if sys.platform == "win32" else ("Helvetica", 12)
FONT_B = (FONT[0], FONT[1], "bold")
FONT_S = (FONT[0], FONT[1] - 2)


class Toggle(tk.Canvas):
    """Công tắc dạng viên thuốc."""

    W, H = 44, 24

    def __init__(self, master, command):
        super().__init__(master, width=self.W, height=self.H, bg=CARD,
                         highlightthickness=0, cursor="hand2")
        self.command = command
        self.bind("<Button-1>", lambda e: self.command())
        self.set(False, True)

    def set(self, on: bool, enabled: bool, busy: bool = False):
        self.delete("all")
        w, h, r = self.W, self.H, self.H // 2
        color = (ON if on else OFF) if enabled else "#3a3c44"
        self.create_oval(0, 0, h, h, fill=color, outline=color)
        self.create_oval(w - h, 0, w, h, fill=color, outline=color)
        self.create_rectangle(r, 0, w - r, h, fill=color, outline=color)
        x = w - h + 3 if on else 3
        knob = "#ffffff" if enabled else "#6b6e78"
        self.create_oval(x, 3, x + h - 6, h - 3, fill=knob, outline=knob)
        if busy:
            self.create_text(w / 2, h / 2, text="…", fill=BG, font=FONT_B)

    def set_bg(self, color):
        self.configure(bg=color)


class Row(tk.Frame):
    def __init__(self, master, app: "App", ch: Channel, hotkey: str | None):
        super().__init__(master, bg=CARD, padx=12, pady=8, cursor="hand2")
        self.app, self.ch = app, ch
        self.dot = tk.Label(self, text="●", bg=CARD, font=FONT_S)
        self.dot.grid(row=0, column=0, rowspan=2, padx=(0, 8))
        self.name = tk.Label(self, text=ch.name, bg=CARD, fg=FG, font=FONT, anchor="w")
        self.name.grid(row=0, column=1, sticky="w")
        sub = pretty_hotkey(hotkey) if hotkey else ("Mất kết nối" if not ch.online else "")
        self.sub = tk.Label(self, text=sub, bg=CARD, fg=MUTED, font=FONT_S, anchor="w")
        self.sub.grid(row=1, column=1, sticky="w")
        self.toggle = Toggle(self, command=self.click)
        self.toggle.grid(row=0, column=2, rowspan=2, padx=(10, 0))
        self.columnconfigure(1, weight=1)
        for w in (self, self.dot, self.name, self.sub):
            w.bind("<Button-1>", lambda e: self.click())
            w.bind("<Enter>", lambda e: self.hover(True))
            w.bind("<Leave>", lambda e: self.hover(False))
        self.render()

    def hover(self, on):
        c = CARD_HOVER if on else CARD
        for w in (self, self.dot, self.name, self.sub):
            w.configure(bg=c)
        self.toggle.set_bg(c)

    def click(self):
        self.app.toggle(self.ch)

    def render(self, busy=False):
        self.dot.configure(fg=(ON if self.ch.on else MUTED) if self.ch.online else DANGER)
        self.name.configure(fg=FG if self.ch.online else MUTED)
        self.toggle.set(self.ch.on, self.ch.online, busy)


def pretty_hotkey(hk: str) -> str:
    parts = [p.strip("<>").capitalize() for p in hk.split("+")]
    return "Phím tắt: " + " + ".join(parts)


class App:
    def __init__(self, demo: bool):
        self.demo = demo
        self.ui_q: queue.Queue = queue.Queue()
        self.channels: list[Channel] = []
        self.rows: dict[str, Row] = {}
        self.busy: set[str] = set()
        self.hotkey_listener = None

        if demo:
            self.cfg = {"hotkeys": {"<ctrl>+<alt>+1": "Đèn phòng khách",
                                    "<ctrl>+<alt>+2": "Đèn phòng ngủ",
                                    "<ctrl>+<alt>+0": "ALL_OFF"},
                        "refresh_seconds": 30, "always_on_top": True}
            self.client = DemoClient()
        else:
            self.cfg = load_config()
            self.client = EWeLinkClient.from_config(self.cfg)

        self.root = tk.Tk()
        self.root.title("eWeLink" + (" (demo)" if demo else ""))
        self.root.configure(bg=BG)
        self.root.minsize(320, 120)
        self.root.resizable(False, False)
        self.topmost = bool(self.cfg.get("always_on_top", True))
        self.root.attributes("-topmost", self.topmost)
        self.restore_geometry()
        self.root.protocol("WM_DELETE_WINDOW", self.quit)

        self.build_header()
        self.body = tk.Frame(self.root, bg=BG, padx=10)
        self.body.pack(fill="both", expand=True)
        self.status = tk.Label(self.root, text="", bg=BG, fg=MUTED, font=FONT_S, anchor="w",
                               padx=12, pady=6)
        self.status.pack(fill="x")

        self.root.after(50, self.pump)
        self.start_hotkeys()
        if self.client.logged_in:
            self.refresh()
        else:
            self.show_login()
        self.schedule_refresh()

    # ------------------------------------------------------------------ UI parts
    def build_header(self):
        h = tk.Frame(self.root, bg=BG, padx=12, pady=10)
        h.pack(fill="x")
        tk.Label(h, text="💡 Nhà thông minh", bg=BG, fg=FG, font=FONT_B).pack(side="left")

        def btn(text, cmd, tip_color=MUTED):
            b = tk.Label(h, text=text, bg=BG, fg=tip_color, font=FONT, cursor="hand2", padx=4)
            b.bind("<Button-1>", lambda e: cmd())
            b.pack(side="right")
            return b

        self.pin_btn = btn("📌", self.toggle_pin)
        btn("⟳", self.refresh)
        btn("Tắt hết", lambda: self.set_all(False), DANGER)
        self.update_pin()

    def toggle_pin(self):
        self.topmost = not self.topmost
        self.root.attributes("-topmost", self.topmost)
        self.update_pin()

    def update_pin(self):
        self.pin_btn.configure(fg=ON if self.topmost else MUTED)

    def show_login(self):
        for w in self.body.winfo_children():
            w.destroy()
        box = tk.Frame(self.body, bg=CARD, padx=16, pady=16)
        box.pack(fill="x", pady=(0, 6))
        tk.Label(box, text="Chưa đăng nhập eWeLink", bg=CARD, fg=FG, font=FONT_B).pack()
        tk.Label(box, text="Bấm nút dưới để mở trình duyệt\nvà đăng nhập tài khoản eWeLink.",
                 bg=CARD, fg=MUTED, font=FONT_S, justify="center").pack(pady=6)
        b = tk.Label(box, text="Đăng nhập", bg=ON, fg=BG, font=FONT_B, padx=16, pady=6,
                     cursor="hand2")
        b.bind("<Button-1>", lambda e: self.login())
        b.pack(pady=(4, 0))
        self.set_status("")

    def render_channels(self):
        for w in self.body.winfo_children():
            w.destroy()
        self.rows.clear()
        hk_by_key = {}
        for hk, target in self.cfg.get("hotkeys", {}).items():
            name = target if isinstance(target, str) else target.get("device", "")
            try:
                hk_by_key.setdefault(find_channel(self.channels, name).key, hk)
            except EWeLinkError:
                pass
        if not self.channels:
            tk.Label(self.body, text="Không có thiết bị nào", bg=BG, fg=MUTED,
                     font=FONT).pack(pady=12)
        for ch in self.channels:
            row = Row(self.body, self, ch, hk_by_key.get(ch.key))
            row.pack(fill="x", pady=(0, 6))
            self.rows[ch.key] = row

    def set_status(self, text, error=False):
        self.status.configure(text=text, fg=DANGER if error else MUTED)

    def toast(self, text, on: bool | None = None):
        t = tk.Toplevel(self.root)
        t.overrideredirect(True)
        t.attributes("-topmost", True)
        color = ON if on else (OFF if on is False else CARD)
        f = tk.Frame(t, bg=CARD, padx=16, pady=10, highlightthickness=2,
                     highlightbackground=color)
        f.pack()
        tk.Label(f, text=text, bg=CARD, fg=FG, font=FONT_B).pack()
        t.update_idletasks()
        sw, sh = t.winfo_screenwidth(), t.winfo_screenheight()
        t.geometry(f"+{sw - t.winfo_width() - 24}+{sh - t.winfo_height() - 80}")
        t.after(1600, t.destroy)

    # ------------------------------------------------------------------ threading
    def run_bg(self, fn, done=None, fail=None):
        def worker():
            try:
                res = fn()
            except NeedLogin as e:
                self.ui_q.put(lambda: (self.show_login(), self.set_status(str(e), True)))
                return
            except Exception as e:  # noqa: BLE001
                msg = str(e)
                self.ui_q.put(lambda: (fail and fail(), self.set_status(msg, True)))
                return
            if done:
                self.ui_q.put(lambda: done(res))
        threading.Thread(target=worker, daemon=True).start()

    def pump(self):
        try:
            while True:
                self.ui_q.get_nowait()()
        except queue.Empty:
            pass
        self.root.after(50, self.pump)

    # ------------------------------------------------------------------ actions
    def login(self):
        self.set_status("Đang chờ đăng nhập trên trình duyệt…")

        def done(_):
            self.set_status("Đăng nhập thành công")
            self.refresh()
        self.run_bg(lambda: self.client.login_interactive(on_status=lambda s: None), done)

    def refresh(self):
        if not self.client.logged_in:
            return
        self.set_status("Đang tải thiết bị…")

        def done(chans):
            self.channels = chans
            self.busy.clear()
            self.render_channels()
            self.set_status(f"{len(chans)} thiết bị · cập nhật lúc {self.now()}")
        self.run_bg(self.client.list_channels, done)

    def schedule_refresh(self):
        secs = int(self.cfg.get("refresh_seconds", 30))
        if secs > 0:
            def tick():
                if not self.busy:
                    self.refresh()
                self.root.after(secs * 1000, tick)
            self.root.after(secs * 1000, tick)

    def toggle(self, ch: Channel, turn_on: bool | None = None, notify=False):
        if ch.key in self.busy:
            return
        if not ch.online:
            self.set_status(f"'{ch.name}' đang mất kết nối", True)
            if notify:
                self.toast(f"⚠ {ch.name}: mất kết nối")
            return
        target = (not ch.on) if turn_on is None else turn_on
        self.busy.add(ch.key)
        row = self.rows.get(ch.key)
        if row:
            row.render(busy=True)

        def done(_):
            self.busy.discard(ch.key)
            if row:
                row.render()
            self.set_status(f"{ch.name}: {'BẬT' if target else 'TẮT'}")
            if notify:
                self.toast(f"{'💡' if target else '⚫'} {ch.name}: {'BẬT' if target else 'TẮT'}",
                           target)

        def fail():
            self.busy.discard(ch.key)
            if row:
                row.render()
        self.run_bg(lambda: self.client.set_channel(ch, target), done, fail)

    def set_all(self, turn_on: bool, notify=False):
        for ch in self.channels:
            if ch.online and ch.on != turn_on:
                self.toggle(ch, turn_on)
        if notify:
            self.toast("💡 Bật tất cả" if turn_on else "⚫ Tắt tất cả", turn_on)

    def show_window(self):
        self.root.deiconify()
        self.root.lift()
        self.root.attributes("-topmost", True)
        if not self.topmost:
            self.root.after(300, lambda: self.root.attributes("-topmost", False))

    # ------------------------------------------------------------------ hotkeys
    def on_hotkey(self, target):
        if isinstance(target, str):
            name, action = target, "toggle"
        else:
            name, action = target.get("device", ""), target.get("action", "toggle")
        special = name.upper()
        if special == "ALL_OFF":
            return self.set_all(False, notify=True)
        if special == "ALL_ON":
            return self.set_all(True, notify=True)
        if special == "SHOW":
            return self.show_window()
        try:
            ch = find_channel(self.channels, name)
        except EWeLinkError as e:
            self.set_status(str(e), True)
            self.toast(f"⚠ {e}")
            return
        turn_on = None if action == "toggle" else action == "on"
        self.toggle(ch, turn_on, notify=True)

    def start_hotkeys(self):
        hotkeys = self.cfg.get("hotkeys") or {}
        if not hotkeys:
            return
        try:
            from pynput import keyboard
        except ImportError:
            self.set_status("Chưa cài pynput → phím tắt chưa hoạt động (pip install pynput)", True)
            return
        mapping = {hk: (lambda t=t: self.ui_q.put(lambda: self.on_hotkey(t)))
                   for hk, t in hotkeys.items()}
        try:
            self.hotkey_listener = keyboard.GlobalHotKeys(mapping)
            self.hotkey_listener.daemon = True
            self.hotkey_listener.start()
        except Exception as e:  # noqa: BLE001
            self.set_status(f"Phím tắt lỗi: {e}", True)

    # ------------------------------------------------------------------ misc
    @staticmethod
    def now():
        import time
        return time.strftime("%H:%M")

    def restore_geometry(self):
        try:
            pos = json.loads(STATE_PATH.read_text(encoding="utf-8")).get("pos")
            if pos:
                self.root.geometry(pos)
        except (OSError, ValueError):
            pass

    def quit(self):
        try:
            STATE_PATH.write_text(json.dumps(
                {"pos": f"+{self.root.winfo_x()}+{self.root.winfo_y()}"}), encoding="utf-8")
        except OSError:
            pass
        if self.hotkey_listener:
            self.hotkey_listener.stop()
        self.root.destroy()

    def run(self):
        self.root.mainloop()


def main():
    demo = "--demo" in sys.argv
    try:
        App(demo).run()
    except EWeLinkError as e:
        r = tk.Tk()
        r.withdraw()
        messagebox.showerror("eWeLink", str(e))


if __name__ == "__main__":
    main()

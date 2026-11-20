"""Bật/tắt thiết bị (qua Home Assistant hoặc eWeLink) bằng dòng lệnh.

    python ewelink_ctl.py list                  # liệt kê thiết bị
    python ewelink_ctl.py toggle "Đèn phòng khách"
    python ewelink_ctl.py on  "Đèn bếp"
    python ewelink_ctl.py off all               # tắt hết

Có thể gán các lệnh này cho phím tắt của hệ điều hành, Stream Deck, AutoHotkey…
"""
import sys

from ewelink_api import DemoClient, EWeLinkError, find_channel, load_config, make_client


def main(argv: list[str]) -> int:
    demo = "--demo" in argv
    argv = [a for a in argv if a != "--demo"]
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    cmd, rest = argv[0], " ".join(argv[1:])
    try:
        client = DemoClient() if demo else make_client(load_config())
        if cmd == "login":
            client.login_interactive()
            return 0
        chans = client.list_channels()
        if cmd == "list":
            for c in chans:
                state = "BẬT" if c.on else "tắt"
                online = "" if c.online else "  (mất kết nối)"
                print(f"{state:4}  {c.name:30}  {c.key}{online}")
            return 0
        if cmd in ("on", "off", "toggle"):
            targets = chans if rest.lower() == "all" else [find_channel(chans, rest)]
            for c in targets:
                if not c.online:
                    print(f"Bỏ qua '{c.name}' (thiết bị đang mất kết nối)")
                    continue
                turn_on = (not c.on) if cmd == "toggle" else (cmd == "on")
                client.set_channel(c, turn_on)
                print(f"{c.name}: {'BẬT' if turn_on else 'TẮT'}")
            return 0
        print(f"Lệnh không hợp lệ: {cmd}\n{__doc__}")
        return 2
    except EWeLinkError as e:
        print(f"Lỗi: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

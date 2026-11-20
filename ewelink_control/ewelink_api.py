"""Thư viện nhỏ gọi eWeLink Cloud API v2 (chỉ dùng khi KHÔNG dùng Home Assistant) (CoolKit) – chỉ dùng thư viện chuẩn của Python.

Luồng đăng nhập: OAuth 2.0 (cách chính thức cho tài khoản nhà phát triển miễn phí
tại https://dev.ewelink.cc). Token được lưu vào token.json và tự làm mới.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import random
import string
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.json"
TOKEN_PATH = BASE_DIR / "token.json"

API_HOSTS = {
    "cn": "https://cn-apia.coolkit.cn",
    "as": "https://as-apia.coolkit.cc",
    "us": "https://us-apia.coolkit.cc",
    "eu": "https://eu-apia.coolkit.cc",
}
OAUTH_PAGE = "https://c2ccdn.coolkit.cc/oauth/index.html"


class EWeLinkError(Exception):
    pass


class NeedLogin(EWeLinkError):
    pass


# --------------------------------------------------------------------------- config
def load_config() -> dict:
    if not CONFIG_PATH.exists():
        raise EWeLinkError(
            f"Chưa có file cấu hình {CONFIG_PATH.name}. Hãy copy config.example.json "
            "thành config.json rồi điền app_id / app_secret."
        )
    with CONFIG_PATH.open(encoding="utf-8") as f:
        cfg = json.load(f)
    cfg.setdefault("region", "as")
    cfg.setdefault("redirect_url", "http://127.0.0.1:8765/callback")
    cfg.setdefault("hotkeys", {})
    return cfg


# --------------------------------------------------------------------------- models
@dataclass
class Channel:
    """Một nút bật/tắt được: cả thiết bị 1 kênh, hoặc 1 kênh của công tắc nhiều nút."""

    device_id: str
    name: str
    online: bool
    on: bool
    style: str  # "switch" | "switches" | "state"
    outlet: int | None = None
    device_name: str = ""

    @property
    def key(self) -> str:
        return self.device_id if self.outlet is None else f"{self.device_id}:{self.outlet}"

    def params_for(self, turn_on: bool) -> dict:
        val = "on" if turn_on else "off"
        if self.style == "switches":
            return {"switches": [{"switch": val, "outlet": self.outlet}]}
        if self.style == "state":
            return {"state": val}
        return {"switch": val}


def channels_from_thing(item: dict) -> list[Channel]:
    data = item.get("itemData") or {}
    dev_id = data.get("deviceid")
    if not dev_id:
        return []
    name = data.get("name") or dev_id
    online = bool(data.get("online"))
    params = data.get("params") or {}
    out: list[Channel] = []

    if isinstance(params.get("switches"), list) and params["switches"]:
        names = ((data.get("tags") or {}).get("ck_channel_name") or {})
        sw_list = params["switches"]
        if names:  # chỉ lấy các kênh mà người dùng đã đặt tên trong app
            wanted = {int(k) for k in names.keys() if str(k).isdigit()}
            sw_list = [s for s in sw_list if s.get("outlet") in wanted] or sw_list
        for s in sw_list:
            outlet = int(s.get("outlet", 0))
            ch_name = names.get(str(outlet)) or f"{name} - nút {outlet + 1}"
            if len(sw_list) == 1:
                ch_name = name
            out.append(Channel(dev_id, ch_name, online, s.get("switch") == "on",
                               "switches", outlet, name))
    elif params.get("switch") in ("on", "off"):
        out.append(Channel(dev_id, name, online, params["switch"] == "on", "switch", None, name))
    elif params.get("state") in ("on", "off"):
        out.append(Channel(dev_id, name, online, params["state"] == "on", "state", None, name))
    return out


# --------------------------------------------------------------------------- client
def _nonce(n: int = 8) -> str:
    return "".join(random.choices(string.ascii_letters + string.digits, k=n))


def _sign(secret: str, message: str) -> str:
    digest = hmac.new(secret.encode(), message.encode(), hashlib.sha256).digest()
    return base64.b64encode(digest).decode()


@dataclass
class EWeLinkClient:
    app_id: str
    app_secret: str
    region: str = "as"
    redirect_url: str = "http://127.0.0.1:8765/callback"
    token: dict = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    @classmethod
    def from_config(cls, cfg: dict | None = None) -> "EWeLinkClient":
        cfg = cfg or load_config()
        for key in ("app_id", "app_secret"):
            if not cfg.get(key) or "DIEN_" in str(cfg.get(key)):
                raise EWeLinkError(f"Chưa điền '{key}' trong config.json")
        c = cls(cfg["app_id"], cfg["app_secret"], cfg["region"], cfg["redirect_url"])
        if TOKEN_PATH.exists():
            try:
                c.token = json.loads(TOKEN_PATH.read_text(encoding="utf-8"))
                c.region = c.token.get("region", c.region)
            except (OSError, ValueError):
                c.token = {}
        return c

    # ---- low level
    @property
    def host(self) -> str:
        return API_HOSTS.get(self.region, API_HOSTS["as"])

    def _request(self, method: str, path: str, body: dict | None = None,
                 query: dict | None = None, auth: str = "bearer") -> dict:
        url = self.host + path
        if query:
            url += "?" + urllib.parse.urlencode(query)
        data = None
        headers = {
            "Content-Type": "application/json",
            "X-CK-Appid": self.app_id,
            "X-CK-Nonce": _nonce(),
        }
        if body is not None:
            raw = json.dumps(body, separators=(",", ":"), ensure_ascii=False)
            data = raw.encode("utf-8")
        if auth == "sign":
            headers["Authorization"] = "Sign " + _sign(self.app_secret, raw if body is not None else "")
        else:
            at = self.token.get("at")
            if not at:
                raise NeedLogin("Chưa đăng nhập eWeLink")
            headers["Authorization"] = "Bearer " + at
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            raise EWeLinkError(f"HTTP {e.code}: {e.read().decode('utf-8', 'ignore')[:200]}")
        except urllib.error.URLError as e:
            raise EWeLinkError(f"Không kết nối được máy chủ eWeLink: {e.reason}")
        return payload

    def _call(self, method: str, path: str, body: dict | None = None,
              query: dict | None = None) -> dict:
        """Gọi API có Bearer token, tự làm mới token khi hết hạn."""
        with self._lock:
            if self.token.get("atExpiredTime", 0) and self.token["atExpiredTime"] / 1000 < time.time() + 60:
                self.refresh()
            res = self._request(method, path, body, query)
            if res.get("error") in (401, 402):
                self.refresh()
                res = self._request(method, path, body, query)
        if res.get("error") != 0:
            raise EWeLinkError(f"eWeLink lỗi {res.get('error')}: {res.get('msg')}")
        return res.get("data") or {}

    def _save_token(self) -> None:
        self.token["region"] = self.region
        TOKEN_PATH.write_text(json.dumps(self.token, indent=2), encoding="utf-8")

    # ---- auth
    def oauth_url(self, state: str) -> str:
        seq = str(int(time.time() * 1000))
        q = {
            "state": state,
            "clientId": self.app_id,
            "authorization": _sign(self.app_secret, f"{self.app_id}_{seq}"),
            "seq": seq,
            "redirectUrl": self.redirect_url,
            "nonce": _nonce(),
            "grantType": "authorization_code",
            "showQRCode": "false",
        }
        return OAUTH_PAGE + "?" + urllib.parse.urlencode(q)

    def exchange_code(self, code: str, region: str | None = None) -> None:
        if region:
            self.region = region
        res = self._request("POST", "/v2/user/oauth/token", {
            "code": code,
            "redirectUrl": self.redirect_url,
            "grantType": "authorization_code",
        }, auth="sign")
        if res.get("error") != 0:
            raise EWeLinkError(f"Đổi mã đăng nhập thất bại ({res.get('error')}): {res.get('msg')}")
        d = res["data"]
        self.token = {
            "at": d["accessToken"], "rt": d["refreshToken"],
            "atExpiredTime": d.get("atExpiredTime", 0), "rtExpiredTime": d.get("rtExpiredTime", 0),
        }
        self._save_token()

    def refresh(self) -> None:
        rt = self.token.get("rt")
        if not rt:
            raise NeedLogin("Chưa đăng nhập eWeLink")
        res = self._request("POST", "/v2/user/refresh", {"rt": rt})
        if res.get("error") != 0:
            self.token = {}
            TOKEN_PATH.unlink(missing_ok=True)
            raise NeedLogin("Phiên đăng nhập đã hết hạn, hãy đăng nhập lại")
        d = res["data"]
        now_ms = int(time.time() * 1000)
        self.token.update({
            "at": d["at"], "rt": d["rt"],
            # access token sống 30 ngày; đặt mốc an toàn 25 ngày
            "atExpiredTime": now_ms + 25 * 86400 * 1000,
        })
        self._save_token()

    def login_interactive(self, on_status=print, timeout: int = 300) -> None:
        """Mở trình duyệt để đăng nhập, chờ eWeLink chuyển hướng về máy local."""
        state = _nonce(12)
        result: dict = {}
        parsed = urllib.parse.urlparse(self.redirect_url)
        local = parsed.hostname in ("127.0.0.1", "localhost")

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):  # noqa: N802
                q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
                if "code" in q:
                    result.update({k: v[0] for k, v in q.items()})
                    msg = "Đăng nhập thành công! Anh có thể đóng tab này và quay lại ứng dụng."
                else:
                    msg = "Không nhận được mã đăng nhập."
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(f"<h2 style='font-family:sans-serif'>{msg}</h2>".encode())

            def log_message(self, *a):
                pass

        if not local:
            raise EWeLinkError("redirect_url phải có dạng http://127.0.0.1:<port>/callback")
        server = HTTPServer((parsed.hostname, parsed.port or 80), Handler)
        server.timeout = 1
        on_status("Đang mở trình duyệt để đăng nhập eWeLink…")
        webbrowser.open(self.oauth_url(state))
        deadline = time.time() + timeout
        try:
            while "code" not in result and time.time() < deadline:
                server.handle_request()
        finally:
            server.server_close()
        if "code" not in result:
            raise EWeLinkError("Hết thời gian chờ đăng nhập")
        if result.get("state") and result["state"] != state:
            raise EWeLinkError("Sai mã state – hãy thử đăng nhập lại")
        self.exchange_code(result["code"], result.get("region"))
        on_status("Đăng nhập thành công")

    @property
    def logged_in(self) -> bool:
        return bool(self.token.get("at"))

    # ---- devices
    def list_channels(self) -> list[Channel]:
        data = self._call("GET", "/v2/device/thing", query={"num": 0})
        chans: list[Channel] = []
        for item in data.get("thingList", []):
            if item.get("itemType") in (1, 2):  # 1 = của mình, 2 = được chia sẻ
                chans.extend(channels_from_thing(item))
        return chans

    def set_channel(self, ch: Channel, turn_on: bool) -> None:
        self._call("POST", "/v2/device/thing/status", {
            "type": 1, "id": ch.device_id, "params": ch.params_for(turn_on),
        })
        ch.on = turn_on


def make_client(cfg: dict):
    """Có 'ha_url' trong config → dùng Home Assistant, ngược lại dùng eWeLink Cloud."""
    if cfg.get("ha_url") or cfg.get("ha_token"):
        from ha_api import HAClient
        return HAClient.from_config(cfg)
    return EWeLinkClient.from_config(cfg)


class DemoClient:
    """Thiết bị giả để xem thử giao diện khi chưa có tài khoản nhà phát triển."""

    logged_in = True

    def __init__(self):
        self._chans = [
            Channel("1000aa0001", "Đèn phòng khách", True, True, "switch"),
            Channel("1000aa0002", "Đèn phòng ngủ", True, False, "switch"),
            Channel("1000aa0003", "Đèn bếp", True, False, "switches", 0, "Công tắc bếp"),
            Channel("1000aa0003", "Quạt hút bếp", True, True, "switches", 1, "Công tắc bếp"),
            Channel("1000aa0004", "Đèn cổng", False, False, "switch"),
        ]

    def list_channels(self):
        time.sleep(0.2)
        return [Channel(**{k: getattr(c, k) for k in c.__dataclass_fields__}) for c in self._chans]

    def set_channel(self, ch, turn_on):
        time.sleep(0.2)
        for c in self._chans:
            if c.key == ch.key:
                c.on = turn_on
        ch.on = turn_on

    def login_interactive(self, on_status=print, timeout=300):
        pass


def find_channel(chans: list[Channel], query: str) -> Channel:
    q = query.strip().lower()
    for c in chans:
        if c.key.lower() == q or c.name.lower() == q:
            return c
    matches = [c for c in chans if q in c.name.lower()]
    if len(matches) == 1:
        return matches[0]
    if not matches:
        raise EWeLinkError(f"Không tìm thấy thiết bị '{query}'")
    raise EWeLinkError(f"'{query}' khớp nhiều thiết bị: " + ", ".join(c.name for c in matches))

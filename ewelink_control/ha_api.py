"""Điều khiển thiết bị qua Home Assistant REST API (chạy trong mạng nội bộ).

Cần: địa chỉ Home Assistant (vd http://homeassistant.local:8123) và
"Long-lived access token" tạo trong trang Hồ sơ (Profile → Security) của HA.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request

from ewelink_api import Channel, EWeLinkError, NeedLogin

DEFAULT_DOMAINS = ("light", "switch", "fan", "input_boolean")


class HAClient:
    def __init__(self, url: str, token: str, entities: list[str] | None = None,
                 domains: list[str] | None = None):
        self.url = url.rstrip("/")
        self.token = token
        self.entities = entities or []
        self.domains = tuple(domains or DEFAULT_DOMAINS)

    @classmethod
    def from_config(cls, cfg: dict) -> "HAClient":
        token = cfg.get("ha_token", "")
        if not token or "DIEN_" in token:
            raise EWeLinkError("Chưa điền 'ha_token' trong config.json "
                               "(tạo ở Home Assistant → Hồ sơ → Bảo mật → Long-lived access tokens)")
        return cls(cfg.get("ha_url", "http://homeassistant.local:8123"), token,
                   cfg.get("entities"), cfg.get("domains"))

    @property
    def logged_in(self) -> bool:
        return bool(self.token)

    def login_interactive(self, on_status=print, timeout=0):
        raise EWeLinkError("Hãy điền ha_token trong config.json")

    def _req(self, method: str, path: str, body: dict | None = None):
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(self.url + path, data=data, method=method, headers={
            "Authorization": "Bearer " + self.token,
            "Content-Type": "application/json",
        })
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return json.loads(r.read().decode() or "null")
        except urllib.error.HTTPError as e:
            if e.code == 401:
                raise NeedLogin("Token Home Assistant sai hoặc đã bị xoá")
            raise EWeLinkError(f"Home Assistant báo lỗi HTTP {e.code}")
        except urllib.error.URLError as e:
            raise EWeLinkError(f"Không kết nối được Home Assistant tại {self.url} ({e.reason})")

    def list_channels(self) -> list[Channel]:
        states = self._req("GET", "/api/states") or []
        by_id = {s["entity_id"]: s for s in states}
        if self.entities:
            picked = [by_id[e] for e in self.entities if e in by_id]
        else:
            picked = sorted((s for s in states if s["entity_id"].split(".")[0] in self.domains
                             and not s.get("attributes", {}).get("hidden")),
                            key=lambda s: s.get("attributes", {}).get("friendly_name", ""))
        out = []
        for s in picked:
            name = s.get("attributes", {}).get("friendly_name") or s["entity_id"]
            online = s.get("state") not in ("unavailable", "unknown")
            out.append(Channel(s["entity_id"], name, online, s.get("state") == "on", "ha"))
        return out

    def set_channel(self, ch: Channel, turn_on: bool) -> None:
        service = "turn_on" if turn_on else "turn_off"
        self._req("POST", f"/api/services/homeassistant/{service}", {"entity_id": ch.device_id})
        ch.on = turn_on

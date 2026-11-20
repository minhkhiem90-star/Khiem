# Điều khiển đèn & công tắc nhà thông minh trên máy tính

> **Cách khuyên dùng: qua Home Assistant** (gom cả eWeLink lẫn Tuya, chạy trong mạng nhà, không cần tài khoản nhà phát triển).
> 👉 Làm theo **[HUONG_DAN_HOME_ASSISTANT.md](HUONG_DAN_HOME_ASSISTANT.md)** từ đầu đến cuối.
>
> Phần bên dưới mô tả cách dùng widget/phím tắt và **cách cũ** kết nối thẳng eWeLink Cloud (cần tài khoản nhà phát triển, chỉ dùng khi không có Home Assistant).

Công cụ có 3 cách điều khiển:

| Cách | Mô tả |
|---|---|
| **Widget** | Cửa sổ nhỏ luôn nổi trên màn hình, mỗi thiết bị có một nút gạt bật/tắt |
| **Phím tắt** | Bấm ví dụ `Ctrl + Alt + 1` ở bất kỳ đâu để bật/tắt đèn, góc màn hình hiện thông báo |
| **Dòng lệnh** | `python ewelink_ctl.py toggle "Đèn phòng khách"` (dùng được với AutoHotkey, Stream Deck…) |

---

## (Cách cũ) Kết nối thẳng eWeLink Cloud

Trong `config.json` bỏ `ha_url`/`ha_token` và thêm `app_id`, `app_secret`, `region`, `redirect_url`.

### Bước 1 – Cài Python (làm 1 lần)

- **Windows:** tải ở https://www.python.org/downloads/ → khi cài **nhớ tick "Add python.exe to PATH"**.
- **Mac:** tải ở cùng địa chỉ trên và cài bình thường.

### Bước 2 – Lấy mã App ID / App Secret (làm 1 lần, miễn phí)

eWeLink yêu cầu ứng dụng bên ngoài phải có mã nhà phát triển:

1. Vào https://dev.ewelink.cc và đăng nhập bằng **chính tài khoản eWeLink** đang dùng trên điện thoại.
2. Đăng ký làm nhà phát triển cá nhân (miễn phí), sau đó vào **Console → Create App** (tạo ứng dụng).
3. Ở ô **Redirect URL** điền chính xác:
   ```
   http://127.0.0.1:8765/callback
   ```
4. Tạo xong, anh sẽ thấy **APPID** và **APP SECRET**.

### Bước 3 – Điền cấu hình

1. Trong thư mục `ewelink_control`, copy file `config.example.json` và đổi tên bản copy thành `config.json`.
2. Mở `config.json` bằng Notepad, điền `app_id` và `app_secret`.
3. `region`: tài khoản ở Việt Nam thường là `"as"` (châu Á). Các giá trị khác: `"eu"`, `"us"`, `"cn"`.

### Bước 4 – Chạy

- **Windows:** nháy đúp `Chay_tren_Windows.bat`
- **Mac:** nháy đúp `Chay_tren_Mac.command` (lần đầu: chuột phải → Open)

Lần đầu, widget hiện nút **Đăng nhập**. Bấm vào, trình duyệt sẽ mở trang eWeLink. Anh đăng nhập và đồng ý cấp quyền, sau đó danh sách đèn và công tắc hiện ra trong widget. Thông tin đăng nhập được lưu vào `token.json` và tự gia hạn, nên những lần sau không phải đăng nhập lại.

Có thể chạy thử giao diện với thiết bị giả trước khi có mã: `python widget.py --demo`

---

## Cài phím tắt

Sửa phần `hotkeys` trong `config.json`, rồi tắt widget và mở lại:

```json
"hotkeys": {
  "<ctrl>+<alt>+1": "Đèn phòng khách",
  "<ctrl>+<alt>+2": { "device": "Đèn ngủ", "action": "on" },
  "<ctrl>+<alt>+3": { "device": "Đèn ngủ", "action": "off" },
  "<ctrl>+<alt>+0": "ALL_OFF",
  "<ctrl>+<alt>+e": "SHOW"
}
```

- Tên thiết bị phải **giống tên trong app eWeLink**. Không phân biệt hoa thường, và gõ một phần tên cũng được nếu không trùng với thiết bị khác.
- `action`: `toggle` (đảo trạng thái, mặc định), `on` hoặc `off`.
- Lệnh đặc biệt: `ALL_OFF` (tắt hết), `ALL_ON` (bật hết), `SHOW` (gọi widget lên trước).
- Các phím có thể dùng: `<ctrl>`, `<alt>`, `<shift>`, `<cmd>` (phím Windows/Command), `<f1>`…`<f12>`, chữ cái, số.
- **Mac:** lần đầu phải cấp quyền tại *System Settings → Privacy & Security → Accessibility* (và *Input Monitoring*) cho Terminal/Python, nếu không phím tắt sẽ không hoạt động.

## Các nút trên widget

- Bấm vào một dòng hoặc nút gạt để bật/tắt thiết bị đó.
- **Tắt hết**: tắt mọi thiết bị đang bật.
- **⟳**: tải lại trạng thái. Widget cũng tự cập nhật mỗi 30 giây (đổi bằng `refresh_seconds`).
- **📌**: bật/tắt chế độ luôn nổi trên các cửa sổ khác.
- Chấm đỏ kèm chữ "Mất kết nối" nghĩa là thiết bị đang offline (mất điện hoặc mất wifi).

## Tự chạy khi mở máy

- **Windows:** nhấn `Win + R`, gõ `shell:startup` rồi Enter. Chuột phải vào `Chay_tren_Windows.bat` → *Create shortcut*, sau đó kéo shortcut vừa tạo vào thư mục Startup.
- **Mac:** *System Settings → General → Login Items* → bấm **+** và chọn `Chay_tren_Mac.command`.

## Dòng lệnh

```bash
python ewelink_ctl.py list
python ewelink_ctl.py toggle "Đèn phòng khách"
python ewelink_ctl.py on "Đèn bếp"
python ewelink_ctl.py off all
```

## Gặp lỗi?

| Lỗi | Cách xử lý |
|---|---|
| Không thấy thiết bị nào | Kiểm tra lại `region` trong `config.json` |
| Lỗi redirect khi đăng nhập | Redirect URL trong dev.ewelink.cc phải **giống hệt** `redirect_url` trong `config.json` |
| Phiên đăng nhập hết hạn | Bấm **Đăng nhập** lại (hoặc xóa `token.json`) |
| Phím tắt không chạy | Chạy `pip install pynput`; trên Mac cần cấp quyền Accessibility |

> Không chia sẻ `config.json` và `token.json` cho người khác vì trong đó có mã truy cập vào nhà anh.

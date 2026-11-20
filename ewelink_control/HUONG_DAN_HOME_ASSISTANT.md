# Hướng dẫn dựng nhà thông minh với Home Assistant

Kết quả sau khi làm xong:

```
 Đèn/công tắc eWeLink (Sonoff)  ─┐
                                 ├──►  Home Assistant  ──►  Trình duyệt / app điện thoại
 Thiết bị Tuya / Smart Life     ─┘     (máy chủ trong nhà)  Widget + phím tắt trên máy tính
```

Có **5 bước**. Làm lần lượt từ trên xuống, mỗi bước đều có điểm kiểm tra **✅** để biết đã làm đúng chưa.

---

## Bước 1 – Chọn máy để chạy Home Assistant

Home Assistant cần một máy **bật 24/7** và cắm vào **cùng mạng wifi/router** với các thiết bị. Anh chọn **một** trong các phương án sau:

| Phương án | Ưu điểm | Nhược điểm |
|---|---|---|
| **A. Máy tính Windows có sẵn** (chạy máy ảo) | Không tốn tiền, thử ngay được | Máy phải luôn bật; tắt máy thì Home Assistant cũng dừng |
| **B. Mini PC cũ / laptop cũ** (cài thẳng) | Rẻ, mạnh, ổn định | Phải xoá sạch ổ cứng của máy đó |
| **C. Raspberry Pi 4/5** hoặc **Home Assistant Green** | Nhỏ, ít tốn điện, chuyên dụng | Phải mua thêm |

> Em khuyên: **làm thử bằng phương án A trước**. Khi đã quen và thấy thích thì chuyển sang B hoặc C. Home Assistant có tính năng sao lưu/khôi phục nên chuyển máy không phải làm lại từ đầu.

### Phương án A – Máy ảo trên Windows (VirtualBox)

1. Tải và cài **VirtualBox**: https://www.virtualbox.org/wiki/Downloads → chọn *Windows hosts*.
2. Tải file Home Assistant cho VirtualBox (file đuôi **.vdi.zip**) tại https://www.home-assistant.io/installation/windows rồi **giải nén** ra file `.vdi`.
3. Mở VirtualBox → **New (Mới)**:
   - Name: `HomeAssistant`
   - Type: **Linux**, Version: **Other Linux (64-bit)**
   - Memory (RAM): **2048 MB** trở lên, CPU: **2**
   - Tick **Enable EFI**
   - Ở mục ổ đĩa: chọn **Use an existing virtual hard disk file** → chọn file `.vdi` vừa giải nén
4. Chọn máy ảo → **Settings → Network → Adapter 1** → Attached to: **Bridged Adapter** → Name: chọn card mạng đang dùng (wifi hoặc dây LAN). **Bước này rất quan trọng.** Thiếu nó thì Home Assistant không thấy được thiết bị trong nhà.
5. Bấm **Start**. Đợi màn hình đen hiện chữ `homeassistant login:` là xong.

Mẹo: muốn máy ảo tự chạy cùng Windows thì dùng *Task Scheduler*, hoặc đơn giản là nhớ bật VirtualBox → Start mỗi lần mở máy.

### Phương án B/C – Máy riêng

- **Raspberry Pi:** cài **Raspberry Pi Imager** → Choose OS → *Other specific-purpose OS → Home assistants and home automation → Home Assistant* → ghi vào thẻ nhớ/SSD → cắm vào Pi, cắm dây mạng LAN, cấp điện.
- **Mini PC/laptop:** làm theo https://www.home-assistant.io/installation/generic-x86-64
- **Home Assistant Green:** cắm điện + dây mạng là chạy.

✅ **Kiểm tra:** chờ 5–20 phút (lần đầu nó tự tải bản cập nhật), rồi mở trình duyệt trên máy tính vào:
**http://homeassistant.local:8123**
Nếu không vào được, anh xem địa chỉ IP của máy Home Assistant trong trang quản lý router (hoặc trên màn hình đen của máy ảo), rồi vào `http://<địa-chỉ-IP>:8123`.

---

## Bước 2 – Tạo tài khoản Home Assistant

1. Ở trang chào mừng bấm **Create my smart home**.
2. Đặt tên, tên đăng nhập, mật khẩu. **Ghi lại mật khẩu này**: đây là tài khoản của riêng Home Assistant, không liên quan tới eWeLink.
3. Chọn vị trí nhà (để tính giờ mặt trời mọc/lặn), múi giờ **Asia/Ho_Chi_Minh**.
4. Có thể bỏ qua các thiết bị nó tự tìm thấy.
5. Bấm vào tên anh ở góc dưới bên trái → bật **Advanced mode (Chế độ nâng cao)**. Ở đây anh cũng có thể đổi **Language** sang **Tiếng Việt**.

✅ **Kiểm tra:** thấy trang tổng quan (Overview) của Home Assistant.

---

## Bước 3 – Đưa thiết bị eWeLink vào (qua HACS + Sonoff LAN)

**Sonoff LAN** là tiện ích (integration) phổ biến nhất để đưa thiết bị eWeLink vào Home Assistant. Anh chỉ cần đăng nhập **tài khoản eWeLink bình thường**, không cần tài khoản nhà phát triển. Thiết bị nào hỗ trợ điều khiển trong mạng LAN thì Home Assistant điều khiển trực tiếp trong nhà, không qua internet.

Sonoff LAN không có sẵn trong Home Assistant, nên trước hết phải cài **HACS**, tức "kho" tiện ích do cộng đồng làm.

### 3.1 Cài HACS
1. Vào **Settings (Cài đặt) → Add-ons → Add-on Store** → bấm **⋮** góc trên bên phải → **Repositories** → dán địa chỉ sau rồi bấm **Add**:
   ```
   https://github.com/hacs/addons
   ```
2. Tải lại trang, tìm **Get HACS** → **Install** → **Start** → mở tab **Log**, chờ đến khi log báo đã xong.
3. Vào **Settings → System → ⋮ → Restart Home Assistant**.
4. Sau khi khởi động lại: **Settings → Devices & services → + Add integration** → tìm **HACS** → tick đồng ý hết các ô → làm theo hướng dẫn: nó đưa một mã, anh mở github.com/login/device rồi nhập mã đó. Nếu chưa có tài khoản GitHub thì đăng ký miễn phí.

✅ **Kiểm tra:** thanh menu bên trái có thêm mục **HACS**.

### 3.2 Cài Sonoff LAN
1. Bấm **HACS** → ô tìm kiếm gõ **Sonoff LAN** → mở ra → **Download** → **Download**.
2. **Restart Home Assistant** (như bước 3.1, mục 3).
3. **Settings → Devices & services → + Add integration** → tìm **Sonoff** → nhập **email/số điện thoại** và **mật khẩu eWeLink** → Submit.
   - Số điện thoại nhập dạng `+84912345678`.
   - Chọn đúng quốc gia/khu vực **Vietnam**.

✅ **Kiểm tra:** vào **Settings → Devices & services → Sonoff** thấy danh sách bóng đèn và công tắc. Bật/tắt thử trong Home Assistant, đèn thật phải đổi theo.

> **Nếu app eWeLink trên điện thoại bị đăng xuất** hoặc Home Assistant báo đăng nhập từ nơi khác: tạo thêm một tài khoản eWeLink thứ hai (bằng email khác), rồi trong app eWeLink dùng chức năng **Chia sẻ (Share)** để chia sẻ thiết bị sang tài khoản đó. Sau đó dùng tài khoản thứ hai này cho Home Assistant.

---

## Bước 4 – Đưa thiết bị Tuya / Smart Life vào (nếu có)

Tiện ích Tuya có sẵn trong Home Assistant, không cần HACS, và cũng không cần tài khoản nhà phát triển.

1. Mở app **Smart Life** (hoặc **Tuya Smart**) trên điện thoại → tab **Tôi (Me)** → biểu tượng **⚙ Cài đặt** → **Tài khoản và bảo mật** → chép **User Code**.
2. Trong Home Assistant: **Settings → Devices & services → + Add integration** → **Tuya** → dán **User Code** → Submit.
3. Một mã QR hiện ra. Mở app Smart Life → biểu tượng **quét** (góc trên bên phải) → quét mã → bấm **Xác nhận đăng nhập**.

✅ **Kiểm tra:** vào **Settings → Devices & services → Tuya** thấy các thiết bị Tuya.

> Lưu ý: tiện ích Tuya điều khiển qua đám mây của Tuya. Nếu cần chạy hoàn toàn trong mạng nhà thì sau này có thể dùng thêm tiện ích **LocalTuya** (cài qua HACS).

---

## Bước 5 – Điều khiển trên máy tính

### Cách 1: Giao diện Home Assistant trên trình duyệt
Mở `http://homeassistant.local:8123` trong Chrome → **⋮ → Truyền, lưu và chia sẻ → Cài đặt trang dưới dạng ứng dụng**. Khi đó Home Assistant có biểu tượng riêng trên màn hình. Anh có thể sắp xếp lại bảng điều khiển: **Overview → ✏ (Edit dashboard)**.

### Cách 2: Widget nhỏ + phím tắt (em đã làm sẵn trong thư mục này)

1. **Tạo token:** trong Home Assistant bấm vào tên anh (góc dưới bên trái) → tab **Security (Bảo mật)** → kéo xuống cuối → **Long-lived access tokens → Create token** → đặt tên `widget` → **chép chuỗi token** (chuỗi này chỉ hiện một lần).
2. Cài **Python** từ https://www.python.org/downloads/. Trên Windows nhớ tick **Add python.exe to PATH**.
3. Trong thư mục `ewelink_control`: copy `config.example.json` thành `config.json`, mở bằng Notepad:
   - `ha_url`: giữ nguyên `http://homeassistant.local:8123` (hoặc thay bằng `http://<IP>:8123`)
   - `ha_token`: dán token vừa chép
   - `hotkeys`: sửa tên thiết bị cho **giống tên hiển thị trong Home Assistant**
4. Nháy đúp **`Chay_tren_Windows.bat`** (hoặc `Chay_tren_Mac.command` trên Mac).

✅ **Kiểm tra:** widget hiện danh sách đèn và công tắc (cả eWeLink lẫn Tuya). Bấm `Ctrl + Alt + 1` thì đèn đổi trạng thái và góc màn hình hiện thông báo.

Mặc định widget hiện mọi thiết bị dạng `light`, `switch`, `fan`. Nếu muốn chỉ hiện vài cái, thêm vào `config.json`:
```json
"entities": ["light.den_phong_khach", "switch.sonoff_1000xxxxxx_1"]
```
Mã `entity_id` của từng thiết bị xem ở **Settings → Devices & services → Entities**.

### Cách 3 (Windows, nâng cao): HASS.Agent
HASS.Agent là phần mềm cộng đồng cho Windows: có biểu tượng ở khay hệ thống, gán phím tắt và còn cho Home Assistant điều khiển ngược lại máy tính (tắt máy, khoá màn hình…). Xem tại https://github.com/hass-agent/HASS.Agent.

---

## Sau khi đã chạy ổn

- **App điện thoại:** cài **Home Assistant** (Companion app) trên iOS/Android, đăng nhập bằng tài khoản Home Assistant ở Bước 2.
- **Tự động hoá:** **Settings → Automations & scenes**, ví dụ "18:00 bật đèn cổng" hoặc "tắt hết đèn lúc 23:30".
- **Sao lưu:** **Settings → System → Backups → Back up now**. Nên làm định kỳ.
- **Điều khiển khi ra khỏi nhà:** đơn giản nhất là dịch vụ **Home Assistant Cloud** (trả phí). Miễn phí thì dùng add-on **Tailscale**.

## Gặp lỗi thường gặp

| Hiện tượng | Cách xử lý |
|---|---|
| Không vào được `homeassistant.local:8123` | Đợi thêm 10–20 phút; thử `http://<IP>:8123`; với máy ảo kiểm tra lại **Bridged Adapter** |
| Không thấy mục Add-ons | Bật **Advanced mode** trong trang hồ sơ (Bước 2.5) |
| Sonoff không hiện thiết bị | Kiểm tra lại quốc gia, mật khẩu; xem mục *Logs* trong Settings → System |
| Widget báo "Không kết nối được Home Assistant" | Kiểm tra `ha_url`; máy tính và Home Assistant phải chung mạng |
| Widget báo "Token sai" | Tạo token mới (Bước 5, Cách 2) và dán lại vào `config.json` |

# Army2 Hoàng Gia iOS — Vòng xoay V9 và tốc độ đi bộ

Đã build và đóng gói `Army2Hoanggia-V9-Wheel-Speed.ipa` cho iPhone arm64, iOS 12 trở lên. Giao diện đã mở trên iOS Simulator; các kiểm tra native và giao thức đều qua. Chưa cài trên iPhone thật, đăng nhập hoặc đặt xu với máy chủ đang hoạt động. IPA cần ký lại ứng dụng và thư viện đi kèm trước khi cài.

## Thay đổi

- Giao diện vòng xoay theo ảnh JAR `27450.jpg`: chữ pixel gốc, nền xanh nhạt, viền xanh/góc vàng, tiêu đề vàng, đồng hồ, thanh tỷ lệ thắng, số dư/quỹ/xu tham gia/thuế và kết quả trước. Ba nút dưới là Tham gia, Cập nhật, Trở ra. Khi chưa đủ hai người, hiện 02:00 và chờ người thứ hai.
- Vòng xoay là dòng đầu của menu V9 trong trận, trên Tắt vẽ căn góc, theo `27451.jpg`. Giữ dòng riêng dưới Quay số ở menu chính. Xem giờ vẫn hoạt động; xóa trạng thái phím trước khi mở vòng xoay.
- Tách nhịp đi bộ trái/phải khỏi speed game: tối đa 20 bước gốc/giây theo thời gian thực, đổi hướng ngay, không xếp hàng bước khi ngừng giữ phím. Giữ vòng lặp speed và các điểm gọi hoạt ảnh khác. Cần người dùng thử trên iPhone để đối chiếu cảm giác di chuyển với `27002.mp4`.
- Giữ tên phòng theo video 2 `26938(2).mp4`: phòng 0, 1, 2, 17 dùng tên mặc định; 3–16 là Bom, Bom 2, Nhện máy, Người máy, T-rex máy, UFO, UFO, Khí cầu, Nhện độc, Ma, Ma 2, Trùm liên hoàn, Trùm liên hoàn, Super Boss. Tên được chọn theo ID ngay tại chỗ vẽ, không theo vị trí hàng. ID khác giữ tên máy chủ; không đổi nhóm/lệnh vào phòng.
- Giữ các bản vá DataFix, Biệt đội/Top đội và toàn bộ 523 mục tài nguyên từ bản Room-Clan-Fix.

Vòng xoay dùng giao thức `-101` trong JAR/server đã cung cấp, qua kết nối game hiện tại. Nhập xu rồi xác nhận; khóa đặt 10 giây cuối; giới hạn 1–50 triệu xu/lượt và tổng 50 triệu xu/vòng; gửi lại cùng nonce khi chưa có xác nhận. Giao thức/nonce không thay đổi theo giao diện mới.

## Kiểm tra

- ARM64: 122 ca hook cũ; 54 ca menu chính; 900 ca chiều rộng/thanh ghi; 612 ca tên phòng; 324 đường chạy đến hàm vẽ chữ; 48 ca menu V9, callback Xem giờ và gate đi bộ; 18 lần tạo/sắp xếp phòng gốc cùng 24 ca vẽ tên.
- Chạy chính dylib iPhone mới trên Unicorn: 48 ca trạng thái/giao thức vòng xoay, 36 ca phòng/JNI, 36 ca nhịp di chuyển; mô phỏng hệ điều hành/Java/mạng, không gửi đến máy chủ thật.
- C: 16 mẫu giao thức và 24.524 ca lỗi/fuzz; 5 gói phòng hợp lệ, 319 gói lỗi và 60 danh sách; nhịp đi bộ ổn định ở 20–1.000 lượt gọi/giây.
- Đã xem ảnh Simulator của vòng đang đếm, chờ người thứ hai với số dư lớn, ô nhập xu và bàn phím. Dữ liệu mẫu chỉ nằm trong ứng dụng preview riêng, không nằm trong dylib đóng IPA.
- ZIP, checksum, exports, phiên bản dyld và bố cục Mach-O hợp lệ; vùng mã RX/dữ liệu RW riêng; LINKEDIT cuối. Kiểm tra tài nguyên cũ không đổi.

## Build và đóng gói

Trên macOS có Xcode: `bash native-wheel/build.sh`. Workflow `.github/workflows/native-wheel.yml` xuất dylib và ba ảnh Simulator. `AGWheel.m`, `ClassicWheelUI.inc` và `PixelFonts.h` chứa giao diện/chữ nhúng; `Movement.c` chứa nhịp đi bộ; `NativeGuard.S` bọc ngoại lệ RoboVM; `RoomBridge.c`/`RoomNames.c` giữ cache tên phòng.

Đóng gói cần IPA nền `deliverables/Army2Hoanggia-Room-Clan-Fix.ipa` (SHA-256 `8c4779afad7981f4bf8cf5e756bdf03450437cc4e56cf949c805e2d2affc636d`), executable gốc `inspect-ipa/Army2Hoanggia` (SHA-256 `34778a89dac9103a1fd62a6e712dce1bedd012da3bbb47c7ce908724b1d4c7d6`), `review/patched-native`, Python với Keystone/Unicorn/LIEF. Dựng lại bản đồ cần Capstone và `review/native.py`. Patcher từ chối IPA sai checksum hoặc dylib thiếu AGMoveAllow.

```bash
python native-wheel/patch_ipa.py --dylib native-wheel/build/AGWheel.dylib --output deliverables/Army2Hoanggia-V9-Wheel-Speed.ipa
python native-wheel/test_menu_room_display.py
python native-wheel/test_battle_hooks.py
python native-wheel/test_movement.py
python native-wheel/test_room_native.py
python native-wheel/test_device_bridge.py native-wheel/build/AGWheel.dylib
```

## Bản đã kiểm tra

- Source commit: `707866d166fd658da3f05129493bdd3423e9cc66`.
- [GitHub Actions thành công](https://github.com/lykien0311-jpg/Army2Hoanggia-iOS/actions/runs/40531573505); artifact `12746861405`.
- Dylib SHA-256: `362a6ca1cee2e5112cf790b15ef0b88de549d16cc005e43f6ffcea2ac05c6d49`.
- IPA SHA-256: `08357ec70cb6c04b7bfd2278d54f79c904aa01defb5cf415e4e7fc6e17a87aa4`; 16521098 byte.

Không dùng IPA từ workflow miniJVM cũ: đó là ứng dụng khác.

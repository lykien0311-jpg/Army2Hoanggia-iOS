# Vòng xoay V9 và sửa tên phòng — Army2 Hoàng Gia iOS

Đã biên dịch mô-đun iPhone arm64, chạy thử giao diện trên iOS Simulator và đóng `Army2Hoanggia-V9-Wheel-RoomFix.ipa`. Chưa thử cài/đăng nhập trên iPhone thật hoặc giao dịch với máy chủ đang hoạt động. IPA cần ký lại ứng dụng và thư viện đi kèm để cài.

## Thay đổi

- **V9 → Vòng xoay may mắn** thay cho Xem giờ. Giữ nguyên Quay số cũ. Vòng xoay lấy dữ liệu và kết quả từ giao thức `-101` trong JAR/server đã cung cấp, qua phiên kết nối game hiện tại.
- Giao diện có vòng chia theo tỷ lệ xu, đếm giờ, danh sách/phân trang, số dư và kết quả. Người chơi nhập xu rồi xác nhận. Khóa đặt 10 giây cuối, giới hạn 1–50 triệu xu/lượt và tổng 50 triệu xu/vòng; gửi lại cùng mã lượt khi chưa nhận xác nhận.
- **Tên phòng theo ID**, lưu tên cả khi gói tên đến trước danh sách và gán lại sau mỗi lần tải danh sách. Giữ nhóm theo video: Full item/phòng 0, Cấm item/phòng 1, Bầu cua/phòng 2, Đấu trùm/phòng 3–16, Đấu đội/phòng 17. Tên tùy chỉnh tiếp tục lấy từ máy chủ.
- Các phòng dùng tên mặc định được gán NULL vì mã vẽ cũ so sánh chuỗi rỗng bằng địa chỉ; tạo một String rỗng mới sẽ làm mất chữ trên hàng đó.
- Giữ các bản vá DataFix, Biệt đội/Top đội đã có. Speed 10 đã tương ứng thời gian nghỉ 0 ms, không tăng quá mức đó.

## Kiểm tra

- 16 gói vòng xoay v1/v2 và 24.524 trường hợp gói cắt/dư/biến đổi; Unicode, số 64 bit, giới hạn xu và thời điểm khóa.
- 122 ca chạy mã hook ARM64 trên cả sáu phiên bản; giữ luồng lệnh cũ, speed, thanh ghi và bắt ngoại lệ Java.
- 18 lần chạy mã ARM64 tạo/sắp xếp phòng gốc khớp thứ tự nhóm video; 24 ca chọn tên mặc định/tùy chỉnh.
- Bộ C phòng: 5 mẫu hợp lệ, 319 gói lỗi, 60 danh sách đổi thứ tự/tạo lại; giữ dòng nhóm và thông tin phòng.
- Thực thi **chính dylib iPhone đã build** trên Unicorn: 48 ca vòng xoay và 36 ca cache phòng/JNI; kiểm tra byte gửi, gửi lại cùng nonce, xác nhận đến muộn, đổi kết nối và phục hồi ngoại lệ RoboVM. Các hàm hệ điều hành, cấp phát Java và mạng được mô phỏng.
- Simulator đã mở màn hình vòng xoay và ô nhập xu/bàn phím. Dữ liệu mẫu chỉ nằm trong ứng dụng preview, không nằm trong dylib iPhone.
- IPA ZIP và bố cục Mach-O hợp lệ; `__LINKEDIT` ở cuối; vùng mã RX và dữ liệu RW riêng; phiên bản thư viện yêu cầu khớp dylib. Giữ nguyên 718 binding, 845.133 rebase và tài nguyên cũ.

Các kiểm tra mô phỏng không thay cho cài thử trên thiết bị và phản hồi của máy chủ thật. Không có đăng nhập hay đặt xu trên máy chủ trong quá trình kiểm tra.

## Bản build

- Nguồn dylib: commit `3de2ccf7707e5cf2959e821df80769bd010d02d9`.
- GitHub Actions thành công: https://github.com/lykien0311-jpg/Army2Hoanggia-iOS/actions/runs/40419576327
- Dylib SHA-256: `9fac50bbc4da985c12b572d20bf8e2012e401a20cfc152aedadd0046bf621658`.
- IPA SHA-256: `82802ce256e4a96daca59f4c4ffd784e33b28171af2a70a5f1fee5549c8df8c6`.
- iPhone arm64, iOS tối thiểu 12.0. Bản IPA đã chỉnh sửa, không có chữ ký phân phối dùng để cài.

## Biên dịch và đóng gói

Trên macOS có Xcode/iOS SDK: `bash native-wheel/build.sh`. Workflow nằm ở `.github/workflows/native-wheel.yml`. Preview là ứng dụng riêng, không được đóng vào IPA.

Đầu vào đóng gói bắt buộc:

- `deliverables/Army2Hoanggia-Room-Clan-Fix.ipa`, SHA-256 `8c4779afad7981f4bf8cf5e756bdf03450437cc4e56cf949c805e2d2affc636d`.
- `inspect-ipa/Army2Hoanggia`, executable gốc SHA-256 `34778a89dac9103a1fd62a6e712dce1bedd012da3bbb47c7ce908724b1d4c7d6`.
- `review/patched-native`, executable của IPA Room-Clan-Fix để đối chiếu.
- Python có keystone-engine 0.9.2, Unicorn 2, LIEF 1; dựng lại bảng địa chỉ cần Capstone 5 và `review/native.py`.

```bash
python native-wheel/patch_ipa.py --dylib native-wheel/build/AGWheel.dylib --output deliverables/Army2Hoanggia-V9-Wheel-RoomFix.ipa
python native-wheel/test_hooks.py
python native-wheel/test_room_native.py
python native-wheel/test_device_bridge.py native-wheel/build/AGWheel.dylib
```

Patcher từ chối bản IPA khác checksum. `AGWheel.m` chứa UI và trạng thái vòng xoay; `WheelProtocol.c` xử lý giao thức; `RoomNames.c` và `RoomBridge.c` lưu/gán tên phòng; `NativeGuard.S` bọc ngoại lệ Java; `NativeMap.h` ánh xạ sáu phiên bản của đúng executable gốc.

ABI JNI/bắt ngoại lệ đối chiếu MobiVM/robovm tag robovm-2.3.26, các tệp `compiler/vm/core/include/jni.h`, `robovm/types.h`, `trycatch.h`, `src/native.c` và `src/exception.c`. Giao thức đối chiếu trực tiếp các lớp LuckyWheelClient52, LuckyWheel52 và RoomRoutes56 trong JAR được cung cấp.

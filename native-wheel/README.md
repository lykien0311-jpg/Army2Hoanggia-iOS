# Vòng xoay kiểu JAR, menu V9 trong trận và đi bộ độc lập — Army2 Hoàng Gia iOS

## Bản cập nhật đang chờ build

Mã nguồn và hook của bản cập nhật đã chuẩn bị xong. **Chưa build dylib hoặc IPA mới cho các thay đổi dưới đây.** IPA đã giao trước đó vẫn là bản có vòng tròn, chưa có dòng vòng xoay trong V9 khi ở trận và chưa tách tốc độ đi bộ.

- Dựng lại giao diện theo ảnh JAR `27450.jpg`: nền xanh nhạt, khung xanh/góc vàng, chữ pixel gốc, tiêu đề vàng, đếm giờ, thanh tỷ lệ thắng, quỹ/số người/xu tham gia/số dư/thuế và kết quả người thắng trước. Ba nút dưới là Tham gia, Cập nhật, Trở ra. Khi chưa đủ hai người, hiển thị 02:00 và trạng thái chờ người thứ hai.
- Thêm Vòng xoay may mắn ở dòng đầu menu V9 trong trận, phía trên Tắt vẽ căn góc, theo ảnh `27451.jpg`. Giữ dòng dưới Quay số ở menu chính và hành động Xem giờ. Xóa trạng thái phím trước khi mở giao diện để tránh giữ phím di chuyển.
- Giới hạn riêng hai điểm gọi đi bộ trái/phải của người chơi bằng đồng hồ thời gian thực, tối đa 20 bước gốc/giây. Đổi hướng được xử lý ngay; không xếp hàng bước di chuyển khi ngừng giữ phím. Giữ vòng lặp speed game và các điểm gọi hoạt ảnh khác. Mức này cần đối chiếu trên iPhone với video `27002.mp4` trước khi xác nhận cảm giác di chuyển khớp mẫu.
- Giữ các sửa tên phòng theo video 2, DataFix, Biệt đội và Top đội của bản trước.

Các tệp mới: `ClassicWheelUI.inc`, `PixelFonts.h`, `Movement.c`, `Movement.h`, `test_battle_hooks.py` và `test_movement.py`. Hai bộ chữ được nhúng trực tiếp trong `PixelFonts.h`; không cần sao chép thư mục ảnh riêng. Dylib mới phải xuất `AGMoveAllow`; patcher từ chối dylib cũ thiếu hàm này.

Kiểm tra cục bộ đã qua: 122 ca hook cũ, 54 ca menu chính, 900 ca chiều rộng/thanh ghi, 612 ca tên phòng, 324 đường chạy đến hàm vẽ chữ, 48 ca menu V9/Xem giờ/gate di chuyển mới, cùng các kiểm tra C về nhịp đi bộ ở nhiều tần số gọi. Bộ giao thức và tên phòng vẫn qua. **Giao diện UIKit mới chưa được biên dịch hoặc xem trên Simulator; các kiểm tra dylib/Simulator ở phần bản trước không xác nhận bản cập nhật này.**

Sau khi build bằng Xcode, cần xem ảnh Simulator của giao diện mới, chạy `test_device_bridge.py` trên chính dylib mới, đóng gói và kiểm tra IPA trước khi giao. Chưa thử trên thiết bị hoặc máy chủ thật.

## Bản đã giao trước đó

Đã đóng `Army2Hoanggia-Phong-Video2-Wheel.ipa` với mã menu và hiển thị phòng mới. Giữ mô-đun iPhone arm64 đã build và xem giao diện trên iOS Simulator. Chưa thử cài/đăng nhập trên iPhone thật hoặc giao dịch với máy chủ đang hoạt động. IPA cần ký lại ứng dụng và thư viện đi kèm để cài.

## Thay đổi

- **Vòng xoay may mắn** là dòng riêng ngay dưới **Quay số** trong menu chính. Giữ Quay số và khôi phục Xem giờ của V9. Danh sách tăng từ sáu lên bảy dòng, mở đúng hành động của dòng mới và điều chỉnh chiều rộng theo màn hình. Vòng xoay lấy dữ liệu và kết quả từ giao thức `-101` trong JAR/server đã cung cấp, qua phiên kết nối game hiện tại.
- Giao diện có vòng chia theo tỷ lệ xu, đếm giờ, danh sách/phân trang, số dư và kết quả. Người chơi nhập xu rồi xác nhận. Khóa đặt 10 giây cuối, giới hạn 1–50 triệu xu/lượt và tổng 50 triệu xu/vòng; gửi lại cùng mã lượt khi chưa nhận xác nhận.
- **Tên phòng khớp video 2** (`26938(2).mp4`, 7,818 giây), chọn theo mã phòng ngay tại chỗ vẽ chữ. Phòng 0, 1, 2, 17 dùng tên mặc định; phòng 3–16 lần lượt là Bom, Bom 2, Nhện máy, Người máy, T-rex máy, UFO, UFO, Khí cầu, Nhện độc, Ma, Ma 2, Trùm liên hoàn, Trùm liên hoàn, Super Boss. Cách này áp dụng kể cả khi tên chưa nhận được, tên bị lệch như video 1 hoặc danh sách vừa tải lại. Mã phòng, nhóm, trạng thái và lệnh vào phòng không đổi. Mã ngoài 0–17 tiếp tục dùng tên máy chủ.
- Giữ cache tên từ gói `-19` và áp dụng lại sau khi dựng danh sách. Nhóm vẫn là Full item/phòng 0, Cấm item/phòng 1, Bầu cua/phòng 2, Đấu trùm/phòng 3–16, Đấu đội/phòng 17. Chuỗi tham chiếu ở phần vẽ được tạo một lần, dùng cache cố định được RoboVM đăng ký với GC.
- Các phòng dùng tên mặc định được gán NULL vì mã vẽ cũ so sánh chuỗi rỗng bằng địa chỉ; tạo một String rỗng mới sẽ làm mất chữ trên hàng đó.
- Giữ các bản vá DataFix, Biệt đội/Top đội đã có. Speed 10 đã tương ứng thời gian nghỉ 0 ms, không tăng quá mức đó.

## Kiểm tra

- 16 gói vòng xoay v1/v2 và 24.524 trường hợp gói cắt/dư/biến đổi; Unicode, số 64 bit, giới hạn xu và thời điểm khóa.
- 122 ca chạy mã hook ARM64 trên cả sáu phiên bản; giữ luồng lệnh cũ, speed, thanh ghi và bắt ngoại lệ Java.
- 54 ca tạo menu/chọn dòng và 900 ca chiều rộng/thanh ghi; 612 ca tên phòng với dữ liệu thiếu, lệch như video 1 hoặc bị ghi lại; 324 đường chạy mã gốc từ chọn tên đến lời gọi vẽ chữ, khớp từng tên phòng 0–17 theo video 2. Quay số và Xem giờ được kiểm tra giữ nguyên.
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
- IPA SHA-256: `0c0c1b4dd957e599dd246f7a8c6172348540c86dd49f298c3514681b8b455fc4` (16.520.722 byte).
- Bản đã giao này chỉ đổi mã hook trong executable; dylib và toàn bộ tài nguyên giữ nguyên bản đã kiểm tra. **Bản cập nhật đang chờ ở đầu tài liệu cần build lại dylib.**
- iPhone arm64, iOS tối thiểu 12.0. Bản IPA đã chỉnh sửa, không có chữ ký phân phối dùng để cài.

## Biên dịch và đóng gói

Trên macOS có Xcode/iOS SDK: `bash native-wheel/build.sh`. Workflow nằm ở `.github/workflows/native-wheel.yml`. Preview là ứng dụng riêng, không được đóng vào IPA.

Đầu vào đóng gói bắt buộc:

- `deliverables/Army2Hoanggia-Room-Clan-Fix.ipa`, SHA-256 `8c4779afad7981f4bf8cf5e756bdf03450437cc4e56cf949c805e2d2affc636d`.
- `inspect-ipa/Army2Hoanggia`, executable gốc SHA-256 `34778a89dac9103a1fd62a6e712dce1bedd012da3bbb47c7ce908724b1d4c7d6`.
- `review/patched-native`, executable của IPA Room-Clan-Fix để đối chiếu.
- Python có keystone-engine 0.9.2, Unicorn 2, LIEF 1; dựng lại bảng địa chỉ cần Capstone 5 và `review/native.py`.

```bash
python native-wheel/map_native.py
python native-wheel/patch_ipa.py --dylib native-wheel/build/AGWheel.dylib --output deliverables/Army2Hoanggia-Phong-Video2-Wheel.ipa
python native-wheel/test_menu_room_display.py
python native-wheel/test_battle_hooks.py
python native-wheel/test_movement.py
python native-wheel/test_room_native.py
python native-wheel/test_device_bridge.py native-wheel/build/AGWheel.dylib
```

Patcher từ chối bản IPA khác checksum. `AGWheel.m` chứa UI và trạng thái vòng xoay; `WheelProtocol.c` xử lý giao thức; `RoomNames.c` và `RoomBridge.c` lưu/gán tên phòng; `NativeGuard.S` bọc ngoại lệ Java; `NativeMap.h` ánh xạ sáu phiên bản của đúng executable gốc.

ABI JNI/bắt ngoại lệ đối chiếu MobiVM/robovm tag robovm-2.3.26, các tệp `compiler/vm/core/include/jni.h`, `robovm/types.h`, `trycatch.h`, `src/native.c` và `src/exception.c`. Giao thức đối chiếu trực tiếp các lớp LuckyWheelClient52, LuckyWheel52 và RoomRoutes56 trong JAR được cung cấp.

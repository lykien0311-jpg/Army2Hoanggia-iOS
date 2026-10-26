# Vòng xoay may mắn cho IPA Army2 Hoàng Gia

Trạng thái: đã viết mã nguồn và kiểm tra giao thức/bản vá ARM64. **Chưa biên dịch mô-đun UIKit, chưa tạo IPA có vòng xoay, chưa thử trên iPhone.**

Mục V9 → Xem giờ được thay bằng **Vòng xoay may mắn**. Quay số cũ được giữ nguyên. Phần thêm mới đọc vòng, thời gian, người tham gia, số dư, phí và kết quả từ giao thức `-101` của JAR/server đã cung cấp. Người chơi nhập xu rồi xác nhận; máy chủ quyết định kết quả và phần thưởng. Không có tự đặt xu hay tự cộng thưởng trên máy.

Mã có phần vẽ vòng theo tỷ lệ xu, đếm giờ, phân trang người tham gia, hiển thị kết quả, tải lại mỗi 2 giây, gửi lại cùng nonce sau 7 giây khi lượt đặt chưa được xác nhận, khóa 10 giây cuối, giới hạn 1–50 triệu xu/lượt và tối đa 50 triệu xu/vòng. Màn hình iOS dùng UIKit, nối vào phiên kết nối game hiện tại. UI không gọi Java từ luồng UIKit.

## Những tệp chính

- `AGWheel.m`: giao diện và nối vào kết nối game.
- `WheelProtocol.c/.h`: đọc/ghi gói tin, số 64 bit, tên tiếng Việt/Unicode, kiểm tra giới hạn.
- `NativeGuard.S`: bọc lời gọi Java bằng cơ chế bắt ngoại lệ của RoboVM 2.3.26.
- `NativeMap.h`, `native-map.json`: vị trí mã tương ứng cả 6 phiên bản trong đúng IPA gốc.
- `patch_ipa.py`: gắn thư viện và các điểm gọi vào IPA đã sửa phòng/Biệt đội; giữ `__LINKEDIT` ở cuối và tách vùng mã RX khỏi bộ đệm RW.
- `test_protocol.py`, `test_hooks.py`: kiểm tra giao thức và thực thi mã ARM64 trên Unicorn.
- `build.sh`, `Preview.m`: build dylib cho iPhone và một ứng dụng xem thử riêng cho simulator. Dữ liệu mẫu không được đưa vào dylib dành cho iPhone.
- `native-wheel.yml`: workflow dự kiến đặt ở `.github/workflows/native-wheel.yml` trong repo riêng đã dùng để build game.

## Kiểm tra đã đạt

- 16 mẫu gói v1/v2, gồm 0/1/2/20 người, có/không có kết quả.
- 24.524 ca gói bị cắt, có dữ liệu dư hoặc bị làm lỗi; tên có dấu/emoji, số dư vượt 32 bit, byte gửi đúng thứ tự và giới hạn lượt đặt.
- 86 ca ARM64 trên cả 6 phiên bản: mở menu, nhận riêng lệnh -101, giữ luồng xử lý lệnh khác, callback không tìm thấy, cache callback, giữ giá trị speed và bắt ngoại lệ Java.
- Giữ nguyên toàn bộ bản sửa phòng/Biệt đội/DataFix ngoài các vùng mã mới đã liệt kê; giữ nguyên 718 binding, 845.133 rebase, symbol và bảng điểm bắt đầu hàm của mã cũ.

Các kiểm tra này chưa chứng minh giao diện chạy được trên iPhone hoặc máy chủ đang hoạt động hỗ trợ đúng giao thức. Không đăng nhập, đặt xu hay thử giao dịch trên máy chủ trong quá trình kiểm tra.

## Biên dịch và đóng gói

Trên máy macOS có Xcode/iOS SDK: `bash native-wheel/build.sh`.

Khi đã có `native-wheel/build/AGWheel.dylib`, chạy tại thư mục công việc có các đầu vào bên dưới:

```bash
PYTHONPATH=analysis-deps python native-wheel/patch_ipa.py --prepare
PYTHONPATH=analysis-deps python native-wheel/test_hooks.py
PYTHONPATH=analysis-deps python native-wheel/patch_ipa.py --dylib native-wheel/build/AGWheel.dylib
```

Đầu vào bắt buộc:

- `deliverables/Army2Hoanggia-Room-Clan-Fix.ipa`, SHA-256 `8c4779afad7981f4bf8cf5e756bdf03450437cc4e56cf949c805e2d2affc636d`.
- `inspect-ipa/Army2Hoanggia`, executable gốc SHA-256 `34778a89dac9103a1fd62a6e712dce1bedd012da3bbb47c7ce908724b1d4c7d6`.
- `review/patched-native`, bản executable của IPA đã sửa phòng/Biệt đội, dùng để đối chiếu kiểm tra.
- Python: keystone-engine 0.9.2, Unicorn 2, LIEF 1. `map_native.py` cần thêm Capstone 5 và `review/native.py` nếu muốn dựng lại bảng địa chỉ.

Script từ chối đầu vào khác checksum để không vá nhầm phiên bản. IPA xuất ra cần ký lại cả ứng dụng lẫn dylib như một IPA đã chỉnh sửa thông thường.

## Việc còn lại

1. Biên dịch bằng iOS SDK và sửa mọi lỗi biên dịch nếu có.
2. Xem ảnh simulator, kiểm tra menu/nhập xu/bố cục.
3. Đóng IPA, kiểm tra cấu trúc, ký/cài thử trên iPhone; kiểm tra đăng nhập, V9 và phản hồi máy chủ. Không tự đặt xu khi chưa có thao tác xác nhận của người chơi.

Nguồn đối chiếu ABI bắt ngoại lệ: `MobiVM/robovm`, tag `robovm-2.3.26`, `compiler/vm/core/include/robovm/types.h`, `trycatch.h` và `compiler/vm/core/src/exception.c`. Giao thức đối chiếu trực tiếp từ `game/LuckyWheelClient52` và `army2.server.LuckyWheel52` trong các JAR được cung cấp.

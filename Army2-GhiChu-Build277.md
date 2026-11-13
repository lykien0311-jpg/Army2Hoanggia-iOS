# Ghi chú build 277 — hoàn thiện ở build 278

Đã gom bốn yêu cầu từ ảnh người dùng và ghép vào IPA 2.4.1, build 278.

- **Chiến trường:** vào từ menu Chơi ngay và bố cục menu thay thế; giữ luồng bảng hạng, xác nhận Đồng ý/Hủy và quay về bảng hạng sau trận.
- **Hào quang ngoài trận:** vẽ hào quang của mình ở sảnh và Trang bị; trong phòng chờ dùng đúng ID và nhân vật của từng người chơi. Giữ hai lớp hào quang trước/sau nhân vật.
- **Rương gian hàng:** dùng đúng sprite trang bị, căn giữa icon theo rương, đặt số lượng và dấu nâng cấp như +16 theo ô vật phẩm.
- **Phòng 18–19:** Thung Lũng Rồng có rồng lửa và băng; Đền Gương Vỡ có Kẻ Mạo Danh. Tên map, ảnh xem trước và tài nguyên boss lấy từ đúng APK người dùng gửi.

## Kết quả kiểm tra

Đã thực thi mã ARM64 của gói IPA và thư viện Apple đã build: 318 trường hợp menu gốc, 96 trường hợp hào quang, 24 trường hợp cập nhật ảnh/tên xem trước và 24 trường hợp chọn ảnh boss. Kiểm thử giao diện trình duyệt của Rương gian hàng, thách đấu, bảng hạng và quay về menu đã qua.

137 tệp framework khớp SHA của bản build trên Mac. 46 tài nguyên boss khớp APK; map và tile khớp server được gửi kèm. Giữ nguyên 522 mục của IPA nền ngoài tệp thực thi, thông tin phiên bản và framework thay thế. Đóng gói lại hai lần cho cùng SHA256.

IPA: `Army2HoangGia-2.4.1-B278-QA.ipa`.

SHA256: `01d8669bcae44d2438963eb96f8bb792126786395dcbd18588328964a520bbc1`.

Đây là bản QA cần ký lại ứng dụng và thư viện theo chứng chỉ/công cụ cài của chủ máy. Chưa thử trên iPhone thật hoặc đăng nhập tài khoản vào server thật. Các kiểm tra ARM64 mô phỏng biên UIKit, JVM, hệ điều hành và thao tác vẽ cuối cùng; chúng không thay thế việc cài thử thực tế.

Xem `native-wheel/BUILD278.md` và `native-wheel/validation278.json` để dựng lại và đối chiếu bằng chứng.

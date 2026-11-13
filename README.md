# Army2HoangGia iOS — build 278 QA

[**Tải IPA build 278**](https://github.com/lykien0311-jpg/Army2Hoanggia-iOS/raw/refs/heads/qa/ios-278-artifacts/Army2HoangGia-2.4.1-B278-QA.ipa)

Nếu dùng điện thoại, đăng nhập GitHub của chủ repo rồi mở liên kết trên. Có thể mở tệp `Army2HoangGia-2.4.1-B278-QA.ipa` trong danh sách và chọn **Download raw file**.

IPA cần ký lại ứng dụng và thư viện theo công cụ/chứng chỉ cài đặt của bạn. Đây là bản QA; chưa thử trên iPhone thật hoặc server thật.

Bốn mục đã ghép: đường vào Chiến trường/thách đấu, hào quang ngoài trận của từng người chơi, icon Rương gian hàng, map/boss phòng 18–19.

Đã qua 462 trường hợp ARM64 có mô phỏng các biên hệ thống, kiểm thử giao diện trình duyệt và các kiểm thử C. Xem [ghi chú](Army2-GhiChu-Build277.md), [báo cáo](validation278.json) và [mã nguồn/PR số 4](https://github.com/lykien0311-jpg/Army2Hoanggia-iOS/pull/4).

SHA256 IPA: `01d8669bcae44d2438963eb96f8bb792126786395dcbd18588328964a520bbc1`.

Tệp `B278-Apple-framework-delta.zip` giữ nguyên thư viện đã build trên Mac và được lưu để dựng lại gói. Nhánh tải riêng được dùng vì GitHub trả lỗi xác thực 401 khi tải tệp lên Releases; không phụ thuộc hạn mức Actions artifacts.

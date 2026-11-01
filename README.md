# Army2Hoanggia iOS

Dự án thử nghiệm chạy nguyên client Army2D-Kien trên iPhone bằng miniJVM/J2ME. Giữ 456 class của client, gồm menu vòng xoay và bầu cua. Chưa xác nhận hoạt động trên iPhone.

## Build

GitHub Actions tự kiểm tra Java/TCP/HTTP trên Ubuntu, sau đó build IPA chưa ký trên macOS khi mở/cập nhật pull request vào main. Xem tab Actions để tải artifact Army2Hoanggia-unsigned-IPA sau khi cả hai job thành công. IPA cần ký trước khi cài.

Mã nguồn và client nằm trong payload/source.zip.part000…025. Chạy `python3 ci/prepare.py --with-font` để ghép và giải nén vào project-src. SHA256 gói nguồn được kiểm tra trước khi giải nén. Soundfont được lấy từ đúng commit upstream và kiểm tra SHA256. Sau đó chạy `cd project-src && bash tools/build_ios.sh` trên Mac có Xcode 26.

Trên Linux: `python3 ci/prepare.py`, rồi trong project-src chạy `bash j2me_api/build.sh`, `python3 tools/audit_client.py J2MEEmulator/Resources/jars/army2hoanggia.jar --report build/linkage.json`, `python3 tools/run_runtime_probe.py`.

Mã tùy chỉnh bổ sung cho các lần sửa sau đặt trong overrides/ theo cấu trúc project-src. README và báo cáo đầy đủ của dự án nằm trong project-src sau giải nén.

Nguồn iOS/J2ME: https://github.com/ccbkv/J2MEEmulator-iOS tại commit 8afc8d808ca22160139333d1d58138c7dca91169, giấy phép Apache 2.0; giữ LICENSE và UPSTREAM_README.md trong gói nguồn. Client game do người dùng cung cấp, không được cấp lại giấy phép Apache.

"""Add only the IPA release marker to the exact supplied Notes78 server package."""
from pathlib import Path
import argparse,hashlib,io,json,os,shutil,subprocess,tempfile,zipfile,copy
ROOT=Path(__file__).resolve().parent
EXPECTED='f77a7a3e7af86323154afc4c55a5f886bb96dfeb9428082a0789bd76aa771769'
GUIDE='''ARMY2 HOÀNG GIA — NOTES78 + IPA 2.4.1

BẢN MỚI
- IPA 2.4.0 nâng lên 2.4.1 (build iOS 241 → 242), mã đăng nhập riêng 2.4.1-HG78-IPA.
- Server chỉ nhận ba mã phát hành 2.4.1-HG78-JAR / APK / IPA. IPA cũ, JAR/APK cũ và tên phiên bản 2.4.1 đơn thuần bị chặn trước khi truy cập tài khoản.
- Thông báo bản cũ: Cập nhật bản mới tại army2hoanggia.com
- IPA tải riêng: Army2Hoanggia-2.4.1-Notes78-GitHub.ipa. Giữ vòng xoay theo video ở sảnh/V9, kích thước theo màn hình, Notes77 và sửa OK cấu hình về sảnh.

CẬP NHẬT
- Nếu VPS đã chạy đúng Notes78: sao lưu server.jar hiện tại, dừng GAME, thay duy nhất server.jar bằng file trong gói này rồi bật GAME. Không cần thay JAR/APK/web/database lần nữa.
- Nếu chưa lên Notes78: dùng hướng dẫn Notes78 gốc bên dưới để cập nhật đầy đủ; lấy server.jar trong gói này.
- Đưa IPA 2.4.1 cùng JAR/APK 2.4.1 lên trang tải trước khi bật server mới. Người dùng iPhone cần ký lại IPA bằng chứng chỉ của mình.
- Cài IPA mới riêng không bật luật chặn trên server cũ. Server Notes78 ban đầu chưa nhận IPA mới; phải dùng server.jar trong gói này.
- Không xóa database, không đổi dữ liệu/tài khoản, không tự triển khai lên VPS.

KIỂM TRA
- Đã chạy native ARM64 login của 6 biến thể IPA với hai mẫu thông tin đăng nhập; chỉ UTF thứ ba đổi, username/password và đuôi z1 giữ nguyên.
- 100 kiểm tra server thực thi ClientEntry thật, có socket loopback: chặn bản cũ, nhận ba mã mới, giữ validation/tải dữ liệu gốc. Chưa đăng nhập tài khoản thật trên VPS.
- Runtime của gói chỉ đổi army2/server/ClientBuild78.class trong server.jar; toàn bộ JAR/APK/web/lib/rollback giữ nguyên.
- IPA build thư viện bằng Apple Xcode qua GitHub, kiểm chữ ký và Simulator; chưa thử IPA đã ký trên iPhone thật.
- Mã phiên bản là dấu nhận diện bản phát hành, không phải chữ ký chống giả mạo client.

HƯỚNG DẪN NOTES78 GỐC (đoạn nói IPA chưa có được thay bằng hướng dẫn trên)
'''

def main():
 p=argparse.ArgumentParser();p.add_argument('--notes78-zip',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--native-packets',type=Path,required=True);a=p.parse_args()
 assert hashlib.sha256(a.notes78_zip.read_bytes()).hexdigest()==EXPECTED,'Unexpected Notes78 input'
 with tempfile.TemporaryDirectory(prefix='army78-server-') as temp:
  tmp=Path(temp);classes=tmp/'classes';classes.mkdir()
  with zipfile.ZipFile(a.notes78_zip) as src:
   server=tmp/'server.jar';server.write_bytes(src.read('server.jar'))
   lib=tmp/'json_simple-1.1.jar';lib.write_bytes(src.read('lib/json_simple-1.1.jar'))
   cp=os.pathsep.join(map(str,[server,lib]));compiler=['javac'] if shutil.which('javac') else ['java','-m','jdk.compiler/com.sun.tools.javac.Main']
   subprocess.run([*compiler,'-encoding','UTF-8','-cp',cp,'-d',str(classes),*[str(ROOT/'server78/army2/server'/n)for n in ('ClientBuild78.java','ClientBuildProbe78.java')]],check=True)
   old=server.read_bytes();out=io.BytesIO();class_name='army2/server/ClientBuild78.class'
   with zipfile.ZipFile(io.BytesIO(old)) as jar,zipfile.ZipFile(out,'w') as dst:
    for zi in jar.infolist():dst.writestr(copy.copy(zi),(classes/class_name).read_bytes() if zi.filename==class_name else jar.read(zi.filename))
   updated=out.getvalue();server.write_bytes(updated)
   with zipfile.ZipFile(io.BytesIO(old)) as x,zipfile.ZipFile(io.BytesIO(updated)) as y:
    assert x.namelist()==y.namelist();assert [n for n in x.namelist()if x.read(n)!=y.read(n)]==[class_name]
   # The final JAR precedes the fixture classes: exercise the shipped gate.
   cp=os.pathsep.join(map(str,[server,classes,lib]))
   run=subprocess.run(['java','-Xverify:all','-cp',cp,'army2.server.ClientBuildProbe78',str(a.native_packets.resolve())],check=True,text=True,capture_output=True)
   print(run.stdout.strip())
   modifications={'server.jar':updated,
    'technical/src/army2/server/ClientBuild78.java':(ROOT/'server78/army2/server/ClientBuild78.java').read_bytes(),
    'technical/tests/army2/server/ClientBuildProbe78.java':(ROOT/'server78/army2/server/ClientBuildProbe78.java').read_bytes(),
    'HUONG_DAN.txt':(GUIDE+'\n'+src.read('HUONG_DAN.txt').decode()).encode(),
    'VALIDATION.txt':('NOTES78 IPA ADDENDUM — 2026-10-30\n'+run.stdout+'Only one runtime class changed from supplied Notes78. All other runtime payloads unchanged. No physical iPhone or live VPS account login tested. Earlier IPA-excluded statements below describe the original Notes78 baseline.\n\n'+src.read('VALIDATION.txt').decode()).encode(),
    'technical/README.txt':('IPA 2.4.1 ADDENDUM\nClientBuild78 now accepts 2.4.1-HG78-IPA as well as the original JAR/APK markers. Source and native login fixtures: GitHub lykien0311-jpg/Army2Hoanggia-iOS, branch codex/army-ios-build, native-wheel/. Rebuild with update_server78.py using the original Notes78 ZIP.\n\n'+src.read('technical/README.txt').decode()).encode()}
   a.output.parent.mkdir(parents=True,exist_ok=True)
   with zipfile.ZipFile(a.output,'w') as dst:
    for zi in src.infolist():dst.writestr(copy.copy(zi),modifications.get(zi.filename,src.read(zi.filename)))
   with zipfile.ZipFile(a.output) as dst:
    assert dst.testzip() is None and dst.namelist()==src.namelist()
    assert set(n for n in src.namelist()if src.read(n)!=dst.read(n))==set(modifications)
   report={'passed':True,'input_sha256':EXPECTED,'server_sha256':hashlib.sha256(updated).hexdigest(),'output_sha256':hashlib.sha256(a.output.read_bytes()).hexdigest(),'changed_archive_entries':list(modifications),'changed_runtime_classes':[class_name],'server_assertions':100,'live_vps_tested':False,'test_output':run.stdout.strip()}
   (ROOT/'build/server78-check.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()

"""Generate offline wire/image fixtures from the exact user-supplied Notes77 ZIP."""
from pathlib import Path
import argparse,hashlib,os,subprocess,tempfile,zipfile,shutil

ROOT=Path(__file__).resolve().parent
EXPECTED={'8f5fc20843fcf0014dc87807ff34a459279e2266ec55e36e38a180b7380a49d8','f77a7a3e7af86323154afc4c55a5f886bb96dfeb9428082a0789bd76aa771769'}

def main():
    p=argparse.ArgumentParser();p.add_argument('--notes77-zip',type=Path,required=True)
    p.add_argument('--java-home',type=Path,default=os.environ.get('JAVA_HOME'))
    p.add_argument('--output',type=Path,default=ROOT.parent/'fixtures/data');a=p.parse_args()
    assert hashlib.sha256(a.notes77_zip.read_bytes()).hexdigest() in EXPECTED,'Notes77/78 ZIP differs'
    a.output.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='army-notes77-fixtures-') as tmp:
        root=Path(tmp);deps=[]
        with zipfile.ZipFile(a.notes77_zip) as z:
            for name in z.namelist():
                if name=='server.jar' or (name.startswith('lib/') and name.endswith('.jar')):
                    file=root/Path(name).name;file.write_bytes(z.read(name));deps.append(str(file))
        cp=os.pathsep.join(deps);classes=root/'classes';classes.mkdir()
        javac=str(a.java_home/'bin/javac') if a.java_home else 'javac'
        java=str(a.java_home/'bin/java') if a.java_home else 'java'
        compiler=[javac] if shutil.which(javac) else [java,'-m','jdk.compiler/com.sun.tools.javac.Main']
        subprocess.run([*compiler,'-encoding','UTF-8','-cp',cp,'-d',str(classes),str(ROOT/'fixtures-src/army2/server/EmitNotes77.java')],check=True)
        subprocess.run([java,'-Djava.awt.headless=true','-cp',os.pathsep.join([str(classes),cp]),'army2.server.EmitNotes77',str(a.output.resolve())],check=True)
    assert len(list(a.output.glob('*.bin')))==30

if __name__=='__main__':main()

"""Package the matching server for build 275 from the exact supplied JAR."""
import argparse
from hashlib import sha256
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
from zipfile import ZipFile
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from boss_assets import SERVER_SHA


def assemble(source, output):
    if sha256(source.read_bytes()).hexdigest() != SERVER_SHA or output.exists():
        raise ValueError("Expected the original server(4).jar and a new output")
    root = Path(__file__).resolve().parent
    classes = "army2/server/"
    retained = [classes + name + ".class" for name in ("ClientEntry", "BauCua55")]
    with TemporaryDirectory() as folder, ZipFile(source) as original:
        build = Path(folder)
        (build / classes).mkdir(parents=True)
        for name in retained:
            (build / name).write_bytes(original.read(name))
        subprocess.run(["java", "-m", "jdk.compiler/com.sun.tools.javac.Main", "-source", "17", "-target", "17",
                        "-cp", str(source), "-d", folder, *map(str, (root / classes).glob("*.java"))],
                       check=True)
        flags = ["--add-exports", "java.base/jdk.internal.org.objectweb.asm=ALL-UNNAMED"]
        subprocess.run(["java", *flags, "-m", "jdk.compiler/com.sun.tools.javac.Main",
                        *flags, "-d", folder, str(root / "CarryIpaCompatibility.java")], check=True)
        for name in retained:
            subprocess.run(["java", *flags, "-cp", folder, "CarryIpaCompatibility", str(build / name)],
                           check=True)
        replacements = {str(path.relative_to(build)): path.read_bytes()
                        for path in (build / classes).glob("*.class")}
        if len(replacements) != 4 or not replacements.keys() <= set(original.namelist()):
            raise ValueError("Unexpected server class set")
        with ZipFile(output, "x") as edited:
            for info in original.infolist():
                content = replacements[info.filename] if info.filename in replacements else original.read(info)
                edited.writestr(info, content)
    with ZipFile(source) as original, ZipFile(output) as edited:
        if edited.testzip() or edited.namelist() != original.namelist():
            raise ValueError("Invalid server archive")
        changed = {name for name in original.namelist() if original.read(name) != edited.read(name)}
        if changed != replacements.keys():
            raise ValueError("Unexpected server class changes")


if __name__ == "__main__":
    cli = argparse.ArgumentParser()
    cli.add_argument("original", type=Path)
    cli.add_argument("output", type=Path)
    args = cli.parse_args()
    assemble(args.original.resolve(), args.output.resolve())

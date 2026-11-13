"""Take the exact client art and verify terrain against the server archive."""
from hashlib import sha256
from pathlib import Path
from struct import unpack_from
from zipfile import ZipFile

CLIENT_SHA = "0d0ecdcd03749feed48d719355293f65bb18e42d78e3e3870131dbe67cca4d99"
SERVER_SHA = "c4e0dba233085e5d38a79d92d0b8dd072e0b8c7b00efdd86edc9af92c338e922"
DRAGON_ART = ("background.png", "fire-226.png", "fire-100.png", "ice-226.png",
              "ice-100.png", "egg-0.png", "egg-1.png")
MIMIC_ART = ("background.png", "boss.png")


def boss_assets(client: Path, server: Path):
    if sha256(client.read_bytes()).hexdigest() not in (CLIENT_SHA, "a74947b824dfc95fc91fc6be499abcf0647f6bbfb5af675825b690bc0cd4d5e0"):
        raise ValueError("Unexpected reference client JAR")
    if sha256(server.read_bytes()).hexdigest() != SERVER_SHA:
        raise ValueError("Unexpected reference server JAR")
    result = {}
    with ZipFile(client) as c, ZipFile(server) as s:
        for root, map_id, dims, ids, art in (
            ("dragon105", 41, (1120, 840), list(range(90, 110)), DRAGON_ART),
            ("mimic111", 42, (960, 560), [*range(90, 99), 102], MIMIC_ART),
        ):
            name = f"{root}/{map_id}.map"
            layout = c.read(name)
            width, height, count = unpack_from(">HHB", layout)
            if ((width, height) != dims or count != len(ids) or layout[5:5 + 5 * count:5] != bytes(ids)
                    or len(layout) != 38 + 5 * count or layout[5 + 5 * count] != 8):
                raise ValueError(f"Unexpected map layout {map_id}")
            for key in (name, *(f"{root}/tile-{i}.png" for i in ids)):
                content = c.read(key)
                if content != s.read(key):
                    raise ValueError(f"Client and server terrain differ at {key}")
                result[key] = content
            for key in (f"{root}/{p}" for p in art):
                result[key] = c.read(key)
    return result


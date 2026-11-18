"""Fetch pinned public runtime assets; never write into the model or source tree."""

import argparse
import hashlib
import os
import shutil
import tarfile
from pathlib import Path
from urllib.request import urlopen

from beyond_move.training import BASE_ID, BASE_REV

BASE_FILES = {
    "config.json": (659, "18e18afcaccafade98daf13a54092927904649e1dd4eba8299ab717d5d94ff45"),
    "generation_config.json": (
        242,
        "e558847a8b4402616f1273797b015104dc266fe4b520056fca88823ba8f8ebe6",
    ),
    "tokenizer.json": (
        7031645,
        "c0382117ea329cdf097041132f6d735924b697924d6f6fc3945713e96ce87539",
    ),
    "tokenizer_config.json": (
        7305,
        "5b5d4f65d0acd3b2d56a35b56d374a36cbc1c8fa5cf3b3febbbfabf22f359583",
    ),
    "model.safetensors": (
        988097824,
        "fdf756fa7fcbe7404d5c60e26bff1a0c8b8aa1f72ced49e7dd0210fe288fb7fe",
    ),
    "LICENSE": (11343, "832dd9e00a68dd83b3c3fb9f5588dad7dcf337a0db50f7d9483f310cd292e92e"),
}


def fetch(url: str, path: Path, size: int, expected: str) -> None:
    def verified(file: Path) -> bool:
        if not file.is_file() or file.stat().st_size != size:
            return False
        with file.open("rb") as stream:
            return hashlib.file_digest(stream, "sha256").hexdigest() == expected

    if verified(path):
        print(f"Verified: {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".part")
    try:
        with urlopen(url, timeout=40) as remote, temp.open("wb") as local:
            received = 0
            while chunk := remote.read(1 << 20):
                received += len(chunk)
                if received > size:
                    raise ValueError(f"Download exceeds expected size: {path.name}")
                local.write(chunk)
        if not verified(temp):
            raise ValueError(f"Downloaded file checksum mismatch: {path.name}")
        temp.replace(path)
    finally:
        temp.unlink(missing_ok=True)
    print(f"Fetched: {path}")


def install_engine(root: Path) -> None:
    url = "https://github.com/official-stockfish/Stockfish/releases/download/sf_17.1"
    asset = "stockfish-ubuntu-x86-64-avx2"
    archive = root / "sf.tar"
    fetch(
        f"{url}/{asset}.tar",
        archive,
        80087040,
        "09e953222dbe80aaea5c33dab265413b295cb8376418445c877708c61e31987d",
    )
    binary = root / "stockfish"
    with tarfile.open(archive) as tar:
        member = tar.getmember(f"stockfish/{asset}")
        if not member.isfile():
            raise ValueError("Engine archive member is not a regular file.")
        source = tar.extractfile(member)
        if source is None:
            raise ValueError("Engine archive contains no readable binary.")
        with source, binary.open("wb") as destination:
            shutil.copyfileobj(source, destination)
    os.chmod(binary, 0o755)


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--engine-only", action="store_true")
    args = cli.parse_args()
    root = Path(".local")
    install_engine(root)
    if not args.engine_only:
        for name, (size, digest) in BASE_FILES.items():
            fetch(
                f"https://huggingface.co/{BASE_ID}/resolve/{BASE_REV}/{name}",
                root / "base" / name,
                size,
                digest,
            )


if __name__ == "__main__":
    main()

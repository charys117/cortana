"""
Streaming AES-256-GCM encryption for archived media files.

File format ("CAG1"):
    magic "CAG1" | file_id (8 random bytes) | chunk records...
    chunk record: uint32 BE ciphertext length | ciphertext
    chunk nonce = file_id + uint32 BE chunk counter (starting at 0)

The key comes from the ARCHIVE_MEDIA_KEY env var (base64, 32 bytes). Losing
the key means losing every encrypted file — keep a copy outside the cluster.

Standalone decryption CLI (no bot/DB dependencies):
    python -m src.core.mediacrypto --genkey
    python -m src.core.mediacrypto <file.enc> [-o output]
"""

import base64
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

MAGIC = b"CAG1"
KEY_ENV = "ARCHIVE_MEDIA_KEY"


def load_key():
    """Return the 32-byte media key, or None when encryption is not configured."""
    raw = os.environ.get(KEY_ENV)
    if not raw:
        return None
    key = base64.b64decode(raw)
    if len(key) != 32:
        raise ValueError(f"{KEY_ENV} must be 32 bytes, base64-encoded")
    return key


class StreamEncryptor:
    """Wraps a binary file object; write() plaintext chunks, get ciphertext."""

    def __init__(self, f, key):
        self._aes = AESGCM(key)
        self._f = f
        self._file_id = os.urandom(8)
        self._counter = 0
        f.write(MAGIC + self._file_id)

    def write(self, chunk):
        nonce = self._file_id + self._counter.to_bytes(4, "big")
        ct = self._aes.encrypt(nonce, chunk, None)
        self._f.write(len(ct).to_bytes(4, "big") + ct)
        self._counter += 1


def decrypt_file(src_path, dst_f, key):
    """Decrypt a CAG1 file to an open binary file object."""
    aes = AESGCM(key)
    with open(src_path, "rb") as f:
        if f.read(4) != MAGIC:
            raise ValueError(f"{src_path} is not a CAG1 encrypted file")
        file_id = f.read(8)
        counter = 0
        while True:
            header = f.read(4)
            if not header:
                break
            ct = f.read(int.from_bytes(header, "big"))
            nonce = file_id + counter.to_bytes(4, "big")
            dst_f.write(aes.decrypt(nonce, ct, None))
            counter += 1


def _main():
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Decrypt archived media files")
    parser.add_argument("file", nargs="?", help="encrypted file (*.enc)")
    parser.add_argument("-o", "--output", help="output path (default: strip .enc)")
    parser.add_argument(
        "--genkey", action="store_true", help=f"generate a new {KEY_ENV}"
    )
    args = parser.parse_args()
    if args.genkey:
        print(base64.b64encode(AESGCM.generate_key(bit_length=256)).decode())
        return
    if not args.file:
        parser.error("file is required unless --genkey is given")
    key = load_key()
    if key is None:
        sys.exit(f"{KEY_ENV} is not set")
    out = args.output or args.file.removesuffix(".enc")
    if out == args.file:
        sys.exit("output path equals input; pass -o")
    with open(out, "wb") as f:
        decrypt_file(args.file, f, key)
    print(out)


if __name__ == "__main__":
    _main()

import base64
import io
import os

import pytest
from cryptography.exceptions import InvalidTag

from src.core.mediacrypto import MAGIC, StreamEncryptor, decrypt_file, load_key


@pytest.fixture
def key():
    return os.urandom(32)


def encrypt_to_file(path, key, chunks):
    with open(path, "wb") as f:
        enc = StreamEncryptor(f, key)
        for chunk in chunks:
            enc.write(chunk)


class TestRoundtrip:
    def test_multi_chunk_roundtrip(self, key, tmp_path):
        chunks = [b"hello ", b"cortana " * 1000, b"!"]
        path = tmp_path / "f.enc"
        encrypt_to_file(path, key, chunks)
        out = io.BytesIO()
        decrypt_file(path, out, key)
        assert out.getvalue() == b"".join(chunks)

    def test_ciphertext_has_magic_and_no_plaintext(self, key, tmp_path):
        path = tmp_path / "f.enc"
        encrypt_to_file(path, key, [b"secret payload" * 100])
        data = path.read_bytes()
        assert data.startswith(MAGIC)
        assert b"secret payload" not in data

    def test_wrong_key_fails(self, key, tmp_path):
        path = tmp_path / "f.enc"
        encrypt_to_file(path, key, [b"data"])
        with pytest.raises(InvalidTag):
            decrypt_file(path, io.BytesIO(), os.urandom(32))

    def test_tampered_file_fails(self, key, tmp_path):
        path = tmp_path / "f.enc"
        encrypt_to_file(path, key, [b"data"])
        raw = bytearray(path.read_bytes())
        raw[-1] ^= 0xFF
        path.write_bytes(bytes(raw))
        with pytest.raises(InvalidTag):
            decrypt_file(path, io.BytesIO(), key)

    def test_non_cag1_file_is_rejected(self, key, tmp_path):
        path = tmp_path / "f.enc"
        path.write_bytes(b"plain old file")
        with pytest.raises(ValueError):
            decrypt_file(path, io.BytesIO(), key)


class TestLoadKey:
    def test_absent_env_returns_none(self, monkeypatch):
        monkeypatch.delenv("ARCHIVE_MEDIA_KEY", raising=False)
        assert load_key() is None

    def test_valid_key_roundtrip(self, monkeypatch, key):
        monkeypatch.setenv("ARCHIVE_MEDIA_KEY", base64.b64encode(key).decode())
        assert load_key() == key

    def test_wrong_length_raises(self, monkeypatch):
        monkeypatch.setenv("ARCHIVE_MEDIA_KEY", base64.b64encode(b"short").decode())
        with pytest.raises(ValueError):
            load_key()

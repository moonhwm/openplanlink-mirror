"""Read existing HMAC material without creating, rotating, or reporting keys."""
from dataclasses import dataclass, field
import base64
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import struct


class KeyPolicyError(ValueError):
    pass


@dataclass(repr=False)
class KeyMaterial:
    key: bytes = field(repr=False)
    key_id: str
    source_file: Path | None = field(repr=False, default=None)

    def environment(self):
        return {'OPL_A2A_HMAC_KEY_B64': base64.b64encode(self.key).decode('ascii'),
                'OPL_A2A_HMAC_KEY_ID': self.key_id}

    def verify_unchanged(self):
        if self.source_file is not None:
            try:
                same = hmac.compare_digest(self.source_file.read_bytes(), self.key)
            except OSError:
                raise KeyPolicyError('key_source_unavailable') from None
            if not same:
                raise KeyPolicyError('key_source_changed')

    def authenticate_manifest_root(self, encoded):
        try:
            document = json.loads(encoded)
            root, tag = document['merkle_root_sha3_512'], document['hmac_sha3_512']
            count, stamp = document['file_count'], document['generated_at']
            if (document['schema'] != 'opl-hmac-sha3-512-tree/1'
                    or document['key_id'] != self.key_id
                    or type(count) is not int or not 1 <= count < 2 ** 53
                    or not re.fullmatch(r'[0-9a-f]{128}', root)
                    or not re.fullmatch(r'[0-9a-f]{128}', tag)
                    or not isinstance(stamp, str)):
                raise ValueError()
            kid, when = self.key_id.encode('utf-8'), stamp.encode('utf-8')
            message = b'OpenPlanLink-A2A-Merkle-v1\x00' + bytes.fromhex(root)
            message += struct.pack('>Q', count)
            message += struct.pack('>H', len(kid)) + kid + struct.pack('>H', len(when)) + when
            expected = hmac.new(self.key, message, hashlib.sha3_512).hexdigest()
            if not hmac.compare_digest(expected, tag):
                raise ValueError()
        except (ValueError, KeyError, TypeError, OverflowError, struct.error):
            raise KeyPolicyError('prior_tree_authentication_failed') from None


def load_existing_key(key_file=None, key_id=None):
    identity = key_id or os.environ.get('OPL_A2A_HMAC_KEY_ID', 'opl-a2a-2026q4')
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._:-]{0,127}', identity):
        raise KeyPolicyError('key_id_invalid')
    path = None
    encoded = os.environ.get('OPL_A2A_HMAC_KEY_B64')
    if key_file is None and encoded is not None:
        try:
            key = base64.b64decode(encoded, validate=True)
            if base64.b64encode(key).decode('ascii') != encoded:
                raise ValueError()
        except (ValueError, UnicodeError):
            raise KeyPolicyError('key_encoding_invalid') from None
    else:
        path = Path(key_file or os.environ.get('OPL_A2A_HMAC_KEY_FILE',
                                              str(Path.home() / '.a2a-hmac-key.bin')))
        try:
            before = path.stat()
            key = path.read_bytes()
            after = path.stat()
        except OSError:
            raise KeyPolicyError('key_source_unavailable') from None
        if before.st_size != after.st_size or before.st_mtime_ns != after.st_mtime_ns:
            raise KeyPolicyError('key_source_changed')
    if len(key) != 64:
        raise KeyPolicyError('key_size_invalid')
    return KeyMaterial(key, identity, path)

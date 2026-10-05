"""Build a delivery-directory tree; Git index attestation uses sha3-tree.mjs."""
import argparse
from datetime import datetime, timezone
import hashlib
import hmac
import json
import os
from pathlib import Path
import struct
import sys
import uuid

from hmac_key_policy import KeyPolicyError, load_existing_key

OUTPUT = 'hmac_attest.json'


def sha3(value):
    return hashlib.sha3_512(value).digest()


def leaf(path_utf8, size, content_digest_hex):
    encoded = path_utf8.encode('utf-8')
    value = b'\x00' + struct.pack('>I', len(encoded)) + encoded
    value += struct.pack('>Q', size) + bytes.fromhex(content_digest_hex)
    return sha3(value).hex()


def merkle_root(leaves):
    level = [bytes.fromhex(value) for value in leaves]
    while len(level) > 1:
        level = [sha3(b'\x01' + level[i] + (level[i + 1] if i + 1 < len(level) else level[i]))
                 for i in range(0, len(level), 2)]
    return level[0].hex() if level else ''


def build_manifest(directory, key, key_id, generated_at=None):
    directory = Path(directory).resolve(strict=True)
    if not directory.is_dir():
        raise ValueError('delivery_directory_missing')
    entries = []
    paths = []
    for path in directory.rglob('*'):
        if path.is_symlink() or (hasattr(path, 'is_junction') and path.is_junction()):
            raise ValueError('delivery_link_not_supported')
        if path.is_file() and path.relative_to(directory).as_posix() != OUTPUT:
            if not path.resolve().is_relative_to(directory):
                raise ValueError('delivery_path_outside_directory')
            paths.append(path)
    for path in sorted(paths, key=lambda value: value.relative_to(directory).as_posix().encode('utf-8')):
        before = path.stat()
        content = path.read_bytes()
        after = path.stat()
        if before.st_size != after.st_size or before.st_mtime_ns != after.st_mtime_ns:
            raise ValueError('delivery_changed_during_read')
        relative = path.relative_to(directory).as_posix()
        content_digest = sha3(content).hex()
        entries.append({'path': relative, 'size': len(content),
                        'content_sha3_512': content_digest,
                        'leaf_sha3_512': leaf(relative, len(content), content_digest)})
    if not entries:
        raise ValueError('empty_delivery_directory')
    root = merkle_root([item['leaf_sha3_512'] for item in entries])
    stamp = generated_at or datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')
    kid, when = key_id.encode('utf-8'), stamp.encode('utf-8')
    message = b'OpenPlanLink-A2A-Merkle-v1\x00' + bytes.fromhex(root)
    message += struct.pack('>Q', len(entries))
    message += struct.pack('>H', len(kid)) + kid + struct.pack('>H', len(when)) + when
    return {
        'schema': 'opl-hmac-sha3-512-tree/1', 'generated_at': stamp,
        'tree_algorithm': 'sha3-512', 'mac_algorithm': 'hmac-sha3-512',
        'leaf_encoding': '0x00 || uint32be(path_utf8_len) || path_utf8 || uint64be(size) || sha3_512(content)',
        'node_encoding': '0x01 || left_digest || right_digest; duplicate odd right node',
        'mac_encoding': 'UTF8(OpenPlanLink-A2A-Merkle-v1\\0) || root_digest || uint64be(file_count) || uint16be(key_id_utf8_len) || key_id_utf8 || uint16be(generated_at_utf8_len) || generated_at_utf8',
        'key_id': key_id, 'file_count': len(entries), 'merkle_root_sha3_512': root,
        'hmac_sha3_512': hmac.new(key, message, hashlib.sha3_512).hexdigest(), 'files': entries,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--directory', type=Path, default=Path('deliverables/20261003'))
    parser.add_argument('--key-file', type=Path)
    parser.add_argument('--key-id')
    args = parser.parse_args(argv)
    temporary = None
    try:
        root = args.repo.resolve(strict=True)
        directory = (root / args.directory).resolve(strict=True)
        if not directory.is_relative_to(root):
            raise ValueError('delivery_path_outside_repo')
        material = load_existing_key(args.key_file, args.key_id)
        output = directory / OUTPUT
        if output.is_symlink():
            raise ValueError('manifest_link_not_supported')
        prior = output.read_bytes() if output.exists() else None
        manifest = build_manifest(directory, material.key, material.key_id)
        material.verify_unchanged()
        if (output.read_bytes() if output.exists() else None) != prior:
            raise ValueError('manifest_changed_before_replace')
        temporary = directory / (OUTPUT + '.tmp-' + uuid.uuid4().hex)
        with temporary.open('x', encoding='utf-8') as stream:
            stream.write(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
        os.replace(temporary, output)
        print(json.dumps({'status': 'built', 'file_count': manifest['file_count'],
                          'scope': 'delivery_directory; not Git index attestation'}))
        return 0
    except KeyPolicyError as error:
        print(json.dumps({'status': 'blocked', 'code': str(error)}))
        return 1
    except (OSError, ValueError, TypeError, OverflowError):
        print('{"status":"blocked","code":"delivery_build_failed"}')
        return 1
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    raise SystemExit(main())

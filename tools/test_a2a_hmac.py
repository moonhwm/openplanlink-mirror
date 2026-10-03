#!/usr/bin/env python
# -*- coding: utf-8 -*-

import copy
from concurrent.futures import ThreadPoolExecutor
import pathlib
import secrets
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import a2a_hmac as M

KEY = bytes(range(64))
KEY_ID = "k-test-1"
SENDER = "cairn-dsh"
RECIPIENT = "workbuddy-hy4"
BODY = b"hello"
TIMESTAMP = "2026-10-03T18:00:00+08:00"
NONCE = "0123456789abcdef0123456789abcdef"
NOW = datetime.fromisoformat(TIMESTAMP)
EXPECTED_BODY_HASH = "75d527c368f2efe848ecf6b073a36767800805e9eef2b1857d5f984f036eb6df891d75f72d9b154518c1cd58835286d1da9a38deba3de98b5a53e5ed78a84976"
EXPECTED_TAG = "53d0d652af398f630eab41787fd4086300dc0ee298d5527aea4574f0679aefd42e27c4ac46cf11f6554b9251727f065ac41c41c5d0e58c8d9435b297c3f5f09a"
CACHE_DIRECTORY = tempfile.TemporaryDirectory()


def replay_cache(path=None):
    database = path or pathlib.Path(CACHE_DIRECTORY.name, f"{secrets.token_hex(12)}.sqlite3")
    return M.ReplayCache(database)


def envelope():
    return M.build_envelope(
        SENDER,
        RECIPIENT,
        BODY,
        KEY,
        KEY_ID,
        timestamp=TIMESTAMP,
        nonce=NONCE,
    )


def verify(value, *, body=BODY, key=KEY, key_id=KEY_ID, sender=SENDER,
           recipient=RECIPIENT, cache=None, now=NOW, window=300):
    return M.verify_envelope(
        value,
        key,
        key_id,
        sender,
        recipient,
        body,
        cache if cache is not None else replay_cache(),
        now=now,
        window=window,
    )


class A2AHmacTests(unittest.TestCase):
    def test_platform_support(self):
        self.assertTrue(M.platform_supported())

    def test_public_vector(self):
        value = envelope()
        self.assertEqual(value["body_sha3_512"], EXPECTED_BODY_HASH)
        self.assertEqual(value["tag"], EXPECTED_TAG)

    def test_canonical_envelope(self):
        value = envelope()
        value.pop("tag")
        self.assertEqual(
            M.canonicalize_envelope(value).decode(),
            '{"body_sha3_512":"' + EXPECTED_BODY_HASH + '","key_id":"k-test-1",'
            '"nonce":"0123456789abcdef0123456789abcdef","recipient_id":"workbuddy-hy4",'
            '"sender_id":"cairn-dsh","timestamp":"2026-10-03T18:00:00+08:00",'
            '"version":"a2a-hmac-sha3-512/v1"}',
        )

    def test_valid_envelope(self):
        self.assertEqual(verify(envelope()), (True, "ok"))

    def test_replay_rejected(self):
        cache = replay_cache()
        self.assertEqual(verify(envelope(), cache=cache), (True, "ok"))
        self.assertEqual(verify(envelope(), cache=cache), (False, "重复 nonce"))

    def test_replay_rejected_after_cache_reopen(self):
        path = pathlib.Path(CACHE_DIRECTORY.name, f"{secrets.token_hex(12)}.sqlite3")
        self.assertEqual(verify(envelope(), cache=replay_cache(path)), (True, "ok"))
        self.assertEqual(verify(envelope(), cache=replay_cache(path)), (False, "重复 nonce"))

    def test_future_timestamp_nonce_retained_for_full_acceptance_period(self):
        future = NOW + timedelta(seconds=M.DEFAULT_WINDOW)
        value = M.build_envelope(
            SENDER,
            RECIPIENT,
            BODY,
            KEY,
            KEY_ID,
            timestamp=future.isoformat(),
            nonce=NONCE,
        )
        cache = replay_cache()
        self.assertEqual(verify(value, cache=cache, now=NOW), (True, "ok"))
        self.assertEqual(
            verify(value, cache=cache, now=NOW + timedelta(seconds=M.DEFAULT_WINDOW + 1)),
            (False, "重复 nonce"),
        )

    def test_concurrent_replay_claim_is_atomic(self):
        path = pathlib.Path(CACHE_DIRECTORY.name, f"{secrets.token_hex(12)}.sqlite3")
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(
                lambda _: verify(envelope(), cache=replay_cache(path)),
                range(2),
            ))
        self.assertEqual(results.count((True, "ok")), 1)
        self.assertEqual(results.count((False, "重复 nonce")), 1)

    def test_memory_only_replay_cache_rejected(self):
        with self.assertRaises(ValueError):
            M.ReplayCache(":memory:")

    def test_missing_replay_cache_rejected(self):
        value = envelope()
        result = M.verify_envelope(value, KEY, KEY_ID, SENDER, RECIPIENT, BODY, None, now=NOW)
        self.assertEqual(result, (False, "nonce 缓存缺失"))

    def test_body_tamper_rejected(self):
        self.assertEqual(verify(envelope(), body=b"hellO"), (False, "正文摘要不匹配"))

    def test_body_is_mandatory_bytes(self):
        self.assertEqual(verify(envelope(), body=None), (False, "包络格式非法"))

    def test_tag_tamper_rejected(self):
        value = envelope()
        value["tag"] = ("0" if value["tag"][0] != "0" else "1") + value["tag"][1:]
        self.assertEqual(verify(value), (False, "tag 不匹配"))

    def test_bad_tag_type_rejected(self):
        value = envelope()
        value["tag"] = None
        self.assertEqual(verify(value), (False, "tag 格式非法"))

    def test_wrong_key_id_rejected(self):
        self.assertEqual(verify(envelope(), key_id="wrong"), (False, "错误 key_id"))

    def test_wrong_sender_rejected(self):
        self.assertEqual(verify(envelope(), sender="other"), (False, "发送方错配"))

    def test_wrong_recipient_rejected(self):
        self.assertEqual(verify(envelope(), recipient="other"), (False, "接收方错配"))

    def test_short_key_rejected(self):
        self.assertEqual(verify(envelope(), key=b"x"), (False, "包络格式非法"))

    def test_stale_timestamp_rejected(self):
        self.assertEqual(
            verify(envelope(), now=NOW + timedelta(seconds=301)),
            (False, "时间窗超界"),
        )

    def test_future_timestamp_rejected(self):
        self.assertEqual(
            verify(envelope(), now=NOW - timedelta(seconds=301)),
            (False, "时间窗超界"),
        )

    def test_naive_now_rejected(self):
        self.assertEqual(
            verify(envelope(), now=datetime(2026, 10, 3, 18, 0, 0)),
            (False, "当前时间缺少时区"),
        )

    def test_naive_timestamp_rejected(self):
        value = envelope()
        value["timestamp"] = "2026-10-03T18:00:00"
        self.assertEqual(verify(value), (False, "包络格式非法"))

    def test_z_timestamp_accepted(self):
        value = M.build_envelope(
            SENDER,
            RECIPIENT,
            BODY,
            KEY,
            KEY_ID,
            timestamp="2026-10-03T10:00:00Z",
            nonce=NONCE,
        )
        self.assertEqual(verify(value), (True, "ok"))

    def test_short_nonce_rejected(self):
        value = envelope()
        value["nonce"] = "abcd"
        self.assertEqual(verify(value), (False, "包络格式非法"))

    def test_non_hex_nonce_rejected(self):
        value = envelope()
        value["nonce"] = "z" * 32
        self.assertEqual(verify(value), (False, "包络格式非法"))

    def test_wrong_version_rejected(self):
        value = envelope()
        value["version"] = "a2a-hmac-sha3-256/v1"
        self.assertEqual(verify(value), (False, "version 不匹配"))

    def test_missing_field_rejected(self):
        value = envelope()
        value.pop("sender_id")
        self.assertEqual(verify(value), (False, "包络字段集合不匹配"))

    def test_extra_field_rejected(self):
        value = envelope()
        value["extra"] = "unexpected"
        self.assertEqual(verify(value), (False, "包络字段集合不匹配"))

    def test_non_default_window_rejected(self):
        for window in (0, 299, 301, True):
            with self.subTest(window=window):
                self.assertEqual(
                    verify(envelope(), window=window),
                    (False, "时间窗必须固定为 300 秒"),
                )

    def test_bad_tag_does_not_poison_cache(self):
        cache = replay_cache()
        bad = copy.deepcopy(envelope())
        bad["tag"] = "0" * 128
        self.assertEqual(verify(bad, cache=cache), (False, "tag 不匹配"))
        self.assertEqual(verify(envelope(), cache=cache), (True, "ok"))

    def test_identifier_rejected(self):
        with self.assertRaises(ValueError):
            M.build_envelope("含空格", RECIPIENT, BODY, KEY, KEY_ID)

    def test_random_nonce_has_128_bits(self):
        value = M.build_envelope(SENDER, RECIPIENT, BODY, secrets.token_bytes(64), KEY_ID)
        self.assertRegex(value["nonce"], r"^[0-9a-f]{32}$")

    def test_non_string_envelope_value_rejected(self):
        value = envelope()
        value["sender_id"] = 1
        self.assertEqual(verify(value), (False, "发送方错配"))


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(A2AHmacTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    print(f"VERDICT={'PASS' if result.wasSuccessful() else 'BAD'} tests={result.testsRun}")
    raise SystemExit(0 if result.wasSuccessful() else 1)

# SHA3-512 A2A Hash Tree

TREE-K3-2026-1003-01 — built by seat k3-main (kimi-work-desktop) under owner directive 2026-10-03.
Standard: SHA3-512 leaves; internal nodes = HMAC-SHA3-512(key, L||R), compatible with
System.Security.Cryptography.HMACSHA3_512 (.NET 10) and any standard implementation (python hashlib/hmac, OpenSSL).
Odd levels duplicate the last node.

- Root: see manifest field `root_sha3_512_hmac`
- Key: self-retained by the key owner on the originating device (NEVER uploaded).
- Key fingerprint (public): see manifest field `key_fingerprint_sha3_512`
- Cross-vendor verification: leaves verify keyless; internal nodes reproduce with the retained key.
- Leaves anchor: owner directive txt, sourceA OpenPlanLink doc, receipt#63 bundle, Supabase bus ids 11204/11372/11375, Neon a2a_archive row 1, WPS archive DF-K3-2026-1001-ARCH-01.
- Gate: pushed after 5-gate outbound review DF-K3-2026-1003-GATE-01 (one-shot authorization).

from __future__ import annotations

from io import BytesIO
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from zipfile import ZipFile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import git_upload_gate as gate

ROOT = Path(__file__).resolve().parents[1]
SECRET = "s" + "k-" + "A1b2C3d4" * 6
ZERO = "0" * 40


class RealGitTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="opl-git-gate-")
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name) / "repo"
        self.repo.mkdir()
        self.env = os.environ.copy()
        self.env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull,
                        GIT_AUTHOR_NAME="Gate Test", GIT_AUTHOR_EMAIL="gate@example.invalid",
                        GIT_COMMITTER_NAME="Gate Test", GIT_COMMITTER_EMAIL="gate@example.invalid",
                        GIT_TERMINAL_PROMPT="0", OPL_PYTHON=sys.executable)
        self.git("init", "-q", "--initial-branch=main")
        self.write("README.md", "clean baseline\n")
        self.base = self.commit("initial")

    def git(self, *args, check=True):
        r = subprocess.run(["git", "-C", str(self.repo), "-c", "commit.gpgsign=false",
                            "-c", "core.autocrlf=false", *args],
                           env=self.env, capture_output=True, timeout=30)
        if check and r.returncode:
            self.fail("Git fixture command failed, exit=" + str(r.returncode))
        return r

    def write(self, name, value):
        p = self.repo / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(value if isinstance(value, bytes) else value.encode())

    def commit(self, msg):
        self.git("add", "--all")
        self.git("commit", "-q", "-m", msg)
        return self.git("rev-parse", "HEAD").stdout.decode().strip()

    def audit(self, new=None, old=None):
        return gate.audit(self.repo, [(new or self.git("rev-parse", "HEAD").stdout.decode().strip(),
                                       old or self.base)])

    def test_clean_range_and_unicode_spaces(self):
        self.write("目录 名/附件 一.txt", "已核验的清洁文本\n")
        self.commit("clean")
        r = self.audit()
        self.assertEqual("pass", r["status"])
        self.assertGreater(r["scanned_objects"], 0)

    def test_secret_deleted_in_later_commit_still_blocks(self):
        self.write("old.txt", SECRET)
        self.commit("credential introduced")
        (self.repo / "old.txt").unlink()
        self.commit("credential removed")
        self.assertEqual("blocked_credentials", self.audit()["status"])

    def test_staged_secret_with_clean_worktree_still_blocks(self):
        self.write("staged.txt", SECRET)
        self.git("add", "staged.txt")
        self.write("staged.txt", "clean worktree")
        self.git("commit", "-q", "-m", "staged")
        self.assertEqual("blocked_credentials", self.audit()["status"])

    def test_non_head_and_multiple_ref_updates(self):
        self.git("switch", "-q", "-c", "topic")
        self.write("topic.txt", SECRET)
        topic = self.commit("topic")
        self.git("switch", "-q", "main")
        r = gate.audit(self.repo, [(self.base, self.base), (topic, ZERO)])
        self.assertEqual("blocked_credentials", r["status"])

    def test_unknown_remote_oid_scans_all_history(self):
        self.write("value.txt", SECRET)
        self.commit("value")
        r = self.audit(old="f" * 40)
        self.assertEqual("blocked_credentials", r["status"])

    def test_force_update_checks_new_side(self):
        self.write("old-branch.txt", "old clean")
        remote = self.commit("remote")
        self.git("switch", "-q", "--detach", self.base)
        self.write("new.txt", SECRET)
        new = self.commit("new diverged")
        self.assertEqual("blocked_credentials", self.audit(new, remote)["status"])

    def test_annotated_tag_message_is_scanned(self):
        self.git("tag", "-a", "v1", "-m", SECRET)
        tag = self.git("rev-parse", "v1").stdout.decode().strip()
        self.assertEqual("blocked_credentials", self.audit(tag)["status"])

    def test_commit_message_is_scanned(self):
        self.write("clean.txt", "clean")
        self.commit(SECRET)
        self.assertEqual("blocked_credentials", self.audit()["status"])

    def test_deletion_does_not_scan_old_history(self):
        r = gate.audit(self.repo, [(ZERO, self.base)])
        self.assertEqual("pass", r["status"])
        self.assertEqual(0, r["scanned_objects"])

    def test_repository_replace_cannot_hide_secret(self):
        self.write("value.txt", SECRET)
        secret_commit = self.commit("secret")
        self.git("replace", secret_commit, self.base)
        self.assertEqual("blocked_credentials", self.audit(secret_commit)["status"])

    def test_shallow_repository_is_incomplete(self):
        (self.repo / ".git/shallow").write_text(self.base + "\n")
        self.assertEqual("incomplete", self.audit()["status"])

    def test_partial_clone_is_incomplete(self):
        self.git("config", "remote.origin.promisor", "true")
        self.assertEqual("incomplete", self.audit()["status"])

    def test_missing_object_does_not_pass_or_echo_errors(self):
        r = self.audit(new="a" * 40)
        self.assertEqual("incomplete", r["status"])
        self.assertNotIn("fatal", json.dumps(r))

    def test_test_and_api_key_context_do_not_downgrade(self):
        self.write("fixture.py", 'API_KEY = "' + SECRET + '" # test fixture\n')
        self.commit("fixture")
        self.assertEqual("blocked_credentials", self.audit()["status"])

    def test_output_omits_secret_and_filename(self):
        self.write(SECRET + ".txt", SECRET)
        self.commit("opaque test")
        serialized = json.dumps(self.audit())
        self.assertNotIn(SECRET, serialized)
        self.assertNotIn(SECRET[:8], serialized)
        self.assertNotIn(SECRET[-8:], serialized)
        self.assertIn("tree/name", serialized)

    def test_utf16_value_is_checked(self):
        self.write("wide.txt", SECRET.encode("utf-16"))
        self.commit("wide")
        self.assertEqual("blocked_credentials", self.audit()["status"])

    def test_opaque_binary_is_incomplete(self):
        self.write("asset.bin", b"\x00\xff\x00")
        self.commit("asset")
        self.assertEqual("incomplete", self.audit()["status"])

    def test_lfs_pointer_does_not_claim_external_content_checked(self):
        self.write("large.txt", "version https://git-lfs.github.com/spec/v1\noid sha256:" + "a" * 64 + "\nsize 100\n")
        self.commit("lfs")
        self.assertEqual("incomplete", self.audit()["status"])

    def test_large_blob_is_incomplete(self):
        self.write("large.txt", b"a" * (gate.MAX_BYTES + 1))
        self.commit("large")
        self.assertEqual("incomplete", self.audit()["status"])

    def test_ooxml_split_runs_and_relationship_attributes(self):
        for label, member, data in [
            ("runs", "word/document.xml", '<doc><t>' + SECRET[:12] + '</t><t>' + SECRET[12:] + '</t></doc>'),
            ("rels", "word/_rels/document.xml.rels", '<rels Target="https://host.invalid/?to' + 'ken=' + SECRET + '"/>')]:
            with self.subTest(label=label):
                container = BytesIO()
                with ZipFile(container, "w") as z:
                    z.writestr(member, data)
                self.write(label + ".docx", container.getvalue())
                self.commit(label)
                self.assertEqual("blocked_credentials", self.audit()["status"])

    def test_zip_member_names_do_not_extract_paths(self):
        container = BytesIO()
        with ZipFile(container, "w") as z:
            z.writestr("../../outside.txt", SECRET)
        self.write("archive.zip", container.getvalue())
        self.commit("archive")
        self.assertEqual("blocked_credentials", self.audit()["status"])
        self.assertFalse((Path(self.temp.name).parent / "outside.txt").exists())

    def install_hook(self):
        self.write("tools/git_upload_gate.py", (ROOT / "tools/git_upload_gate.py").read_bytes())
        hook = self.repo / ".git/hooks/pre-push"
        hook.write_bytes((ROOT / "tools/hooks/pre-push").read_bytes())
        hook.chmod(0o755)
        remote = Path(self.temp.name) / "remote.git"
        r = subprocess.run(["git", "init", "--bare", "-q", str(remote)], capture_output=True,
                           env=self.env, timeout=30)
        self.assertEqual(0, r.returncode)
        self.git("remote", "add", "origin", str(remote))
        self.commit("install local gate")
        return remote

    def test_real_push_passes_clean_and_blocks_deleted_history(self):
        remote = self.install_hook()
        self.assertEqual(0, self.git("push", "-q", "origin", "HEAD:refs/heads/topic", check=False).returncode)
        before = subprocess.run(["git", "--git-dir", str(remote), "rev-parse", "refs/heads/topic"],
                                capture_output=True, env=self.env).stdout
        self.write("credential.txt", SECRET)
        self.commit("credential")
        (self.repo / "credential.txt").unlink()
        self.commit("removed")
        r = self.git("push", "-q", "origin", "HEAD:refs/heads/topic", check=False)
        self.assertNotEqual(0, r.returncode)
        self.assertNotIn(SECRET.encode(), r.stdout + r.stderr)
        after = subprocess.run(["git", "--git-dir", str(remote), "rev-parse", "refs/heads/topic"],
                               capture_output=True, env=self.env).stdout
        self.assertEqual(before, after)

    def test_real_push_missing_checker_is_blocked(self):
        self.install_hook()
        (self.repo / "tools/git_upload_gate.py").unlink()
        r = self.git("push", "-q", "origin", "main", check=False)
        self.assertNotEqual(0, r.returncode)
        self.assertIn(b"checker_missing", r.stderr)

    def test_bad_hook_input_is_rejected(self):
        with self.assertRaises(gate.GateError):
            gate.updates_from_stdin("refs/heads/main --bad refs/heads/main " + ZERO)

    def test_unsigned_main_commit_blocks(self):
        self.write("new.txt", "clean")
        new = self.commit("unsigned main")
        r = gate.audit(self.repo, [(new, self.base)], signed_updates=[(new, self.base)])
        self.assertEqual("blocked_signature", r["status"])

    def configure_test_signer(self):
        key = Path(self.temp.name) / "test_signer"
        r = subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(key)],
                           env=self.env, capture_output=True, timeout=30)
        self.assertEqual(0, r.returncode)
        allowed = Path(self.temp.name) / "allowed_signers"
        allowed.write_text("gate@example.invalid " + key.with_suffix(".pub").read_text(), encoding="utf-8")
        self.git("config", "gpg.format", "ssh")
        self.git("config", "user.signingkey", str(key))
        self.git("config", "gpg.ssh.allowedSignersFile", str(allowed))
        return allowed

    def test_trusted_ssh_signature_passes(self):
        self.configure_test_signer()
        self.write("new.txt", "clean signed")
        self.git("add", "--all")
        self.git("commit", "-q", "-S", "-m", "signed main")
        new = self.git("rev-parse", "HEAD").stdout.decode().strip()
        r = gate.audit(self.repo, [(new, self.base)], signed_updates=[(new, self.base)])
        self.assertEqual("pass", r["status"])

    def test_signature_without_allowed_signer_blocks(self):
        allowed = self.configure_test_signer()
        self.write("new.txt", "clean signed")
        self.git("add", "--all")
        self.git("commit", "-q", "-S", "-m", "signed")
        new = self.git("rev-parse", "HEAD").stdout.decode().strip()
        allowed.write_text("", encoding="utf-8")
        r = gate.audit(self.repo, [(new, self.base)], signed_updates=[(new, self.base)])
        self.assertEqual("blocked_signature", r["status"])


if __name__ == "__main__":
    unittest.main()

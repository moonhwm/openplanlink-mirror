"""Real local/bare Git fixtures; no network service or real credentials."""
import base64
import importlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

TOOLS = Path(__file__).resolve().parents[1] / 'tools'
sys.path.insert(0, str(TOOLS))
import build_opl_tree
import hmac_key_policy
import push_gate


class DeliveryTreeTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name)
        self.delivery = self.root / 'deliveries'
        self.delivery.mkdir()
        (self.delivery / 'one.txt').write_text('one', encoding='utf-8')
        self.key_file = self.root / 'existing.key'
        self.key = bytes(range(64))
        self.key_file.write_bytes(self.key)

    def invoke(self, key_file):
        output = io.StringIO()
        with redirect_stdout(output):
            status = build_opl_tree.main(['--repo', str(self.root), '--directory', 'deliveries',
                                          '--key-file', str(key_file)])
        return status, output.getvalue()

    def test_import_has_no_home_or_key_side_effect(self):
        before = self.key_file.read_bytes()
        environment = dict(os.environ, HOME=str(self.root), USERPROFILE=str(self.root),
                           OPL_A2A_HMAC_KEY_FILE=str(self.key_file))
        command = 'import sys; sys.path.insert(0,sys.argv[1]); import build_opl_tree'
        result = subprocess.run([sys.executable, '-c', command, str(TOOLS)],
                                env=environment, capture_output=True, timeout=20)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, b'')
        self.assertEqual(before, self.key_file.read_bytes())
        self.assertFalse((self.delivery / build_opl_tree.OUTPUT).exists())

    def test_missing_and_invalid_key_never_creates_or_replaces_it(self):
        missing = self.root / 'missing.key'
        self.assertEqual(self.invoke(missing)[0], 1)
        self.assertFalse(missing.exists())
        self.key_file.write_bytes(b'short')
        self.assertEqual(self.invoke(self.key_file)[0], 1)
        self.assertEqual(self.key_file.read_bytes(), b'short')
        self.assertFalse((self.delivery / build_opl_tree.OUTPUT).exists())

    def test_existing_key_and_delivery_contract_match_canonical_node(self):
        (self.delivery / '二.txt').write_text('two', encoding='utf-8')
        stamp = '2026-10-05T12:00:00.000Z'
        actual = build_opl_tree.build_manifest(self.delivery, self.key, 'fixture', stamp)
        inputs = [{'path': p.name, 'bytes': list(p.read_bytes())}
                  for p in self.delivery.iterdir()]
        command = ('import {buildManifest} from ' + json.dumps((TOOLS / 'sha3-tree.mjs').as_uri()) + ';'
                   'let data="";for await(const p of process.stdin)data+=p;'
                   'const f=JSON.parse(data).map(x=>({path:x.path,bytes:Buffer.from(x.bytes)}));'
                   'console.log(JSON.stringify(buildManifest(f,Buffer.from(process.env.FIXTURE_KEY,"base64"),"fixture","' + stamp + '")));')
        environment = dict(os.environ, FIXTURE_KEY=base64.b64encode(self.key).decode('ascii'))
        result = subprocess.run(['node', '--input-type=module', '-e', command],
                                input=json.dumps(inputs).encode(), env=environment,
                                capture_output=True, timeout=20)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(actual, json.loads(result.stdout))
        self.assertEqual(self.invoke(self.key_file)[0], 0)
        self.assertEqual(self.key_file.read_bytes(), self.key)
        self.assertEqual(json.loads((self.delivery / build_opl_tree.OUTPUT).read_text())['file_count'], 2)

    def test_invalid_environment_key_does_not_fall_back_to_valid_file(self):
        with patch.dict(os.environ, {'OPL_A2A_HMAC_KEY_B64': 'invalid',
                                     'OPL_A2A_HMAC_KEY_FILE': str(self.key_file)}):
            with self.assertRaises(hmac_key_policy.KeyPolicyError):
                hmac_key_policy.load_existing_key()
        self.assertEqual(self.key_file.read_bytes(), self.key)

    def test_nested_manifest_is_content_and_only_output_self_is_excluded(self):
        nested = self.delivery / 'nested'
        nested.mkdir()
        (nested / build_opl_tree.OUTPUT).write_text('nested attachment')
        (self.delivery / build_opl_tree.OUTPUT).write_text('old output')
        manifest = build_opl_tree.build_manifest(self.delivery, self.key, 'fixture')
        self.assertEqual(manifest['file_count'], 2)
        self.assertEqual([item['path'] for item in manifest['files']],
                         ['nested/hmac_attest.json', 'one.txt'])


class PushOrchestrationTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name)
        self.repo = self.root / 'working'
        self.repo.mkdir()
        environment = dict(os.environ)
        for name in list(environment):
            if name.startswith('OPL_A2A_HMAC_') or name in ('GIT_DIR', 'GIT_WORK_TREE', 'GIT_INDEX_FILE'):
                environment.pop(name)
        environment.update(GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull,
                           GIT_TERMINAL_PROMPT='0')
        context = patch.dict(os.environ, environment, clear=True)
        context.start()
        self.addCleanup(context.stop)
        self.key_file = self.root / 'fixture.key'
        self.key = bytes(range(64))
        self.key_file.write_bytes(self.key)
        self.git('init', '-b', 'feature')
        self.configure(self.repo)
        (self.repo / '.gitignore').write_text('__pycache__/\n*.pyc\n')
        (self.repo / 'initial.txt').write_text('initial\n')
        (self.repo / 'tools').mkdir()
        for name in ('sha3-tree.mjs', 'git_upload_gate.py'):
            shutil.copyfile(TOOLS / name, self.repo / 'tools' / name)
        self.commit('base')
        self.remotes = []
        for name in ('origin', 'gitcode'):
            bare = self.root / (name + '.git')
            self.raw(self.root, 'git', 'init', '--bare', '-b', 'feature', str(bare))
            self.git('remote', 'add', name, str(bare))
            self.git('push', name, 'HEAD:refs/heads/feature')
            self.remotes.append(bare)
        self.base = self.git('rev-parse', 'HEAD')

    def raw(self, cwd, *arguments):
        result = subprocess.run(arguments, cwd=cwd, capture_output=True, timeout=30)
        if result.returncode:
            self.fail('fixture_command_failed')
        return result.stdout.decode('utf-8').strip()

    def git(self, *arguments):
        return self.raw(self.repo, 'git', *arguments)

    def configure(self, repo):
        for key, value in (('user.name', 'Fixture'), ('user.email', 'fixture@example.invalid'),
                           ('commit.gpgsign', 'false')):
            self.raw(repo, 'git', 'config', key, value)

    def commit(self, message):
        self.git('add', '--all')
        self.git('commit', '-m', message)

    def heads(self, branch='feature'):
        return [self.raw(path, 'git', 'rev-parse', 'refs/heads/' + branch) for path in self.remotes]

    def controller(self, cls=push_gate.Controller, **kwargs):
        return cls(self.repo, key_file=kwargs.pop('key_file', self.key_file), **kwargs)

    def add_clean(self):
        (self.repo / 'clean.txt').write_text('new work\n')
        self.commit('clean work')

    def peer(self, index=0):
        peer = self.root / ('peer' + str(index))
        self.raw(self.root, 'git', 'clone', str(self.remotes[index]), str(peer))
        self.configure(peer)
        return peer

    def test_actual_dual_fast_forward_push_and_idempotent_second_run(self):
        self.add_clean()
        result = self.controller().gate()
        self.assertEqual(result['status'], 'success')
        head = self.git('rev-parse', 'HEAD')
        self.assertEqual(self.heads(), [head, head])
        self.assertEqual(self.key_file.read_bytes(), self.key)
        self.assertFalse(result['force_push_used'])
        self.assertFalse(result['distributed_atomicity'])
        second = self.controller().gate()
        self.assertEqual(second['status'], 'success')
        self.assertEqual(self.git('rev-parse', 'HEAD'), head)

    def test_dirty_tree_is_preserved_without_stash(self):
        content = b'uncommitted work'
        (self.repo / 'initial.txt').write_bytes(content)
        result = self.controller().gate()
        self.assertEqual(result['code'], 'dirty_worktree')
        self.assertEqual((self.repo / 'initial.txt').read_bytes(), content)
        self.assertEqual(self.heads(), [self.base, self.base])
        self.assertFalse((self.repo / '.git/refs/stash').exists())

    def test_missing_key_stops_before_fetch_or_generation(self):
        missing = self.root / 'missing.key'
        result = self.controller(key_file=missing).gate()
        self.assertEqual(result['code'], 'key_source_unavailable')
        self.assertEqual(result['events'], [])
        self.assertFalse(missing.exists())
        self.assertEqual(self.heads(), [self.base, self.base])

    def test_fetch_failure_does_not_echo_remote_error_or_continue(self):
        marker = ('s' + 'k-') + 'Q' * 40
        self.git('remote', 'set-url', 'origin', str(self.root / ('absent-' + marker)))
        result = self.controller().gate()
        self.assertEqual(result['code'], 'fetch_failed')
        self.assertFalse(marker in json.dumps(result), 'remote_error_echoed')
        self.assertFalse(marker in (self.repo / '.git/opl-push-gate.jsonl').read_text(), 'journal_error_echoed')
        self.assertEqual(self.heads(), [self.base, self.base])

    def test_primary_rebase_preserves_nonconflicting_work_and_pushes_both(self):
        peer = self.peer()
        (peer / 'peer.txt').write_text('peer work\n')
        self.raw(peer, 'git', 'add', '--all')
        self.raw(peer, 'git', 'commit', '-m', 'peer')
        self.raw(peer, 'git', 'push', 'origin', 'feature')
        self.add_clean()
        result = self.controller().gate()
        self.assertEqual(result['status'], 'success')
        self.assertTrue(any(e['stage'] == 'rebased' for e in result['events']))
        self.assertTrue((self.repo / 'peer.txt').is_file())
        self.assertTrue((self.repo / 'clean.txt').is_file())
        head = self.git('rev-parse', 'HEAD')
        self.assertEqual(self.heads(), [head, head])

    def test_rebase_conflict_is_aborted_without_pushing(self):
        peer = self.peer()
        (peer / 'initial.txt').write_text('remote change\n')
        self.raw(peer, 'git', 'add', '--all')
        self.raw(peer, 'git', 'commit', '-m', 'remote')
        self.raw(peer, 'git', 'push', 'origin', 'feature')
        (self.repo / 'initial.txt').write_text('local change\n')
        self.commit('local')
        old_head, old_remotes = self.git('rev-parse', 'HEAD'), self.heads()
        result = self.controller().gate()
        self.assertEqual(result['code'], 'rebase_conflict_aborted')
        self.assertEqual(self.git('rev-parse', 'HEAD'), old_head)
        self.assertEqual(self.heads(), old_remotes)
        self.assertEqual(self.git('status', '--porcelain'), '')

    def test_divergent_mirror_is_not_forced_or_partially_uploaded(self):
        peer = self.peer(1)
        (peer / 'mirror.txt').write_text('mirror change\n')
        self.raw(peer, 'git', 'add', '--all')
        self.raw(peer, 'git', 'commit', '-m', 'mirror')
        self.raw(peer, 'git', 'push', 'origin', 'feature')
        self.add_clean()
        old_remotes = self.heads()
        result = self.controller().gate()
        self.assertEqual(result['code'], 'mirror_not_fast_forward')
        self.assertEqual(self.heads(), old_remotes)

    def test_deleted_historical_credential_blocks_all_remotes(self):
        marker = ('s' + 'k-') + 'Q' * 40
        path = self.repo / 'removed.txt'
        path.write_text(marker)
        self.commit('temporary content')
        path.unlink()
        self.commit('remove temporary content')
        result = self.controller().gate()
        self.assertEqual(result['code'], 'outgoing_objects_blocked_credentials')
        self.assertFalse(marker in json.dumps(result), 'credential_echoed')
        self.assertEqual(self.heads(), [self.base, self.base])

    def test_each_remote_uses_its_own_object_baseline(self):
        marker = ('s' + 'k-') + 'Q' * 40
        (self.repo / 'past.txt').write_text(marker)
        self.commit('past content')
        (self.repo / 'past.txt').unlink()
        self.commit('past removal')
        self.git('push', 'origin', 'feature')
        old_remotes = self.heads()
        result = self.controller().gate()
        self.assertEqual(result['code'], 'outgoing_objects_blocked_credentials')
        self.assertEqual(self.heads(), old_remotes)
        self.assertTrue(any(e['stage'] == 'outgoing_objects_pass' and e['remote_index'] == 0 for e in result['events']))

    def test_second_remote_rejection_records_partial_success(self):
        self.add_clean()
        hook = self.remotes[1] / 'hooks/pre-receive'
        hook.write_bytes(b'#!/bin/sh\nexit 1\n')
        hook.chmod(0o755)
        result = self.controller().gate()
        self.assertEqual(result['status'], 'partial_or_unknown')
        self.assertEqual(result['code'], 'push_not_confirmed')
        head = self.git('rev-parse', 'HEAD')
        self.assertEqual(self.heads(), [head, self.base])
        self.assertFalse(result['force_push_used'])

    def test_error_after_first_push_is_unknown_then_can_be_reconciled(self):
        self.add_clean()
        class Interrupted(push_gate.Controller):
            def run(instance, args, *other, **kwargs):
                result = super().run(args, *other, **kwargs)
                if args[0] == 'git' and 'push' in args:
                    raise subprocess.TimeoutExpired('hidden', 120)
                return result
        first = self.controller(Interrupted).gate()
        self.assertEqual(first['status'], 'partial_or_unknown')
        self.assertEqual(first['code'], 'operation_failed')
        second = self.controller().gate()
        self.assertEqual(second['status'], 'success')
        head = self.git('rev-parse', 'HEAD')
        self.assertEqual(self.heads(), [head, head])

    def test_main_unsigned_commits_remain_blocked(self):
        self.git('checkout', '-b', 'main')
        for name in ('origin', 'gitcode'):
            self.git('push', name, 'HEAD:refs/heads/main')
        self.add_clean()
        result = self.controller().gate()
        self.assertEqual(result['code'], 'outgoing_objects_blocked_signature')
        self.assertEqual(self.heads('main'), [self.base, self.base])

    def test_wrong_key_does_not_resign_existing_tree(self):
        self.assertEqual(self.controller().gate()['status'], 'success')
        manifest = (self.repo / push_gate.MANIFEST).read_bytes()
        self.add_clean()
        prior_head, prior_remotes = self.git('rev-parse', 'HEAD'), self.heads()
        other = self.root / 'other.key'
        other.write_bytes(bytes(reversed(range(64))))
        result = self.controller(key_file=other).gate()
        self.assertEqual(result['code'], 'prior_tree_authentication_failed')
        self.assertEqual((self.repo / push_gate.MANIFEST).read_bytes(), manifest)
        self.assertEqual(self.git('rev-parse', 'HEAD'), prior_head)
        self.assertEqual(self.heads(), prior_remotes)

    def test_key_change_before_push_is_preserved_and_blocks_upload(self):
        self.add_clean()
        replacement = bytes(reversed(range(64)))
        class ChangedKey(push_gate.Controller):
            def remote_oid(instance, remote, reference):
                result = super().remote_oid(remote, reference)
                instance.key_file.write_bytes(replacement)
                return result
        result = self.controller(ChangedKey).gate()
        self.assertEqual(result['code'], 'key_source_changed')
        self.assertEqual(self.key_file.read_bytes(), replacement)
        self.assertEqual(self.heads(), [self.base, self.base])

    def test_existing_pre_push_hook_is_preserved(self):
        self.add_clean()
        hook = self.repo / '.git/hooks/pre-push'
        hook.write_bytes(b'#!/bin/sh\nprintf retained > .git/fixture-hook-marker\nexit 1\n')
        hook.chmod(0o755)
        result = self.controller().gate()
        self.assertEqual(result['code'], 'push_not_confirmed')
        self.assertTrue((self.repo / '.git/fixture-hook-marker').exists())
        self.assertEqual(self.heads(), [self.base, self.base])

    def test_remote_rewind_after_precheck_uses_actual_server_reference(self):
        marker = ('s' + 'k-') + 'Q' * 40
        path = self.repo / 'past.txt'
        path.write_text(marker)
        self.commit('past content')
        path.unlink()
        self.commit('past removal')
        for name in ('origin', 'gitcode'):
            self.git('push', name, 'feature')
        mirror_prior = self.heads()[1]
        fixture = self
        class Rewound(push_gate.Controller):
            def run(instance, args, *other, **kwargs):
                if args[0] == 'git' and 'push' in args:
                    fixture.raw(fixture.remotes[0], 'git', 'update-ref', 'refs/heads/feature', fixture.base)
                return super().run(args, *other, **kwargs)
        result = self.controller(Rewound).gate()
        self.assertEqual(result['code'], 'push_not_confirmed')
        self.assertEqual(self.heads(), [self.base, mirror_prior])
        self.assertFalse(marker in json.dumps(result), 'credential_echoed')


if __name__ == '__main__':
    unittest.main()

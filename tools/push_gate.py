"""Fetch, reconcile, attest, inspect and fast-forward selected Git remotes."""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import subprocess
import sys

import git_upload_gate
from hmac_key_policy import KeyPolicyError, load_existing_key

MANIFEST = 'attest-hmac-sha3-512.json'
OID = re.compile(r'(?:[0-9a-f]{40}|[0-9a-f]{64})\Z')
PRE_PUSH = '''#!/bin/sh
set -eu
task_input=$(mktemp) || exit 2
trap 'rm -f -- "$task_input"' EXIT
cat > "$task_input"
"$OPL_PUSH_GATE_PYTHON" "$OPL_PUSH_GATE_CHECKER" --repo "$OPL_PUSH_GATE_REPO" --pre-push --require-signed-main < "$task_input" > /dev/null || exit $?
if [ -n "$OPL_PUSH_GATE_PREVIOUS_HOOK" ] && [ -x "$OPL_PUSH_GATE_PREVIOUS_HOOK" ]; then
  "$OPL_PUSH_GATE_PREVIOUS_HOOK" "$@" < "$task_input" || exit $?
fi
'''


class PushGateError(ValueError):
    pass


class Controller:
    def __init__(self, repo, remotes=None, branch=None, key_file=None, key_id=None):
        self.repo = Path(repo).resolve()
        self.requested_remotes = remotes
        self.requested_branch = branch
        self.key_file, self.key_id = key_file, key_id
        self.events = []
        self.server_reference_hook_configured = False
        self.git_dir = None
        self.env = dict(os.environ)
        for name in ('GIT_DIR', 'GIT_WORK_TREE', 'GIT_COMMON_DIR', 'GIT_INDEX_FILE',
                     'GIT_OBJECT_DIRECTORY', 'GIT_ALTERNATE_OBJECT_DIRECTORIES',
                     'GIT_NAMESPACE', 'GIT_SHALLOW_FILE', 'OPL_A2A_HMAC_KEY_B64'):
            self.env.pop(name, None)
        self.env.update(GIT_TERMINAL_PROMPT='0', GIT_NO_REPLACE_OBJECTS='1')

    def run(self, args, data=None, extra_env=None):
        environment = dict(self.env)
        if extra_env:
            environment.update(extra_env)
        return subprocess.run(args, cwd=self.repo, input=data, capture_output=True,
                              env=environment, timeout=120)

    def git(self, *args, code='git_command_failed'):
        result = self.run(['git', *args])
        if result.returncode:
            raise PushGateError(code)
        return result.stdout.decode('utf-8', errors='strict').strip()

    def head(self):
        value = self.git('rev-parse', '--verify', 'HEAD')
        if not OID.fullmatch(value):
            raise PushGateError('head_oid_invalid')
        return value

    def clean(self):
        if self.git('status', '--porcelain', '--untracked-files=all'):
            raise PushGateError('dirty_worktree')
        for name in ('rebase-merge', 'rebase-apply', 'MERGE_HEAD', 'CHERRY_PICK_HEAD', 'REVERT_HEAD'):
            if (self.git_dir / name).exists():
                raise PushGateError('git_operation_in_progress')

    @contextmanager
    def lock(self):
        path = self.git_dir / 'opl-push-gate.lock'
        try:
            descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except OSError:
            raise PushGateError('push_gate_lock_unavailable') from None
        original = os.fstat(descriptor)
        os.close(descriptor)
        try:
            yield
        finally:
            current = path.stat()
            if current.st_ino != original.st_ino:
                raise PushGateError('push_gate_lock_changed')
            path.unlink()

    def remote_oid(self, remote, reference):
        result = self.run(['git', 'ls-remote', '--exit-code', '--', remote, reference])
        if result.returncode:
            raise PushGateError('remote_reference_unavailable')
        lines = result.stdout.decode('ascii').splitlines()
        fields = lines[0].split() if len(lines) == 1 else []
        if len(fields) != 2 or fields[1] != reference or not OID.fullmatch(fields[0]):
            raise PushGateError('remote_reference_invalid')
        return fields[0]

    def ancestor(self, old, new):
        result = self.run(['git', 'merge-base', '--is-ancestor', old, new])
        if result.returncode not in (0, 1):
            raise PushGateError('ancestry_check_failed')
        return result.returncode == 0

    def push_hook(self):
        previous = Path(self.git('rev-parse', '--git-path', 'hooks/pre-push'))
        if not previous.is_absolute():
            previous = self.repo / previous
        directory = self.git_dir / 'opl-push-gate-hooks'
        directory.mkdir(exist_ok=True)
        hook = directory / 'pre-push'
        if previous.resolve() == hook.resolve():
            raise PushGateError('recursive_previous_hook')
        if hook.is_symlink() or directory.is_symlink():
            raise PushGateError('controlled_hook_link_not_supported')
        hook.write_bytes(PRE_PUSH.encode('utf-8'))
        hook.chmod(0o755)
        self.server_reference_hook_configured = True
        return directory, {'OPL_PUSH_GATE_PYTHON': sys.executable,
                           'OPL_PYTHON': self.env.get('OPL_PYTHON') or sys.executable,
                           'OPL_PUSH_GATE_CHECKER': str(Path(git_upload_gate.__file__).resolve()),
                           'OPL_PUSH_GATE_REPO': str(self.repo),
                           'OPL_PUSH_GATE_PREVIOUS_HOOK': str(previous) if previous.is_file() else ''}

    def execute(self):
        actual_root = Path(self.git('rev-parse', '--show-toplevel')).resolve()
        if actual_root != self.repo:
            raise PushGateError('run_from_selected_repository_root')
        self.git_dir = Path(self.git('rev-parse', '--absolute-git-dir'))
        with self.lock():
            self.clean()
            if self.git('rev-parse', '--is-shallow-repository') != 'false':
                raise PushGateError('shallow_repository')
            current = self.git('symbolic-ref', '--quiet', '--short', 'HEAD', code='detached_head')
            branch = self.requested_branch or current
            if current != branch or branch.startswith('-'):
                raise PushGateError('branch_mismatch')
            self.git('check-ref-format', '--branch', branch, code='branch_invalid')
            reference = 'refs/heads/' + branch
            configured = self.git('remote').splitlines()
            remotes = self.requested_remotes or [name for name in ('origin', 'gitcode') if name in configured]
            if not remotes or len(remotes) != len(set(remotes)):
                raise PushGateError('remote_selection_invalid')
            if any(name not in configured or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,63}', name) for name in remotes):
                raise PushGateError('remote_selection_invalid')
            material = load_existing_key(self.key_file, self.key_id)
            builder = self.repo / 'tools/sha3-tree.mjs'
            if not builder.is_file() or not (self.repo / 'tools/git_upload_gate.py').is_file():
                raise PushGateError('required_checker_missing')
            snapshots = []
            for index, remote in enumerate(remotes):
                target = 'refs/remotes/' + remote + '/' + branch
                self.git('fetch', '--no-tags', '--', remote, reference + ':' + target, code='fetch_failed')
                old = self.git('rev-parse', '--verify', target)
                if not OID.fullmatch(old):
                    raise PushGateError('fetched_oid_invalid')
                snapshots.append((remote, old))
                self.events.append({'stage': 'fetched', 'remote_index': index, 'old_oid': old})
            old_head = self.head()
            if not self.ancestor(snapshots[0][1], old_head):
                result = self.run(['git', '-c', 'rebase.autoStash=false', 'rebase', snapshots[0][1]])
                if result.returncode:
                    aborted = self.run(['git', 'rebase', '--abort'])
                    if aborted.returncode or self.head() != old_head:
                        raise PushGateError('rebase_abort_not_verified')
                    raise PushGateError('rebase_conflict_aborted')
                self.events.append({'stage': 'rebased', 'head_oid': self.head()})
            self.clean()
            if any(not self.ancestor(old, self.head()) for _, old in snapshots):
                raise PushGateError('mirror_not_fast_forward')
            verification = self.run(['node', str(builder), 'verify'], extra_env=material.environment())
            if verification.returncode:
                tracked = self.run(['git', 'ls-files', '--error-unmatch', '--', MANIFEST])
                if tracked.returncode == 0:
                    material.authenticate_manifest_root(self.git('show', ':' + MANIFEST))
                elif tracked.returncode != 1:
                    raise PushGateError('prior_manifest_read_failed')
                result = self.run(['node', str(builder), 'build'], extra_env=material.environment())
                if result.returncode:
                    raise PushGateError('tree_build_failed')
                self.git('add', '--', MANIFEST, code='manifest_stage_failed')
                checked = self.run(['node', str(builder), 'verify'], extra_env=material.environment())
                if checked.returncode:
                    raise PushGateError('tree_verification_failed')
                if self.git('diff', '--cached', '--name-only', '-z') != MANIFEST + '\0':
                    raise PushGateError('unexpected_staged_changes_before_manifest_commit')
                self.git('commit', '--only', '-m', 'push-gate: refresh verified tree',
                         '--', MANIFEST, code='manifest_commit_failed')
                self.events.append({'stage': 'tree_refreshed', 'head_oid': self.head()})
            else:
                self.events.append({'stage': 'existing_tree_verified'})
            self.clean()
            head = self.head()
            hook_directory, hook_environment = self.push_hook()
            for index, (_, old) in enumerate(snapshots):
                updates = [(head, old)]
                result = git_upload_gate.audit(self.repo, updates,
                                               signed_updates=updates if reference == 'refs/heads/main' else None)
                if result['status'] != 'pass':
                    raise PushGateError('outgoing_objects_' + result['status'])
                self.events.append({'stage': 'outgoing_objects_pass', 'remote_index': index,
                                    'scanned_objects': result['scanned_objects']})
            material.verify_unchanged()
            for remote, old in snapshots:
                if self.remote_oid(remote, reference) != old:
                    raise PushGateError('remote_changed_before_push')
            for index, (remote, old) in enumerate(snapshots):
                self.clean()
                if self.head() != head:
                    raise PushGateError('local_head_changed_before_push')
                material.verify_unchanged()
                self.events.append({'stage': 'push_started', 'remote_index': index, 'head_oid': head})
                result = self.run(['git', '-c', 'core.hooksPath=' + str(hook_directory),
                                   'push', '--', remote, head + ':' + reference],
                                  extra_env=hook_environment)
                try:
                    actual = self.remote_oid(remote, reference)
                except PushGateError:
                    self.events.append({'stage': 'push_readback_unavailable', 'remote_index': index,
                                        'push_exit': result.returncode})
                    raise
                if actual != head:
                    self.events.append({'stage': 'push_not_confirmed', 'remote_index': index,
                                        'push_exit': result.returncode, 'observed_oid': actual})
                    raise PushGateError('push_not_confirmed')
                self.events.append({'stage': 'remote_verified', 'remote_index': index,
                                    'head_oid': head, 'push_exit': result.returncode})
            return {'status': 'success', 'head_oid': head, 'remote_count': len(remotes)}

    def gate(self):
        try:
            result = self.execute()
        except (PushGateError, KeyPolicyError) as error:
            result = {'status': 'partial_or_unknown' if any(e['stage'] == 'push_started' for e in self.events) else 'blocked',
                      'code': str(error)}
        except (OSError, ValueError, UnicodeError, subprocess.SubprocessError):
            result = {'status': 'partial_or_unknown' if any(e['stage'] == 'push_started' for e in self.events) else 'blocked',
                      'code': 'operation_failed'}
        result.update(schema='openplanlink.push-orchestration/1', events=self.events,
                      recorded_at=datetime.now(timezone.utc).isoformat(),
                      force_push_used=False, distributed_atomicity=False,
                      existing_pre_push_hook_preserved=True,
                      server_reference_hook_configured=self.server_reference_hook_configured)
        if self.git_dir is not None:
            journal = self.git_dir / 'opl-push-gate.jsonl'
            try:
                if journal.is_symlink():
                    raise OSError()
                with journal.open('a', encoding='utf-8') as stream:
                    stream.write(json.dumps(result, ensure_ascii=False) + '\n')
            except OSError:
                result.update(status='receipt_write_failed', code='receipt_write_failed')
        return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--remote', action='append')
    parser.add_argument('--branch')
    parser.add_argument('--key-file', type=Path)
    parser.add_argument('--key-id')
    args = parser.parse_args(argv)
    result = Controller(args.repo, args.remote, args.branch, args.key_file, args.key_id).gate()
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result['status'] == 'success' else 1


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    raise SystemExit(main())

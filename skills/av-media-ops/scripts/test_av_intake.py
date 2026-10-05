#!/usr/bin/env python3
import io
import json
import os
import posixpath
import subprocess
import tempfile
import unittest
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from types import SimpleNamespace
from unittest.mock import mock_open, patch

import av_intake as A


SOURCE_INFO = {
    'duration_s': 60,
    'format_name': 'mov,mp4,m4a,3gp,3g2,mj2',
    'chapters': 0,
    'streams': [{
        'codec_type': 'video', 'codec_name': 'h264', 'width': 1920, 'height': 1080,
        'avg_frame_rate': '30/1',
    }],
}
OUTPUT_INFO = {
    'duration_s': 60,
    'format_name': 'mov,mp4,m4a,3gp,3g2,mj2',
    'chapters': 0,
    'streams': [{
        'codec_type': 'video', 'codec_name': 'hevc', 'width': 1920, 'height': 1080,
        'avg_frame_rate': '30/1',
    }],
}


def make_source(directory):
    path = os.path.join(directory, 'in.mp4')
    with open(path, 'wb') as source:
        source.write(b'source-media')
    return path


def stage_names(directory):
    return [name for name in os.listdir(directory) if name.startswith('._av_stage_')]


class CodecProfileTests(unittest.TestCase):
    def setUp(self):
        self.real_resolver = A.resolve_media_executable
        self.real_pinner = A.pinned_media_executable

        def trusted_binary(name):
            return os.path.abspath(os.path.join(os.sep, 'trusted', name + '.exe'))

        @contextmanager
        def pinned_binary(name):
            yield trusted_binary(name), ()

        resolver = patch.object(A, 'resolve_media_executable', side_effect=trusted_binary)
        pinner = patch.object(A, 'pinned_media_executable', side_effect=pinned_binary)
        resolver.start()
        pinner.start()
        self.addCleanup(resolver.stop)
        self.addCleanup(pinner.stop)

    def test_parse_video_encoders(self):
        output = """
 V....D libsvtav1           SVT-AV1 encoder
 V..... libaom-av1          libaom AV1
 A..... aac                 AAC encoder
 V....D libx265             libx265 H.265
"""
        self.assertEqual(A.parse_video_encoders(output), {'libsvtav1', 'libaom-av1', 'libx265'})

    def test_av1_prefers_svt_and_bounds_native_workers(self):
        encoder, options = A.select_video_profile('av1', {'libaom-av1', 'libsvtav1'})
        self.assertEqual(encoder, 'libsvtav1')
        self.assertIn('lp=4', options)

    def test_unknown_codec_is_rejected(self):
        with self.assertRaises(ValueError):
            A.select_video_profile('vp9', set())

    def test_media_executable_rejects_relative_override_and_cwd_lookup(self):
        with patch.dict(A.os.environ, {'AV_FFMPEG_PATH': 'relative.exe'}):
            self.assertIsNone(self.real_resolver('ffmpeg'))
        cwd_binary = os.path.join(os.getcwd(), 'tools', 'ffmpeg.exe')
        with patch.dict(A.os.environ, {'AV_FFMPEG_PATH': ''}):
            with patch.object(A.shutil, 'which', return_value=cwd_binary):
                self.assertIsNone(self.real_resolver('ffmpeg'))

    def test_media_executable_ignores_relative_path_entries(self):
        with tempfile.TemporaryDirectory() as td:
            path_value = os.pathsep.join(('relative-bin', td))
            with patch.dict(A.os.environ, {'AV_FFMPEG_PATH': '', 'PATH': path_value}):
                with patch.object(A.shutil, 'which', return_value=None) as which:
                    self.assertIsNone(self.real_resolver('ffmpeg'))
        self.assertEqual(which.call_args.kwargs['path'], td)

    def test_pinned_media_executable_detects_content_change(self):
        with tempfile.TemporaryDirectory() as td:
            executable = os.path.join(td, 'ffmpeg.exe')
            with open(executable, 'wb') as stream:
                stream.write(b'fixed-binary')
            with patch.object(A, 'resolve_media_executable', return_value=executable):
                with patch.object(
                        A, 'sha3_512_open_file',
                        side_effect=('before', 'after')):
                    with self.assertRaises(OSError):
                        with self.real_pinner('ffmpeg') as pinned:
                            self.assertIsNotNone(pinned[0])

    def test_pinned_transcode_reuses_executable_and_passes_descriptor(self):
        @contextmanager
        def pinned_ffmpeg(name):
            self.assertEqual(name, 'ffmpeg')
            yield '/proc/self/fd/77', (77,)

        with tempfile.TemporaryFile() as generated:
            with patch.object(A, 'pinned_media_executable', side_effect=pinned_ffmpeg):
                with patch.object(
                        A, 'available_video_encoders',
                        return_value=({'libx265'}, None)) as encoders:
                    with patch.object(
                            A, 'run_transcode_command',
                            return_value=(0, '')) as run:
                        command, code, error = A.run_pinned_transcode(
                            'stage.mp4', 'out.mp4', 'h265', '.mp4',
                            generated, (55,))
        self.assertEqual(command[0], '/proc/self/fd/77')
        self.assertEqual((code, error), (0, ''))
        encoders.assert_called_once_with('/proc/self/fd/77', (77,))
        self.assertEqual(run.call_args.args[2], (55, 77))

    def test_av1_webm_command_uses_staged_file_and_open_output(self):
        command = A.transcode_command('stage.mp4', 'out.webm', 'av1', {'libsvtav1'})
        self.assertTrue(os.path.isabs(command[0]))
        self.assertEqual(command[1:3], ['-nostdin', '-y'])
        whitelists = [command[index + 1] for index, value in enumerate(command)
                      if value == '-protocol_whitelist']
        self.assertEqual(whitelists, ['file', 'pipe'])
        self.assertEqual(command[command.index('-i') + 1], 'stage.mp4')
        self.assertEqual(command[-1], 'pipe:1')
        self.assertEqual(command[command.index('-c:a') + 1], 'libopus')
        self.assertIn('-xerror', command)
        self.assertIn('-map_metadata:s', command)
        self.assertIn('-map_chapters', command)
        self.assertEqual(command[command.index('-disposition:v:0') + 1], '0')
        self.assertEqual(command[command.index('-disposition:a:0') + 1], '0')
        self.assertIn('-filter_threads', command)
        self.assertEqual(command[command.index('-fs') + 1], str(A.MAX_OUTPUT_BYTES))
        self.assertNotIn('-movflags', command)

    def test_h265_mp4_command_uses_compatibility_tag(self):
        command = A.transcode_command('stage.mov', 'out.mp4', 'h265', {'libx265'})
        self.assertEqual(command[command.index('-tag:v') + 1], 'hvc1')
        self.assertEqual(command[command.index('-movflags') + 1], '+frag_keyframe+empty_moov')
        self.assertEqual(command[command.index('-enable_drefs') + 1], '0')
        self.assertEqual(command[command.index('-use_absolute_path') + 1], '0')
        self.assertIn('pools=4:frame-threads=2', command)

    def test_h265_mkv_command_omits_mp4_tag(self):
        command = A.transcode_command('stage.mov', 'out.mkv', 'h265', {'libx265'})
        self.assertNotIn('-tag:v', command)
        self.assertNotIn('-movflags', command)

    def test_probe_output_limit_fails_closed(self):
        process = SimpleNamespace(
            stdout=io.BytesIO(b'x' * (A.MAX_PROBE_OUTPUT_BYTES + 1)),
            returncode=0,
            poll=lambda: 0,
            kill=lambda: None,
            wait=lambda: 0,
        )
        with patch.object(A.subprocess, 'Popen', return_value=process):
            self.assertEqual(
                A.run_probe_command(['ffprobe']),
                (None, 'ffprobe_output_too_large'),
            )

    def test_probe_captures_programs_side_data_disposition_and_normalizes_tags(self):
        payload = json.dumps({
            'format': {
                'duration': '60', 'format_name': 'matroska',
                'tags': {'ENCODER': 'Lavf61.1.100'},
            },
            'chapters': [],
            'programs': [{'program_id': 1}],
            'streams': [{
                'codec_type': 'video', 'codec_name': 'hevc', 'width': 1920,
                'height': 1080, 'avg_frame_rate': '30/1',
                'tags': {'ENCODER': 'Lavc61.1.100 libx265'},
                'disposition': {'default': 1},
                'side_data_list': [{'side_data_type': 'Display Matrix'}],
            }],
        })
        with tempfile.TemporaryFile() as media:
            with patch.object(A, 'run_probe_command', return_value=(payload, None)) as run:
                info = A.probe_open_file(media, 'matroska')
        command = run.call_args.args[0]
        entries = command[command.index('-show_entries') + 1]
        self.assertTrue(os.path.isabs(command[0]))
        self.assertEqual(command[command.index('-max_alloc') + 1], str(A.MAX_ALLOC_BYTES))
        self.assertEqual(command[command.index('-probesize') + 1], str(A.MAX_PROBE_INPUT_BYTES))
        self.assertEqual(
            command[command.index('-analyzeduration') + 1], str(A.MAX_ANALYZE_MICROSECONDS))
        self.assertIn('program=program_id', entries)
        self.assertIn('stream_disposition', entries)
        self.assertIn('stream_side_data=side_data_type', entries)
        self.assertEqual(info['programs'], 1)
        self.assertEqual(info['tags'], {'encoder': 'Lavf61.1.100'})
        self.assertEqual(info['streams'][0]['side_data_types'], ['Display Matrix'])

    def test_probe_preserves_malformed_disposition_for_rejection(self):
        payload = json.dumps({
            'format': {'duration': '60', 'format_name': 'mov,mp4,m4a,3gp,3g2,mj2'},
            'chapters': [],
            'programs': [],
            'streams': [{
                'codec_type': 'video', 'codec_name': 'hevc', 'width': 1920,
                'height': 1080, 'avg_frame_rate': '30/1', 'disposition': [],
            }],
        })
        info = A.parse_probe_output(payload, '<opened-file>')
        self.assertEqual(info['streams'][0]['disposition'], [])
        self.assertEqual(
            A.validate_transcoded_output(info, 'h265', '.mp4', SOURCE_INFO),
            'unexpected_output_disposition',
        )

    def test_path_probe_applies_parse_limits(self):
        @contextmanager
        def pinned_ffprobe(name):
            self.assertEqual(name, 'ffprobe')
            yield '/proc/self/fd/88', (88,)

        with patch.object(A, 'pinned_media_executable', side_effect=pinned_ffprobe):
            with patch.object(A, 'run_probe_command', return_value=(json.dumps({
                    'format': {'duration': '1', 'format_name': 'mov'},
                    'streams': [],
            }), None)) as run:
                A.probe_local_path('stage.mp4', 'mov', (55,))
        command = run.call_args.args[0]
        self.assertEqual(command[0], '/proc/self/fd/88')
        self.assertEqual(run.call_args.kwargs['pass_fds'], (55, 88))
        self.assertEqual(command[command.index('-max_alloc') + 1], str(A.MAX_ALLOC_BYTES))
        self.assertEqual(command[command.index('-probesize') + 1], str(A.MAX_PROBE_INPUT_BYTES))
        self.assertEqual(
            command[command.index('-analyzeduration') + 1], str(A.MAX_ANALYZE_MICROSECONDS))

    def test_linux_mount_allowlist_rejects_network_filesystems(self):
        mount_template = '1 0 {} / /mnt/local rw - {} {} rw\n'
        path_patches = (
            patch.object(A.os, 'name', 'posix'),
            patch.object(A.sys, 'platform', 'linux'),
            patch.object(A.os.path, 'abspath', return_value='/mnt/local/video.mp4'),
            patch.object(A.os.path, 'exists', return_value=True),
            patch.object(A.os.path, 'realpath', return_value='/mnt/local/video.mp4'),
            patch.object(A.os.path, 'commonpath', side_effect=posixpath.commonpath),
        )
        cases = (
            ('8:1', 'ext4', '/dev/sda1', True),
            ('0:42', 'nfs', 'server:/share', False),
            ('0:99', 'ext4', 'overlay', False),
        )
        for device, filesystem, source, expected in cases:
            with self.subTest(device=device, filesystem=filesystem, source=source):
                mountinfo = mount_template.format(device, filesystem, source)
                with path_patches[0], path_patches[1], path_patches[2], path_patches[3], \
                        path_patches[4], path_patches[5], \
                        patch('builtins.open', mock_open(read_data=mountinfo)):
                    self.assertIs(A.is_fixed_local_path('/mnt/local/video.mp4'), expected)

    def test_protocol_unc_and_pseudo_paths_are_rejected(self):
        self.assertEqual(A.validate_transcode_paths('https://host/video.mp4', 'out.webm', 'av1'),
                         'local_paths_only')
        self.assertEqual(A.validate_transcode_paths('pipe:0', 'out.webm', 'av1'),
                         'local_paths_only')
        self.assertEqual(A.validate_transcode_paths('in.mp4', 'rtmp://host/live', 'av1'),
                         'local_paths_only')
        self.assertEqual(A.validate_transcode_paths(r'\\server\share\in.mp4', 'out.webm', 'av1'),
                         'fixed_local_drive_required')

    def test_windows_device_names_and_ads_are_rejected(self):
        with patch.object(A.os, 'name', 'nt'):
            self.assertTrue(A.is_windows_special_path(r'C:\media\NUL.mp4'))
            self.assertTrue(A.is_windows_special_path(r'C:\media\clip.mp4:payload'))
            self.assertTrue(A.is_windows_special_path(r'C:\media\CONIN$.mp4'))
            self.assertFalse(A.is_windows_special_path(r'C:\media\clip.mp4'))

    def test_container_matrix_rejects_h265_webm(self):
        with tempfile.TemporaryDirectory() as td:
            src = make_source(td)
            self.assertEqual(A.validate_transcode_paths(src, os.path.join(td, 'out.webm'), 'h265'),
                             'unsupported_output_container')

    def test_existing_output_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            src = make_source(td)
            dst = os.path.join(td, 'out.mp4')
            with open(dst, 'wb'):
                pass
            self.assertEqual(A.validate_transcode_paths(src, dst, 'h265'), 'output_already_exists')

    def test_media_limits_fail_closed_on_unknown_values(self):
        self.assertEqual(A.validate_media_limits({'duration_s': 1, 'streams': []}),
                         'video_stream_required')
        self.assertEqual(A.validate_media_limits({'duration_s': float('nan'), 'streams': []}),
                         'media_duration_invalid')
        self.assertEqual(A.validate_media_limits({
            'duration_s': 1,
            'streams': [{'codec_type': 'video', 'width': None, 'height': 1080,
                         'avg_frame_rate': '30/1'}],
        }), 'video_dimensions_invalid')
        self.assertEqual(A.validate_media_limits({
            'duration_s': 1,
            'streams': [{'codec_type': 'video', 'width': 1920, 'height': 1080,
                         'avg_frame_rate': 'N/A'}],
        }), 'video_frame_rate_invalid')

    def test_output_validation_rejects_structural_mismatches(self):
        cases = []
        wrong_codec = dict(OUTPUT_INFO)
        wrong_codec['streams'] = [dict(OUTPUT_INFO['streams'][0], codec_name='h264')]
        cases.append((wrong_codec, 'output_codec_mismatch'))
        cases.append((dict(OUTPUT_INFO, chapters=1), 'output_chapters_present'))
        cases.append((dict(OUTPUT_INFO, duration_s=70), 'output_duration_mismatch'))
        cases.append((dict(OUTPUT_INFO, format_name='matroska'), 'output_container_mismatch'))
        extra_stream = dict(OUTPUT_INFO)
        extra_stream['streams'] = OUTPUT_INFO['streams'] + [{'codec_type': 'subtitle'}]
        cases.append((extra_stream, 'unexpected_output_stream'))
        metadata = dict(OUTPUT_INFO, tags={'comment': 'copied'})
        cases.append((metadata, 'unexpected_output_metadata'))
        metadata_value = dict(OUTPUT_INFO, tags={'encoder': 'copied source title'})
        cases.append((metadata_value, 'unexpected_output_metadata'))
        cases.append((dict(OUTPUT_INFO, programs=1), 'output_programs_present'))
        side_data = dict(OUTPUT_INFO)
        side_data['streams'] = [dict(OUTPUT_INFO['streams'][0], side_data_types=['Display Matrix'])]
        cases.append((side_data, 'unexpected_output_side_data'))
        disposition = dict(OUTPUT_INFO)
        disposition['streams'] = [dict(
            OUTPUT_INFO['streams'][0], disposition={'default': 1, 'attached_pic': 1})]
        cases.append((disposition, 'unexpected_output_disposition'))
        malformed_disposition = dict(OUTPUT_INFO)
        malformed_disposition['streams'] = [dict(
            OUTPUT_INFO['streams'][0], disposition=[])]
        cases.append((malformed_disposition, 'unexpected_output_disposition'))
        for info, expected in cases:
            with self.subTest(expected=expected):
                self.assertEqual(
                    A.validate_transcoded_output(info, 'h265', '.mp4', SOURCE_INFO),
                    expected,
                )

    def test_output_audio_presence_and_codec_match_source(self):
        source = dict(SOURCE_INFO)
        source['streams'] = SOURCE_INFO['streams'] + [{'codec_type': 'audio', 'codec_name': 'aac'}]
        missing_audio = dict(OUTPUT_INFO)
        wrong_audio = dict(OUTPUT_INFO)
        wrong_audio['streams'] = OUTPUT_INFO['streams'] + [
            {'codec_type': 'audio', 'codec_name': 'mp3', 'avg_frame_rate': '0/0'}]
        valid_audio = dict(OUTPUT_INFO)
        valid_audio['streams'] = OUTPUT_INFO['streams'] + [
            {'codec_type': 'audio', 'codec_name': 'aac', 'avg_frame_rate': '0/0'}]

        self.assertEqual(
            A.validate_transcoded_output(missing_audio, 'h265', '.mp4', source),
            'unexpected_output_stream',
        )
        self.assertEqual(
            A.validate_transcoded_output(wrong_audio, 'h265', '.mp4', source),
            'output_audio_codec_mismatch',
        )
        self.assertIsNone(A.validate_transcoded_output(valid_audio, 'h265', '.mp4', source))
        zero_disposition = dict(OUTPUT_INFO)
        zero_disposition['streams'] = [dict(
            OUTPUT_INFO['streams'][0], disposition={'default': 0, 'forced': False})]
        self.assertIsNone(
            A.validate_transcoded_output(zero_disposition, 'h265', '.mp4', SOURCE_INFO))

    def test_transcode_parser_rejects_extra_position(self):
        with redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                A.parse_transcode_args(['in.mp4', 'unexpected', '--codec', 'av1', '--out', 'out.webm'])

    def test_transcode_help_preserves_success_exit(self):
        with redirect_stdout(io.StringIO()):
            self.assertEqual(A.main(['transcode', '--help']), 0)

    def test_runner_discards_unbounded_stderr(self):
        completed = SimpleNamespace(returncode=0)
        with tempfile.TemporaryFile() as generated:
            with patch.object(A.subprocess, 'run', return_value=completed) as run:
                self.assertEqual(A.run_transcode_command(['ffmpeg'], generated), (0, ''))
        kwargs = run.call_args.kwargs
        self.assertIs(kwargs['stderr'], subprocess.DEVNULL)
        self.assertNotIn('capture_output', kwargs)
        self.assertEqual(kwargs['timeout'], 600)

    def test_missing_encoder_fails_closed_and_cleans_stage(self):
        with tempfile.TemporaryDirectory() as td:
            src = make_source(td)
            dst = os.path.join(td, 'out.webm')
            output = io.StringIO()
            with patch.object(A, 'probe_local_path', return_value=SOURCE_INFO):
                with patch.object(A, 'available_video_encoders', return_value=(set(), 'not found')):
                    with redirect_stdout(output):
                        result = A.transcode(src, dst, 'av1')
            self.assertEqual(result, 1)
            self.assertEqual(json.loads(output.getvalue())['error'], 'codec_encoder_unavailable')
            self.assertFalse(os.path.exists(dst))
            self.assertEqual(stage_names(td), [])

    def test_failed_encode_cleans_partial_and_final_path(self):
        with tempfile.TemporaryDirectory() as td:
            src = make_source(td)
            dst = os.path.join(td, 'out.mp4')
            output = io.StringIO()

            def fail_encode(command, generated, pass_fds=()):
                generated.write(b'partial')
                return 1, 'failed'

            with patch.object(A, 'probe_local_path', return_value=SOURCE_INFO):
                with patch.object(A, 'available_video_encoders', return_value=({'libx265'}, None)):
                    with patch.object(A, 'run_transcode_command', side_effect=fail_encode):
                        with redirect_stdout(output):
                            result = A.transcode(src, dst, 'h265')
            self.assertEqual(result, 1)
            self.assertEqual(json.loads(output.getvalue())['error'], 'ffmpeg_transcode_failed')
            self.assertFalse(os.path.exists(dst))
            self.assertEqual(stage_names(td), [])

    def test_opened_source_must_match_validated_path(self):
        with tempfile.TemporaryDirectory() as td:
            src = make_source(td)
            other = os.path.join(td, 'other.mp4')
            with open(other, 'wb') as stream:
                stream.write(b'other-media')
            dst = os.path.join(td, 'out.mp4')
            output = io.StringIO()
            real_open = os.open

            def replace_open(path):
                return real_open(
                    other if path == os.path.abspath(src) else path,
                    os.O_RDONLY | getattr(os, 'O_BINARY', 0))

            with patch.object(A, 'open_source_file', side_effect=replace_open):
                with redirect_stdout(output):
                    result = A.transcode(src, dst, 'h265')
            self.assertEqual(result, 1)
            self.assertEqual(json.loads(output.getvalue())['error'], 'input_changed_after_validation')
            self.assertFalse(os.path.exists(dst))

    def test_source_path_replacement_after_validation_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            src = make_source(td)
            replacement = os.path.join(td, 'replacement.mp4')
            with open(replacement, 'wb') as stream:
                stream.write(b'replacement-media')
            dst = os.path.join(td, 'out.mp4')
            output = io.StringIO()
            real_inspect = A.inspect_transcode_paths

            def inspect_then_replace(source_path, output_path, codec):
                error, source_stat = real_inspect(source_path, output_path, codec)
                os.replace(replacement, source_path)
                return error, source_stat

            with patch.object(A, 'inspect_transcode_paths', side_effect=inspect_then_replace):
                with redirect_stdout(output):
                    result = A.transcode(src, dst, 'h265')
            self.assertEqual(result, 1)
            self.assertEqual(json.loads(output.getvalue())['error'], 'input_changed_after_validation')
            self.assertFalse(os.path.exists(dst))

    def test_source_mtime_change_during_snapshot_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            src = make_source(td)
            dst = os.path.join(td, 'out.mp4')
            output = io.StringIO()
            source_inode = os.stat(src).st_ino
            source_checks = 0
            real_fstat = os.fstat

            def changed_fstat(fd):
                nonlocal source_checks
                result = real_fstat(fd)
                if result.st_ino != source_inode:
                    return result
                source_checks += 1
                if source_checks != 2:
                    return result
                return SimpleNamespace(
                    st_dev=result.st_dev, st_ino=result.st_ino,
                    st_size=result.st_size, st_mtime_ns=result.st_mtime_ns + 1,
                    st_ctime_ns=result.st_ctime_ns, st_mode=result.st_mode)

            with patch.object(A.os, 'fstat', side_effect=changed_fstat):
                with redirect_stdout(output):
                    result = A.transcode(src, dst, 'h265')
            self.assertEqual(result, 1)
            self.assertEqual(json.loads(output.getvalue())['error'], 'input_changed_after_validation')
            self.assertFalse(os.path.exists(dst))
            self.assertEqual(stage_names(td), [])

    @unittest.skipUnless(os.name == 'nt', 'Windows sharing contract')
    def test_windows_source_handle_denies_concurrent_write(self):
        with tempfile.TemporaryDirectory() as td:
            src = make_source(td)
            source_fd = A.open_source_file(src)
            try:
                with self.assertRaises(OSError):
                    os.open(src, os.O_WRONLY | getattr(os, 'O_BINARY', 0))
            finally:
                os.close(source_fd)

    def test_success_uses_private_snapshot_then_atomically_publishes(self):
        with tempfile.TemporaryDirectory() as td:
            src = make_source(td)
            dst = os.path.join(td, 'out.mp4')
            output = io.StringIO()
            encoded_commands = []
            published_open = []
            real_publish = A.publish_without_overwrite

            def encode(command, generated, pass_fds=()):
                encoded_commands.append(command)
                generated.write(b'encoded')
                return 0, ''

            def publish(
                    generated, temp_path, output_path, parent_fd=None,
                    expected_digest=None):
                published_open.append(not generated.closed)
                return real_publish(
                    generated, temp_path, output_path, parent_fd, expected_digest)

            with patch.object(A, 'probe_local_path', return_value=SOURCE_INFO) as source_probe:
                with patch.object(A, 'probe_open_file', return_value=OUTPUT_INFO) as output_probe:
                    with patch.object(A, 'available_video_encoders', return_value=({'libx265'}, None)):
                        with patch.object(A, 'run_transcode_command', side_effect=encode):
                            with patch.object(A, 'publish_without_overwrite', side_effect=publish):
                                with redirect_stdout(output):
                                    result = A.transcode(src, dst, 'h265')
            self.assertEqual(result, 0)
            self.assertTrue(os.path.isfile(dst))
            self.assertEqual(published_open, [True])
            self.assertEqual(json.loads(output.getvalue())['encoder'], 'libx265')
            self.assertEqual(source_probe.call_count, 1)
            self.assertEqual(output_probe.call_count, 1)
            snapshot_path = encoded_commands[0][encoded_commands[0].index('-i') + 1]
            self.assertNotEqual(snapshot_path, src)
            self.assertIn('._av_stage_', snapshot_path)
            self.assertEqual(encoded_commands[0][-1], 'pipe:1')
            self.assertEqual(stage_names(td), [])

    def test_published_output_survives_success_report_failure(self):
        report_errors = (
            OSError('stdout closed'),
            ValueError('invalid report value'),
            UnicodeEncodeError('utf-8', 'x', 0, 1, 'encoding failed'),
        )
        for report_error in report_errors:
            with self.subTest(error=type(report_error).__name__):
                with tempfile.TemporaryDirectory() as td:
                    src = make_source(td)
                    dst = os.path.join(td, 'out.mp4')

                    def encode(command, generated, pass_fds=()):
                        generated.write(b'encoded')
                        return 0, ''

                    with patch.object(A, 'probe_local_path', return_value=SOURCE_INFO):
                        with patch.object(A, 'probe_open_file', return_value=OUTPUT_INFO):
                            with patch.object(
                                    A, 'available_video_encoders',
                                    return_value=({'libx265'}, None)):
                                with patch.object(
                                        A, 'run_transcode_command', side_effect=encode):
                                    with patch('builtins.print', side_effect=report_error):
                                        result = A.transcode(src, dst, 'h265')
                    self.assertEqual(result, 0)
                    self.assertTrue(os.path.isfile(dst))
                    self.assertEqual(stage_names(td), [])

    def test_snapshot_cleanup_failure_prevents_publish(self):
        with tempfile.TemporaryDirectory() as td:
            src = make_source(td)
            dst = os.path.join(td, 'out.mp4')
            output = io.StringIO()
            real_remove_staged = A.remove_staged_file

            def encode(command, generated, pass_fds=()):
                generated.write(b'encoded')
                return 0, ''

            def fail_snapshot_remove(path, dir_fd=None):
                name = os.path.basename(os.fspath(path))
                if name.startswith('source') or '_source' in name:
                    raise OSError('snapshot cleanup failed')
                return real_remove_staged(path, dir_fd)

            with patch.object(A, 'probe_local_path', return_value=SOURCE_INFO):
                with patch.object(A, 'probe_open_file', return_value=OUTPUT_INFO):
                    with patch.object(A, 'available_video_encoders', return_value=({'libx265'}, None)):
                        with patch.object(A, 'run_transcode_command', side_effect=encode):
                            with patch.object(
                                    A, 'remove_staged_file',
                                    side_effect=fail_snapshot_remove):
                                with redirect_stdout(output):
                                    result = A.transcode(src, dst, 'h265')
            self.assertEqual(result, 1)
            self.assertEqual(json.loads(output.getvalue())['error'], 'snapshot_cleanup_failed')
            self.assertFalse(os.path.exists(dst))
            self.assertEqual(stage_names(td), [])

    def test_post_publish_close_failure_preserves_success(self):
        with tempfile.TemporaryDirectory() as td:
            src = make_source(td)
            dst = os.path.join(td, 'out.mp4')
            output = io.StringIO()
            real_fdopen = os.fdopen
            fdopen_count = 0

            class RaiseOnExit:
                def __init__(self, file_obj):
                    self.file_obj = file_obj

                def __enter__(self):
                    return self.file_obj

                def __exit__(self, exc_type, exc, traceback):
                    self.file_obj.close()
                    raise OSError('close failed after publish')

            def tracked_fdopen(*args, **kwargs):
                nonlocal fdopen_count
                fdopen_count += 1
                file_obj = real_fdopen(*args, **kwargs)
                return RaiseOnExit(file_obj) if fdopen_count == 3 else file_obj

            def encode(command, generated, pass_fds=()):
                generated.write(b'encoded')
                return 0, ''

            with patch.object(A, 'probe_local_path', return_value=SOURCE_INFO):
                with patch.object(A, 'probe_open_file', return_value=OUTPUT_INFO):
                    with patch.object(A, 'available_video_encoders', return_value=({'libx265'}, None)):
                        with patch.object(A, 'run_transcode_command', side_effect=encode):
                            with patch.object(A.os, 'fdopen', side_effect=tracked_fdopen):
                                with redirect_stdout(output):
                                    result = A.transcode(src, dst, 'h265')
            self.assertEqual(result, 0)
            self.assertTrue(os.path.isfile(dst))
            self.assertEqual(json.loads(output.getvalue())['encoder'], 'libx265')
            self.assertEqual(stage_names(td), [])

    def test_staged_input_mutation_during_transcode_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            src = make_source(td)
            dst = os.path.join(td, 'out.mp4')
            output = io.StringIO()
            real_hash = A.sha3_512_open_file
            snapshot_hashes = 0

            def encode(command, generated, pass_fds=()):
                generated.write(b'encoded')
                return 0, ''

            def changed_snapshot_hash(file_obj):
                nonlocal snapshot_hashes
                digest = real_hash(file_obj)
                if os.fstat(file_obj.fileno()).st_size == len(b'source-media'):
                    snapshot_hashes += 1
                    if snapshot_hashes == 3:
                        return 'changed'
                return digest

            with patch.object(A, 'probe_local_path', return_value=SOURCE_INFO):
                with patch.object(A, 'available_video_encoders', return_value=({'libx265'}, None)):
                    with patch.object(A, 'run_transcode_command', side_effect=encode):
                        with patch.object(
                                A, 'sha3_512_open_file',
                                side_effect=changed_snapshot_hash):
                            with redirect_stdout(output):
                                result = A.transcode(src, dst, 'h265')
            self.assertEqual(result, 1)
            self.assertEqual(json.loads(output.getvalue())['error'], 'staged_input_changed')
            self.assertFalse(os.path.exists(dst))
            self.assertEqual(stage_names(td), [])

    def test_same_size_output_mutation_during_probe_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            src = make_source(td)
            dst = os.path.join(td, 'out.mp4')
            output = io.StringIO()

            def encode(command, generated, pass_fds=()):
                generated.write(b'encoded')
                return 0, ''

            def mutate_after_probe(generated, format_name):
                generated.seek(0)
                generated.write(b'changed')
                generated.flush()
                return OUTPUT_INFO

            with patch.object(A, 'probe_local_path', return_value=SOURCE_INFO):
                with patch.object(A, 'probe_open_file', side_effect=mutate_after_probe):
                    with patch.object(A, 'available_video_encoders', return_value=({'libx265'}, None)):
                        with patch.object(A, 'run_transcode_command', side_effect=encode):
                            with redirect_stdout(output):
                                result = A.transcode(src, dst, 'h265')
            self.assertEqual(result, 1)
            self.assertEqual(json.loads(output.getvalue())['error'], 'staged_output_changed')
            self.assertFalse(os.path.exists(dst))
            self.assertEqual(stage_names(td), [])

    def test_changed_staged_output_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            src = make_source(td)
            dst = os.path.join(td, 'out.mp4')
            output = io.StringIO()
            real_stat = os.stat

            def encode(command, generated, pass_fds=()):
                generated.write(b'encoded')
                return 0, ''

            def changed_stat(path, *args, **kwargs):
                result = real_stat(path, *args, **kwargs)
                if (os.path.basename(os.fspath(path)).startswith('output_')
                        and kwargs.get('follow_symlinks') is False):
                    return SimpleNamespace(st_dev=result.st_dev, st_ino=result.st_ino,
                                           st_size=result.st_size + 1)
                return result

            with patch.object(A, 'probe_local_path', return_value=SOURCE_INFO):
                with patch.object(A, 'probe_open_file', return_value=OUTPUT_INFO):
                    with patch.object(A, 'available_video_encoders', return_value=({'libx265'}, None)):
                        with patch.object(A, 'run_transcode_command', side_effect=encode):
                            with patch.object(A.os, 'stat', side_effect=changed_stat):
                                with redirect_stdout(output):
                                    result = A.transcode(src, dst, 'h265')
            self.assertEqual(result, 1)
            self.assertEqual(json.loads(output.getvalue())['error'], 'staged_output_changed')
            self.assertFalse(os.path.exists(dst))
            self.assertEqual(stage_names(td), [])

    def test_changed_output_directory_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            src = make_source(td)
            dst = os.path.join(td, 'out.mp4')
            output = io.StringIO()
            real_stat = os.stat
            parent_checks = 0

            def encode(command, generated, pass_fds=()):
                generated.write(b'encoded')
                return 0, ''

            def changed_parent_stat(path, *args, **kwargs):
                nonlocal parent_checks
                result = real_stat(path, *args, **kwargs)
                if (os.path.abspath(os.fspath(path)) == os.path.abspath(td)
                        and kwargs.get('follow_symlinks') is False):
                    parent_checks += 1
                    if parent_checks == 2:
                        return SimpleNamespace(st_dev=result.st_dev, st_ino=result.st_ino + 1)
                return result

            with patch.object(A, 'probe_local_path', return_value=SOURCE_INFO):
                with patch.object(A, 'probe_open_file', return_value=OUTPUT_INFO):
                    with patch.object(A, 'available_video_encoders', return_value=({'libx265'}, None)):
                        with patch.object(A, 'run_transcode_command', side_effect=encode):
                            with patch.object(A.os, 'stat', side_effect=changed_parent_stat):
                                with redirect_stdout(output):
                                    result = A.transcode(src, dst, 'h265')
            self.assertEqual(result, 1)
            self.assertEqual(json.loads(output.getvalue())['error'], 'output_directory_changed')
            self.assertFalse(os.path.exists(dst))
            self.assertEqual(stage_names(td), [])

    def test_posix_parent_descriptor_is_closed_on_early_exit(self):
        with tempfile.TemporaryDirectory() as td:
            src = make_source(td)
            dst = os.path.join(td, 'out.mp4')
            parent = os.path.dirname(os.path.abspath(dst))
            fake_parent_fd = 987654
            parent_stat = os.stat(parent)
            real_open = os.open
            real_fstat = os.fstat
            real_close = os.close
            closed = []

            def anchored_open(path, flags, mode=0o777, **kwargs):
                if os.path.abspath(os.fspath(path)) == parent:
                    return fake_parent_fd
                return real_open(path, flags, mode, **kwargs)

            def anchored_fstat(fd):
                return parent_stat if fd == fake_parent_fd else real_fstat(fd)

            def anchored_close(fd):
                if fd == fake_parent_fd:
                    closed.append(fd)
                else:
                    real_close(fd)

            with patch.object(
                    A, 'inspect_transcode_paths', return_value=(None, os.stat(src))):
                with patch.object(A.os, 'name', 'posix'):
                    with patch.object(A, 'has_reparse_component', return_value=True):
                        with patch.object(A.os, 'open', side_effect=anchored_open):
                            with patch.object(A.os, 'fstat', side_effect=anchored_fstat):
                                with patch.object(A.os, 'close', side_effect=anchored_close):
                                    with redirect_stdout(io.StringIO()):
                                        result = A.transcode(src, dst, 'h265')
            self.assertEqual(result, 1)
            self.assertEqual(closed, [fake_parent_fd])

    def test_posix_staging_operations_are_anchored_to_parent_descriptor(self):
        parent_fd = 12345
        staged_stat = SimpleNamespace(st_dev=1, st_ino=2, st_size=3)
        with patch.object(A.os, 'name', 'posix'):
            with patch.object(A.os, 'open', return_value=54321) as opened:
                with patch.object(A.os, 'stat', return_value=staged_stat) as checked:
                    with patch.object(A.os, 'unlink') as unlinked:
                        with A.staged_paths('/ignored', parent_fd, '.mp4', '.webm') as staged:
                            snapshot_path, temp_path, staged_dir_fd = staged
                            self.assertFalse(os.path.isabs(snapshot_path))
                            self.assertFalse(os.path.isabs(temp_path))
                            self.assertEqual(staged_dir_fd, parent_fd)
                            self.assertEqual(
                                A.open_staged_file(snapshot_path, staged_dir_fd), 54321)
                            self.assertIs(
                                A.stat_staged_file(temp_path, staged_dir_fd), staged_stat)
                            A.remove_staged_file(snapshot_path, staged_dir_fd)

        flags = os.O_RDWR | os.O_CREAT | os.O_EXCL | getattr(os, 'O_NOFOLLOW', 0)
        opened.assert_called_once_with(
            snapshot_path, flags, 0o600, dir_fd=parent_fd)
        checked.assert_called_once_with(
            temp_path, dir_fd=parent_fd, follow_symlinks=False)
        self.assertEqual(unlinked.call_count, 3)
        self.assertTrue(all(
            call.kwargs.get('dir_fd') == parent_fd for call in unlinked.call_args_list))

    def test_posix_publish_rolls_back_if_visible_path_detaches(self):
        parent_fd = 12345
        with tempfile.TemporaryFile() as generated:
            generated.write(b'encoded')
            generated.flush()
            generated_stat = os.fstat(generated.fileno())
            anchored_stat = SimpleNamespace(
                st_dev=generated_stat.st_dev, st_ino=generated_stat.st_ino,
                st_size=generated_stat.st_size)
            detached_stat = SimpleNamespace(
                st_dev=generated_stat.st_dev, st_ino=generated_stat.st_ino + 1,
                st_size=generated_stat.st_size)
            with patch.object(A.os, 'name', 'posix'):
                with patch.object(A.os, 'link') as linked:
                    with patch.object(A.os, 'fstat', return_value=generated_stat):
                        with patch.object(
                                A.os, 'stat',
                                side_effect=(anchored_stat, detached_stat, anchored_stat)):
                            with patch.object(A.os, 'unlink') as unlinked:
                                with patch.object(A, 'remove_staged_file') as removed:
                                    with self.assertRaises(OSError):
                                        A.publish_without_overwrite(
                                            generated, 'stage.mp4', '/moved/out.mp4',
                                            parent_fd)
        linked.assert_called_once()
        unlinked.assert_called_once_with('out.mp4', dir_fd=parent_fd)
        removed.assert_not_called()

    def test_posix_publish_rechecks_visible_path_after_hashing(self):
        parent_fd = 12345
        with tempfile.TemporaryFile() as generated:
            generated.write(b'encoded')
            generated.flush()
            generated_stat = os.fstat(generated.fileno())
            matching_stat = SimpleNamespace(
                st_dev=generated_stat.st_dev, st_ino=generated_stat.st_ino,
                st_size=generated_stat.st_size)
            detached_stat = SimpleNamespace(
                st_dev=generated_stat.st_dev, st_ino=generated_stat.st_ino + 1,
                st_size=generated_stat.st_size)
            published_stats = (
                matching_stat, matching_stat,
                matching_stat, detached_stat,
                matching_stat,
            )
            with patch.object(A.os, 'name', 'posix'):
                with patch.object(A.os, 'link'):
                    with patch.object(A.os, 'fstat', return_value=generated_stat):
                        with patch.object(A.os, 'stat', side_effect=published_stats):
                            with patch.object(A, 'sha3_512_open_file', return_value='digest'):
                                with patch.object(A.os, 'unlink') as unlinked:
                                    with patch.object(A, 'remove_staged_file') as removed:
                                        with self.assertRaises(OSError):
                                            A.publish_without_overwrite(
                                                generated, 'stage.mp4',
                                                '/moved/out.mp4', parent_fd,
                                                'digest')
        unlinked.assert_called_once_with('out.mp4', dir_fd=parent_fd)
        removed.assert_not_called()

    def test_publish_commit_survives_temp_cleanup_failure(self):
        with tempfile.TemporaryDirectory() as td:
            temp_path = os.path.join(td, 'output.tmp')
            dst = os.path.join(td, 'out.mp4')
            with open(temp_path, 'w+b') as generated:
                generated.write(b'encoded')
                generated.flush()
                parent_fd = None
                if os.name != 'nt':
                    parent_fd = os.open(td, os.O_RDONLY | getattr(os, 'O_DIRECTORY', 0))
                try:
                    with patch.object(A, 'remove_staged_file', side_effect=OSError):
                        A.publish_without_overwrite(generated, temp_path, dst, parent_fd)
                    self.assertFalse(generated.closed)
                finally:
                    if parent_fd is not None:
                        os.close(parent_fd)
            with open(dst, 'rb') as published:
                self.assertEqual(published.read(), b'encoded')

    def test_atomic_publish_failure_cleans_stage(self):
        with tempfile.TemporaryDirectory() as td:
            src = make_source(td)
            dst = os.path.join(td, 'out.mp4')
            output = io.StringIO()

            def encode(command, generated, pass_fds=()):
                generated.write(b'encoded')
                return 0, ''

            with patch.object(A, 'probe_local_path', return_value=SOURCE_INFO):
                with patch.object(A, 'probe_open_file', return_value=OUTPUT_INFO):
                    with patch.object(A, 'available_video_encoders', return_value=({'libx265'}, None)):
                        with patch.object(A, 'run_transcode_command', side_effect=encode):
                            with patch.object(A, 'publish_without_overwrite', side_effect=OSError):
                                with redirect_stdout(output):
                                    result = A.transcode(src, dst, 'h265')
            self.assertEqual(result, 1)
            self.assertEqual(json.loads(output.getvalue())['error'], 'atomic_publish_failed')
            self.assertFalse(os.path.exists(dst))
            self.assertEqual(stage_names(td), [])


if __name__ == '__main__':
    unittest.main()

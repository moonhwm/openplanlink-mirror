#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""av_intake.py v0.2.0 — 音视频作战室管线脚本（2026-09-09 创刊）
本地化铁律：一切处理在本机，零出域。低置信段【存疑】禁猜读。
用法：
  av_intake.py probe <音视频路径>                     # ffprobe 探针（时长/流信息）
  av_intake.py transcribe <音视频路径> [--model base] [--out 目录]   # ASR 逐字稿（jsonl+md）
  av_intake.py ingest <音视频路径>... --out <摄取包目录>               # 摄取包（契约 v1.0）
  av_intake.py frames <视频路径> [--interval 60] [--out 目录]          # 抽帧（信源核查用）
  av_intake.py tts <文本路径> --out <mp3路径>          # 语音化末节（本地 espeak/ffmpeg 兜底）
  av_intake.py codecs                                 # AV1/H265 编码能力探测
  av_intake.py transcode <视频路径> --codec <av1|h265> --out <输出路径>
  av_intake.py --self-test                            # 五夹具自检
"""
import argparse, datetime, hashlib, json, math, ntpath, os, re, secrets, shutil, stat, subprocess, sys, tempfile, threading
from contextlib import contextmanager, nullcontext


def sh(cmd, pass_fds=()):
    options = {'capture_output': True, 'text': True, 'timeout': 600}
    if pass_fds:
        options['pass_fds'] = pass_fds
    try:
        r = subprocess.run(cmd, **options)
        return r.returncode, r.stdout, r.stderr
    except FileNotFoundError:
        return 127, '', 'executable_not_found: %s' % cmd[0]
    except subprocess.TimeoutExpired:
        return 124, '', 'command_timeout: %s' % cmd[0]


VIDEO_PROFILES = {
    'av1': [
        ('libsvtav1', ['-crf', '30', '-preset', '8', '-svtav1-params', 'lp=4']),
        ('libaom-av1', ['-crf', '30', '-b:v', '0', '-cpu-used', '6']),
    ],
    'h265': [
        ('libx265', ['-crf', '28', '-preset', 'medium',
                     '-x265-params', 'pools=4:frame-threads=2']),
    ],
}
VIDEO_INPUT_FORMATS = {
    '.avi': 'avi',
    '.m4v': 'mov',
    '.mkv': 'matroska',
    '.mov': 'mov',
    '.mp4': 'mov',
    '.mts': 'mpegts',
    '.ts': 'mpegts',
    '.webm': 'matroska',
}
VIDEO_OUTPUT_FORMATS = {
    '.mkv': 'matroska',
    '.mov': 'mp4',
    '.mp4': 'mp4',
    '.webm': 'webm',
}
VIDEO_OUTPUT_EXTENSIONS = {
    'av1': {'.mkv', '.mov', '.mp4', '.webm'},
    'h265': {'.mkv', '.mov', '.mp4'},
}
EXPECTED_VIDEO_CODECS = {'av1': 'av1', 'h265': 'hevc'}
MAX_INPUT_BYTES = 8 * 1024 * 1024 * 1024
MAX_OUTPUT_BYTES = 16 * 1024 * 1024 * 1024
MAX_PROBE_OUTPUT_BYTES = 1024 * 1024
MAX_PROBE_INPUT_BYTES = 64 * 1024 * 1024
MAX_ANALYZE_MICROSECONDS = 60 * 1000 * 1000
MAX_DURATION_SECONDS = 4 * 60 * 60
MAX_VIDEO_PIXELS = 7680 * 4320
MAX_STREAMS = 16
MAX_ALLOC_BYTES = 512 * 1024 * 1024
FFMPEG_THREADS = 4
PROTOCOL_PATH = re.compile(r'^[A-Za-z][A-Za-z0-9+.-]*://')
FFMPEG_PSEUDO_PATH = re.compile(r'^(?:concat|crypto|data|fd|pipe|subfile):', re.IGNORECASE)
LOCAL_LINUX_FILESYSTEMS = {
    'btrfs', 'ext2', 'ext3', 'ext4', 'f2fs', 'jfs', 'nilfs2', 'reiserfs', 'xfs',
}
ALLOWED_FORMAT_TAGS = {'compatible_brands', 'encoder', 'major_brand', 'minor_version'}
ALLOWED_STREAM_TAGS = {'duration', 'encoder', 'handler_name', 'language', 'vendor_id'}


def parse_video_encoders(output):
    encoders = set()
    for line in output.splitlines():
        fields = line.split()
        if len(fields) >= 2 and len(fields[0]) == 6 and fields[0].startswith('V'):
            encoders.add(fields[1])
    return encoders


def available_video_encoders(executable=None, pass_fds=()):
    if executable is not None:
        code, out, err = sh(
            [executable, '-hide_banner', '-encoders'], pass_fds=pass_fds)
        if code != 0:
            return set(), err
        return parse_video_encoders(out), None
    try:
        with pinned_media_executable('ffmpeg') as pinned:
            executable, executable_fds = pinned
            if executable is None:
                return set(), 'trusted_executable_not_found: ffmpeg'
            return available_video_encoders(executable, executable_fds)
    except OSError:
        return set(), 'trusted_executable_changed: ffmpeg'


def select_video_profile(codec, encoders):
    if codec not in VIDEO_PROFILES:
        raise ValueError('codec 必须是 av1 或 h265')
    for encoder, options in VIDEO_PROFILES[codec]:
        if encoder in encoders:
            return encoder, options
    return None


def codec_capabilities():
    encoders, error = available_video_encoders()
    return {
        'ffmpeg': error is None,
        'av1': [name for name, _ in VIDEO_PROFILES['av1'] if name in encoders],
        'h265': [name for name, _ in VIDEO_PROFILES['h265'] if name in encoders],
        'error': error,
    }


def is_protocol_path(path):
    return bool(PROTOCOL_PATH.match(path) or FFMPEG_PSEUDO_PATH.match(path))


def is_windows_special_path(path):
    if os.name != 'nt':
        return False
    absolute = ntpath.abspath(path).replace('/', '\\')
    tail = ntpath.splitdrive(absolute)[1]
    if ':' in tail:
        return True
    reserved = {'CON', 'PRN', 'AUX', 'NUL', 'CLOCK$', 'CONIN$', 'CONOUT$'}
    reserved.update('COM%d' % n for n in range(1, 10))
    reserved.update('LPT%d' % n for n in range(1, 10))
    for component in tail.split('\\'):
        normalized = component.rstrip(' .')
        stem = normalized.split('.', 1)[0].upper()
        if normalized != component or stem in reserved:
            return True
    return False


def is_fixed_local_path(path):
    if str(path).startswith(('\\\\', '//')):
        return False
    absolute = os.path.abspath(path)
    if os.name == 'nt':
        drive = os.path.splitdrive(absolute)[0]
        if not drive:
            return False
        try:
            import ctypes
            return ctypes.windll.kernel32.GetDriveTypeW(drive + '\\') == 3
        except (AttributeError, OSError):
            return False
    if not sys.platform.startswith('linux'):
        return False
    existing = absolute
    while not os.path.exists(existing):
        parent = os.path.dirname(existing)
        if parent == existing:
            return False
        existing = parent
    existing = os.path.realpath(existing)
    try:
        with open('/proc/self/mountinfo', encoding='utf-8') as mounts:
            candidates = []
            for line in mounts:
                fields = line.split()
                separator = fields.index('-')
                mountpoint = fields[4].replace('\\040', ' ').replace('\\134', '\\')
                mountpoint = mountpoint.replace('\\011', '\t').replace('\\012', '\n')
                if os.path.commonpath((existing, mountpoint)) == mountpoint:
                    candidates.append((
                        len(mountpoint), fields[separator + 1], fields[separator + 2], fields[2],
                    ))
    except (OSError, ValueError):
        return False
    if not candidates:
        return False
    _, filesystem, source, device = max(candidates)
    return (filesystem in LOCAL_LINUX_FILESYSTEMS
            and source.startswith('/dev/')
            and not device.startswith('0:'))


def has_reparse_component(path):
    cursor = os.path.abspath(path)
    if not os.path.lexists(cursor):
        cursor = os.path.dirname(cursor)
    while cursor:
        try:
            item = os.lstat(cursor)
        except OSError:
            return True
        attributes = getattr(item, 'st_file_attributes', 0)
        reparse_flag = getattr(stat, 'FILE_ATTRIBUTE_REPARSE_POINT', 0)
        if stat.S_ISLNK(item.st_mode) or attributes & reparse_flag:
            return True
        parent = os.path.dirname(cursor)
        if parent == cursor:
            break
        cursor = parent
    return False


def resolve_media_executable(name):
    configured = os.environ.get('AV_%s_PATH' % name.upper())
    if configured and not os.path.isabs(configured):
        return None
    search_path = os.pathsep.join(
        entry for entry in os.environ.get('PATH', os.defpath).split(os.pathsep)
        if entry and os.path.isabs(entry)
    )
    candidate = configured or shutil.which(name, path=search_path)
    if not candidate:
        return None
    absolute = os.path.abspath(candidate)
    if not configured:
        try:
            cwd = os.path.normcase(os.path.realpath(os.getcwd()))
            resolved = os.path.normcase(os.path.realpath(absolute))
            if os.path.commonpath((cwd, resolved)) == cwd:
                return None
        except ValueError:
            return None
    try:
        executable_stat = os.stat(absolute, follow_symlinks=False)
    except OSError:
        return None
    if (not stat.S_ISREG(executable_stat.st_mode) or is_windows_special_path(absolute)
            or has_reparse_component(absolute) or not is_fixed_local_path(absolute)):
        return None
    if os.name != 'nt' and not os.access(absolute, os.X_OK):
        return None
    return absolute


def open_source_file(path):
    if os.name != 'nt':
        flags = os.O_RDONLY | getattr(os, 'O_BINARY', 0) | getattr(os, 'O_NOFOLLOW', 0)
        return os.open(path, flags)
    import ctypes
    import msvcrt
    kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
    create_file = kernel32.CreateFileW
    create_file.argtypes = [
        ctypes.c_wchar_p, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_void_p,
        ctypes.c_uint32, ctypes.c_uint32, ctypes.c_void_p,
    ]
    create_file.restype = ctypes.c_void_p
    handle = create_file(
        path, 0x80000000, 0x00000001, None, 3, 0x00200080, None)
    if handle == ctypes.c_void_p(-1).value:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        return msvcrt.open_osfhandle(
            handle, os.O_RDONLY | getattr(os, 'O_BINARY', 0))
    except Exception:
        kernel32.CloseHandle(ctypes.c_void_p(handle))
        raise


def open_staged_file(path, dir_fd=None):
    if os.name != 'nt':
        flags = os.O_RDWR | os.O_CREAT | os.O_EXCL | getattr(os, 'O_NOFOLLOW', 0)
        return os.open(path, flags, 0o600, dir_fd=dir_fd)
    import ctypes
    import msvcrt
    kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
    create_file = kernel32.CreateFileW
    create_file.argtypes = [
        ctypes.c_wchar_p, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_void_p,
        ctypes.c_uint32, ctypes.c_uint32, ctypes.c_void_p,
    ]
    create_file.restype = ctypes.c_void_p
    handle = create_file(
        path, 0x80000000 | 0x40000000, 0x00000001, None, 1, 0x00000080, None)
    if handle == ctypes.c_void_p(-1).value:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        return msvcrt.open_osfhandle(handle, os.O_RDWR | getattr(os, 'O_BINARY', 0))
    except Exception:
        kernel32.CloseHandle(ctypes.c_void_p(handle))
        raise


@contextmanager
def staged_paths(parent, parent_fd, input_extension, output_extension):
    if os.name == 'nt':
        with tempfile.TemporaryDirectory(
                prefix='._av_stage_', dir=parent, ignore_cleanup_errors=True) as staging:
            yield (
                os.path.join(staging, 'source' + input_extension),
                os.path.join(staging, 'output_' + secrets.token_hex(16) + output_extension),
                None,
            )
        return
    token = secrets.token_hex(16)
    snapshot_path = '._av_stage_' + token + '_source' + input_extension
    temp_path = '._av_stage_' + token + '_output' + output_extension
    try:
        yield snapshot_path, temp_path, parent_fd
    finally:
        for path in (snapshot_path, temp_path):
            try:
                os.unlink(path, dir_fd=parent_fd)
            except OSError:
                pass


def remove_staged_file(path, dir_fd=None):
    if os.name == 'nt':
        os.remove(path)
    else:
        os.unlink(path, dir_fd=dir_fd)


def stat_staged_file(path, dir_fd=None):
    if os.name == 'nt':
        return os.stat(path, follow_symlinks=False)
    return os.stat(path, dir_fd=dir_fd, follow_symlinks=False)


def inherited_fds(file_obj):
    return () if os.name == 'nt' else (file_obj.fileno(),)


def opened_file_path(file_obj, path):
    return path if os.name == 'nt' else '/proc/self/fd/%d' % file_obj.fileno()


def sha3_512_open_file(file_obj):
    position = file_obj.tell()
    digest = hashlib.sha3_512()
    try:
        file_obj.seek(0)
        for chunk in iter(lambda: file_obj.read(1 << 20), b''):
            digest.update(chunk)
    finally:
        file_obj.seek(position)
    return digest.hexdigest()


def source_file_identity(file_stat):
    identity = (
        file_stat.st_dev, file_stat.st_ino, file_stat.st_size,
        file_stat.st_mtime_ns)
    return identity if os.name == 'nt' else identity + (file_stat.st_ctime_ns,)


@contextmanager
def sealed_linux_executable(executable_file, name, expected_digest):
    if not sys.platform.startswith('linux') or not hasattr(os, 'memfd_create'):
        raise OSError('trusted_executable_platform_unsupported: %s' % name)
    import fcntl
    required = ('F_ADD_SEALS', 'F_GET_SEALS', 'F_SEAL_WRITE', 'F_SEAL_GROW',
                'F_SEAL_SHRINK', 'F_SEAL_SEAL')
    if any(not hasattr(fcntl, item) for item in required):
        raise OSError('trusted_executable_sealing_unavailable: %s' % name)
    flags = getattr(os, 'MFD_CLOEXEC', 0) | getattr(os, 'MFD_ALLOW_SEALING', 0)
    if not getattr(os, 'MFD_ALLOW_SEALING', 0):
        raise OSError('trusted_executable_sealing_unavailable: %s' % name)
    sealed_fd = os.memfd_create('av-' + name, flags)
    with os.fdopen(sealed_fd, 'w+b') as sealed_file:
        executable_file.seek(0)
        for chunk in iter(lambda: executable_file.read(1 << 20), b''):
            sealed_file.write(chunk)
        sealed_file.flush()
        os.fchmod(sealed_file.fileno(), 0o500)
        if (sha3_512_open_file(executable_file) != expected_digest
                or sha3_512_open_file(sealed_file) != expected_digest):
            raise OSError('trusted_executable_changed: %s' % name)
        seals = (fcntl.F_SEAL_WRITE | fcntl.F_SEAL_GROW
                 | fcntl.F_SEAL_SHRINK | fcntl.F_SEAL_SEAL)
        try:
            fcntl.fcntl(sealed_file.fileno(), fcntl.F_ADD_SEALS, seals)
            applied = fcntl.fcntl(sealed_file.fileno(), fcntl.F_GET_SEALS)
        except OSError as exc:
            raise OSError('trusted_executable_sealing_failed: %s' % name) from exc
        if applied & seals != seals:
            raise OSError('trusted_executable_sealing_failed: %s' % name)
        yield opened_file_path(sealed_file, ''), inherited_fds(sealed_file)


@contextmanager
def pinned_media_executable(name):
    path = resolve_media_executable(name)
    if path is None:
        yield None, ()
        return
    try:
        expected = os.stat(path, follow_symlinks=False)
        executable_fd = open_source_file(path)
    except OSError:
        yield None, ()
        return
    with os.fdopen(executable_fd, 'rb') as executable_file:
        try:
            opened = os.fstat(executable_file.fileno())
            current = os.stat(path, follow_symlinks=False)
        except OSError:
            yield None, ()
            return
        identity = source_file_identity(opened)
        if (not stat.S_ISREG(opened.st_mode)
                or source_file_identity(expected) != identity
                or source_file_identity(current) != identity
                or has_reparse_component(path) or not is_fixed_local_path(path)):
            yield None, ()
            return
        digest = sha3_512_open_file(executable_file)
        execution = (
            nullcontext((path, ())) if os.name == 'nt'
            else sealed_linux_executable(executable_file, name, digest))
        with execution as pinned:
            yield pinned
        try:
            final_opened = os.fstat(executable_file.fileno())
            final_path = os.stat(path, follow_symlinks=False)
        except OSError as exc:
            raise OSError('trusted_executable_changed: %s' % name) from exc
        if (source_file_identity(final_opened) != identity
                or source_file_identity(final_path) != identity
                or sha3_512_open_file(executable_file) != digest):
            raise OSError('trusted_executable_changed: %s' % name)


def run_pinned_media_command(name, arguments, pass_fds=()):
    try:
        with pinned_media_executable(name) as (executable, executable_fds):
            if executable is None:
                return 127, '', 'trusted_executable_not_found: %s' % name
            inherited = tuple(dict.fromkeys((*pass_fds, *executable_fds)))
            return sh([executable, *arguments], pass_fds=inherited)
    except OSError:
        return 126, '', 'trusted_executable_changed: %s' % name


def inspect_transcode_paths(src, dst, codec):
    if is_protocol_path(src) or is_protocol_path(dst):
        return 'local_paths_only', None
    if is_windows_special_path(src) or is_windows_special_path(dst):
        return 'windows_device_or_ads_rejected', None
    if not is_fixed_local_path(src) or not is_fixed_local_path(dst):
        return 'fixed_local_drive_required', None
    src_abs = os.path.abspath(src)
    dst_abs = os.path.abspath(dst)
    if has_reparse_component(src_abs) or has_reparse_component(os.path.dirname(dst_abs)):
        return 'symlink_or_reparse_path_rejected', None
    if os.path.realpath(src_abs) == os.path.realpath(dst_abs):
        return 'input_output_must_differ', None
    try:
        src_stat = os.stat(src_abs, follow_symlinks=False)
    except OSError:
        return 'input_must_be_regular_file', None
    if not stat.S_ISREG(src_stat.st_mode):
        return 'input_must_be_regular_file', None
    if os.path.splitext(src_abs)[1].lower() not in VIDEO_INPUT_FORMATS:
        return 'unsupported_input_container', None
    if src_stat.st_size > MAX_INPUT_BYTES:
        return 'input_too_large', None
    if os.path.splitext(dst_abs)[1].lower() not in VIDEO_OUTPUT_EXTENSIONS[codec]:
        return 'unsupported_output_container', None
    if os.path.lexists(dst_abs):
        return 'output_already_exists', None
    parent = os.path.dirname(dst_abs) or os.curdir
    if not os.path.isdir(parent):
        return 'output_directory_missing', None
    return None, src_stat


def validate_transcode_paths(src, dst, codec):
    error, _ = inspect_transcode_paths(src, dst, codec)
    return error


def parse_frame_rate(value):
    try:
        numerator, denominator = str(value).split('/', 1)
        rate = float(numerator) / float(denominator)
    except (TypeError, ValueError, ZeroDivisionError):
        return None
    return rate if math.isfinite(rate) and rate > 0 else None


def validate_media_limits(info):
    if 'error' in info:
        return 'media_probe_failed'
    try:
        duration = float(info['duration_s'])
    except (KeyError, TypeError, ValueError):
        return 'media_duration_invalid'
    if not math.isfinite(duration) or duration <= 0:
        return 'media_duration_invalid'
    if duration > MAX_DURATION_SECONDS:
        return 'media_duration_exceeded'
    streams = info.get('streams', [])
    if not isinstance(streams, list) or len(streams) > MAX_STREAMS:
        return 'media_stream_count_exceeded'
    videos = [stream for stream in streams if stream.get('codec_type') == 'video']
    if not videos:
        return 'video_stream_required'
    for stream in videos:
        try:
            width = int(stream['width'])
            height = int(stream['height'])
        except (KeyError, TypeError, ValueError):
            return 'video_dimensions_invalid'
        if width <= 0 or height <= 0:
            return 'video_dimensions_invalid'
        if width * height > MAX_VIDEO_PIXELS:
            return 'video_resolution_exceeded'
        frame_rate = parse_frame_rate(stream.get('avg_frame_rate'))
        if frame_rate is None or frame_rate > 120:
            return 'video_frame_rate_invalid'
    return None


def parse_probe_output(out, path):
    try:
        data = json.loads(out)
        fmt = data.get('format', {})
        return {'path': path,
                'duration_s': float(fmt.get('duration')),
                'format_name': fmt.get('format_name'),
                'tags': {str(key).lower(): value
                         for key, value in (fmt.get('tags') or {}).items()},
                'chapters': len(data.get('chapters', [])),
                'programs': len(data.get('programs', [])),
                'streams': [{'codec_type': stream.get('codec_type'),
                             'codec_name': stream.get('codec_name'),
                             'width': stream.get('width'),
                             'height': stream.get('height'),
                             'avg_frame_rate': stream.get('avg_frame_rate'),
                             'tags': {str(key).lower(): value for key, value
                                      in (stream.get('tags') or {}).items()},
                             'disposition': stream.get('disposition', {}),
                             'side_data_types': [
                                 item.get('side_data_type')
                                 for item in stream.get('side_data_list', [])]}
                            for stream in data.get('streams', [])]}
    except (AttributeError, TypeError, ValueError):
        return {'error': 'ffprobe_invalid_output'}


def demuxer_safety_options(format_name):
    if format_name == 'mov':
        return ['-enable_drefs', '0', '-use_absolute_path', '0']
    return []


def run_probe_command(command, stdin=None, pass_fds=()):
    options = {
        'stdin': stdin,
        'stdout': subprocess.PIPE,
        'stderr': subprocess.DEVNULL,
        'close_fds': True,
    }
    if pass_fds:
        options['pass_fds'] = pass_fds
    try:
        process = subprocess.Popen(command, **options)
    except FileNotFoundError:
        return None, 'executable_not_found: ffprobe'
    timed_out = threading.Event()

    def kill_after_timeout():
        if process.poll() is None:
            timed_out.set()
            process.kill()

    timer = threading.Timer(60, kill_after_timeout)
    timer.start()
    try:
        output = process.stdout.read(MAX_PROBE_OUTPUT_BYTES + 1)
        if len(output) > MAX_PROBE_OUTPUT_BYTES:
            process.kill()
        process.wait()
    finally:
        timer.cancel()
        process.stdout.close()
    if timed_out.is_set():
        return None, 'ffprobe_timeout'
    if len(output) > MAX_PROBE_OUTPUT_BYTES:
        return None, 'ffprobe_output_too_large'
    if process.returncode != 0:
        return None, 'ffprobe_failed'
    try:
        return output.decode('utf-8'), None
    except UnicodeDecodeError:
        return None, 'ffprobe_invalid_output'


def probe_open_file(file_obj, format_name, executable=None, executable_fds=()):
    if executable is None:
        try:
            with pinned_media_executable('ffprobe') as pinned:
                pinned_executable, pinned_fds = pinned
                if pinned_executable is None:
                    return {'error': 'trusted_executable_not_found: ffprobe'}
                return probe_open_file(
                    file_obj, format_name, pinned_executable, pinned_fds)
        except OSError:
            return {'error': 'trusted_executable_changed: ffprobe'}
    file_obj.seek(0)
    command = [
        executable, '-v', 'quiet', '-max_alloc', str(MAX_ALLOC_BYTES),
        '-probesize', str(MAX_PROBE_INPUT_BYTES),
        '-analyzeduration', str(MAX_ANALYZE_MICROSECONDS),
        '-protocol_whitelist', 'pipe', '-f', format_name,
        '-print_format', 'json', '-show_entries',
        'format=duration,format_name:format_tags:'
        'stream=codec_type,codec_name,width,height,avg_frame_rate:stream_tags:'
        'stream_disposition:stream_side_data=side_data_type:program=program_id:chapter=id',
        '-i', 'pipe:0',
    ]
    out, error = run_probe_command(
        command, stdin=file_obj, pass_fds=executable_fds)
    return {'error': error} if error else parse_probe_output(out, '<opened-file>')


def probe_local_path(
        path, format_name, pass_fds=(), executable=None, executable_fds=()):
    if executable is None:
        try:
            with pinned_media_executable('ffprobe') as pinned:
                pinned_executable, pinned_fds = pinned
                if pinned_executable is None:
                    return {'error': 'trusted_executable_not_found: ffprobe'}
                return probe_local_path(
                    path, format_name, pass_fds, pinned_executable, pinned_fds)
        except OSError:
            return {'error': 'trusted_executable_changed: ffprobe'}
    command = [
        executable, '-v', 'quiet', '-max_alloc', str(MAX_ALLOC_BYTES),
        '-probesize', str(MAX_PROBE_INPUT_BYTES),
        '-analyzeduration', str(MAX_ANALYZE_MICROSECONDS),
        '-protocol_whitelist', 'file',
        '-f', format_name, *demuxer_safety_options(format_name),
        '-print_format', 'json', '-show_entries',
        'format=duration,format_name:format_tags:'
        'stream=codec_type,codec_name,width,height,avg_frame_rate:stream_tags:'
        'stream_disposition:stream_side_data=side_data_type:program=program_id:chapter=id',
        '-i', path,
    ]
    inherited = tuple(dict.fromkeys((*pass_fds, *executable_fds)))
    out, error = run_probe_command(command, pass_fds=inherited)
    return {'error': error} if error else parse_probe_output(out, '<staged-file>')


def transcode_command(
        src, dst, codec, encoders, input_extension=None, executable=None):
    profile = select_video_profile(codec, encoders)
    executable = executable or resolve_media_executable('ffmpeg')
    if profile is None or executable is None:
        return None
    encoder, options = profile
    input_extension = input_extension or os.path.splitext(src)[1].lower()
    output_extension = os.path.splitext(dst)[1].lower()
    audio_encoder = 'libopus' if codec == 'av1' and output_extension == '.webm' else 'aac'
    input_format = VIDEO_INPUT_FORMATS[input_extension]
    command = [
        executable, '-nostdin', '-y', '-xerror', '-max_alloc', str(MAX_ALLOC_BYTES),
        '-filter_threads', '1', '-filter_complex_threads', '1', '-threads', '1',
        '-protocol_whitelist', 'file', '-f', input_format,
        *demuxer_safety_options(input_format), '-max_pixels', str(MAX_VIDEO_PIXELS),
        '-i', src,
        '-map', '0:v:0', '-map', '0:a:0?',
        '-map_metadata', '-1', '-map_metadata:s', '-1', '-map_chapters', '-1',
        '-disposition:v:0', '0', '-disposition:a:0', '0',
        '-c:v', encoder, *options, '-pix_fmt', 'yuv420p', '-fpsmax', '120',
        '-threads', str(FFMPEG_THREADS), '-c:a', audio_encoder, '-b:a', '128k',
        '-t', str(MAX_DURATION_SECONDS), '-fs', str(MAX_OUTPUT_BYTES),
        '-protocol_whitelist', 'pipe', '-f', VIDEO_OUTPUT_FORMATS[output_extension],
    ]
    if codec == 'h265' and output_extension in ('.mp4', '.mov'):
        command.extend(['-tag:v', 'hvc1'])
    if output_extension in ('.mp4', '.mov'):
        command.extend(['-movflags', '+frag_keyframe+empty_moov'])
    command.append('pipe:1')
    return command


def run_transcode_command(command, output, pass_fds=()):
    options = {
        'stdin': subprocess.DEVNULL,
        'stdout': output,
        'stderr': subprocess.DEVNULL,
        'timeout': 600,
        'close_fds': True,
    }
    if pass_fds:
        options['pass_fds'] = pass_fds
    try:
        result = subprocess.run(command, **options)
        return result.returncode, ''
    except FileNotFoundError:
        return 127, 'executable_not_found: ffmpeg'
    except subprocess.TimeoutExpired:
        return 124, 'ffmpeg_timeout'


def run_pinned_transcode(
        src, dst, codec, input_extension, output, input_fds=()):
    try:
        with pinned_media_executable('ffmpeg') as pinned:
            executable, executable_fds = pinned
            if executable is None:
                return None, None, 'trusted_executable_not_found: ffmpeg'
            encoders, discovery_error = available_video_encoders(
                executable, executable_fds)
            command = transcode_command(
                src, dst, codec, encoders, input_extension, executable)
            if command is None:
                return None, None, discovery_error
            inherited = tuple(dict.fromkeys((*input_fds, *executable_fds)))
            code, error = run_transcode_command(command, output, inherited)
            return command, code, error
    except OSError:
        return None, None, 'trusted_executable_changed: ffmpeg'


def valid_output_metadata(tags, allowed_keys):
    if not isinstance(tags, dict) or set(tags) - allowed_keys:
        return False
    patterns = {
        'compatible_brands': r'[A-Za-z0-9]{1,64}',
        'duration': r'\d{2,6}:\d{2}:\d{2}\.\d{1,9}',
        'encoder': r'Lav[cf]\d+(?:\.\d+){2}(?: [A-Za-z0-9._+-]+)?',
        'handler_name': r'(?:VideoHandler|SoundHandler)',
        'language': r'[A-Za-z]{3}',
        'major_brand': r'[A-Za-z0-9 ]{4}',
        'minor_version': r'\d{1,10}',
        'vendor_id': r'(?:[A-Za-z0-9]{4}|\[0\]\[0\]\[0\]\[0\])',
    }
    return all(
        isinstance(value, str) and re.fullmatch(patterns[key], value) is not None
        for key, value in tags.items()
    )


def validate_transcoded_output(info, codec, output_extension, source_info):
    limit_error = validate_media_limits(info)
    if limit_error:
        return limit_error
    videos = [stream for stream in info['streams'] if stream.get('codec_type') == 'video']
    if len(videos) != 1 or videos[0].get('codec_name') != EXPECTED_VIDEO_CODECS[codec]:
        return 'output_codec_mismatch'
    if any(stream.get('codec_type') not in ('audio', 'video') for stream in info['streams']):
        return 'unexpected_output_stream'
    source_has_audio = any(
        stream.get('codec_type') == 'audio' for stream in source_info.get('streams', []))
    audios = [stream for stream in info['streams'] if stream.get('codec_type') == 'audio']
    if len(audios) != int(source_has_audio):
        return 'unexpected_output_stream'
    expected_audio = 'opus' if codec == 'av1' and output_extension == '.webm' else 'aac'
    if audios and audios[0].get('codec_name') != expected_audio:
        return 'output_audio_codec_mismatch'
    format_tokens = set((info.get('format_name') or '').split(','))
    if VIDEO_OUTPUT_FORMATS[output_extension] not in format_tokens:
        return 'output_container_mismatch'
    source_duration = float(source_info['duration_s'])
    tolerance = max(2.0, source_duration * 0.02)
    if abs(float(info['duration_s']) - source_duration) > tolerance:
        return 'output_duration_mismatch'
    if info.get('chapters'):
        return 'output_chapters_present'
    if info.get('programs'):
        return 'output_programs_present'
    if not valid_output_metadata(info.get('tags') or {}, ALLOWED_FORMAT_TAGS):
        return 'unexpected_output_metadata'
    for stream in info['streams']:
        if stream.get('side_data_types'):
            return 'unexpected_output_side_data'
        disposition = stream.get('disposition', {})
        if (not isinstance(disposition, dict)
                or any(value not in (0, False) for value in disposition.values())):
            return 'unexpected_output_disposition'
        if not valid_output_metadata(stream.get('tags') or {}, ALLOWED_STREAM_TAGS):
            return 'unexpected_output_metadata'
    return None


def publish_without_overwrite(
        file_obj, temp_path, dst, parent_fd=None, expected_digest=None):
    published_name = dst if os.name == 'nt' else os.path.basename(dst)
    if os.name == 'nt':
        os.link(temp_path, dst)
    else:
        os.link(
            '/proc/self/fd/%d' % file_obj.fileno(),
            published_name,
            dst_dir_fd=parent_fd,
            follow_symlinks=True,
        )
    generated_stat = os.fstat(file_obj.fileno())
    generated_identity = (
        generated_stat.st_dev, generated_stat.st_ino, generated_stat.st_size)

    def publication_matches():
        if os.name == 'nt':
            published_stats = [os.stat(dst, follow_symlinks=False)]
        else:
            published_stats = [
                os.stat(published_name, dir_fd=parent_fd, follow_symlinks=False),
                os.stat(dst, follow_symlinks=False),
            ]
        return all(
            (item.st_dev, item.st_ino, item.st_size) == generated_identity
            for item in published_stats
        )

    try:
        if not publication_matches():
            raise OSError('published_path_mismatch')
        if (expected_digest is not None
                and sha3_512_open_file(file_obj) != expected_digest):
            raise OSError('published_content_changed')
        if not publication_matches():
            raise OSError('published_path_mismatch')
    except OSError:
        try:
            if os.name == 'nt':
                current = os.stat(dst, follow_symlinks=False)
            else:
                current = os.stat(
                    published_name, dir_fd=parent_fd, follow_symlinks=False)
            if (current.st_dev, current.st_ino, current.st_size) == generated_identity:
                if os.name == 'nt':
                    os.unlink(dst)
                else:
                    os.unlink(published_name, dir_fd=parent_fd)
        except OSError:
            pass
        raise
    try:
        remove_staged_file(temp_path, parent_fd)
    except OSError:
        pass


def transcode(src, dst, codec):
    if codec not in VIDEO_PROFILES:
        print(json.dumps({'error': 'codec_must_be_av1_or_h265'}, ensure_ascii=False))
        return 1
    path_error, validated_source_stat = inspect_transcode_paths(src, dst, codec)
    if path_error:
        print(json.dumps({'error': path_error}, ensure_ascii=False))
        return 1
    src_abs = os.path.abspath(src)
    dst_abs = os.path.abspath(dst)
    validated_source_identity = source_file_identity(validated_source_stat)
    input_extension = os.path.splitext(src_abs)[1].lower()
    output_extension = os.path.splitext(dst_abs)[1].lower()
    parent = os.path.dirname(dst_abs)
    parent_fd = None
    published = False
    try:
        if os.name == 'nt':
            parent_identity = os.stat(parent, follow_symlinks=False)
        else:
            parent_flags = os.O_RDONLY | getattr(os, 'O_DIRECTORY', 0) | getattr(os, 'O_NOFOLLOW', 0)
            parent_fd = os.open(parent, parent_flags)
            parent_identity = os.fstat(parent_fd)
        source_fd = open_source_file(src_abs)
    except OSError:
        if parent_fd is not None:
            os.close(parent_fd)
        print(json.dumps({'error': 'input_or_output_open_failed'}, ensure_ascii=False))
        return 1
    try:
        with os.fdopen(source_fd, 'rb') as source:
            source_stat = os.fstat(source.fileno())
            path_stat = os.stat(src_abs, follow_symlinks=False)
            source_identity = source_file_identity(source_stat)
            path_identity = source_file_identity(path_stat)
            if (not stat.S_ISREG(source_stat.st_mode) or source_stat.st_size > MAX_INPUT_BYTES
                    or source_identity != validated_source_identity
                    or source_identity != path_identity or has_reparse_component(src_abs)
                    or not is_fixed_local_path(src_abs)):
                print(json.dumps({'error': 'input_changed_after_validation'}, ensure_ascii=False))
                return 1
            with staged_paths(
                    parent, parent_fd, input_extension, output_extension) as staged:
                snapshot_path, temp_path, staged_dir_fd = staged
                snapshot_fd = open_staged_file(snapshot_path, staged_dir_fd)
                snapshot_path_present = True
                with os.fdopen(snapshot_fd, 'w+b') as snapshot:
                    if os.name != 'nt':
                        remove_staged_file(snapshot_path, staged_dir_fd)
                        snapshot_path_present = False
                    remaining = source_stat.st_size
                    while remaining:
                        chunk = source.read(min(1 << 20, remaining))
                        if not chunk:
                            break
                        snapshot.write(chunk)
                        remaining -= len(chunk)
                    source_grew = bool(source.read(1))
                    current_source = os.fstat(source.fileno())
                    current_identity = source_file_identity(current_source)
                    snapshot.flush()
                    os.fsync(snapshot.fileno())
                    if (remaining or source_grew or current_identity != source_identity
                            or os.fstat(snapshot.fileno()).st_size != source_stat.st_size):
                        print(json.dumps({'error': 'input_changed_after_validation'}, ensure_ascii=False))
                        return 1
                    snapshot_digest = sha3_512_open_file(snapshot)
                    input_path = opened_file_path(snapshot, snapshot_path)
                    input_fds = inherited_fds(snapshot)
                    generated_fd = open_staged_file(temp_path, staged_dir_fd)
                    with os.fdopen(generated_fd, 'w+b') as generated:
                        try:
                            with pinned_media_executable('ffprobe') as pinned_probe:
                                probe_executable, probe_fds = pinned_probe
                                if probe_executable is None:
                                    print(json.dumps({
                                        'error': 'trusted_executable_not_found: ffprobe',
                                    }, ensure_ascii=False))
                                    return 1
                                info = probe_local_path(
                                    input_path, VIDEO_INPUT_FORMATS[input_extension], input_fds,
                                    probe_executable, probe_fds)
                                limit_error = validate_media_limits(info)
                                if limit_error:
                                    print(json.dumps({'error': limit_error}, ensure_ascii=False))
                                    return 1
                                if sha3_512_open_file(snapshot) != snapshot_digest:
                                    print(json.dumps({
                                        'error': 'staged_input_changed',
                                    }, ensure_ascii=False))
                                    return 1
                                command, code, err = run_pinned_transcode(
                                    input_path, dst_abs, codec, input_extension,
                                    generated, input_fds)
                                if command is None:
                                    print(json.dumps({
                                        'error': 'codec_encoder_unavailable',
                                        'codec': codec,
                                        'detail': err,
                                    }, ensure_ascii=False))
                                    return 1
                                generated.flush()
                                os.fsync(generated.fileno())
                                if sha3_512_open_file(snapshot) != snapshot_digest:
                                    print(json.dumps({
                                        'error': 'staged_input_changed',
                                    }, ensure_ascii=False))
                                    return 1
                                generated_stat = os.fstat(generated.fileno())
                                generated_size = generated_stat.st_size
                                if code != 0:
                                    print(json.dumps({
                                        'error': 'ffmpeg_transcode_failed', 'stderr': err,
                                    }, ensure_ascii=False))
                                    return 1
                                if generated_size == 0:
                                    print(json.dumps({
                                        'error': 'ffmpeg_output_missing',
                                    }, ensure_ascii=False))
                                    return 1
                                if generated_size > MAX_OUTPUT_BYTES:
                                    print(json.dumps({
                                        'error': 'output_too_large',
                                    }, ensure_ascii=False))
                                    return 1
                                output_digest = sha3_512_open_file(generated)
                                output_info = probe_open_file(
                                    generated, VIDEO_OUTPUT_FORMATS[output_extension],
                                    probe_executable, probe_fds)
                                output_error = validate_transcoded_output(
                                    output_info, codec, output_extension, info)
                                if output_error:
                                    print(json.dumps({
                                        'error': output_error,
                                    }, ensure_ascii=False))
                                    return 1
                                if sha3_512_open_file(generated) != output_digest:
                                    print(json.dumps({
                                        'error': 'staged_output_changed',
                                    }, ensure_ascii=False))
                                    return 1
                        except OSError:
                            print(json.dumps({
                                'error': 'trusted_executable_changed: ffprobe',
                            }, ensure_ascii=False))
                            return 1
                        snapshot.close()
                        if snapshot_path_present:
                            try:
                                remove_staged_file(snapshot_path, staged_dir_fd)
                            except OSError:
                                print(json.dumps({
                                    'error': 'snapshot_cleanup_failed',
                                }, ensure_ascii=False))
                                return 1
                        current_temp = stat_staged_file(temp_path, staged_dir_fd)
                        current_parent = os.stat(parent, follow_symlinks=False)
                        anchored_parent = (
                            os.fstat(parent_fd) if parent_fd is not None else current_parent)
                        temp_identity = (
                            generated_stat.st_dev, generated_stat.st_ino, generated_stat.st_size)
                        if ((current_temp.st_dev, current_temp.st_ino, current_temp.st_size)
                                != temp_identity):
                            print(json.dumps({'error': 'staged_output_changed'}, ensure_ascii=False))
                            return 1
                        expected_parent = (parent_identity.st_dev, parent_identity.st_ino)
                        if ((current_parent.st_dev, current_parent.st_ino) != expected_parent
                                or (anchored_parent.st_dev, anchored_parent.st_ino)
                                != expected_parent):
                            print(json.dumps({'error': 'output_directory_changed'}, ensure_ascii=False))
                            return 1
                        if has_reparse_component(parent) or not is_fixed_local_path(parent):
                            print(json.dumps({'error': 'output_directory_changed'}, ensure_ascii=False))
                            return 1
                        try:
                            publish_without_overwrite(
                                generated, temp_path, dst_abs, parent_fd, output_digest)
                            published = True
                        except FileExistsError:
                            print(json.dumps({'error': 'output_already_exists'}, ensure_ascii=False))
                            return 1
                        except OSError:
                            print(json.dumps({'error': 'atomic_publish_failed'}, ensure_ascii=False))
                            return 1
    except OSError:
        if not published:
            print(json.dumps({'error': 'local_io_failed'}, ensure_ascii=False))
            return 1
    finally:
        if parent_fd is not None:
            try:
                os.close(parent_fd)
            except OSError:
                pass
    try:
        print(json.dumps({
            'output': dst_abs,
            'codec': codec,
            'encoder': command[command.index('-c:v') + 1],
        }, ensure_ascii=False))
    except (OSError, ValueError, UnicodeError):
        pass
    return 0

def md5file(p):
    h = hashlib.md5()
    with open(p, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()

def probe(path, local_only=False):
    arguments = ['-v', 'quiet']
    if local_only:
        arguments.extend(['-protocol_whitelist', 'file'])
    arguments.extend(['-print_format', 'json', '-show_format', '-show_streams', path])
    code, out, err = run_pinned_media_command('ffprobe', arguments)
    if code != 0:
        return {'error': 'ffprobe_failed', 'stderr': err[:300]}
    d = json.loads(out)
    fmt = d.get('format', {})
    return {'path': path,
            'duration_s': float(fmt.get('duration', 0) or 0),
            'size': int(fmt.get('size', 0) or 0),
            'streams': [{'codec_type': s.get('codec_type'), 'codec_name': s.get('codec_name'),
                         'width': s.get('width'), 'height': s.get('height')}
                        for s in d.get('streams', [])]}

def extract_wav(src, dst):
    code, _, err = run_pinned_media_command(
        'ffmpeg', ['-y', '-i', src, '-ac', '1', '-ar', '16000',
                   '-vn', '-f', 'wav', dst])
    if code != 0:
        raise RuntimeError('ffmpeg_extract_failed: ' + err[:300])
    return dst

LOW_LOGPROB = -1.0  # 低于此 avg_logprob 的段标【存疑】

def transcribe(path, model_size='base', out_dir=None):
    out_dir = out_dir or os.path.dirname(os.path.abspath(path)) or '.'
    os.makedirs(out_dir, exist_ok=True)
    info = probe(path)
    if 'error' in info:
        print(json.dumps(info, ensure_ascii=False)); return 1
    tmpwav = os.path.join(out_dir, '._av_tmp.wav')
    extract_wav(path, tmpwav)
    from faster_whisper import WhisperModel
    model = WhisperModel(model_size, device='cpu', compute_type='int8')
    segments, meta = model.transcribe(tmpwav, vad_filter=True)
    base = os.path.splitext(os.path.basename(path))[0]
    jpath = os.path.join(out_dir, base + '.transcript.jsonl')
    mpath = os.path.join(out_dir, base + '.transcript.md')
    n_seg = n_low = 0
    lines = ['# 逐字稿：%s' % base,
             '> 引擎=faster-whisper 本地 / 档位=%s / 语言=%s / 时长=%.1fs' % (
                 model_size, getattr(meta, 'language', '?'), info['duration_s']),
             '> 低置信段标【存疑】禁猜读；speaker 归属 v0.1 不承诺（静音切分近似）。', '']
    with open(jpath, 'w', encoding='utf-8') as jf:
        for seg in segments:
            n_seg += 1
            low = seg.avg_logprob < LOW_LOGPROB
            n_low += low
            rec = {'start': round(seg.start, 2), 'end': round(seg.end, 2),
                   'text': seg.text.strip(), 'avg_logprob': round(seg.avg_logprob, 3),
                   'flag': 'LOW_CONF' if low else 'ok'}
            jf.write(json.dumps(rec, ensure_ascii=False) + '\n')
            t = '[%7.2f→%7.2f] %s%s' % (seg.start, seg.end,
                                        '【存疑】' if low else '', seg.text.strip())
            lines.append(t)
    lines += ['', '---', '段数=%d，其中【存疑】段=%d。凡引用先抽段人工勾稽，准字率断言最高 conf=estimated。'
              % (n_seg, n_low)]
    open(mpath, 'w', encoding='utf-8').write('\n'.join(lines))
    try:
        os.remove(tmpwav)
    except OSError:
        pass
    print(json.dumps({'jsonl': jpath, 'md': mpath, 'segments': n_seg,
                      'low_conf': n_low, 'duration_s': info['duration_s']},
                     ensure_ascii=False))
    return 0

def ingest(paths, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    rows = []
    for p in paths:
        info = probe(p)
        dst = os.path.join(out_dir, os.path.basename(p))
        if os.path.abspath(p) != os.path.abspath(dst):
            with open(p, 'rb') as fi, open(dst, 'wb') as fo:
                fo.write(fi.read())
        rows.append({'source_uri': os.path.abspath(p),
                     'fetched_ts': datetime.datetime.now().isoformat(timespec='seconds'),
                     'title': os.path.basename(p), 'raw_path': dst,
                     'content_hash': md5file(dst), 'media_type': 'av',
                     'duration_s': info.get('duration_s')})
    with open(os.path.join(out_dir, 'index.jsonl'), 'w', encoding='utf-8') as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')
    man = ['# 摄取包 manifest（av-media-ops）', '',
           '> 契约=摄取蒸馏两段式管线契约 v1.0；原始件原格式不动。', '',
           '| # | 文件 | 时长(s) | content_hash |', '|---|---|---|---|']
    for i, r in enumerate(rows, 1):
        man.append('| %d | %s | %s | %s |' % (i, r['title'], r['duration_s'], r['content_hash']))
    open(os.path.join(out_dir, 'manifest.md'), 'w', encoding='utf-8').write('\n'.join(man))
    print(json.dumps({'ingest_pack': out_dir, 'items': len(rows)}, ensure_ascii=False))
    return 0

def frames(path, interval=60, out_dir=None):
    out_dir = out_dir or (os.path.splitext(path)[0] + '_frames')
    os.makedirs(out_dir, exist_ok=True)
    pat = os.path.join(out_dir, 'frame_%05d.jpg')
    code, _, err = run_pinned_media_command(
        'ffmpeg', ['-y', '-i', path, '-vf',
                   'fps=1/%d' % interval, '-q:v', '3', pat])
    if code != 0:
        print(json.dumps({'error': 'ffmpeg_frames_failed', 'stderr': err[:300]})); return 1
    n = len([f for f in os.listdir(out_dir) if f.startswith('frame_')])
    print(json.dumps({'frames_dir': out_dir, 'frames': n, 'interval_s': interval},
                     ensure_ascii=False))
    return 0

def tts(text_path, out_mp3):
    txt = open(text_path, encoding='utf-8').read()
    # 掩码闸：手机/身份证/银行卡长数字串先掩码再合成
    txt2 = re.sub(r'\d{7,}', '〔长数字已掩码〕', txt)
    # 本地通道：espeak-ng 直出 wav 再转 mp3
    tmp = out_mp3 + '.tmp.wav'
    with open('/tmp/._tts_in.txt', 'w', encoding='utf-8') as f:
        f.write(txt2)
    exe = 'espeak-ng' if subprocess.run(['which', 'espeak-ng'],
                                        capture_output=True).returncode == 0 else 'espeak'
    if subprocess.run(['which', exe], capture_output=True).returncode != 0:
        print(json.dumps({'error': 'no_local_tts_engine',
                          'note': 'espeak-ng/espeak 不在场；请装 espeak-ng 或改用内置兜底通道（出域先过脱敏闸）'},
                         ensure_ascii=False)); return 1
    code, _, err = sh([exe, '-v', 'cmn', '-f', '/tmp/._tts_in.txt', '-w', tmp])
    if code != 0:
        print(json.dumps({'error': 'tts_failed', 'stderr': (err or '')[:300]})); return 1
    code, _, err = run_pinned_media_command(
        'ffmpeg', ['-y', '-i', tmp, '-codec:a', 'libmp3lame',
                   '-q:a', '4', out_mp3])
    try:
        os.remove(tmp)
    except OSError:
        pass
    if code != 0:
        print(json.dumps({'error': 'mp3_conv_failed', 'stderr': err[:300]})); return 1
    print(json.dumps({'mp3': out_mp3, 'masked': txt2 != txt}, ensure_ascii=False))
    return 0

FIXTURE_TRANSCRIPT = [
    {'start': 0.0, 'end': 1.2, 'text': '测试一句。', 'avg_logprob': -0.2, 'flag': 'ok'},
    {'start': 1.2, 'end': 2.5, 'text': '含糊不清的一段', 'avg_logprob': -1.4, 'flag': 'LOW_CONF'},
]

def self_test():
    ok = []
    # F1 probe 夹具：对生成的 1s 正弦 wav 探针
    run_pinned_media_command(
        'ffmpeg', ['-y', '-f', 'lavfi', '-i',
                   'sine=frequency=440:duration=1', '/tmp/._f1.wav'])
    info = probe('/tmp/._f1.wav')
    ok.append(('F1 probe', abs(info.get('duration_s', 0) - 1.0) < 0.2))
    # F2 ingest 夹具
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        ingest(['/tmp/._f1.wav'], td)
        ok.append(('F2 ingest_pack', os.path.exists(os.path.join(td, 'index.jsonl'))
                   and os.path.exists(os.path.join(td, 'manifest.md'))))
    # F3 低置信判级夹具
    lows = [r for r in FIXTURE_TRANSCRIPT if r['avg_logprob'] < LOW_LOGPROB]
    ok.append(('F3 low_conf_triage', len(lows) == 1 and lows[0]['flag'] == 'LOW_CONF'))
    # F4 掩码闸夹具
    t = '联系电话 13800138000 请回电'
    masked = re.sub(r'\d{7,}', '〔长数字已掩码〕', t)
    ok.append(('F4 pii_mask', '13800138000' not in masked))
    # F5 frames 夹具
    with tempfile.TemporaryDirectory() as td:
        run_pinned_media_command(
            'ffmpeg', ['-y', '-f', 'lavfi', '-i',
                       'testsrc=duration=3:size=320x240:rate=10', '/tmp/._f5.mp4'])
        frames('/tmp/._f5.mp4', interval=1, out_dir=td)
        ok.append(('F5 frames', len([f for f in os.listdir(td) if f.startswith('frame_')]) >= 2))
    allpass = all(v for _, v in ok)
    for name, v in ok:
        print('%s %s' % ('PASS' if v else 'FAIL', name))
    print('SELF-TEST', 'PASS' if allpass else 'FAIL')
    return 0 if allpass else 1

def parse_transcode_args(argv):
    parser = argparse.ArgumentParser(prog='av_intake.py transcode')
    parser.add_argument('input')
    parser.add_argument('--codec', required=True, choices=sorted(VIDEO_PROFILES))
    parser.add_argument('--out', required=True)
    return parser.parse_args(argv)


def main(argv):
    if not argv or argv[0] in ('-h', '--help'):
        print(__doc__); return 2
    cmd = argv[0]
    if cmd == '--self-test':
        return self_test()
    if cmd == 'probe' and len(argv) == 2:
        print(json.dumps(probe(argv[1]), ensure_ascii=False, indent=1)); return 0
    if cmd == 'codecs' and len(argv) == 1:
        capabilities = codec_capabilities()
        print(json.dumps(capabilities, ensure_ascii=False, indent=1))
        return 0 if capabilities['ffmpeg'] else 1
    if cmd == 'transcode':
        try:
            args = parse_transcode_args(argv[1:])
        except SystemExit as exc:
            return exc.code
        return transcode(args.input, args.out, args.codec)
    if cmd == 'transcribe' and len(argv) >= 2:
        model = 'base'; out = None
        if '--model' in argv:
            model = argv[argv.index('--model') + 1]
        if '--out' in argv:
            out = argv[argv.index('--out') + 1]
        return transcribe(argv[1], model, out)
    if cmd == 'ingest' and '--out' in argv:
        out = argv[argv.index('--out') + 1]
        paths = [a for a in argv[1:] if not a.startswith('-') and a != out]
        return ingest(paths, out)
    if cmd == 'frames' and len(argv) >= 2:
        interval = 60; out = None
        if '--interval' in argv:
            interval = int(argv[argv.index('--interval') + 1])
        if '--out' in argv:
            out = argv[argv.index('--out') + 1]
        return frames(argv[1], interval, out)
    if cmd == 'tts' and len(argv) >= 2 and '--out' in argv:
        return tts(argv[1], argv[argv.index('--out') + 1])
    print('bad args'); print(__doc__); return 2

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))

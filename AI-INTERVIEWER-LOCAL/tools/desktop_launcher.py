"""Windows desktop bootstrap; no training or application data reset."""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
from urllib.parse import urlsplit
import webbrowser

ROOT = Path(__file__).resolve().parents[1]


def run(arguments, root=ROOT, **kwargs):
    subprocess.run([str(item) for item in arguments], cwd=root, check=True, **kwargs)


def json_command(python, code, root=ROOT):
    result = subprocess.run([str(python), '-c', code], cwd=root, check=True,
                            capture_output=True, text=True, encoding='utf-8')
    return json.loads(result.stdout)


def get_json(url):
    # Loopback must not be sent through a corporate HTTP proxy.
    with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(url, timeout=3) as response:
        return json.load(response)


def local_ollama_url(value):
    url = urlsplit(value)
    if (url.scheme != 'http' or url.hostname not in {'localhost', '127.0.0.1', '::1'}
            or url.username or url.password or url.path not in {'', '/'} or url.query or url.fragment):
        raise RuntimeError('Launcher chi tu quan li Ollama HTTP loopback. Xem OLLAMA_BASE_URL trong .env.')
    _ = url.port  # Validate malformed ports before installing anything.
    return value.rstrip('/')


def model_present(tags, name):
    expected = name if ':' in name else name + ':latest'
    return any(item.get('name') in {name, expected} or item.get('model') in {name, expected}
               for item in tags.get('models', []))


@contextlib.contextmanager
def launch_lock(directory):
    import msvcrt
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / 'launcher.lock').open('a+b') as lock:
        lock.seek(0, 2)
        if not lock.tell():
            lock.write(b'0'); lock.flush()
        lock.seek(0)
        try:
            msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError as exc:
            raise RuntimeError('Launcher da chay. Dung cua so dang mo, khong bam nhieu lan.') from exc
        try:
            yield
        finally:
            lock.seek(0); msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)


def prepare_python(root, repair=False):
    python = root / '.venv/Scripts/python.exe'
    if not python.exists():
        print('[1/5] Tao moi truong .venv...', flush=True)
        run([sys.executable, '-m', 'venv', root / '.venv'], root)
    identity = json_command(python, 'import sys,struct,json; print(json.dumps([list(sys.version_info[:2]),struct.calcsize("P")]))', root)
    if identity != [[3, 11], 8]:
        raise RuntimeError('.venv hien tai khong phai Python 3.11 x64. Giu nguyen de khong lam hong; xem ONE_CLICK_SETUP.md.')
    stamp = root / '.runtime/desktop-setup.json'
    fingerprint = hashlib.sha256((root / 'requirements.txt').read_bytes()).hexdigest()
    try:
        installed = json.loads(stamp.read_text(encoding='utf-8')).get('requirements_sha256') == fingerprint
    except (OSError, ValueError):
        installed = False
    broken = False
    if installed and not repair:
        try:
            run([python, '-m', 'pip', 'check'], root)
            run([python, '-c', 'import fastapi,uvicorn,httpx,openpyxl,faster_whisper,onnxruntime,onnx,tokenizers,dotenv,multipart'], root)
        except subprocess.CalledProcessError:
            installed = False; broken = True
    if not installed or repair:
        print('[1/5] Cai thu vien runtime (can Internet)...', flush=True)
        arguments = [python, '-m', 'pip', 'install', '-r', 'requirements.txt']
        if repair or broken:
            arguments.append('--force-reinstall')
        run(arguments, root)
        run([python, '-m', 'pip', 'check'], root)
        stamp.parent.mkdir(parents=True, exist_ok=True)
        temporary = stamp.with_suffix('.tmp')
        temporary.write_text(json.dumps({'requirements_sha256': fingerprint}), encoding='utf-8')
        temporary.replace(stamp)
    else:
        print('[1/5] Thu vien da san sang.', flush=True)
    # Exclusive creation preserves custom .env, including after interrupted setup.
    try:
        with (root / '.env').open('x', encoding='utf-8') as config:
            config.write((root / '.env.example').read_text(encoding='utf-8'))
    except FileExistsError:
        pass
    return python


SETTINGS_CODE = '''import json
from app.config import Settings
from app.services.speech_to_text import stt_status
from app.services.rubric_transformer import transformer_status
s=Settings.from_env()
p=s.rubric_transformer_path or s.root_dir/'models/rubricguard-lite'
print(json.dumps(dict(ollama_url=s.ollama_base_url,model=s.ollama_model,
    transformer_path=str(p),transformer=transformer_status(p),stt=stt_status(s))))
'''


def find_ollama(root=ROOT):
    candidates = [shutil.which('ollama'),
                  str(Path(os.environ.get('LOCALAPPDATA', '')) / 'Programs/Ollama/ollama.exe'),
                  str(root / 'tools/ollama/ollama.exe')]
    return next((Path(item) for item in candidates if item and Path(item).is_file()), None)


def stop_owned(process):
    if process is not None and process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            process.kill(); process.wait(timeout=10)


def prepare_ollama(settings, root, logs):
    url = local_ollama_url(settings['ollama_url'])
    owned = None
    try:
        get_json(url + '/api/tags')
    except (OSError, ValueError):
        executable = find_ollama(root)
        if not executable:
            winget = shutil.which('winget')
            if not winget:
                raise RuntimeError('Thieu Ollama va WinGet. Cai Ollama tu ollama.com/download/windows roi bam lai.')
            print('[2/5] Cai Ollama cho tai khoan hien tai...', flush=True)
            run([winget, 'install', '--id', 'Ollama.Ollama', '--exact', '--source', 'winget',
                 '--scope', 'user', '--architecture', 'x64', '--silent', '--accept-package-agreements',
                 '--accept-source-agreements', '--disable-interactivity'], root)
            executable = find_ollama(root)
        if not executable:
            raise RuntimeError('Chua tim thay ollama.exe sau khi cai; mo lai launcher.')
        env = os.environ.copy()
        env['OLLAMA_HOST'] = urlsplit(url).netloc
        if executable == root / 'tools/ollama/ollama.exe' and 'OLLAMA_MODELS' not in env:
            env['OLLAMA_MODELS'] = str(root / 'models/ollama')
        # An installer may have started the normal tray service in the meantime.
        try:
            get_json(url + '/api/tags')
        except (OSError, ValueError):
            log = logs.enter_context((root / '.runtime/ollama-launcher.log').open('a', encoding='utf-8'))
            owned = subprocess.Popen([str(executable), 'serve'], cwd=root, env=env,
                                     stdout=log, stderr=subprocess.STDOUT,
                                     creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            logs.callback(stop_owned, owned)
    deadline = time.monotonic() + 60
    while True:
        try:
            tags = get_json(url + '/api/tags'); break
        except (OSError, ValueError):
            if time.monotonic() >= deadline or (owned and owned.poll() is not None):
                raise RuntimeError('Ollama chua san sang. Xem .runtime/ollama-launcher.log va kiem tra cong.')
            time.sleep(1)
    if not model_present(tags, settings['model']):
        executable = find_ollama(root)
        if not executable:
            raise RuntimeError('Ollama da chay nhung thieu CLI de tai model. Cai Ollama roi bam lai.')
        print('[2/5] Tai ' + settings['model'] + ' (lan dau co the rat lau)...', flush=True)
        env = os.environ.copy(); env['OLLAMA_HOST'] = urlsplit(url).netloc
        run([executable, 'pull', settings['model']], root, env=env)
        if not model_present(get_json(url + '/api/tags'), settings['model']):
            raise RuntimeError('Tai model xong nhung dich vu Ollama chua thay model can dung.')
    print('[2/5] Ollama va model da san sang.', flush=True)


def prepare_models(python, settings, root):
    if not settings['stt']['ready']:
        print('[3/5] Tai/kiem tra Whisper. Lan dau se nap model de thu...', flush=True)
        run([python, '-m', 'app.stt_setup'], root)
    else:
        print('[3/5] Whisper da duoc setup; se nap khi bat dau phien.', flush=True)
    target = Path(settings['transformer_path'])
    if not settings['transformer']['installed']:
        if target.exists() and any(target.iterdir()):
            raise RuntimeError('Thu muc Transformer co du lieu nhung chua du file. Khong ghi de; khoi phuc model hoac chon thu muc moi trong .env.')
        print('[4/5] Tai Transformer baseline INT8; khong fine-tune...', flush=True)
        target.parent.mkdir(parents=True, exist_ok=True)
        staging = target.parent / ('.' + target.name + '-launcher-download')
        run([python, 'tools/setup_rubricguard_lite.py', '--output-dir', staging], root)
        if target.exists():
            target.rmdir()  # Only an empty directory can be replaced.
        staging.replace(target)
    else:
        print('[4/5] Giu nguyen Transformer va metadata da co.', flush=True)


def serve(python, port, root, logs, verify_startup=False):
    with socket.socket() as probe:
        try:
            probe.bind(('127.0.0.1', port))
        except OSError as exc:
            raise RuntimeError(f'Cong {port} dang dung. Dung backend cu truoc, hoac chon -Port khac neu la ung dung khac.') from exc
    url = f'http://127.0.0.1:{port}'
    process = subprocess.Popen([str(python), '-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', str(port)], cwd=root)
    logs.callback(stop_owned, process)
    deadline = time.monotonic() + 60
    while True:
        if process.poll() is not None:
            raise RuntimeError('Backend dung truoc khi san sang. Xem loi phia tren.')
        try:
            get_json(url + '/api/health'); break
        except (OSError, ValueError):
            if time.monotonic() >= deadline:
                raise RuntimeError('Backend chua san sang sau 60 giay. Xem loi phia tren.')
            time.sleep(1)
    if verify_startup:
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        for path, expected in [('/', b'appShell'), ('/static/app.js', b'LUCIDE_ICONS')]:
            with opener.open(url + path, timeout=10) as response:
                if response.status != 200 or expected not in response.read(2 * 1024 * 1024):
                    raise RuntimeError('Web chua tra dung noi dung: ' + path)
        (root / '.runtime/launcher-startup-check.json').write_text(
            json.dumps({'verified': True, 'url': url, 'index_http': 200, 'javascript_http': 200,
                        'checked_at': time.time()}), encoding='utf-8')
        print('[5/5] Kiem tra web thanh cong: ' + url + ' (HTTP 200). Da dung ban thu.', flush=True)
        return
    print('[5/5] Mo web: ' + url + '\nGiu cua so nay mo. Ctrl+C de dung.', flush=True)
    webbrowser.open(url)
    process.wait()
    if process.returncode:
        raise RuntimeError(f'Backend dung voi ma {process.returncode}.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8001)
    parser.add_argument('--setup-only', action='store_true')
    parser.add_argument('--repair', action='store_true')
    parser.add_argument('--verify-startup', action='store_true', help='Check real web HTTP then stop owned processes; do not open a browser')
    args = parser.parse_args()
    if args.setup_only and args.verify_startup:
        parser.error('Choose --setup-only or --verify-startup, not both')
    if not 1 <= args.port <= 65535:
        parser.error('port must be 1..65535')
    if os.name != 'nt' or sys.version_info[:2] != (3, 11):
        parser.error('Use setup_and_run.ps1 with Windows x64 and Python 3.11')
    os.environ['PYTHONUTF8'] = '1'
    with launch_lock(ROOT / '.runtime'), contextlib.ExitStack() as logs:
        python = prepare_python(ROOT, args.repair)
        settings = json_command(python, SETTINGS_CODE)
        local_ollama_url(settings['ollama_url'])
        prepare_ollama(settings, ROOT, logs)
        prepare_models(python, settings, ROOT)
        if args.setup_only:
            print('Da hoan tat setup. Bam CAI_DAT_VA_CHAY.bat de mo web.')
        else:
            serve(python, args.port, ROOT, logs, verify_startup=args.verify_startup)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('\nDa dung launcher.')
    except Exception as exc:
        print(f'LOI: {exc}\nXem ONE_CLICK_SETUP.md. Du lieu va .env khong bi xoa.', file=sys.stderr)
        sys.exit(1)

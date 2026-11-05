import contextlib
import importlib.util
from pathlib import Path
import socket
import subprocess

import pytest

SPEC = importlib.util.spec_from_file_location('desktop_launcher', Path(__file__).parents[1] / 'tools/desktop_launcher.py')
launcher = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(launcher)


@pytest.mark.parametrize('value', ['https://127.0.0.1:11434', 'http://example.com', 'http://user:pass@localhost',
                                  'http://localhost/api', 'http://localhost?token=x', 'http://localhost#x'])
def test_auto_setup_never_targets_remote_or_credentialed_ollama(value):
    with pytest.raises(RuntimeError):
        launcher.local_ollama_url(value)


def test_local_url_and_model_name_resolution():
    assert launcher.local_ollama_url('http://127.0.0.1:11434/') == 'http://127.0.0.1:11434'
    assert launcher.model_present({'models': [{'name': 'qwen2.5:3b'}]}, 'qwen2.5:3b')
    assert launcher.model_present({'models': [{'name': 'qwen:latest'}]}, 'qwen')
    assert not launcher.model_present({'models': [{'name': 'qwen3:8b'}]}, 'qwen2.5:3b')


def python_fixture(tmp_path, monkeypatch):
    python = tmp_path / '.venv/Scripts/python.exe'
    python.parent.mkdir(parents=True); python.touch()
    (tmp_path / 'requirements.txt').write_text('example==1\n')
    (tmp_path / '.env.example').write_text('CUSTOM=default\n')
    monkeypatch.setattr(launcher, 'json_command', lambda *args: [[3, 11], 8])
    calls = []
    monkeypatch.setattr(launcher, 'run', lambda args, *rest, **kwargs: calls.append([str(v) for v in args]))
    return python, calls


def test_first_install_stamp_then_cached_run_preserves_config(tmp_path, monkeypatch):
    python, calls = python_fixture(tmp_path, monkeypatch)
    (tmp_path / '.env').write_text('CUSTOM=keep\n')
    assert launcher.prepare_python(tmp_path) == python
    assert any('install' in call for call in calls)
    assert (tmp_path / '.env').read_text() == 'CUSTOM=keep\n'
    calls.clear()
    launcher.prepare_python(tmp_path)
    assert not any('install' in call for call in calls)
    assert any('check' in call for call in calls)
    (tmp_path / 'requirements.txt').write_text('example==2\n')
    calls.clear(); launcher.prepare_python(tmp_path)
    assert any('install' in call for call in calls)


def test_failed_dependency_install_never_marks_ready(tmp_path, monkeypatch):
    python_fixture(tmp_path, monkeypatch)
    def fail(*args, **kwargs):
        raise subprocess.CalledProcessError(1, ['pip'])
    monkeypatch.setattr(launcher, 'run', fail)
    with pytest.raises(subprocess.CalledProcessError):
        launcher.prepare_python(tmp_path)
    assert not (tmp_path / '.runtime/desktop-setup.json').exists()


def test_wrong_existing_venv_is_not_replaced(tmp_path, monkeypatch):
    python_fixture(tmp_path, monkeypatch)
    monkeypatch.setattr(launcher, 'json_command', lambda *args: [[3, 12], 8])
    with pytest.raises(RuntimeError, match='3.11'):
        launcher.prepare_python(tmp_path)
    assert (tmp_path / '.venv/Scripts/python.exe').exists()


def test_failed_cache_probe_reinstalls_dependencies(tmp_path, monkeypatch):
    python_fixture(tmp_path, monkeypatch)
    launcher.prepare_python(tmp_path)
    calls = []
    def run(args, *rest, **kwargs):
        calls.append(args)
        if len(calls) == 1:
            raise subprocess.CalledProcessError(1, args)
    monkeypatch.setattr(launcher, 'run', run)
    launcher.prepare_python(tmp_path)
    assert any('install' in call for call in calls)


def settings(tmp_path, installed=True):
    return dict(stt={'ready': True}, transformer={'installed': installed},
                transformer_path=str(tmp_path / 'model'), ollama_url='http://127.0.0.1:11434', model='qwen2.5:3b')


def test_existing_finetune_and_stt_are_never_overwritten(tmp_path, monkeypatch):
    value = settings(tmp_path)
    target = Path(value['transformer_path']); target.mkdir()
    (target / 'training_summary.json').write_text('finetuned-metadata')
    def fail(*args, **kwargs):
        pytest.fail('Existing models must not invoke setup')
    monkeypatch.setattr(launcher, 'run', fail)
    launcher.prepare_models('python', value, tmp_path)
    assert (target / 'training_summary.json').read_text() == 'finetuned-metadata'


def test_incomplete_existing_transformer_is_not_repaired_over_user_files(tmp_path, monkeypatch):
    value = settings(tmp_path, False)
    target = Path(value['transformer_path']); target.mkdir()
    (target / 'config.json').write_text('custom')
    with pytest.raises(RuntimeError, match='Khong ghi de'):
        launcher.prepare_models('python', value, tmp_path)
    assert (target / 'config.json').read_text() == 'custom'


def test_new_transformer_is_published_only_after_success(tmp_path, monkeypatch):
    value = settings(tmp_path, False)
    def download(args, *rest):
        staging = Path(args[-1]); staging.mkdir(); (staging / 'model.int8.onnx').write_bytes(b'fixture')
    monkeypatch.setattr(launcher, 'run', download)
    launcher.prepare_models('python', value, tmp_path)
    assert (Path(value['transformer_path']) / 'model.int8.onnx').read_bytes() == b'fixture'


def test_interrupted_download_leaves_target_unmodified(tmp_path, monkeypatch):
    value = settings(tmp_path, False)
    def fail(args, *rest):
        staging = Path(args[-1]); staging.mkdir(); (staging / 'config.json.download').write_bytes(b'partial')
        raise subprocess.CalledProcessError(1, args)
    monkeypatch.setattr(launcher, 'run', fail)
    with pytest.raises(subprocess.CalledProcessError):
        launcher.prepare_models('python', value, tmp_path)
    assert not Path(value['transformer_path']).exists()


def test_busy_port_never_starts_second_backend(tmp_path, monkeypatch):
    with socket.socket() as listener, contextlib.ExitStack() as logs:
        listener.bind(('127.0.0.1', 0)); listener.listen()
        with pytest.raises(RuntimeError, match='Cong'):
            launcher.serve('not-a-python', listener.getsockname()[1], tmp_path, logs)


def test_existing_ollama_does_not_install_or_stop_service(tmp_path, monkeypatch):
    value = settings(tmp_path)
    monkeypatch.setattr(launcher, 'get_json', lambda url: {'models': [{'name': value['model']}]})
    monkeypatch.setattr(launcher, 'find_ollama', lambda *args: pytest.fail('Must reuse running service'))
    with contextlib.ExitStack() as logs:
        launcher.prepare_ollama(value, tmp_path, logs)


def test_owned_process_is_only_terminated_when_running():
    class Process:
        stopped = False
        def poll(self): return None if not self.stopped else 0
        def terminate(self): self.stopped = True
        def wait(self, timeout): pass
    process = Process()
    launcher.stop_owned(process)
    assert process.stopped
    launcher.stop_owned(None)


def test_setup_download_failure_does_not_publish_partial_config(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location('rubric_setup_fixture', Path(__file__).parents[1] / 'tools/setup_rubricguard_lite.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    monkeypatch.setattr(module.sys if hasattr(module, 'sys') else launcher.sys, 'argv', ['setup', '--output-dir', str(tmp_path)])
    def fail(url, path):
        Path(path).write_bytes(b'incomplete')
        raise OSError('network interrupted')
    monkeypatch.setattr(module.urllib.request, 'urlretrieve', fail)
    with pytest.raises(OSError, match='interrupted'):
        module.main()
    assert not (tmp_path / 'config.json').exists()
    assert (tmp_path / 'config.json.download').read_bytes() == b'incomplete'


def test_setup_quantization_failure_does_not_publish_partial_model(tmp_path, monkeypatch):
    import onnxruntime.quantization as quantization
    spec = importlib.util.spec_from_file_location('rubric_setup_quant_fixture', Path(__file__).parents[1] / 'tools/setup_rubricguard_lite.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    monkeypatch.setattr(launcher.sys, 'argv', ['setup', '--output-dir', str(tmp_path)])
    for name in module.FILES:
        (tmp_path / name).write_bytes(b'fixture')
    def fail(source, output, **kwargs):
        Path(output).write_bytes(b'incomplete')
        raise RuntimeError('quantization interrupted')
    monkeypatch.setattr(quantization, 'quantize_dynamic', fail)
    with pytest.raises(RuntimeError, match='interrupted'):
        module.main()
    assert not (tmp_path / 'model.int8.onnx').exists()
    assert not (tmp_path / 'training_summary.json').exists()


@pytest.mark.parametrize('valid_html', [True, False])
def test_verify_startup_checks_web_content_and_cleans_owned_server(tmp_path, monkeypatch, valid_html):
    (tmp_path / '.runtime').mkdir()
    class Process:
        stopped = False
        def poll(self): return 0 if self.stopped else None
        def terminate(self): self.stopped = True
        def wait(self, timeout=0): pass
    process = Process()
    monkeypatch.setattr(launcher.subprocess, 'Popen', lambda *a, **kw: process)
    monkeypatch.setattr(launcher, 'get_json', lambda *a: {'status': 'ok'})
    monkeypatch.setattr(launcher.webbrowser, 'open', lambda *a: pytest.fail('Verification must not leave a browser pointing at a stopped server'))
    class Response:
        status = 200
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self, size): return b'appShell LUCIDE_ICONS' if valid_html else b'other application'
    class Opener:
        def open(self, *args, **kwargs): return Response()
    monkeypatch.setattr(launcher.urllib.request, 'build_opener', lambda *args: Opener())
    with socket.socket() as port_probe:
        port_probe.bind(('127.0.0.1', 0)); port = port_probe.getsockname()[1]
    with contextlib.ExitStack() as logs:
        if valid_html:
            launcher.serve('python', port, tmp_path, logs, verify_startup=True)
        else:
            with pytest.raises(RuntimeError, match='Web'):
                launcher.serve('python', port, tmp_path, logs, verify_startup=True)
    assert process.stopped
    assert (tmp_path / '.runtime/launcher-startup-check.json').exists() is valid_html

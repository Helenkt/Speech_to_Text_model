import pytest

from tools.check_rubricguard_live import local_ollama_host


def test_managed_live_check_respects_the_configured_local_port():
    assert local_ollama_host("http://127.0.0.1:11588") == "127.0.0.1:11588"
    assert local_ollama_host("http://localhost:11434/") == "localhost:11434"


@pytest.mark.parametrize("url", ["https://127.0.0.1:11588", "http://example.com:11588"])
def test_managed_live_check_does_not_launch_an_unrelated_remote_service(url):
    with pytest.raises(ValueError, match="local"):
        local_ollama_host(url)

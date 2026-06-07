import json
import urllib.request
import urllib.error
from io import BytesIO
from termstory.ai import (
    generate_ai_summary,
    get_last_ai_error,
    clear_last_ai_error
)

import pytest

@pytest.fixture(autouse=True)
def mock_config_path(tmp_path, monkeypatch):
    config_file = tmp_path / "config.json"
    monkeypatch.setattr("termstory.config.get_config_path", lambda: str(config_file))

def test_get_and_clear_error():
    clear_last_ai_error()
    assert get_last_ai_error() is None

def test_invalid_url_sets_error():
    clear_last_ai_error()
    res = generate_ai_summary(
        ["pytest tests/"],
        "test-key",
        "",
        "llama3",
        "groq"
    )
    assert res is None
    assert get_last_ai_error() == "API Base URL is not configured or invalid."

def test_url_error_sets_error(monkeypatch):
    clear_last_ai_error()
    
    def mock_urlopen(req, timeout=None):
        raise urllib.error.URLError("Connection refused")
        
    monkeypatch.setattr(urllib.request, "urlopen", mock_urlopen)
    
    res = generate_ai_summary(
        ["pytest tests/"],
        "test-key",
        "https://api.groq.com/openai/v1",
        "llama3",
        "groq"
    )
    assert res is None
    assert "Connection refused" in get_last_ai_error()

def test_http_error_json_body_parsing(monkeypatch):
    clear_last_ai_error()
    
    def mock_urlopen(req, timeout=None):
        # Create an HTTPError with a json body containing an error message
        body = json.dumps({
            "error": {
                "message": "Invalid API Key provided"
            }
        }).encode("utf-8")
        fp = BytesIO(body)
        raise urllib.error.HTTPError(
            url="https://api.groq.com/openai/v1",
            code=401,
            msg="Unauthorized",
            hdrs={},
            fp=fp
        )
        
    monkeypatch.setattr(urllib.request, "urlopen", mock_urlopen)
    
    res = generate_ai_summary(
        ["pytest tests/"],
        "test-key",
        "https://api.groq.com/openai/v1",
        "llama3",
        "groq"
    )
    assert res is None
    assert get_last_ai_error() == "HTTP Error 401: Invalid API Key provided"

def test_http_error_non_json_body_parsing(monkeypatch):
    clear_last_ai_error()
    
    def mock_urlopen(req, timeout=None):
        # Create an HTTPError with a non-json text body
        body = b"Service Unavailable"
        fp = BytesIO(body)
        raise urllib.error.HTTPError(
            url="https://api.groq.com/openai/v1",
            code=503,
            msg="Service Unavailable",
            hdrs={},
            fp=fp
        )
        
    monkeypatch.setattr(urllib.request, "urlopen", mock_urlopen)
    
    res = generate_ai_summary(
        ["pytest tests/"],
        "test-key",
        "https://api.groq.com/openai/v1",
        "llama3",
        "groq"
    )
    assert res is None
    assert get_last_ai_error() == "HTTP Error 503: Service Unavailable"


def test_concurrent_threads_error_isolation(monkeypatch):
    import threading
    import time
    from termstory.ai import _send_llm_request
    
    barrier = threading.Barrier(2)
    thread_errors = {}
    
    def run_thread_a():
        clear_last_ai_error()
        barrier.wait()
        _send_llm_request("prompt", "key", "", "model", "groq")
        time.sleep(0.1)
        thread_errors["A"] = get_last_ai_error()
        
    def run_thread_b():
        clear_last_ai_error()
        
        def mock_urlopen(req, timeout=None):
            raise urllib.error.URLError("Connection refused")
            
        monkeypatch.setattr(urllib.request, "urlopen", mock_urlopen)
        
        barrier.wait()
        _send_llm_request("prompt", "key", "https://api.groq.com/openai/v1", "model", "groq")
        time.sleep(0.1)
        thread_errors["B"] = get_last_ai_error()
        
    ta = threading.Thread(target=run_thread_a)
    tb = threading.Thread(target=run_thread_b)
    ta.start()
    tb.start()
    ta.join()
    tb.join()
    
    assert thread_errors["A"] == "API Base URL is not configured or invalid."
    assert "Connection refused" in thread_errors["B"]


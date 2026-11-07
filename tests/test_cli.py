"""End-to-end CLI tests using file:// URLs, plus summarizer plumbing tests."""

import json
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from url_to_clean_text import __version__
from url_to_clean_text.summarize import SummarizeError, summarize
from url_to_clean_text.cli import main

PAGE = (
    "<html><head><title>Clean Test</title></head><body>"
    "<nav>NavNoise</nav>"
    "<div class='cookie-consent'>CookieNoise</div>"
    "<article><h1>Article</h1><p>Straight to the point. "
    "<a href='https://ref.example/x'>Source</a></p></article>"
    "</body></html>"
)


@pytest.fixture()
def page_file(tmp_path):
    path = tmp_path / "page.html"
    path.write_text(PAGE, encoding="utf-8")
    return path


def run_cli(capsys, *argv):
    code = main(list(argv))
    out = capsys.readouterr().out
    return code, out


def test_version():
    import argparse
    from url_to_clean_text.cli import build_parser

    with pytest.raises(SystemExit) as exc:
        build_parser().parse_args(["--version"])
    assert exc.value.code == 0


def test_cli_file_url_returns_clean_text(capsys, page_file):
    code, out = run_cli(capsys, f"file://{page_file}")
    assert code == 0
    assert "# Clean Test" in out
    assert "# Article" in out
    assert "Straight to the point. Source [1]" in out
    assert "[1] https://ref.example/x" in out
    assert "NavNoise" not in out
    assert "CookieNoise" not in out


def test_cli_no_footnotes(capsys, page_file):
    code, out = run_cli(capsys, f"file://{page_file}", "--no-footnotes")
    assert code == 0
    assert "Source" in out
    assert "https://" not in out
    assert "Link references:" not in out


def test_cli_output_writes_file(capsys, tmp_path, page_file):
    out_file = tmp_path / "out.txt"
    code, _ = run_cli(capsys, f"file://{page_file}", "-o", str(out_file))
    assert code == 0
    saved = out_file.read_text(encoding="utf-8")
    assert "# Article" in saved
    assert "Source [1]" in saved


def test_cli_max_chars_truncates(capsys, page_file):
    code, out = run_cli(capsys, f"file://{page_file}", "--max-chars", "12")
    assert code == 0
    assert out.strip() == "# Clean Test"


def test_cli_missing_file_url_fails_with_fetch_code(capsys):
    code = main(["file:///nonexistent/path/xyz.html"])
    out = capsys.readouterr().err
    assert code == 2
    assert "error:" in out


class _Beeper(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length))
        assert body["model"] == "test-model"
        assert "messages" in body
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        reply = {"choices": [{"message": {"content": "1. point one\n2. point two"}}]}
        self.wfile.write(json.dumps(reply).encode())

    def log_message(self, *a):  # silence test server
        pass


@pytest.fixture()
def llm_server():
    server = HTTPServer(("127.0.0.1", 0), _Beeper)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}/v1"
    server.shutdown()


def test_cli_summarize_uses_local_server(capsys, page_file, llm_server):
    code, out = run_cli(
        capsys,
        f"file://{page_file}",
        "--summarize",
        "--api-base",
        llm_server,
        "--model",
        "test-model",
    )
    assert code == 0
    assert out.strip() == "1. point one\n2. point two"
    assert "# Article" not in out


def test_cli_summarize_and_keep(capsys, page_file, llm_server):
    code, out = run_cli(
        capsys,
        f"file://{page_file}",
        "--summarize-and-keep",
        "--api-base",
        llm_server,
        "--model",
        "test-model",
    )
    assert code == 0
    assert out.startswith("Summary:\n1. point one")
    assert "# Article" in out


def test_cli_summarize_server_down_returns_exit_4(capsys):
    code = main(["file:///dev/null-itsafile", "--summarize"])
    assert code in (2, 4)


def test_summarize_function_raises_on_bad_server():
    with pytest.raises(SummarizeError):
        summarize("text", api_base="http://127.0.0.1:1/v1", timeout=1.5)


def test_module_entry_point_runs():
    result = subprocess.run(
        [sys.executable, "-m", "url_to_clean_text", "--version"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert __version__ in result.stdout

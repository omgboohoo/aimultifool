from __future__ import annotations

import json
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any, Dict, Generator, Optional
import queue as thread_queue
import time


class SubprocessLlama:
    """
    Thin wrapper that mimics the subset of llama_cpp.Llama API that aiMultiFool uses:
      - create_chat_completion(stream=True/False)
      - tokenize_count(text, add_bos=False, special=False)

    This runs llama_cpp in a separate process to avoid Windows UI freezes caused by
    llama-cpp-python holding the GIL during model load.
    """

    def __init__(self, *, python_exe: str, worker_path: str):
        self.python_exe = python_exe
        self.worker_path = worker_path
        self._proc: Optional[subprocess.Popen[str]] = None
        self._lock = threading.Lock()
        self._streaming: bool = False

    def start(self) -> None:
        if self._proc and self._proc.poll() is None:
            return
        self._proc = subprocess.Popen(
            [self.python_exe, "-u", self.worker_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            # IMPORTANT: keep stdout clean for JSONL protocol.
            # llama.cpp / llama-cpp-python may emit logs to stderr; if we merge it into stdout,
            # json parsing will break.
            stderr=subprocess.DEVNULL,
            text=True,
            bufsize=1,
        )

    def restart(self) -> None:
        """Kill and re-create the subprocess."""
        self.close()
        self.start()

    def close(self) -> None:
        with self._lock:
            if not self._proc:
                return
            try:
                self._send({"cmd": "shutdown"})
            except Exception:
                pass
            try:
                self._proc.kill()
            except Exception:
                pass
            self._proc = None

    def _send(self, obj: Dict[str, Any]) -> None:
        assert self._proc and self._proc.stdin
        self._proc.stdin.write(json.dumps(obj, ensure_ascii=False) + "\n")
        self._proc.stdin.flush()

    def _recv(self) -> Dict[str, Any]:
        assert self._proc and self._proc.stdout
        line = self._proc.stdout.readline()
        if not line:
            raise RuntimeError("LLM subprocess exited")
        return json.loads(line)

    def _drain_stream_locked(self) -> None:
        """Drain any pending streaming output until we see 'done' or an error."""
        try:
            while True:
                resp = self._recv()
                t = resp.get("type")
                if t == "done":
                    return
                if t == "error":
                    return
                # ignore deltas and anything else
        except Exception:
            # If the subprocess died while draining, that's fine for our purposes.
            return

    def _recv_with_timeout(self, timeout_s: float) -> Dict[str, Any]:
        """
        Read exactly one JSON line from stdout with a timeout.
        Windows pipes don't support select() reliably, so we use a helper thread.
        """
        q: "thread_queue.Queue[object]" = thread_queue.Queue()

        def _reader():
            try:
                q.put(self._recv())
            except Exception as e:
                q.put(e)

        t = threading.Thread(target=_reader, daemon=True)
        t.start()
        try:
            item = q.get(timeout=timeout_s)
        except thread_queue.Empty:
            raise TimeoutError(f"Timed out waiting for LLM subprocess ({timeout_s}s)")
        if isinstance(item, Exception):
            raise item
        return item  # type: ignore[return-value]

    def load(
        self,
        *,
        model_path: str,
        n_ctx: int,
        n_gpu_layers: int,
        verbose: bool = False,
        timeout_s: float = 120.0,
    ) -> None:
        self.start()
        with self._lock:
            self._send(
                {
                    "cmd": "load",
                    "model_path": model_path,
                    "n_ctx": int(n_ctx),
                    "n_gpu_layers": int(n_gpu_layers),
                    "verbose": bool(verbose),
                }
            )
            resp = self._recv_with_timeout(timeout_s)
            if resp.get("type") == "loaded" and resp.get("ok"):
                return
            if resp.get("type") == "error":
                raise RuntimeError(resp.get("message", "Load failed"))
            raise RuntimeError(f"Unexpected response: {resp}")

    def tokenize_count(self, text: str, *, add_bos: bool = False, special: bool = False) -> int:
        # IMPORTANT: our subprocess is single-threaded / single-command at a time.
        # If a streaming chat is in progress, we can't interleave tokenize_count without
        # corrupting the JSONL protocol. Return a cheap estimate instead.
        if self._streaming:
            # Rough heuristic: ~4 chars per token on average (English-ish).
            return max(1, len(text) // 4) if text else 0
        with self._lock:
            self._send({"cmd": "tokenize_count", "text": text, "add_bos": add_bos, "special": special})
            resp = self._recv()
            if resp.get("type") == "tokenize_count":
                return int(resp.get("count", 0))
            if resp.get("type") == "error":
                raise RuntimeError(resp.get("message", "tokenize_count failed"))
            raise RuntimeError(f"Unexpected response: {resp}")

    def create_chat_completion(self, *, messages: list[dict], stream: bool = True, **params: Any):
        """
        Returns either a dict (stream=False) or a generator of llama-like chunks (stream=True).
        For stream=True we yield dicts shaped like llama_cpp output:
          {"choices":[{"delta":{"content":"..."}}]}
        """
        params = dict(params)
        params["stream"] = bool(stream)

        if not stream:
            with self._lock:
                self._send({"cmd": "chat", "messages": messages, "params": params})
                resp = self._recv()
                if resp.get("type") == "result":
                    return resp["response"]
                if resp.get("type") == "error":
                    raise RuntimeError(resp.get("message", "chat failed"))
                raise RuntimeError(f"Unexpected response: {resp}")

        def _gen() -> Generator[Dict[str, Any], None, None]:
            with self._lock:
                self._streaming = True
                try:
                    self._send({"cmd": "chat", "messages": messages, "params": params})
                    while True:
                        resp = self._recv()
                        t = resp.get("type")
                        if t == "delta":
                            yield {"choices": [{"delta": {"content": resp.get("content", "")}}]}
                        elif t == "done":
                            return
                        elif t == "error":
                            raise RuntimeError(resp.get("message", "chat failed"))
                        else:
                            raise RuntimeError(f"Unexpected response: {resp}")
                except GeneratorExit:
                    # Caller stopped early (e.g. user pressed Stop). Drain remaining deltas so the
                    # next command starts on a clean JSON boundary.
                    self._drain_stream_locked()
                    raise
                finally:
                    self._streaming = False

        return _gen()


class SubprocessEmbedder:
    """Dedicated embedding subprocess (kept separate from chat subprocess)."""

    def __init__(self, *, python_exe: str, worker_path: str):
        self.python_exe = python_exe
        self.worker_path = worker_path
        self._proc: Optional[subprocess.Popen[str]] = None
        self._lock = threading.Lock()

    def start(self) -> None:
        if self._proc and self._proc.poll() is None:
            return
        self._proc = subprocess.Popen(
            [self.python_exe, "-u", self.worker_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            bufsize=1,
        )

    def close(self) -> None:
        with self._lock:
            if not self._proc:
                return
            try:
                self._send({"cmd": "shutdown"})
            except Exception:
                pass
            try:
                self._proc.kill()
            except Exception:
                pass
            self._proc = None

    def _send(self, obj: Dict[str, Any]) -> None:
        assert self._proc and self._proc.stdin
        self._proc.stdin.write(json.dumps(obj, ensure_ascii=False) + "\n")
        self._proc.stdin.flush()

    def _recv_with_timeout(self, timeout_s: float) -> Dict[str, Any]:
        assert self._proc and self._proc.stdout
        q: "thread_queue.Queue[object]" = thread_queue.Queue()

        def _reader():
            try:
                line = self._proc.stdout.readline()
                if not line:
                    raise RuntimeError("Embed subprocess exited")
                q.put(json.loads(line))
            except Exception as e:
                q.put(e)

        t = threading.Thread(target=_reader, daemon=True)
        t.start()
        try:
            item = q.get(timeout=timeout_s)
        except thread_queue.Empty:
            raise TimeoutError(f"Timed out waiting for embed subprocess ({timeout_s}s)")
        if isinstance(item, Exception):
            raise item
        return item  # type: ignore[return-value]

    def load(self, *, model_path: str, n_ctx: int = 2048, timeout_s: float = 120.0) -> None:
        self.start()
        with self._lock:
            self._send({"cmd": "load_embed", "model_path": model_path, "n_ctx": int(n_ctx), "verbose": False})
            resp = self._recv_with_timeout(timeout_s)
            if resp.get("type") == "embed_loaded" and resp.get("ok"):
                return
            if resp.get("type") == "error":
                raise RuntimeError(resp.get("message", "Embed load failed"))
            raise RuntimeError(f"Unexpected response: {resp}")

    def embed(self, text: str, *, task: str = "document", timeout_s: float = 30.0) -> list[float]:
        with self._lock:
            self._send({"cmd": "embed", "text": text, "task": task})
            resp = self._recv_with_timeout(timeout_s)
            if resp.get("type") == "embed":
                return resp.get("embedding") or []
            if resp.get("type") == "error":
                raise RuntimeError(resp.get("message", "Embed failed"))
            raise RuntimeError(f"Unexpected response: {resp}")



#!/usr/bin/env python3
"""
Subprocess worker for aiMultiFool.

Why: On Windows, llama-cpp-python model loading can hold the GIL inside native code,
which can freeze the Textual UI even if called from a background thread. Running the
LLM in a separate process avoids that entire class of freezes.

Protocol: JSON Lines over stdin/stdout.
Commands:
  - {"cmd":"load", "model_path": "...", "n_ctx": 8192, "n_gpu_layers": 0, "verbose": false}
  - {"cmd":"chat", "messages":[...], "params": {...}}   (params includes stream=true/false)
  - {"cmd":"tokenize_count", "text": "...", "add_bos": false, "special": false}
  - {"cmd":"shutdown"}

Responses:
  - {"type":"loaded", "ok": true, "n_gpu_layers": 0}
  - {"type":"delta", "content": "..."}  (streaming)
  - {"type":"done"}
  - {"type":"result", "response": {...}} (non-stream)
  - {"type":"tokenize_count", "count": 123}
  - {"type":"error", "message": "...", "where": "..."}
"""

from __future__ import annotations

import json
import os
import sys
import traceback


def _write(obj: dict) -> None:
    sys.stdout.write(json.dumps(obj, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def main() -> int:
    llm = None
    embed_llm = None

    # Best effort: make stdout unbuffered (Windows)
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except Exception:
        pass

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue

        try:
            req = json.loads(line)
        except Exception:
            _write({"type": "error", "where": "parse", "message": "Invalid JSON"})
            continue

        cmd = req.get("cmd")
        try:
            if cmd == "shutdown":
                _write({"type": "done"})
                return 0

            if cmd == "load":
                from llama_cpp import Llama

                model_path = req.get("model_path")
                n_ctx = int(req.get("n_ctx", 8192))
                n_gpu_layers = int(req.get("n_gpu_layers", 0))
                verbose = bool(req.get("verbose", False))

                if not model_path:
                    _write({"type": "error", "where": "load", "message": "Missing model_path"})
                    continue

                # Drop previous instance
                llm = None

                llm = Llama(
                    model_path=str(model_path),
                    n_ctx=n_ctx,
                    n_gpu_layers=n_gpu_layers,
                    verbose=verbose,
                )
                _write({"type": "loaded", "ok": True, "n_gpu_layers": n_gpu_layers})
                continue

            if cmd == "load_embed":
                from llama_cpp import Llama

                model_path = req.get("model_path")
                n_ctx = int(req.get("n_ctx", 2048))
                verbose = bool(req.get("verbose", False))

                if not model_path:
                    _write({"type": "error", "where": "load_embed", "message": "Missing model_path"})
                    continue

                embed_llm = None
                embed_llm = Llama(
                    model_path=str(model_path),
                    n_ctx=n_ctx,
                    n_gpu_layers=0,
                    embedding=True,
                    verbose=verbose,
                )
                _write({"type": "embed_loaded", "ok": True})
                continue

            if cmd == "embed":
                if embed_llm is None:
                    _write({"type": "error", "where": "embed", "message": "Embedding model not loaded"})
                    continue
                text = req.get("text", "")
                task = req.get("task", "document")
                prefix = "search_document: " if task == "document" else "search_query: "
                emb = embed_llm.create_embedding(prefix + text)
                vec = emb["data"][0]["embedding"]
                _write({"type": "embed", "embedding": vec})
                continue

            if cmd == "tokenize_count":
                if llm is None:
                    _write({"type": "error", "where": "tokenize_count", "message": "Model not loaded"})
                    continue
                text = req.get("text", "")
                add_bos = bool(req.get("add_bos", False))
                special = bool(req.get("special", False))
                toks = llm.tokenize(text.encode("utf-8"), add_bos=add_bos, special=special)
                _write({"type": "tokenize_count", "count": len(toks)})
                continue

            if cmd == "chat":
                if llm is None:
                    _write({"type": "error", "where": "chat", "message": "Model not loaded"})
                    continue

                messages = req.get("messages") or []
                params = req.get("params") or {}
                stream = bool(params.get("stream", False))

                # llama_cpp expects "messages" arg and params kwargs
                if stream:
                    params["stream"] = True
                    for chunk in llm.create_chat_completion(messages=messages, **params):
                        delta = (
                            chunk.get("choices", [{}])[0]
                            .get("delta", {})
                            .get("content", "")
                        )
                        if delta:
                            _write({"type": "delta", "content": delta})
                    _write({"type": "done"})
                else:
                    params["stream"] = False
                    resp = llm.create_chat_completion(messages=messages, **params)
                    _write({"type": "result", "response": resp})
                continue

            _write({"type": "error", "where": "dispatch", "message": f"Unknown cmd: {cmd}"})

        except Exception as e:
            _write(
                {
                    "type": "error",
                    "where": cmd or "unknown",
                    "message": str(e),
                    "traceback": traceback.format_exc(limit=8),
                }
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())



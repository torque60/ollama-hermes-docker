#!/usr/bin/env python3
"""post_llm_call フック: アシスタント応答が「引継ぎ書」なら /vault に自動保存する。

小型ローカルモデルはファイル書込ツールを正しいタイミング/パスで呼べず不安定なので、
保存はモデルに頼らず Hermes の Shell Hook（＝コード）で決定論的に行う。

診断ログ付き: 毎回の発火内容を /opt/data/agent-hooks/hook.log に残す
（ホスト側 ./hermes-config/agent-hooks/hook.log）。原因切り分け用。
"""

import json
import re
import sys
import traceback
from pathlib import Path

VAULT_ROOT = Path("/vault/torishirabe")
LOG = Path("/opt/data/agent-hooks/hook.log")

# 引継ぎ書の見出し（半角/全角コロン両対応）。この行を保存対象の目印にする。
TITLE_RE = re.compile(r"^#\s*引継ぎ書\s*[:：]\s*(?P<name>.+?)\s*$", re.MULTILINE)

CANDIDATE_KEYS = ["assistant_response", "response", "message", "content", "text", "output"]


def log(msg: str) -> None:
    try:
        LOG.parent.mkdir(parents=True, exist_ok=True)
        with LOG.open("a", encoding="utf-8") as f:
            f.write(msg.rstrip() + "\n")
    except Exception:
        pass


def find_text(payload):
    """応答テキストを payload から探す（キー名の揺れ・一段の入れ子に対応）。"""
    if not isinstance(payload, dict):
        return "", "(payload-not-dict)"
    for key in CANDIDATE_KEYS:
        val = payload.get(key)
        if isinstance(val, str) and val.strip():
            return val, key
    for parent in ("extra", "data", "result"):
        sub = payload.get(parent)
        if isinstance(sub, dict):
            for key in CANDIDATE_KEYS:
                val = sub.get(key)
                if isinstance(val, str) and val.strip():
                    return val, f"{parent}.{key}"
    return "", "(not-found)"


def main() -> None:
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw) if raw.strip() else {}
    except Exception as e:
        log(f"[ERR] json parse: {e} raw_head={raw[:200]!r}")
        print("{}")
        return

    keys = list(payload.keys()) if isinstance(payload, dict) else type(payload).__name__
    text, src = find_text(payload)
    log(f"[FIRE] keys={keys} text_src={src} text_len={len(text)}")

    if not text:
        print("{}")
        return

    m = TITLE_RE.search(text)
    if not m:
        log(f"[SKIP] marker not found. text_head={text[:120]!r}")
        print("{}")
        return

    name = m.group("name").strip()
    # フォルダ名に使えない文字を除去（日本語・英数・空白・-._ は許可）
    safe = re.sub(r"[^\w\-. 　ぁ-んァ-ヶ一-龠]", "_", name).strip() or "project"
    doc = text[m.start():].rstrip() + "\n"
    out = VAULT_ROOT / safe / "引継ぎ書.md"
    try:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(doc, encoding="utf-8")
        log(f"[SAVED] {out} ({len(doc)} chars)")
    except Exception as e:
        log(f"[ERR] save failed: {e}\n{traceback.format_exc()}")

    print("{}")


if __name__ == "__main__":
    main()

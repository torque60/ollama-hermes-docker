#!/usr/bin/env python3
"""post_llm_call フック: アシスタント応答が「引継ぎ書」なら /vault に自動保存する。

小型ローカルモデルはファイル書込ツールを正しいタイミング/パスで呼べず不安定なので、
保存はモデルに頼らず Hermes の Shell Hook（＝コード）で決定論的に行う。

方針: payload のキー名に依存せず、payload 内の**全文字列を再帰的に走査**して
`# 引継ぎ書: <名>` を含む最長の文字列を本体とみなす（＝どこに入っていても拾える）。
診断ログを /opt/data/agent-hooks/hook.log に残す（ホスト ./hermes-config/agent-hooks/hook.log）。
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


def log(msg: str) -> None:
    try:
        LOG.parent.mkdir(parents=True, exist_ok=True)
        with LOG.open("a", encoding="utf-8") as f:
            f.write(msg.rstrip() + "\n")
    except Exception:
        pass


def iter_strings(obj):
    """payload を再帰的に辿って全ての文字列値を yield する。"""
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from iter_strings(v)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            yield from iter_strings(v)


def main() -> None:
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw) if raw.strip() else {}
    except Exception as e:
        log(f"[ERR] json parse: {e} raw_head={raw[:120]!r}")
        print("{}")
        return

    event = payload.get("hook_event_name") if isinstance(payload, dict) else None
    keys = list(payload.keys()) if isinstance(payload, dict) else type(payload).__name__
    extra = payload.get("extra") if isinstance(payload, dict) else None
    extrakeys = list(extra.keys()) if isinstance(extra, dict) else type(extra).__name__

    strings = list(iter_strings(payload))
    longest = max(strings, key=len, default="")
    log(
        f"[FIRE] event={event} topkeys={keys} extrakeys={extrakeys} "
        f"nstr={len(strings)} longest_len={len(longest)} longest_head={longest[:120]!r}"
    )

    # マーカーを含む最長の文字列を本体とみなす
    doc_src = ""
    for s in strings:
        if TITLE_RE.search(s) and len(s) > len(doc_src):
            doc_src = s

    if not doc_src:
        log("[SKIP] marker not found in any string")
        print("{}")
        return

    m = TITLE_RE.search(doc_src)
    name = m.group("name").strip()
    safe = re.sub(r"[^\w\-. 　ぁ-んァ-ヶ一-龠]", "_", name).strip() or "project"
    doc = doc_src[m.start():].rstrip() + "\n"
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

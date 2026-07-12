"""handoff-saver: 引継ぎ書を /vault に自動保存する Hermes プラグイン。

Shell フックは応答本文を受け取れない（公式docs+実測で確認）。応答本文
`assistant_response` に触れられるのは Python プラグインの post_llm_call だけ
（fire-and-forget＝返り値無視で出力を壊さない）。ここでその本文を受け取り、
「# 引継ぎ書: <名>」で始まっていれば /vault/torishirabe/<名>/引継ぎ書.md に保存する。

小型ローカルモデルにファイル書込ツールを頼らず、保存を決定論的にコード側で行う。
"""

import re
from pathlib import Path

VAULT_ROOT = Path("/vault/torishirabe")
LOG = Path("/opt/data/plugins/handoff-saver/plugin.log")

# 引継ぎ書の見出し（半角/全角コロン両対応）。この行を保存対象の目印にする。
TITLE_RE = re.compile(r"^#\s*引継ぎ書\s*[:：]\s*(?P<name>.+?)\s*$", re.MULTILINE)

_TEXT_KEYS = ("assistant_response", "response", "response_text", "text")


def _log(msg: str) -> None:
    try:
        LOG.parent.mkdir(parents=True, exist_ok=True)
        with LOG.open("a", encoding="utf-8") as f:
            f.write(msg.rstrip() + "\n")
    except Exception:
        pass


def _extract_text(args, kwargs) -> str:
    # まず既知のキーワード名で探す
    for k in _TEXT_KEYS:
        v = kwargs.get(k)
        if isinstance(v, str) and v.strip():
            return v
    # 位置引数で来た場合は、最も長い文字列を本文とみなす（response が最長のはず）
    strs = [a for a in args if isinstance(a, str) and a.strip()]
    if strs:
        return max(strs, key=len)
    return ""


def _save(text: str) -> None:
    m = TITLE_RE.search(text) if text else None
    if not m:
        _log(f"[SKIP] no marker. len={len(text)} head={text[:80]!r}")
        return
    name = m.group("name").strip()
    safe = re.sub(r"[^\w\-. 　ぁ-んァ-ヶ一-龠]", "_", name).strip() or "project"
    doc = text[m.start():].rstrip() + "\n"
    out = VAULT_ROOT / safe / "引継ぎ書.md"
    try:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(doc, encoding="utf-8")
        _log(f"[SAVED] {out} ({len(doc)} chars)")
    except Exception as e:  # 保存失敗しても会話は止めない
        _log(f"[ERR] save failed: {e}")


def on_post_llm_call(*args, **kwargs) -> None:
    text = _extract_text(args, kwargs)
    _log(
        f"[FIRE] argtypes={[type(a).__name__ for a in args]} "
        f"kwargs={list(kwargs.keys())} text_len={len(text)}"
    )
    _save(text)


def register(ctx) -> None:
    ctx.register_hook("post_llm_call", on_post_llm_call)

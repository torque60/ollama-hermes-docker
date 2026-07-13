"""handoff-saver: 引継ぎ書を /vault に自動保存する Hermes プラグイン。

捕捉点 = plugin フック `transform_llm_output`。
  def cb(response_text, session_id, model, platform, **kwargs) -> str | None
  response_text にアシスタントのそのターンの最終応答本文が入る（公式docs明記）。
  毎ターン、ツールループ後・配信前に発火。None を返せば出力は素通し（fire-and-forget）。

なぜ transform_llm_output なのか（経緯）:
  - shell フックは envelope のみで応答本文を受け取れない。
  - plugin の post_llm_call / pre_llm_call は VALID_HOOKS に載るだけで本体未実装
    （NousResearch/hermes-agent #2817）＝発火しない。当初これを掴んで詰まった。
  - transform_llm_output は #2817 の対象外で、transform 系は実装済み。ここが正解。

小型ローカルモデルにファイル書込やツール呼び出しを頼らず、応答本文を受け取って
「# 引継ぎ書: <名>」を検知したら /vault/torishirabe/<名>/引継ぎ書.md に決定論的に保存する。
"""

import re
from pathlib import Path

VAULT_ROOT = Path("/vault/torishirabe")
LOG = Path("/opt/data/plugins/handoff-saver/plugin.log")

# 「# 引継ぎ書: <名>」を保存対象の目印にする（半角/全角コロン両対応）。
TITLE_RE = re.compile(r"^#\s*引継ぎ書\s*[:：]\s*(?P<name>.+?)\s*$", re.MULTILINE)


def _log(msg: str) -> None:
    try:
        LOG.parent.mkdir(parents=True, exist_ok=True)
        with LOG.open("a", encoding="utf-8") as f:
            f.write(msg.rstrip() + "\n")
    except Exception:
        pass


def _safe(name: str) -> str:
    cleaned = re.sub(r"[^\w\-. 　ぁ-んァ-ヶ一-龠]", "_", name).strip()
    return cleaned or "project"


def _save(text: str) -> None:
    m = TITLE_RE.search(text) if text else None
    if not m:
        _log(f"[SKIP] no marker. len={len(text)}")
        return
    name = m.group("name").strip()
    # マーカー行から末尾までを引継ぎ書本文として保存
    doc = text[m.start():].rstrip() + "\n"
    out = VAULT_ROOT / _safe(name) / "引継ぎ書.md"
    try:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(doc, encoding="utf-8")
        _log(f"[SAVED] {out} ({len(doc)} chars) name={name!r}")
    except Exception as e:  # 保存失敗しても会話は止めない
        _log(f"[ERR] save failed: {e}")


def on_llm_output(*args, **kwargs):
    """transform_llm_output コールバック。応答本文を受け取り、マーカーがあれば保存。

    署名は cb(response_text, session_id, model, platform, **kwargs) だが、
    位置/キーワードどちらで渡されても拾えるよう防御的に取り出す。
    出力は一切変更しない（None を返す）。
    """
    text = kwargs.get("response_text")
    if not isinstance(text, str) or not text.strip():
        # 位置引数で来た場合は最初の非空文字列を本文とみなす
        for a in args:
            if isinstance(a, str) and a.strip():
                text = a
                break
    text = text if isinstance(text, str) else ""
    _log(f"[FIRE] transform_llm_output len={len(text)} nargs={len(args)} kwargs={list(kwargs.keys())}")
    _save(text)
    return None  # 出力は素通し（fire-and-forget）


def register(ctx) -> None:
    ctx.register_hook("transform_llm_output", on_llm_output)
    _log("[REGISTER] transform_llm_output registered")

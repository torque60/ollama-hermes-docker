#!/usr/bin/env python3
"""save_handoff.py — Hermes の会話ストア(state.db)から引継ぎ書を確定回収する。

なぜこれか（重要）:
  Hermes では応答本文をフックで横取りできない（shell フックは envelope のみ、
  plugin の post_llm_call は本体未実装＝NousResearch/hermes-agent #2817）。
  確実なのは「Hermes が /opt/data に永続化した会話」を後から読むこと。
  = モデルがツールを呼ぼうが呼ぶまいが、対話さえ済めば必ず回収できる（モデル完全非依存）。

やること:
  state.db(SQLite) の全テーブル・全テキストセルを走査し、「# 引継ぎ書: <名>」で
  始まるブロックを見つけて vault/torishirabe/<名>/引継ぎ書.md に保存する。
  会話が JSON blob や zlib 圧縮で入っていても best-effort で復元する。
  マーカーが見つからなければ、代わりにテーブル構造を出して次の手がかりにする。

使い方（ホスト側・リポジトリ直下で。Hermes を exit した後に実行）:
  python3 scripts/save_handoff.py
  python3 scripts/save_handoff.py --db hermes-config/state.db --vault vault
  python3 scripts/save_handoff.py --debug     # 構造ダンプのみ
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
import zlib
from pathlib import Path

# 「# 引継ぎ書: <名>」。半角/全角コロン両対応。行頭アンカーは使わない
# （JSON 内で \n がエスケープされている場合に備え、行頭でなくてもマーカーを拾う）。
MARKER_RE = re.compile(r"#\s*引継ぎ書\s*[:：]\s*(?P<name>[^\n\\]+)")


def _safe(name: str) -> str:
    cleaned = re.sub(r"[^\w\-. 　ぁ-んァ-ヶ一-龠]", "_", name).strip()
    return cleaned or "project"


def _iter_text_cells(db: sqlite3.Connection):
    """(table, column, text) を全部返す。bytes は utf-8 / zlib 復元を試みる。"""
    cur = db.cursor()
    tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'")]
    for t in tables:
        try:
            cols = [c[1] for c in cur.execute(f'PRAGMA table_info("{t}")')]
            rows = cur.execute(f'SELECT * FROM "{t}"').fetchall()
        except sqlite3.Error:
            continue
        for row in rows:
            for col, val in zip(cols, row):
                text = _to_text(val)
                if text:
                    yield t, col, text


def _to_text(val) -> str | None:
    if isinstance(val, str):
        return val
    if isinstance(val, bytes):
        # まず素の utf-8、ダメなら zlib 解凍 → utf-8
        try:
            return val.decode("utf-8")
        except UnicodeDecodeError:
            try:
                return zlib.decompress(val).decode("utf-8", "ignore")
            except Exception:
                return None
    return None


def _extract_blocks(text: str) -> list[tuple[str, str]]:
    """text 内の (name, block) を全部返す。JSON エスケープされた \\n は実改行へ戻す。"""
    out: list[tuple[str, str]] = []
    for m in MARKER_RE.finditer(text):
        name = m.group("name").strip().strip('"').strip()
        block = text[m.start():]
        # JSON 由来のエスケープを可能な範囲で復元（本物の改行が無く \n だらけなら復元）
        if "\\n" in block and block.count("\n") < 3:
            block = block.encode().decode("unicode_escape", "ignore")
        # 次のメッセージ境界っぽい所で軽く切る（JSON の "} 等）。無ければ全部。
        block = re.split(r'"\s*[,}]\s*"role"', block)[0]
        out.append((name, block.rstrip()))
    return out


def _debug_dump(db: sqlite3.Connection) -> None:
    cur = db.cursor()
    tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'")]
    print(f"TABLES ({len(tables)}): {tables}")
    for t in tables:
        try:
            n = cur.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
            cols = [c[1] for c in cur.execute(f'PRAGMA table_info("{t}")')]
        except sqlite3.Error as e:
            print(f"  {t}: <error {e}>")
            continue
        print(f"  {t}: rows={n} cols={cols}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", default="hermes-config/state.db", help="Hermes state.db のパス")
    ap.add_argument("--vault", default="vault", help="vault ルート（torishirabe/ を掘る）")
    ap.add_argument("--debug", action="store_true", help="テーブル構造をダンプして終了")
    args = ap.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        print(f"[ERR] state.db が見つからない: {db_path}", file=sys.stderr)
        print("      Hermes を一度でも起動した環境で、リポジトリ直下から実行してください。", file=sys.stderr)
        return 2

    # 読み取り専用で開く（TUI 実行中でもロックで落ちないように）
    db = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)

    if args.debug:
        _debug_dump(db)
        return 0

    # 全セルからマーカーを収集。最長のブロック＝完成版とみなす。
    candidates: list[tuple[str, str, str, str]] = []  # (name, block, table, col)
    for t, c, text in _iter_text_cells(db):
        if "引継ぎ書" not in text:
            continue
        for name, block in _extract_blocks(text):
            candidates.append((name, block, t, c))

    if not candidates:
        print("[MISS] 「# 引継ぎ書:」を state.db から発見できませんでした。")
        print("       会話がまだ無い / 形式が想定外の可能性。構造を出します:\n")
        _debug_dump(db)
        print("\n（この出力を貼ってくれれば抽出ロジックを合わせます）")
        return 1

    # プロジェクト名ごとに最長ブロックを採用
    best: dict[str, tuple[str, str, str]] = {}
    for name, block, t, c in candidates:
        if name not in best or len(block) > len(best[name][0]):
            best[name] = (block, t, c)

    vault_root = Path(args.vault) / "torishirabe"
    saved = []
    for name, (block, t, c) in best.items():
        out = vault_root / _safe(name) / "引継ぎ書.md"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(block.rstrip() + "\n", encoding="utf-8")
        saved.append(out)
        print(f"[SAVED] {out}  ({len(block)} chars, from {t}.{c})")

    print(f"\n完了: {len(saved)} 件保存。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

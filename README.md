# 要件定義サポートAI — Ollama + Hermes Agent (Docker Compose)

WSL2 + Docker 環境で、**Ollama（常駐）＋ Hermes Agent（CLI/TUI）** を動かす構成。
初学者が Hermes と対話（取り調べ）して要件を固め、引継ぎ書をローカルで作るためのキット。

対話は **Hermes を CLI/TUI で直接使う**（スキル `/n-torishirabe` 等はこの経路で発火する）。
設計方針: Ollama も Hermes も**公式ビルド済みイメージを使う**ので Dockerfile 不要。`image:` を並べるだけ。

---

## 前提

- WSL 上の Docker が使えること（`docker --version` が通る）
  - Docker Desktop の WSL integration 有効、または WSL 内に Docker Engine 導入済み

---

## ステップ1: Ollama を起動

このフォルダで:

```bash
docker compose up -d
```

起動確認:

```bash
curl http://localhost:11434
# → "Ollama is running" と返ればOK
```

---

## ステップ2: モデルを入れて動作確認

最初は軽いモデルで疎通確認するのがおすすめ:

```bash
# モデルをダウンロード（コンテナ内の ollama コマンドを実行）
docker compose exec ollama ollama pull qwen3.5:0.8b

# 対話で試す
docker compose exec -it ollama ollama run qwen3.5:0.8b
```

API 経由でも確認（Hermes連携時はこの形を使う）:

```bash
curl http://localhost:11434/api/generate -d '{
  "model": "qwen3.5:0.8b",
  "prompt": "こんにちは",
  "stream": false
}'
```

---

## ステップ3: GPU（本キットは既定で有効）

既定モデル（gemma 12B）を実用速度で動かすため、`compose.yaml` の `ollama:` 内の `deploy:` ブロック
（NVIDIA GPU 割当）は**最初からコメントが外れて有効**になっています。GPU を使うなら、その
`deploy:` ブロックの**コメントが外れている（有効）ことを確認**するだけでOK。**前提**:

1. Windows側にWSL対応のNVIDIAドライバ
2. WSL 内に `nvidia-container-toolkit` を導入 → Docker再起動（→ `docker compose up -d`）

> **GPU が無い／使わない環境**では、`deploy:` ブロックを**コメントアウト**してから `up` すること
> （有効のままだと起動に失敗する）。その場合 12B は重いので、`config.yaml` の `model.default` を
> 軽いモデル（例: `qwen3.5:4b`）に変えるとよい。

---

## ステップ4: Hermes Agent と対話する（TUI）

hermes は常駐させず、`docker compose run` で**その都度1プロセスだけ**起こす（hermes を
2つ同時に動かすと `/opt/data` のセッション/メモリが競合するため）。`--rm` で毎回破棄しても、
skills・memory・生成物は `./hermes-config`(=/opt/data マウント)に残る:

```bash
docker compose up -d                       # ollama だけ常駐
docker compose run --rm -it hermes bash    # hermes を1個起こして入る
hermes --tui                               # 対話TUI
# 一発でTUIに入るなら:
docker compose run --rm -it hermes --tui
```

接続先モデルは `hermes-config/config.yaml` の `model.default` で指定（既定はローカル Ollama の
モデル、`base_url: http://ollama:11434/v1`）。事前に Ollama 側へ pull しておくこと:

```bash
docker compose exec ollama ollama pull <モデル名>
```

### スキル（/n-torishirabe など）

- Hermes のスキルは `SKILL.md`（Markdown）。ホスト `./hermes-config/skills/<name>/SKILL.md`
  （= コンテナ `/opt/data/skills/`）に置くと、`/<name>` スラッシュコマンドとして自動登録される。
- 同梱スキル: **`/n-torishirabe`**（通常口調）、**`/torishirabe`**（同ロジックの刑事口調）、
  **`/e-torishirabe`**（同ロジック・SKILL.md の指示文だけ英語／応答・成果物は日本語）。
- 進め方：**1問ずつ**、各問に**番号つき選択肢（`1.`/`2.`/`3.`）＋ ★推奨と一言理由**を出す（本人は番号でも自由回答でも可）→
  **腑に落ちるまで同じ点を繰り返し掘る**（共通理解に達するまで先へ進まない）。**技術選定も実装もしない**（それはクラウドの仕事）。
  **ゴールは引継ぎ書の作成そのもの**（本人と合意してから作り、そこで終わり。実装はクラウドAIへ渡す）。
- 成果物はファイルに書く：1問ごとに **`決定ログ.md`** へ逐次追記し、最後に
  **`引継ぎ書.md`**（`# 引継ぎ書: <名>` で始まる全文）を書き出す。これをクラウドAI（Claude Code / Codex 等）へ渡す。
- 書込先は **`/opt/data/vault/torishirabe/<プロジェクト名>/`**（作業領域 `/opt/data` 配下＝file ツールが許可する場所。
  root 直下の `/vault` は "保護" 判定で拒否される）。compose で **`./vault:/opt/data/vault`** を割り当てているので、
  host 側は別フォルダ `./vault` に残る。
  ※モデル自身にファイル書込を委ねる方式で、**ローカル小型モデルでは書き漏らしが起こり得る**。フック/プラグインによる決定論的自動保存は
  Hermes では実現できなかった（顛末と将来のAPI層プロキシ案は `docs/DESIGN-AND-STATUS.md`）。スキル編集は即反映（再ビルド不要）。

---

## よく使うコマンド

```bash
docker compose ps                    # 状態確認
docker compose logs -f ollama        # ログ
docker compose exec ollama ollama list   # 入っているモデル一覧
docker compose stop                  # 停止（コンテナは残す）
docker compose start                 # 再開
docker compose down                  # 停止＆コンテナ削除（ボリューム=モデルは残る）
docker compose down -v               # ボリュームごと削除（モデルも消える）
```

---

## メモ

- **接続先は `http://ollama:11434`**（Compose内のサービス名で解決）。`localhost` は各コンテナ内で別物なので不可。
- **モデルは `ollama_data` ボリュームに永続化**。`down` してもモデルは残る（`down -v` で消える）。
- OllamaのOpenAI互換APIは `/v1` 付き（`http://ollama:11434/v1`）。Hermesからはこちらを使う。

### 参考（公式）

- Ollama — Docker Hub: https://hub.docker.com/r/ollama/ollama
- Hermes Agent: https://github.com/NousResearch/hermes-agent
- Docker Compose networking: https://docs.docker.com/compose/networking/

---

## ライセンス / クレジット

### このリポジトリ（MIT）

**自作の成果物のみ** MIT License（[LICENSE](./LICENSE)）で公開しています。対象は
`compose.yaml`・`README.md`・`hermes-config/config.yaml`・自作スキル（`hermes-config/skills/` の
`n-torishirabe` / `torishirabe` / `e-torishirabe`）など、このリポジトリに含まれるファイルです。

> ⚠️ **「キット全体がMIT」ではありません。** 起動時に取得する各コンテナイメージ・モデルは、
> それぞれ別のライセンス／利用規約に従います（下表）。

`n-torishirabe` / `torishirabe` / `e-torishirabe` は [mattpocock/skills](https://github.com/mattpocock/skills)
（MIT License, Copyright (c) Matt Pocock）の `grilling` / `grill-with-docs` に
**着想を得た日本語のオリジナル**です（逐語コピーではありません）。

### 起動時に取得する第三者構成物（THIRD-PARTY）

本キットは以下を **`image:` 参照／実行時 pull で取得するだけ**で、バイナリ・ソース・モデル重みを
**同梱していません**。各構成物のライセンス／規約は取得元に従います。

| 構成物 | ライセンス / 規約 | 備考 |
|---|---|---|
| Ollama | MIT | — |
| Hermes Agent (Nous Research) | MIT | Powered by Nous Research Hermes Agent |
| 利用モデル（既定: Google Gemma 系） | **Gemma 利用規約（非OSS）** | 下記の用途制限が**常時適用**。利用者自身での確認・遵守が必要 |

### 利用モデルの規約（重要）

既定の利用モデルは Google Gemma 系です。**教育・研究用途であっても**、以下が常時適用されます。
利用前に必ず確認してください。

- Gemma Terms of Use: https://ai.google.dev/gemma/terms
- Gemma Prohibited Use Policy: https://ai.google.dev/gemma/prohibited_use_policy

別のモデル（例: Qwen 系）に変更する場合は、そのモデル固有のライセンス（Apache-2.0 や
Qianwen License 等、モデルにより異なる）を別途確認してください。

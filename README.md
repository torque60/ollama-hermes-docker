# Ollama + (将来)Hermes Agent — Docker Compose

WSL2 + Docker 環境で、まず **Ollama 単体** を起動するための構成。
将来 **Hermes Agent** を足せるよう、`docker-compose.yml` に下準備済み。

設計方針: Ollama も Hermes も**公式ビルド済みイメージを使う**ので、Dockerfile は不要。
`image:` を並べるだけで動く。

---

## 前提

- WSL 上の Docker が使えること（`docker --version` が通る）
  - Docker Desktop の WSL integration 有効、または WSL 内に Docker Engine 導入済み

---

## ステップ1: Ollama を起動（まずはCPUで確実に）

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

## ステップ3（任意）: GPUを有効化

GPUがあると大きいモデルが実用速度になる。**先にWSL2側の準備が必要**:

1. Windows側にWSL対応のNVIDIAドライバ
2. WSL 内に `nvidia-container-toolkit` を導入 → Docker再起動

準備後、`docker-compose.yml` の `ollama:` 内にある `deploy:` ブロックのコメントを外して:

```bash
docker compose up -d
```

> まずCPU（ステップ1〜2）で疎通 → 動いたらGPUを足す、の順がハマりにくい。

---

## ステップ4（将来）: Hermes Agent を足す

1. `docker-compose.yml` の `hermes:` ブロックのコメントを外す
2. このフォルダに `hermes-config/config.yaml` を作成:

   ```yaml
   model:
     default: qwen2.5-coder:32b          # tool-calling 対応モデル
     provider: custom
     base_url: http://ollama:11434/v1     # ★ localhost ではなくサービス名 ollama + /v1
     context_length: 64000                # Hermesはツール呼び出しに64k以上を要求
   ```

3. 連携元のモデルをOllamaに入れておく:

   ```bash
   docker compose exec ollama ollama pull qwen2.5-coder:32b
   ```

4. Hermesは対話CLI/TUIなので、常駐ではなく run で起動:

   ```bash
   docker compose run --rm hermes hermes --tui
   ```

### スキルのカスタマイズ（Hermes本体は触らない）

- Hermesのスキルは `SKILL.md`（Markdown）で、`~/.hermes/skills/` に置くだけ。
- 上記の `./hermes-config:/root/.hermes` マウントにより、ホスト側 `./hermes-config/skills/` を
  好きなエディタで編集 → コンテナ内で即反映・テストできる（コンテナ再ビルド不要）。

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
`grill` / `torishirabe`）など、このリポジトリに含まれるファイルです。

> ⚠️ **「キット全体がMIT」ではありません。** 起動時に取得する各コンテナイメージ・モデルは、
> それぞれ別のライセンス／利用規約に従います（下表）。

`grill` / `torishirabe` は [mattpocock/skills](https://github.com/mattpocock/skills)
（MIT License, Copyright (c) Matt Pocock）の `grilling` / `grill-with-docs` に
**着想を得た日本語のオリジナル**です（逐語コピーではありません）。

### 起動時に取得する第三者構成物（THIRD-PARTY）

本キットは以下を **`image:` 参照／実行時 pull で取得するだけ**で、バイナリ・ソース・モデル重みを
**同梱していません**。各構成物のライセンス／規約は取得元に従います。

| 構成物 | ライセンス / 規約 | 備考 |
|---|---|---|
| Ollama | MIT | — |
| Hermes Agent (Nous Research) | MIT | Powered by Nous Research Hermes Agent |
| Open WebUI | 独自ライセンス（BSD系＋ブランディング保持条項） | **"Open WebUI" のロゴ・名称を除去/改変しないこと**（未改変の公式イメージ利用なら充足）。除去改変は直近30日で実ユーザー50人超の場合、権利者の書面許可またはエンタープライズライセンスが必要 |
| 利用モデル（既定: Google Gemma 系） | **Gemma 利用規約（非OSS）** | 下記の用途制限が**常時適用**。利用者自身での確認・遵守が必要 |

### 利用モデルの規約（重要）

既定の利用モデルは Google Gemma 系です。**教育・研究用途であっても**、以下が常時適用されます。
利用前に必ず確認してください。

- Gemma Terms of Use: https://ai.google.dev/gemma/terms
- Gemma Prohibited Use Policy: https://ai.google.dev/gemma/prohibited_use_policy

別のモデル（例: Qwen 系）に変更する場合は、そのモデル固有のライセンス（Apache-2.0 や
Qianwen License 等、モデルにより異なる）を別途確認してください。

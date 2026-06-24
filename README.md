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
docker compose exec ollama ollama pull llama3.2:1b

# 対話で試す
docker compose exec -it ollama ollama run llama3.2:1b
```

API 経由でも確認（Hermes連携時はこの形を使う）:

```bash
curl http://localhost:11434/api/generate -d '{
  "model": "llama3.2:1b",
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

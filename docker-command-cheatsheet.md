# Docker コマンド早見表

よく使う Docker / Docker Compose コマンドの一覧。
各コマンドは「1行 + 簡潔な説明 + 主なオプション/引数の説明」。`<...>` は自分の値に置き換える。

---

## イメージ（image）

```bash
docker pull <image>
```
イメージをDocker Hub等から取得する。
- `<image>` : イメージ名。`名前:タグ` 形式（例 `ollama/ollama:latest`）。タグ省略時は `:latest`。

```bash
docker images
```
ローカルにあるイメージ一覧を表示する。
- `-a` : 中間レイヤのイメージも含めて表示。
- `-q` : イメージIDだけを表示（スクリプト向け）。

```bash
docker build -t <name>:<tag> .
```
Dockerfile からイメージをビルドする。
- `-t <name>:<tag>` : 作るイメージに名前とタグを付ける。
- `.` : ビルドコンテキスト（Dockerfileや関連ファイルがある場所）。通常はカレント。
- `-f <path>` : Dockerfileの場所を明示指定（名前が `Dockerfile` でない時）。

```bash
docker rmi <image>
```
イメージを削除する。
- `-f` : 使用中でも強制削除。

---

## コンテナ起動（run）

```bash
docker run <image>
```
イメージからコンテナを起動する。ローカルに無ければ自動でpull。
- `<image>` : 起動元イメージ。末尾に実行コマンドを足すと既定コマンドを上書きできる。

```bash
docker run -d <image>
```
バックグラウンド（detached）で起動する。常駐サーバ向け。
- `-d` : 端末を占有せず裏で動かす。起動するとコンテナIDを返す。

```bash
docker run -it <image> bash
```
対話モードで起動しコンテナ内シェルに入る。
- `-i` : 標準入力を開いたままにする（入力を受け付ける）。
- `-t` : 疑似端末(TTY)を割り当てる（プロンプト表示）。
- `bash` : 実行するコマンド。`sh` の場合もある。

```bash
docker run --rm <image>
```
コンテナ終了時に自動削除する。使い捨てのテスト実行向け。
- `--rm` : 停止と同時にコンテナを消す。ゴミが残らない。

```bash
docker run -p 8080:80 <image>
```
ポートを繋ぐ。
- `-p <ホスト>:<コンテナ>` : 左がホスト側ポート、右がコンテナ側。例は ホスト8080→コンテナ80。
- `-p 127.0.0.1:8080:80` : 接続元をローカルのみに限定（先頭にIP）。

```bash
docker run -v <vol>:/path <image>
```
ボリューム/フォルダをマウントしデータを永続化・共有する。
- `-v <名前orホストパス>:<コンテナ内パス>` : 左が名前付きボリューム名 or ホストの実パス、右がコンテナ内のマウント先。
- `:ro` を末尾に付ける（`-v data:/path:ro`）と読み取り専用。

```bash
docker run --name <name> <image>
```
コンテナに名前を付ける。後の操作で名前指定でき楽。
- `--name <name>` : 任意の固定名。省略すると自動生成名になる。

```bash
docker run --gpus all <image>
```
GPUをコンテナから使えるようにする。nvidia-container-toolkit が前提。
- `--gpus all` : 全GPUを割り当て。
- `--gpus '"device=0"'` : 特定GPU(0番)だけ割り当て。

```bash
docker run -d -p 11434:11434 -v ollama_data:/root/.ollama --name ollama ollama/ollama
```
（実例）上記オプションの組み合わせ。裏で起動＋ポート公開＋永続化＋名前付け。

---

## コンテナ管理

```bash
docker ps
```
実行中のコンテナ一覧を表示する。
- `-a` : 停止中も含む全コンテナ。
- `-q` : コンテナIDだけ表示。
- `-l` : 直近に作られた1個だけ表示。

```bash
docker stop <container>
```
実行中コンテナを正常停止する。
- `<container>` : コンテナ名 or ID（先頭数文字でOK）。
- `-t <秒>` : 強制終了までの猶予秒数（既定10秒）。

```bash
docker start <container>
```
停止中コンテナを再開する。
- `-a` : 出力を端末に接続（attach）して起動。

```bash
docker restart <container>
```
コンテナを再起動する（stop + start）。
- `-t <秒>` : 停止時の猶予秒数。

```bash
docker rm <container>
```
停止中コンテナを削除する。
- `-f` : 実行中でも強制削除（内部でstop）。
- `-v` : そのコンテナに紐づく匿名ボリュームも削除。

```bash
docker exec -it <container> bash
```
実行中コンテナ内でシェルを開く。調査・操作に使う。
- `-i` / `-t` : run と同じ（入力維持 / TTY割当）。
- `-u <user>` : 実行ユーザー指定（例 `-u root`）。
- `-w <dir>` : 作業ディレクトリ指定。

```bash
docker exec <container> <command>
```
実行中コンテナ内で任意コマンドを1回実行する。
- `<command>` : 例 `ollama list`。`-it` 無しなので非対話の単発実行向け。

---

## ログ・調査

```bash
docker logs <container>
```
コンテナの標準出力ログを表示する。
- `--tail <n>` : 末尾n行だけ表示。
- `-t` : 各行にタイムスタンプを付ける。

```bash
docker logs -f <container>
```
ログをリアルタイム追従表示する。Ctrl+Cで抜ける。
- `-f` : follow（新しいログを流し続ける）。
- `--since <time>` : 指定時刻/期間以降のみ（例 `--since 10m`）。

```bash
docker inspect <container>
```
コンテナ/イメージの詳細設定をJSONで表示する。
- `-f '<template>'` : 特定項目だけ抽出（例 `-f '{{.NetworkSettings.IPAddress}}'`）。

```bash
docker stats
```
各コンテナのCPU/メモリ使用量をリアルタイム表示する。
- `--no-stream` : 更新せず現在値を1回だけ表示。
- `<container>` : 指定すればそのコンテナのみ。

---

## Docker Compose

```bash
docker compose up -d
```
compose.yml の全サービスをバックグラウンド起動する。
- `-d` : 裏で起動。
- `--build` : 起動前にイメージを再ビルド。
- `<service>` : サービス名を付けるとそれだけ起動。

```bash
docker compose down
```
起動中サービスを停止しコンテナを削除する。ボリュームは残る。
- `--rmi all` : 使ったイメージも削除。
- `--remove-orphans` : compose定義から消えた古いコンテナも掃除。

```bash
docker compose down -v
```
コンテナに加えてボリュームも削除する。
- `-v` : 名前付きボリュームも消す（**データ消失に注意**）。

```bash
docker compose ps
```
compose で起動中のサービス一覧と状態を表示する。
- `-a` : 停止中のサービスも含む。

```bash
docker compose logs -f
```
全サービスのログをまとめて追従表示する。
- `-f` : follow。
- `--tail <n>` : 末尾n行から表示。
- `<service>` : 指定でそのサービスのみ。

```bash
docker compose exec <service> <command>
```
指定サービスのコンテナ内でコマンドを実行する。
- `<service>` : compose.yml のサービス名（コンテナ名ではない）。
- `-T` : TTYを無効化（スクリプトやパイプで使う時）。

```bash
docker compose restart <service>
```
特定サービスだけ再起動する（他は止めない）。
- `<service>` : 省略すると全サービス再起動。

```bash
docker compose build
```
compose 内の `build:` 指定サービスのイメージを再ビルドする。
- `--no-cache` : キャッシュを使わず一から作り直す。

---

## クリーンアップ（容量整理）

```bash
docker system df
```
イメージ/コンテナ/ボリュームの使用容量を表示する。
- `-v` : 個別の内訳まで詳細表示。

```bash
docker container prune
```
停止中のコンテナをまとめて削除する。
- `-f` : 確認プロンプトをスキップ。

```bash
docker image prune
```
使われていない不要イメージを削除する。
- `-a` : どのコンテナにも使われていないイメージを全部（dangling以外も）。
- `-f` : 確認スキップ。

```bash
docker volume prune
```
どこからも使われていないボリュームを削除する。**データ消失に注意**。
- `-f` : 確認スキップ。

```bash
docker system prune
```
不要なコンテナ・ネットワーク・danglingイメージを一括削除する。
- `-a` : 未使用イメージも全部削除。
- `--volumes` : 未使用ボリュームも削除。
- `-f` : 確認スキップ。

---

## GPU 確認

```bash
docker run --rm --gpus all ubuntu nvidia-smi
```
GPUがコンテナから見えるかをテストする。一覧が出れば成功（toolkit導入済みが前提）。
- `--rm` : テスト後に自動削除。
- `--gpus all` : 全GPUを割り当て。
- `ubuntu` : 軽量テスト用イメージ（`nvidia-smi`はtoolkitが注入するのでCUDAイメージ不要）。
- `nvidia-smi` : コンテナ内で実行するGPU状態表示コマンド。

---

## メモ

- `<container>` はコンテナ名でもID（先頭数文字でOK）でも指定できる。
- ホスト⇄コンテナの`-p`、データ永続化の`-v` は特に重要。
- 多くのコマンドで `-f` は文脈で意味が違う（`logs -f`=follow / `rm -f`=強制 / `prune -f`=確認スキップ）。
- 迷ったら `docker <command> --help` で公式ヘルプを確認できる。

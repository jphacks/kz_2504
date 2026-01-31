# プッシュ失敗（HTTP 400 / 108MB）の直し方

動画とフレーム画像を**直前のコミットから外して**、軽い内容だけプッシュし直す手順です。

---

## 1. 直近のコミットを取り消す（ファイルは残す）

```bash
cd /Users/naminami/Desktop/kz_2504
git reset --soft HEAD~1
```

※ これで「直前のコミット」がなくなり、変更はすべてステージされたままになります。

---

## 2. 大きなファイルだけステージから外す

```bash
git reset HEAD connotation_tools_v3/frames/
git reset HEAD "connotation_tools_v3/videos/ワイルドスピード・ファイヤーブースト.mp4"
```

※ ディスク上のファイルはそのまま。Git の管理対象から外すだけです。

---

## 3. .gitignore をコミットに含める

```bash
git add .gitignore
```

※ `.gitignore` に `frames/` と `videos/*.mp4` を追加済みなので、今後これらは追跡されません。

---

## 4. 再度コミットしてプッシュ

```bash
git commit -m "connotation_tools_v3: エディタ・実行手順・test2(150秒)・トークン設定ドキュメント、動画・framesはgitignore"
git push origin v3_demo
```

※ 動画と frames を含まないので、プッシュサイズが小さくなり通常は成功します。

---

## 補足

- **動画**と **frames/** はローカルに残ります。Git には上げず、必要なら別手段（Google Drive 等）で共有してください。
- どうしてもリポジトリに入れたい場合は **Git LFS** の利用を検討してください。

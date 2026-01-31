# GitHub トークン設定のしかた

HTTPS で `git push` するときに、ユーザー名＋**Personal Access Token（PAT）**で認証する方法です。

---

## 1. GitHub でトークンを作る

1. **GitHub にログイン** → 右上のアイコン → **Settings**
2. 左メニュー最下部の **Developer settings**
3. **Personal access tokens** → **Tokens (classic)** または **Fine-grained tokens**
4. **Generate new token**（Classic の場合は **Generate new token (classic)**）
5. **Note**: 用途メモ（例: `kz_2504 push`）
6. **Expiration**: 有効期限（90日 / 1年 / No expiration など）
7. **Select scopes**: 少なくとも **repo** にチェック（リポジトリの読み書き）
8. **Generate token** をクリック
9. 表示されたトークン（`ghp_xxxx...`）を**一度だけ**コピーして安全な場所に控える（あとから再表示できない）

---

## 2. トークンでプッシュする（毎回聞かれる）

リポジトリのルートで:

```bash
cd /Users/naminami/Desktop/kz_2504
git push origin v3_demo
```

- **Username**: あなたの GitHub のユーザー名
- **Password**: パスワードではなく、さきほど作った**トークン**を貼り付け

これでプッシュできます。

---

## 3. トークンを覚えさせておく（毎回入力しない）

### 方法A: 認証情報ヘルパー（おすすめ）

Mac なら「キーチェーン」に保存されます。

```bash
git config --global credential.helper osxkeychain
```

次回 `git push` でユーザー名＋トークンを入力すると、以降は自動で使われます。

### 方法B: URL にトークンを含める（非推奨・漏れ注意）

リモートを次のように変更（`YOUR_USERNAME` と `YOUR_TOKEN` を実際の値に置き換え）:

```bash
git remote set-url origin https://YOUR_USERNAME:YOUR_TOKEN@github.com/jphacks/kz_2504.git
```

トークンが履歴や設定に残るため、共有PCでは避けた方が安全です。

### 方法C: SSH キーを使う

HTTPS ではなく SSH でプッシュする方法です。

1. SSH キーを生成（既にあればスキップ）:
   ```bash
   ssh-keygen -t ed25519 -C "your_email@example.com" -f ~/.ssh/id_ed25519_github -N ""
   ```
2. 公開鍵を GitHub に登録:  
   GitHub → **Settings** → **SSH and GPG keys** → **New SSH key** → 貼り付け
3. リモートを HTTPS から SSH に変更:
   ```bash
   git remote set-url origin git@github.com:jphacks/kz_2504.git
   ```
4. `git push origin v3_demo` でプッシュ（トークン入力不要）

---

## まとめ

| やり方 | 手間 | 安全性 |
|--------|------|--------|
| 毎回トークン入力 | 毎回打つ | ◎ |
| credential.helper (キーチェーン) | 1回だけ | ◎ |
| URL にトークン | 設定1回 | △ 漏れ注意 |
| SSH キー | 初回設定のみ | ◎ |

**まず試すなら**: トークンを作成 → `git push` でユーザー名＋トークン入力 → `credential.helper osxkeychain` で次回以降を楽にする。

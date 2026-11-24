# ジョブ管理機能
バッチ実行時にジョブIDを発行し、作業フォルダを作成し、そのフォルダで進捗管理などを行う
ジョブIDから状況を確認できる

# 機能
- ジョブIDの発行
- ジョブID指定し状況データの更新
- ジョブID指定し状況データの取得

# 副作用の扱い
ファイル保存・読み込みは副作用としない
pdf2zh_next の呼び出しも副作用としない
これらは変更の無い確定した機能なので計算とする

# 使い方
## ジョブIDの発行
```bash
python -m impl_translator.src.libs.job --working-dir <working_dir> --create
```

## ジョブID指定し状況データの更新
```bash
# ジョブそのもののメタデータの日時なども一緒に更新される
python -m impl_translator.src.libs.job --working-dir <working_dir> --update --job-id=<job_id> --sub-key <sub_key> --data <dict data>
```

## ジョブID指定し状況データの取得
```bash
# ジョブそのもののメタデータの日時なども一緒に取得される
python -m impl_translator.src.libs.job --working-dir <working_dir> --get --job-id=<job_id> --sub-key <sub_key>
```

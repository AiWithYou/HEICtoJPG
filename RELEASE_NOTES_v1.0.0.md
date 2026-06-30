# HEIC Converter v1.0.0

## 日本語

安定版としての初回リリースです。Python や PowerShell を触らずに使う場合は、下の Assets から `HEICConverter.zip` をダウンロードし、展開して `HEICConverter.exe` を起動してください。

主な内容:

- HEIC/HEIF と一般的な画像形式から JPEG / PNG / WebP へ変換できます。
- ファイルやフォルダをGUIへドラッグ&ドロップして変換できます。
- JPEG quality / optimize / progressive、PNG compress level、WebP quality / lossless を設定できます。
- 出力先は同じフォルダ、固定フォルダ、`converted` サブフォルダから選べます。
- 同名ファイル時の `rename` / `skip` / `overwrite` / `error` に対応しています。
- Exif保持、ICCプロファイル保持、GPS削除を設定できます。
- 複数ファイル変換で1件失敗しても残りを継続し、失敗ファイル一覧を表示します。
- 進捗バー、処理中ファイル名、キャンセルに対応しています。

配布物には `HEICConverter.exe`、ライセンス表示、第三者ライセンス、ソース提供文書が含まれます。配布や共有には裸のexeではなく `HEICConverter.zip` を使ってください。

## English

This is the first stable release. To use the app without Python or PowerShell, download `HEICConverter.zip` from the Assets section below, unzip it, and run `HEICConverter.exe`.

Highlights:

- Converts HEIC/HEIF and common image formats to JPEG, PNG, or WebP.
- Converts files or folders through the drag-and-drop GUI.
- Supports JPEG quality / optimize / progressive, PNG compress level, and WebP quality / lossless settings.
- Supports same-folder, fixed-folder, and `converted` subfolder output.
- Supports `rename`, `skip`, `overwrite`, and `error` behavior when output files already exist.
- Supports Exif preservation, ICC profile preservation, and GPS removal settings.
- Continues multi-file conversion after individual file failures and reports failed files.
- Shows progress, current file name, and cancellation controls.

The package includes `HEICConverter.exe`, license notices, third-party license files, and source-availability information. For redistribution, share `HEICConverter.zip` rather than the bare exe.

# HEIC Converter v1.1.0

## 日本語

画像を軽く扱うためのリサイズ機能と、連続変換・設定・配布の信頼性を改善したリリースです。Python や PowerShell を使わずに利用する場合は、Assets から `HEICConverter.zip` をダウンロードし、展開して `HEICConverter.exe` を起動してください。

主な変更:

- 最大長辺をピクセル数で指定して、縦横比を維持したまま画像を縮小できるようになりました。小さい画像は拡大しません。保存設定に加え、CLI の `--max-dimension` と `--no-resize` で変換ごとに指定できます。
- 再帰的なフォルダ変換で、`converted` または入力配下にある別の固定出力ツリーを再び入力として処理しないようにしました。
- 1ファイルのデコードや変換で例外が発生しても、バッチ内の残りのファイルを継続して処理するようにしました。
- 不正なエンコーディングや読み取り不能な設定ファイルを、パス付きの分かりやすい設定エラーとして報告するようにしました。
- 回転補正やリサイズ後の実際のピクセル寸法に合わせて、保持する EXIF の寸法情報を更新するようにしました。
- GUI の数値欄が空または不正な場合に、コールバック例外ではなく入力エラーを表示するようにしました。
- 読み取り不能なフォルダの追加や、変換後の出力フォルダを開く処理に失敗しても、GUI がコールバック例外で停止せず、対象を明示して報告するようにしました。
- 設定画面を縦スクロール対応にし、画面の縦幅が小さい環境でも保存・終了ボタンを常に操作できるようにしました。
- この PC へのセットアップ後のショートカットがリポジトリの場所に依存しないようにしました。
- CI と GitHub Release 向けビルドの前に format、lint、テストを実行し、GitHub Actions を Node.js 24 対応版へ更新しました。また、古い `dist\HEICConverter.exe` を削除して旧成果物の誤配布を防ぐようにしました。

配布や共有には、ライセンス文書を含む `HEICConverter.zip` を使用してください。裸の `HEICConverter.exe` は配布しないでください。

## English

This release adds an optional downscaling feature for lighter images and improves the reliability of batch conversion, configuration handling, setup, and distribution. To use the app without Python or PowerShell, download `HEICConverter.zip` from Assets, extract it, and run `HEICConverter.exe`.

Highlights:

- Added a maximum-dimension setting that downsizes an image while preserving its aspect ratio. Smaller images are never enlarged. Use the saved setting or override it per conversion with CLI `--max-dimension` and `--no-resize`.
- Recursive folder conversion now excludes a separate `converted` or nested fixed-output tree so previous results there are not processed as new inputs.
- Batch conversion now continues with the remaining files when decoding or conversion of an individual file raises an exception.
- Invalidly encoded or unreadable configuration files now produce clear configuration errors that include the affected path.
- Preserved EXIF dimension fields are updated to match the actual pixel size after orientation correction and resizing.
- Empty or invalid numeric GUI fields now show an input error instead of raising a callback exception.
- Unreadable folders and failures to open output folders are now reported without stopping the GUI with a callback exception.
- The settings window is now vertically scrollable, while Save and Close remain reachable on shorter displays.
- Start Menu shortcuts created by the local PC setup no longer depend on the repository location.
- CI and GitHub Release builds now run format, lint, and tests first, use Node.js 24-based GitHub Actions, and remove the legacy `dist\HEICConverter.exe` to prevent accidentally shipping stale output.

Redistribute `HEICConverter.zip`, which includes the required license documents. Do not redistribute the bare `HEICConverter.exe`.

# HEIC Converter v1.1.1

## 日本語

画像変換の保存安全性とメタデータ処理を修正したメンテナンス版です。GUI・CLIの操作方法と既存の設定ファイルはそのまま使えます。

### 修正・改善

- **EXIF削除を確実に反映**: EXIF保持を無効にしたPNG出力で、元画像のEXIFが再び保存される問題を修正しました。GPSしか含まれないEXIFからGPSを削除した際に、元の位置情報が復活するケースも防ぎます。
- **同時変換でも保存ポリシーを維持**: 変換開始後に同名ファイルが作成された場合にも、`rename` / `skip` / `error` が既存ファイルを上書きしないようにしました。連番の競合は再エンコードせず、次の番号で保存します。`overwrite` を明示した場合の上書き動作は従来どおりです。
- **保存失敗時の既存ファイル保護**: 一時ファイルへのエンコード、flush/fsync、Windowsの属性処理を終えてから公開します。処理途中の失敗で既存の出力を壊さない構成にしました。
- **透過PNGからWebPへの変換**: RGB PNGの透過色指定をアルファチャンネルへ変換し、透過が失われる問題を修正しました。
- **長いファイル名に対応**: 一時ファイル名に元ファイル名を付加しないようにし、元画像名は有効なのに一時保存名が長すぎて失敗するケースを修正しました。
- **ICC削除時の不要な画像コピーを廃止**: 保存オプションでメタデータ継承を制御します。
- **品質検査を修復**: import整理など既存のlint/format違反を修正し、Ruffの検査ルールを明示しました。バッチの第三者デコーダー失敗隔離とエラーダイアログの最終フォールバックだけは、理由を記載した例外捕捉を維持しています。
- **回帰テストを追加**: メタデータ保持・削除、透過、4並列変換、保存時の競合、連番、シンボリックリンク、長い名前、書込失敗を検査します。

### 範囲・注意

GPS削除は標準EXIFのGPS IFDを対象とします。画像内に写った情報やメーカー独自メタデータまで匿名化する機能ではありません。実際のUSB/exFAT媒体やWindows Explorerの手操作は自動テストと別の確認が必要です。POSIX環境でハードリンクを作れない出力先では、非上書き保存を安全側でエラーにします。新しいZIP配布物は、リリース用タグのビルドが成功した場合に公開されます。

## English

Maintenance release preserving the existing GUI, CLI and configuration format.

- Explicitly clear EXIF/ICC encoder options so PNG cannot inherit metadata that was disabled or emptied by GPS removal.
- Publish completed output with no-clobber semantics for rename/skip/error, including collisions occurring during encoding. Retry numbered names without re-encoding. Explicit overwrite behavior is unchanged.
- Flush and sync temporary output and finish Windows attribute updates before publishing; keep existing files intact on pre-publication failures.
- Preserve PNG color-key transparency when converting to WebP.
- Use short temporary names independent of source filename length.
- Avoid an unnecessary full image copy when dropping ICC metadata.
- Repair existing lint/format failures and declare an explicit Ruff rule set.
- Add regression coverage for metadata, transparency, concurrent writers, collisions, symlinks, long filenames and injected write failures.

GPS removal targets the standard EXIF GPS IFD, not arbitrary proprietary metadata or identifying information visible in the image. POSIX destinations without hard-link support fail safely instead of falling back to destructive overwrite. Physical removable-media and interactive Explorer testing remain separate from automated tests.

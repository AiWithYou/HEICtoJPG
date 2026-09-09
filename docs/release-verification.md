# Release verification

## Automated release gate

`Build EXE` runs for a `v*` tag, a matching `release/v*` branch, or manual workflow dispatch. Manual dispatch only publishes when `publish` is enabled. The branch/tag must agree with the package version, and release notes must exist.

The gate runs lint, formatting, the full test suite, the Windows EXE/ZIP build including existing license documents, and tests again with the exact build interpreter. It then unpacks the actual distribution ZIP and exercises the EXE, rather than substituting a Python entry point.

`verify_release.py` opens real Tk/TkDnD windows, runs the GUI event loop and background converter, and tests cancellation/restart. It starts the unpacked EXE in a separate process and clicks its Convert button through native Windows mouse input. English/JPEG, Japanese/PNG and Japanese/WebP cases use actual HEIF/PNG fixtures in paths containing Japanese characters and spaces. Decoded output is checked for format size, alpha/white compositing, removed EXIF/ICC, and temporary-file cleanup. Screenshots and JSON results are saved.

`verify_exfat.ps1` requires administrator rights. It creates a NEW 256 MB disposable VHD in a unique temporary directory and formats only that virtual disk. It checks that the assigned drive is backed by that VHD and uses exFAT, runs safety regression cases there (excluding unsupported symlink cases), and repeats the GUI/EXE checks using exFAT inputs and outputs. The virtual disk is detached and removed afterwards. No physical disk is selected or formatted.

All checks must succeed before publication. The workflow attaches `HEICConverter.zip`, its SHA-256 checksum, `build-manifest.json`, and `release-verification.zip`. It downloads the uploaded ZIP and checks its SHA-256 before publishing the draft. Already published releases are not silently replaced.

## Run the GUI/EXE checks locally

From the repository root on a Windows desktop:

```powershell
python -m pip install -e ".[dev]" pywinauto
.\scripts\build_exe.ps1
python scripts/verify_release.py --exe dist/HEICConverter/HEICConverter.exe --report-dir release-verification/local
```

The script uses synthetic images and a temporary APPDATA directory; it does not replace the user's saved settings. Native mouse input is used, so keep the test desktop available and do not interact with it during the run.

## 実機でのみ確認できる範囲

Windows hosted runnerでのGUI操作は自動操作であり、人間によるExplorerの右クリック／外部ドラッグ操作の確認とは区別する。exFAT VHDでの検証は実際のexFATファイルシステムを使用するが、物理USB媒体のコントローラー、抜き差し、特定PCのシェル拡張との相性までは検証しない。JSONには `physical_usb_tested: false` を記録する。

ローカルCodex等へ渡す追加確認指示:

```text
HEICtoJPGの公開済みv1.1.1を対象に、Windows実機に固有の残りの確認を行う。
既存の写真・設定・USB内容を変更しない。実ディスクの初期化やフォーマットは禁止。
公開ZIPのSHA-256を照合し、ZIP内のEXEを使う。合成画像または写真のコピーだけでテストする。
1. ExplorerからファイルとフォルダをGUI／EXEにドロップし、日本語と空白のあるパスを確認する。
2. 右クリックメニューが既に登録されている場合、その起動経路と複数選択を確認する。未登録なら勝手にレジストリを変更しない。
3. 接続済みのexFAT USBに新しい専用テストフォルダを作り、JPEG/PNG/WebP変換、同名連番、skip、明示overwriteをコピーだけで確認する。USBがなければ未実施と記録する。
4. 変換中のキャンセル、再実行、終了、進捗表示、150%/200%表示倍率での操作を確認する。
5. 結果・実行コマンド・画面・不具合の再現手順を記録し、実施と未実施を分ける。
必要なコード修正があれば回帰テストを追加し、lint/format/pytestを通す。既存の公開タグを付け替えない。
```

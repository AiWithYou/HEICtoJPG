from __future__ import annotations

import os
import subprocess
import sys
import threading
from pathlib import Path
from tkinter import (
    BooleanVar,
    IntVar,
    StringVar,
    Tcl,
    Tk,
    filedialog,
    messagebox,
    ttk,
)

from tkinterdnd2 import DND_FILES, TkinterDnD

from heictojpg.config import (
    APP_NAME,
    FORMAT_JPEG,
    FORMAT_PNG,
    FORMAT_WEBP,
    LANGUAGE_EN,
    LANGUAGE_JA,
    OUTPUT_MODE_CONVERTED_SUBFOLDER,
    OUTPUT_MODE_FIXED_FOLDER,
    OUTPUT_MODE_SAME_FOLDER,
    OVERWRITE_ERROR,
    OVERWRITE_OVERWRITE,
    OVERWRITE_RENAME,
    OVERWRITE_SKIP,
    AppConfig,
    ConfigError,
    load_config,
)
from heictojpg.converter import (
    SUPPORTED_SOURCE_SUFFIXES,
    ConversionResult,
    convert_files,
    is_webp_supported,
    list_source_images,
)
from heictojpg.version import format_app_title


IMAGE_FILE_PATTERNS = " ".join(f"*{suffix}" for suffix in sorted(SUPPORTED_SOURCE_SUFFIXES))
FORMAT_LABELS = {
    FORMAT_JPEG: "JPEG (.jpg)",
    FORMAT_PNG: "PNG (.png)",
    FORMAT_WEBP: "WebP (.webp)",
}
POLICY_VALUES = (
    OVERWRITE_RENAME,
    OVERWRITE_SKIP,
    OVERWRITE_OVERWRITE,
    OVERWRITE_ERROR,
)

TRANSLATIONS = {
    LANGUAGE_EN: {
        "window_title": format_app_title(APP_NAME),
        "drop_title": "Drop image files here",
        "drop_subtitle": "You can also drag files or folders onto HEICConverter.exe.",
        "files": "Files",
        "add_files": "Add Files",
        "add_folder": "Add Folder",
        "remove": "Remove",
        "clear": "Clear",
        "include_subfolders": "Include subfolders",
        "output_format": "Output format",
        "output_folder": "Output folder",
        "same_folder": "Same folder",
        "fixed_folder": "Fixed folder",
        "converted_subfolder": "converted subfolder",
        "choose": "Choose...",
        "no_fixed_folder": "No fixed folder selected",
        "overwrite": "When output exists",
        "quality_section": "Quality and compression",
        "jpeg": "JPEG",
        "png": "PNG",
        "webp": "WebP",
        "quality": "Quality",
        "compress": "Compress",
        "optimize": "Optimize",
        "progressive": "Progressive",
        "lossless": "Lossless",
        "metadata": "Metadata",
        "keep_exif": "Keep Exif",
        "keep_icc_profile": "Keep ICC profile",
        "remove_gps": "Remove GPS",
        "open_output_folder": "Open output folder after conversion",
        "convert": "Convert",
        "ready": "Ready.",
        "files_added": "Added {count} file(s).",
        "no_files": "Add image files before converting.",
        "converted": "Converted {converted}; skipped {skipped}.",
        "converted_summary": "Converted {converted}; skipped {skipped}; failed {failed}.",
        "cancel": "Cancel",
        "cancelling": "Cancelling after the current file...",
        "cancelled": "Cancelled. Converted {converted}; skipped {skipped}; failed {failed}.",
        "current_file": "Current file: {name}",
        "no_current_file": "Current file: -",
        "failed_title": "Failed files",
        "failed_items": "Some files could not be converted:\n{items}",
        "busy": "Converting...",
        "webp_unavailable": "WebP output is not available in this Pillow build.",
        "webp_unavailable_suffix": " unavailable",
        "config_error": "The saved settings could not be loaded:\n{error}",
        "unsupported_paths": "Some items could not be added:\n{items}",
        "policy_rename": "Rename automatically",
        "policy_skip": "Skip existing files",
        "policy_overwrite": "Overwrite existing files",
        "policy_error": "Show an error",
    },
    LANGUAGE_JA: {
        "window_title": format_app_title(APP_NAME),
        "drop_title": "ここに画像ファイルをドロップ",
        "drop_subtitle": "HEICConverter.exe にファイルやフォルダを直接ドロップしても追加できます。",
        "files": "ファイル",
        "add_files": "ファイル追加",
        "add_folder": "フォルダ追加",
        "remove": "削除",
        "clear": "クリア",
        "include_subfolders": "サブフォルダも含める",
        "output_format": "出力形式",
        "output_folder": "出力先",
        "same_folder": "同じフォルダ",
        "fixed_folder": "固定フォルダ",
        "converted_subfolder": "converted サブフォルダ",
        "choose": "選択...",
        "no_fixed_folder": "固定フォルダが選択されていません",
        "overwrite": "同名ファイル時",
        "quality_section": "品質と圧縮",
        "jpeg": "JPEG",
        "png": "PNG",
        "webp": "WebP",
        "quality": "品質",
        "compress": "圧縮",
        "optimize": "最適化",
        "progressive": "プログレッシブ",
        "lossless": "ロスレス",
        "metadata": "メタデータ",
        "keep_exif": "Exif を保持",
        "keep_icc_profile": "ICC プロファイルを保持",
        "remove_gps": "GPS を削除",
        "open_output_folder": "変換後に出力フォルダを開く",
        "convert": "変換",
        "ready": "準備完了。",
        "files_added": "{count} 件追加しました。",
        "no_files": "変換する画像ファイルを追加してください。",
        "converted": "変換 {converted} 件、スキップ {skipped} 件。",
        "converted_summary": "変換 {converted} 件、スキップ {skipped} 件、失敗 {failed} 件。",
        "cancel": "キャンセル",
        "cancelling": "現在のファイル完了後にキャンセルします...",
        "cancelled": "キャンセルしました。変換 {converted} 件、スキップ {skipped} 件、失敗 {failed} 件。",
        "current_file": "処理中: {name}",
        "no_current_file": "処理中: -",
        "failed_title": "変換に失敗したファイル",
        "failed_items": "変換できないファイルがありました:\n{items}",
        "busy": "変換中...",
        "webp_unavailable": "この Pillow ビルドでは WebP 出力を利用できません。",
        "webp_unavailable_suffix": " 利用不可",
        "config_error": "保存済み設定を読み込めませんでした:\n{error}",
        "unsupported_paths": "追加できない項目がありました:\n{items}",
        "policy_rename": "自動リネーム",
        "policy_skip": "既存ファイルをスキップ",
        "policy_overwrite": "既存ファイルを上書き",
        "policy_error": "エラーを表示",
    },
}
POLICY_LABEL_KEYS = {
    OVERWRITE_RENAME: "policy_rename",
    OVERWRITE_SKIP: "policy_skip",
    OVERWRITE_OVERWRITE: "policy_overwrite",
    OVERWRITE_ERROR: "policy_error",
}


def parse_drop_data(data: str) -> list[Path]:
    return [Path(value) for value in Tcl().splitlist(data)]


def collect_image_files(paths: list[Path], *, recursive: bool) -> tuple[list[Path], list[str]]:
    files: list[Path] = []
    errors: list[str] = []

    for path in paths:
        if path.is_file() and path.suffix.lower() in SUPPORTED_SOURCE_SUFFIXES:
            files.append(path)
        elif path.is_dir():
            folder_files = list_source_images(path, recursive=recursive)
            if folder_files:
                files.extend(folder_files)
            else:
                errors.append(f"{path}: no supported image files")
        elif path.exists():
            errors.append(f"{path}: unsupported source type")
        else:
            errors.append(f"{path}: does not exist")

    deduped: list[Path] = []
    seen: set[Path] = set()
    for file_path in files:
        resolved = file_path.resolve()
        if resolved not in seen:
            seen.add(resolved)
            deduped.append(file_path)

    return deduped, errors


class ConverterWindow:
    def __init__(self, root: Tk, initial_paths: list[Path] | None = None) -> None:
        self.root = root
        self.root.geometry("1020x760")
        self.root.minsize(900, 680)
        self.root.title(format_app_title(APP_NAME))
        self.webp_supported = is_webp_supported()
        self._busy = False

        config_error = None
        try:
            self.config = load_config()
        except ConfigError as exc:
            self.config = AppConfig()
            config_error = str(exc)

        self.language = self.config.language
        self.output_mode = StringVar(value=self.config.output_mode)
        self.output_format = StringVar(value=self._initial_output_format())
        self.fixed_output_dir = self.config.output_dir
        self.recursive = BooleanVar(value=False)
        self.jpeg_quality = IntVar(value=self.config.jpeg_quality)
        self.jpeg_optimize = BooleanVar(value=self.config.jpeg_optimize)
        self.jpeg_progressive = BooleanVar(value=self.config.jpeg_progressive)
        self.webp_quality = IntVar(value=self.config.webp_quality)
        self.webp_lossless = BooleanVar(value=self.config.webp_lossless)
        self.png_compress_level = IntVar(value=self.config.png_compress_level)
        self.keep_exif = BooleanVar(value=self.config.keep_exif)
        self.keep_icc_profile = BooleanVar(value=self.config.keep_icc_profile)
        self.remove_gps = BooleanVar(value=self.config.remove_gps)
        self.open_output_folder = BooleanVar(value=self.config.open_output_folder)
        self.overwrite_policy = self.config.overwrite_policy
        self.overwrite_policy_label = StringVar()
        self.status = StringVar(value=self._t("ready"))
        self.current_file = StringVar(value=self._t("no_current_file"))
        self.cancel_event = threading.Event()

        self.files: list[Path] = []
        self.widgets: dict[str, ttk.Widget] = {}

        self._build()
        self._apply_language()
        self._update_fixed_folder_state()
        self._enable_drop_targets()
        if initial_paths:
            self.add_paths(initial_paths)
        if config_error:
            self.root.after(100, lambda: messagebox.showwarning(
                self._t("window_title"),
                self._t("config_error").format(error=config_error),
                parent=self.root,
            ))

    def _build(self) -> None:
        frame = ttk.Frame(self.root, padding=16)
        frame.grid(row=0, column=0, sticky="nsew")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(1, weight=1)

        drop_frame = ttk.LabelFrame(frame, padding=12)
        drop_frame.grid(row=0, column=0, sticky="ew")
        drop_frame.columnconfigure(0, weight=1)
        self.widgets["drop_frame"] = drop_frame
        self.widgets["drop_title"] = ttk.Label(drop_frame, font=("", 13, "bold"))
        self.widgets["drop_title"].grid(row=0, column=0, sticky="w")
        self.widgets["drop_subtitle"] = ttk.Label(drop_frame)
        self.widgets["drop_subtitle"].grid(row=1, column=0, sticky="w", pady=(4, 0))

        content = ttk.Frame(frame)
        content.grid(row=1, column=0, sticky="nsew", pady=(12, 0))
        content.columnconfigure(0, weight=3)
        content.columnconfigure(1, weight=2)
        content.rowconfigure(0, weight=1)

        list_area = ttk.Frame(content)
        list_area.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        list_area.columnconfigure(0, weight=1)
        list_area.rowconfigure(0, weight=1)

        self.file_list = ttk.Treeview(list_area, columns=("path",), show="headings", selectmode="extended")
        self.file_list.grid(row=0, column=0, sticky="nsew")
        self.file_list.heading("path", text=self._t("files"))
        self.file_list.column("path", width=480, stretch=True)
        scrollbar = ttk.Scrollbar(list_area, orient="vertical", command=self.file_list.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.file_list.configure(yscrollcommand=scrollbar.set)

        button_row = ttk.Frame(list_area)
        button_row.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        button_row.columnconfigure(4, weight=1)
        for index, (key, command) in enumerate(
            (
                ("add_files", self.choose_files),
                ("add_folder", self.choose_folder),
                ("remove", self.remove_selected),
                ("clear", self.clear_files),
            )
        ):
            self.widgets[key] = ttk.Button(button_row, command=command)
            self.widgets[key].grid(row=0, column=index, sticky="w", padx=(0, 8))
        self.widgets["include_subfolders"] = ttk.Checkbutton(button_row, variable=self.recursive)
        self.widgets["include_subfolders"].grid(row=0, column=5, sticky="e")

        settings = ttk.Frame(content)
        settings.grid(row=0, column=1, sticky="nsew")
        settings.columnconfigure(0, weight=1)

        self._build_format_section(settings).grid(row=0, column=0, sticky="ew")
        self._build_quality_section(settings).grid(row=1, column=0, sticky="ew", pady=(12, 0))
        self._build_output_section(settings).grid(row=2, column=0, sticky="ew", pady=(12, 0))
        self._build_overwrite_section(settings).grid(row=3, column=0, sticky="ew", pady=(12, 0))
        self._build_metadata_section(settings).grid(row=4, column=0, sticky="ew", pady=(12, 0))

        bottom = ttk.Frame(frame)
        bottom.grid(row=2, column=0, sticky="ew", pady=(12, 0))
        bottom.columnconfigure(0, weight=1)
        self.widgets["current_file"] = ttk.Label(bottom, textvariable=self.current_file)
        self.widgets["current_file"].grid(row=0, column=0, columnspan=3, sticky="ew")
        self.progress = ttk.Progressbar(bottom, mode="determinate")
        self.progress.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(6, 0))
        self.widgets["status"] = ttk.Label(bottom, textvariable=self.status)
        self.widgets["status"].grid(row=2, column=0, sticky="w", pady=(8, 0))
        self.widgets["cancel"] = ttk.Button(bottom, command=self.cancel)
        self.widgets["cancel"].grid(row=2, column=1, sticky="e", padx=(0, 8), pady=(8, 0))
        self.widgets["convert"] = ttk.Button(bottom, command=self.convert)
        self.widgets["convert"].grid(row=2, column=2, sticky="e", pady=(8, 0))
        self.widgets["cancel"].configure(state="disabled")

    def _build_format_section(self, parent: ttk.Frame) -> ttk.LabelFrame:
        section = ttk.LabelFrame(parent, padding=12)
        self.widgets["format_section"] = section
        self.format_buttons: dict[str, ttk.Radiobutton] = {}
        for column, output_format in enumerate((FORMAT_JPEG, FORMAT_PNG, FORMAT_WEBP)):
            state = "disabled" if output_format == FORMAT_WEBP and not self.webp_supported else "normal"
            button = ttk.Radiobutton(
                section,
                value=output_format,
                variable=self.output_format,
                state=state,
            )
            button.grid(row=0, column=column, sticky="w", padx=(0, 18))
            self.format_buttons[output_format] = button
        return section

    def _build_quality_section(self, parent: ttk.Frame) -> ttk.LabelFrame:
        section = ttk.LabelFrame(parent, padding=12)
        self.widgets["quality_section"] = section
        for column in range(3):
            section.columnconfigure(column, weight=1)

        jpeg = ttk.Frame(section)
        jpeg.grid(row=0, column=0, sticky="nw", padx=(0, 16))
        self.widgets["jpeg_heading"] = ttk.Label(jpeg)
        self.widgets["jpeg_heading"].grid(row=0, column=0, columnspan=2, sticky="w")
        self.widgets["jpeg_quality_label"] = ttk.Label(jpeg)
        self.widgets["jpeg_quality_label"].grid(row=1, column=0, sticky="w", pady=(6, 0))
        ttk.Spinbox(jpeg, from_=1, to=100, width=5, textvariable=self.jpeg_quality).grid(
            row=1,
            column=1,
            sticky="w",
            pady=(6, 0),
        )
        self.widgets["jpeg_optimize"] = ttk.Checkbutton(jpeg, variable=self.jpeg_optimize)
        self.widgets["jpeg_optimize"].grid(row=2, column=0, columnspan=2, sticky="w", pady=(6, 0))
        self.widgets["jpeg_progressive"] = ttk.Checkbutton(jpeg, variable=self.jpeg_progressive)
        self.widgets["jpeg_progressive"].grid(
            row=3,
            column=0,
            columnspan=2,
            sticky="w",
            pady=(6, 0),
        )

        png = ttk.Frame(section)
        png.grid(row=0, column=1, sticky="nw", padx=(0, 16))
        self.widgets["png_heading"] = ttk.Label(png)
        self.widgets["png_heading"].grid(row=0, column=0, columnspan=2, sticky="w")
        self.widgets["png_compress_label"] = ttk.Label(png)
        self.widgets["png_compress_label"].grid(row=1, column=0, sticky="w", pady=(6, 0))
        ttk.Spinbox(
            png,
            from_=0,
            to=9,
            width=5,
            textvariable=self.png_compress_level,
        ).grid(row=1, column=1, sticky="w", pady=(6, 0))

        webp = ttk.Frame(section)
        webp.grid(row=0, column=2, sticky="nw")
        self.widgets["webp_heading"] = ttk.Label(webp)
        self.widgets["webp_heading"].grid(row=0, column=0, columnspan=2, sticky="w")
        self.widgets["webp_quality_label"] = ttk.Label(webp)
        self.widgets["webp_quality_label"].grid(row=1, column=0, sticky="w", pady=(6, 0))
        state = "normal" if self.webp_supported else "disabled"
        ttk.Spinbox(
            webp,
            from_=1,
            to=100,
            width=5,
            textvariable=self.webp_quality,
            state=state,
        ).grid(row=1, column=1, sticky="w", pady=(6, 0))
        self.widgets["webp_lossless"] = ttk.Checkbutton(
            webp,
            variable=self.webp_lossless,
            state=state,
        )
        self.widgets["webp_lossless"].grid(row=2, column=0, columnspan=2, sticky="w", pady=(6, 0))
        return section

    def _build_output_section(self, parent: ttk.Frame) -> ttk.LabelFrame:
        section = ttk.LabelFrame(parent, padding=12)
        section.columnconfigure(0, weight=1)
        self.widgets["output_section"] = section
        self.widgets["same_folder"] = ttk.Radiobutton(
            section,
            value=OUTPUT_MODE_SAME_FOLDER,
            variable=self.output_mode,
            command=self._update_fixed_folder_state,
        )
        self.widgets["same_folder"].grid(row=0, column=0, sticky="w")
        self.widgets["converted_subfolder"] = ttk.Radiobutton(
            section,
            value=OUTPUT_MODE_CONVERTED_SUBFOLDER,
            variable=self.output_mode,
            command=self._update_fixed_folder_state,
        )
        self.widgets["converted_subfolder"].grid(row=1, column=0, sticky="w", pady=(6, 0))
        self.widgets["fixed_folder"] = ttk.Radiobutton(
            section,
            value=OUTPUT_MODE_FIXED_FOLDER,
            variable=self.output_mode,
            command=self._update_fixed_folder_state,
        )
        self.widgets["fixed_folder"].grid(row=2, column=0, sticky="w", pady=(6, 0))
        self.widgets["folder_label"] = ttk.Label(section, wraplength=280)
        self.widgets["folder_label"].grid(row=3, column=0, sticky="ew", pady=(6, 0))
        self.widgets["choose"] = ttk.Button(section, command=self.choose_output_folder)
        self.widgets["choose"].grid(row=4, column=0, sticky="w", pady=(8, 0))
        return section

    def _build_overwrite_section(self, parent: ttk.Frame) -> ttk.LabelFrame:
        section = ttk.LabelFrame(parent, padding=12)
        section.columnconfigure(0, weight=1)
        self.widgets["overwrite_section"] = section
        self.overwrite_combo = ttk.Combobox(
            section,
            textvariable=self.overwrite_policy_label,
            state="readonly",
        )
        self.overwrite_combo.grid(row=0, column=0, sticky="ew")
        self.overwrite_combo.bind("<<ComboboxSelected>>", self._on_overwrite_selected)
        return section

    def _build_metadata_section(self, parent: ttk.Frame) -> ttk.LabelFrame:
        section = ttk.LabelFrame(parent, padding=12)
        self.widgets["metadata_section"] = section
        self.widgets["keep_exif"] = ttk.Checkbutton(section, variable=self.keep_exif)
        self.widgets["keep_exif"].grid(row=0, column=0, sticky="w")
        self.widgets["keep_icc_profile"] = ttk.Checkbutton(section, variable=self.keep_icc_profile)
        self.widgets["keep_icc_profile"].grid(row=1, column=0, sticky="w", pady=(6, 0))
        self.widgets["remove_gps"] = ttk.Checkbutton(section, variable=self.remove_gps)
        self.widgets["remove_gps"].grid(row=2, column=0, sticky="w", pady=(6, 0))
        self.widgets["open_output_folder"] = ttk.Checkbutton(
            section,
            variable=self.open_output_folder,
        )
        self.widgets["open_output_folder"].grid(row=3, column=0, sticky="w", pady=(6, 0))
        return section

    def _enable_drop_targets(self) -> None:
        for widget in (self.root, self.widgets["drop_frame"], self.file_list):
            widget.drop_target_register(DND_FILES)
            widget.dnd_bind("<<Drop>>", self._on_drop)

    def choose_files(self) -> None:
        selected = filedialog.askopenfilenames(
            parent=self.root,
            filetypes=[
                ("Supported images", IMAGE_FILE_PATTERNS),
                ("All files", "*.*"),
            ],
        )
        if selected:
            self.add_paths([Path(value) for value in selected])

    def choose_folder(self) -> None:
        selected = filedialog.askdirectory(parent=self.root)
        if selected:
            self.add_paths([Path(selected)])

    def choose_output_folder(self) -> None:
        selected = filedialog.askdirectory(
            parent=self.root,
            initialdir=str(self.fixed_output_dir) if self.fixed_output_dir else str(Path.home()),
        )
        if selected:
            self.fixed_output_dir = Path(selected)
            self.output_mode.set(OUTPUT_MODE_FIXED_FOLDER)
            self._update_fixed_folder_state()

    def add_paths(self, paths: list[Path]) -> None:
        files, errors = collect_image_files(paths, recursive=self.recursive.get())
        added = 0
        current = {path.resolve() for path in self.files}
        for file_path in files:
            resolved = file_path.resolve()
            if resolved in current:
                continue
            current.add(resolved)
            self.files.append(file_path)
            self.file_list.insert("", "end", values=(str(file_path),))
            added += 1

        if added:
            self.status.set(self._t("files_added").format(count=added))
        if errors:
            messagebox.showwarning(
                self._t("window_title"),
                self._t("unsupported_paths").format(items="\n".join(errors[:12])),
                parent=self.root,
            )

    def remove_selected(self) -> None:
        selected = list(self.file_list.selection())
        if not selected:
            return
        selected_indexes = sorted((self.file_list.index(item) for item in selected), reverse=True)
        for item in selected:
            self.file_list.delete(item)
        for index in selected_indexes:
            del self.files[index]

    def clear_files(self) -> None:
        self.files.clear()
        for item in self.file_list.get_children():
            self.file_list.delete(item)
        self.status.set(self._t("ready"))

    def convert(self) -> None:
        if self._busy:
            return
        if not self.files:
            messagebox.showinfo(self._t("window_title"), self._t("no_files"), parent=self.root)
            return
        if self.output_format.get() == FORMAT_WEBP and not self.webp_supported:
            messagebox.showerror(
                self._t("window_title"),
                self._t("webp_unavailable"),
                parent=self.root,
            )
            return

        try:
            config = self._config_from_ui()
        except ConfigError as exc:
            messagebox.showerror(self._t("window_title"), str(exc), parent=self.root)
            return

        files = list(self.files)
        self.cancel_event.clear()
        self.progress.configure(maximum=len(files), value=0)
        self.current_file.set(self._t("no_current_file"))
        self._set_busy(True)
        thread = threading.Thread(target=self._convert_worker, args=(files, config), daemon=True)
        thread.start()

    def cancel(self) -> None:
        if not self._busy:
            return
        self.cancel_event.set()
        self.widgets["cancel"].configure(state="disabled")
        self.status.set(self._t("cancelling"))

    def _convert_worker(self, files: list[Path], config: AppConfig) -> None:
        results: list[ConversionResult] = []
        total = len(files)
        try:
            for index, file_path in enumerate(files, start=1):
                if self.cancel_event.is_set():
                    break
                self.root.after(0, lambda index=index, file_path=file_path: self._handle_progress(
                    index - 1,
                    total,
                    file_path,
                ))
                result = convert_files([file_path], settings=config)[0]
                results.append(result)
                self.root.after(0, lambda index=index, file_path=file_path: self._handle_progress(
                    index,
                    total,
                    file_path,
                ))
        except (ConfigError, OSError) as exc:
            message = str(exc)
            self.root.after(0, lambda: self._handle_conversion_error(message))
            return

        cancelled = self.cancel_event.is_set()
        self.root.after(0, lambda: self._handle_conversion_success(results, config, cancelled))

    def _handle_progress(self, completed: int, total: int, file_path: Path) -> None:
        self.progress.configure(maximum=total, value=completed)
        self.current_file.set(self._t("current_file").format(name=file_path.name))

    def _handle_conversion_error(self, message: str) -> None:
        self._set_busy(False)
        self.progress.configure(value=0)
        self.current_file.set(self._t("no_current_file"))
        messagebox.showerror(self._t("window_title"), message, parent=self.root)
        self.status.set(self._t("ready"))

    def _handle_conversion_success(
        self,
        results: list[ConversionResult],
        config: AppConfig,
        cancelled: bool,
    ) -> None:
        self._set_busy(False)
        self.progress.configure(value=len(results))
        self.current_file.set(self._t("no_current_file"))
        converted = sum(1 for result in results if result.status == "converted")
        skipped = sum(1 for result in results if result.status == "skipped")
        failed = sum(1 for result in results if result.status == "failed")
        key = "cancelled" if cancelled else "converted_summary"
        self.status.set(
            self._t(key).format(converted=converted, skipped=skipped, failed=failed)
        )
        if failed:
            self._show_failed_results(results)
        if config.open_output_folder:
            self._open_result_folders(results)

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        state = "disabled" if busy else "normal"
        for key in ("add_files", "add_folder", "remove", "clear", "convert"):
            self.widgets[key].configure(state=state)
        self.widgets["cancel"].configure(state="normal" if busy else "disabled")
        if busy:
            self.status.set(self._t("busy"))

    def _config_from_ui(self) -> AppConfig:
        output_mode = self.output_mode.get()
        return self.config.with_changes(
            output_mode=output_mode,
            output_dir=self.fixed_output_dir if output_mode == OUTPUT_MODE_FIXED_FOLDER else None,
            output_format=self.output_format.get(),
            overwrite_policy=self.overwrite_policy,
            jpeg_quality=self.jpeg_quality.get(),
            jpeg_optimize=self.jpeg_optimize.get(),
            jpeg_progressive=self.jpeg_progressive.get(),
            webp_quality=self.webp_quality.get(),
            webp_lossless=self.webp_lossless.get(),
            png_compress_level=self.png_compress_level.get(),
            keep_exif=self.keep_exif.get(),
            keep_icc_profile=self.keep_icc_profile.get(),
            remove_gps=self.remove_gps.get(),
            open_output_folder=self.open_output_folder.get(),
        )

    def _initial_output_format(self) -> str:
        if self.config.output_format == FORMAT_WEBP and not self.webp_supported:
            return FORMAT_JPEG
        return self.config.output_format

    def _on_drop(self, event: object) -> None:
        data = getattr(event, "data")
        self.add_paths(parse_drop_data(data))

    def _on_overwrite_selected(self, _event: object | None = None) -> None:
        labels = self._policy_values_by_label()
        self.overwrite_policy = labels[self.overwrite_policy_label.get()]

    def _apply_language(self) -> None:
        self.root.title(self._t("window_title"))
        self.file_list.heading("path", text=self._t("files"))
        text_keys = {
            "drop_title": "drop_title",
            "drop_subtitle": "drop_subtitle",
            "add_files": "add_files",
            "add_folder": "add_folder",
            "remove": "remove",
            "clear": "clear",
            "include_subfolders": "include_subfolders",
            "same_folder": "same_folder",
            "fixed_folder": "fixed_folder",
            "converted_subfolder": "converted_subfolder",
            "choose": "choose",
            "jpeg_heading": "jpeg",
            "jpeg_quality_label": "quality",
            "jpeg_optimize": "optimize",
            "jpeg_progressive": "progressive",
            "png_heading": "png",
            "png_compress_label": "compress",
            "webp_heading": "webp",
            "webp_quality_label": "quality",
            "webp_lossless": "lossless",
            "keep_exif": "keep_exif",
            "keep_icc_profile": "keep_icc_profile",
            "remove_gps": "remove_gps",
            "open_output_folder": "open_output_folder",
            "cancel": "cancel",
            "convert": "convert",
        }
        for widget_key, translation_key in text_keys.items():
            self.widgets[widget_key].configure(text=self._t(translation_key))

        self.widgets["format_section"].configure(text=self._t("output_format"))
        self.widgets["quality_section"].configure(text=self._t("quality_section"))
        self.widgets["output_section"].configure(text=self._t("output_folder"))
        self.widgets["overwrite_section"].configure(text=self._t("overwrite"))
        self.widgets["metadata_section"].configure(text=self._t("metadata"))

        for output_format, button in self.format_buttons.items():
            label = FORMAT_LABELS[output_format]
            if output_format == FORMAT_WEBP and not self.webp_supported:
                label += self._t("webp_unavailable_suffix")
            button.configure(text=label)

        policy_labels = self._policy_labels()
        self.overwrite_combo.configure(values=list(policy_labels.values()))
        self.overwrite_policy_label.set(policy_labels[self.overwrite_policy])
        self._update_fixed_folder_state()
        if not self._busy:
            self.current_file.set(self._t("no_current_file"))
            self.status.set(self._t("ready"))

    def _update_fixed_folder_state(self) -> None:
        state = "normal" if self.output_mode.get() == OUTPUT_MODE_FIXED_FOLDER else "disabled"
        self.widgets["choose"].configure(state=state)
        label = str(self.fixed_output_dir) if self.fixed_output_dir else self._t("no_fixed_folder")
        self.widgets["folder_label"].configure(text=label)

    def _policy_labels(self) -> dict[str, str]:
        return {
            value: self._t(POLICY_LABEL_KEYS[value])
            for value in POLICY_VALUES
        }

    def _policy_values_by_label(self) -> dict[str, str]:
        return {
            label: value
            for value, label in self._policy_labels().items()
        }

    def _open_result_folders(self, results: list[ConversionResult]) -> None:
        folders = sorted(
            {str(result.target.parent) for result in results if result.status != "failed"}
        )
        for folder in folders:
            if sys.platform == "win32":
                os.startfile(folder)  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", folder])
            else:
                subprocess.Popen(["xdg-open", folder])

    def _t(self, key: str) -> str:
        return TRANSLATIONS[self.language][key]

    def _show_failed_results(self, results: list[ConversionResult]) -> None:
        failures = [result for result in results if result.status == "failed"]
        if not failures:
            return
        items = "\n".join(
            f"{result.source}: {result.error or 'Unknown conversion error.'}"
            for result in failures[:12]
        )
        if len(failures) > 12:
            items += f"\n... {len(failures) - 12} more"
        messagebox.showwarning(
            self._t("failed_title"),
            self._t("failed_items").format(items=items),
            parent=self.root,
        )


def run_converter_app(initial_paths: list[Path] | None = None) -> None:
    root = TkinterDnD.Tk()
    ConverterWindow(root, initial_paths=initial_paths)
    root.mainloop()

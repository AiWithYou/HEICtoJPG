from __future__ import annotations

from pathlib import Path
from tkinter import BooleanVar, IntVar, StringVar, Tk, filedialog, messagebox, ttk

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
    save_config,
)
from heictojpg.converter import is_webp_supported
from heictojpg.version import format_app_title


SETTINGS_TITLE = f"{format_app_title(APP_NAME)} Settings"
SETTINGS_TITLE_JA = f"{format_app_title(APP_NAME)} 設定"


LANGUAGE_LABELS = {
    "English": LANGUAGE_EN,
    "日本語": LANGUAGE_JA,
}
LANGUAGE_NAMES = {
    LANGUAGE_EN: "English",
    LANGUAGE_JA: "日本語",
}

TRANSLATIONS = {
    LANGUAGE_EN: {
        "window_title": SETTINGS_TITLE,
        "language_section": "Language",
        "language_label": "Display language",
        "output_section": "Output folder",
        "same_folder": "Same folder",
        "fixed_folder": "Fixed folder",
        "converted_subfolder": "converted subfolder",
        "choose": "Choose...",
        "no_fixed_folder": "No fixed folder selected",
        "format_section": "Output format",
        "webp_unavailable_suffix": " unavailable",
        "quality_section": "Quality and compression",
        "jpeg": "JPEG",
        "png": "PNG",
        "webp": "WebP",
        "quality": "Quality",
        "compress": "Compress",
        "optimize": "Optimize",
        "progressive": "Progressive",
        "lossless": "Lossless",
        "policy_section": "Existing file behavior",
        "when_output_exists": "When output exists",
        "policy_rename": "Rename automatically",
        "policy_skip": "Skip existing files",
        "policy_overwrite": "Overwrite existing files",
        "policy_error": "Show an error",
        "metadata_section": "Metadata and finish",
        "keep_exif": "Keep Exif",
        "keep_icc_profile": "Keep ICC profile",
        "remove_gps": "Remove GPS",
        "open_output_folder": "Open output folder after conversion",
        "save": "Save",
        "close": "Close",
        "settings_title": SETTINGS_TITLE,
        "webp_unavailable_error": "WebP output is not available in this Pillow build.",
        "saved": "Saved settings to:\n{path}",
        "config_error": (
            "The saved settings could not be loaded.\n\n"
            "{error}\n\n"
            "Choose settings and save to replace the saved settings."
        ),
        "webp_saved_unavailable": (
            "The saved settings requested WebP, but WebP output is not available in this "
            "Pillow build."
        ),
    },
    LANGUAGE_JA: {
        "window_title": SETTINGS_TITLE_JA,
        "language_section": "言語",
        "language_label": "表示言語",
        "output_section": "出力先",
        "same_folder": "同じフォルダ",
        "fixed_folder": "固定フォルダ",
        "converted_subfolder": "converted サブフォルダ",
        "choose": "選択...",
        "no_fixed_folder": "固定フォルダが選択されていません",
        "format_section": "出力形式",
        "webp_unavailable_suffix": " 利用不可",
        "quality_section": "品質と圧縮",
        "jpeg": "JPEG",
        "png": "PNG",
        "webp": "WebP",
        "quality": "品質",
        "compress": "圧縮",
        "optimize": "最適化",
        "progressive": "プログレッシブ",
        "lossless": "ロスレス",
        "policy_section": "同名ファイル時の挙動",
        "when_output_exists": "出力ファイルが存在する場合",
        "policy_rename": "自動リネーム",
        "policy_skip": "既存ファイルをスキップ",
        "policy_overwrite": "既存ファイルを上書き",
        "policy_error": "エラーを表示",
        "metadata_section": "メタデータと完了後の動作",
        "keep_exif": "Exif を保持",
        "keep_icc_profile": "ICC プロファイルを保持",
        "remove_gps": "GPS を削除",
        "open_output_folder": "変換後に出力フォルダを開く",
        "save": "保存",
        "close": "閉じる",
        "settings_title": SETTINGS_TITLE_JA,
        "webp_unavailable_error": "この Pillow ビルドでは WebP 出力を利用できません。",
        "saved": "設定を保存しました:\n{path}",
        "config_error": (
            "保存済み設定を読み込めませんでした。\n\n"
            "{error}\n\n"
            "設定を選び、保存すると保存済み設定を置き換えます。"
        ),
        "webp_saved_unavailable": (
            "保存済み設定で WebP が指定されていますが、この Pillow ビルドでは "
            "WebP 出力を利用できません。"
        ),
    },
}

POLICY_KEYS = {
    OVERWRITE_RENAME: "policy_rename",
    OVERWRITE_SKIP: "policy_skip",
    OVERWRITE_OVERWRITE: "policy_overwrite",
    OVERWRITE_ERROR: "policy_error",
}
FORMAT_LABELS = {
    FORMAT_JPEG: "JPEG (.jpg)",
    FORMAT_PNG: "PNG (.png)",
    FORMAT_WEBP: "WebP (.webp)",
}


class SettingsWindow:
    def __init__(self, root: Tk) -> None:
        self.root = root
        self.root.geometry("680x840")
        self.root.minsize(640, 800)
        self.webp_supported = is_webp_supported()

        config_error = None
        try:
            self.config = load_config()
        except ConfigError as exc:
            self.config = AppConfig()
            config_error = str(exc)

        self.language = self.config.language
        self.language_label = StringVar(value=LANGUAGE_NAMES[self.language])
        self.output_mode = StringVar(value=self.config.output_mode)
        self.fixed_output_dir = self.config.output_dir
        self.output_format = StringVar(value=self._initial_output_format())
        self.jpeg_quality = IntVar(value=self.config.jpeg_quality)
        self.jpeg_optimize = BooleanVar(value=self.config.jpeg_optimize)
        self.jpeg_progressive = BooleanVar(value=self.config.jpeg_progressive)
        self.webp_quality = IntVar(value=self.config.webp_quality)
        self.webp_lossless = BooleanVar(value=self.config.webp_lossless)
        self.png_compress_level = IntVar(value=self.config.png_compress_level)
        self.overwrite_policy = self.config.overwrite_policy
        self.overwrite_policy_label = StringVar()
        self.keep_exif = BooleanVar(value=self.config.keep_exif)
        self.keep_icc_profile = BooleanVar(value=self.config.keep_icc_profile)
        self.remove_gps = BooleanVar(value=self.config.remove_gps)
        self.open_output_folder = BooleanVar(value=self.config.open_output_folder)

        self.sections: dict[str, ttk.LabelFrame] = {}
        self.widgets: dict[str, ttk.Widget] = {}

        self._build()
        self._apply_language()
        self._update_fixed_folder_state()
        if config_error:
            self.root.after(100, lambda: self._show_config_error(config_error))
        if self.config.output_format == FORMAT_WEBP and not self.webp_supported:
            self.root.after(150, self._show_webp_unavailable_warning)

    def _build(self) -> None:
        frame = ttk.Frame(self.root, padding=16)
        frame.grid(row=0, column=0, sticky="nsew")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)

        self._build_language_section(frame).grid(row=0, column=0, sticky="ew")
        self._build_output_section(frame).grid(row=1, column=0, sticky="ew", pady=(12, 0))
        self._build_format_section(frame).grid(row=2, column=0, sticky="ew", pady=(12, 0))
        self._build_quality_section(frame).grid(row=3, column=0, sticky="ew", pady=(12, 0))
        self._build_policy_section(frame).grid(row=4, column=0, sticky="ew", pady=(12, 0))
        self._build_metadata_section(frame).grid(row=5, column=0, sticky="ew", pady=(12, 0))
        self._build_button_row(frame).grid(row=6, column=0, sticky="ew", pady=(16, 0))

    def _build_language_section(self, parent: ttk.Frame) -> ttk.LabelFrame:
        section = ttk.LabelFrame(parent, padding=12)
        section.columnconfigure(1, weight=1)
        self.sections["language"] = section

        label = ttk.Label(section)
        label.grid(row=0, column=0, sticky="w")
        self.widgets["language_label"] = label

        combo = ttk.Combobox(
            section,
            textvariable=self.language_label,
            values=list(LANGUAGE_LABELS.keys()),
            state="readonly",
            width=14,
        )
        combo.grid(row=0, column=1, sticky="w", padx=(12, 0))
        combo.bind("<<ComboboxSelected>>", self._on_language_selected)
        self.widgets["language_combo"] = combo
        return section

    def _build_output_section(self, parent: ttk.Frame) -> ttk.LabelFrame:
        section = ttk.LabelFrame(parent, padding=12)
        section.columnconfigure(1, weight=1)
        self.sections["output"] = section

        self.same_folder_button = ttk.Radiobutton(
            section,
            value=OUTPUT_MODE_SAME_FOLDER,
            variable=self.output_mode,
            command=self._update_fixed_folder_state,
        )
        self.same_folder_button.grid(row=0, column=0, sticky="w")
        self.widgets["same_folder"] = self.same_folder_button

        self.fixed_folder_button = ttk.Radiobutton(
            section,
            value=OUTPUT_MODE_FIXED_FOLDER,
            variable=self.output_mode,
            command=self._update_fixed_folder_state,
        )
        self.fixed_folder_button.grid(row=1, column=0, sticky="w", pady=(6, 0))
        self.widgets["fixed_folder"] = self.fixed_folder_button

        self.converted_subfolder_button = ttk.Radiobutton(
            section,
            value=OUTPUT_MODE_CONVERTED_SUBFOLDER,
            variable=self.output_mode,
            command=self._update_fixed_folder_state,
        )
        self.converted_subfolder_button.grid(row=2, column=0, sticky="w", pady=(6, 0))
        self.widgets["converted_subfolder"] = self.converted_subfolder_button

        self.current_folder_value = ttk.Label(section, wraplength=420)
        self.current_folder_value.grid(row=1, column=1, sticky="ew", padx=(12, 8), pady=(6, 0))
        self.choose_button = ttk.Button(section, command=self.choose_folder)
        self.choose_button.grid(row=1, column=2, sticky="e", pady=(6, 0))
        self.widgets["choose"] = self.choose_button
        return section

    def _build_format_section(self, parent: ttk.Frame) -> ttk.LabelFrame:
        section = ttk.LabelFrame(parent, padding=12)
        self.sections["format"] = section
        self.format_buttons: dict[str, ttk.Radiobutton] = {}
        for index, output_format in enumerate((FORMAT_JPEG, FORMAT_PNG, FORMAT_WEBP)):
            state = "disabled" if output_format == FORMAT_WEBP and not self.webp_supported else "normal"
            button = ttk.Radiobutton(
                section,
                value=output_format,
                variable=self.output_format,
                state=state,
            )
            button.grid(row=0, column=index, sticky="w", padx=(0, 18))
            self.format_buttons[output_format] = button
        return section

    def _build_quality_section(self, parent: ttk.Frame) -> ttk.LabelFrame:
        section = ttk.LabelFrame(parent, padding=12)
        self.sections["quality"] = section
        for column in range(3):
            section.columnconfigure(column, weight=1)

        jpeg = ttk.Frame(section)
        jpeg.grid(row=0, column=0, sticky="nw", padx=(0, 16))
        self.widgets["jpeg_heading"] = ttk.Label(jpeg)
        self.widgets["jpeg_heading"].grid(row=0, column=0, columnspan=2, sticky="w")
        self.widgets["jpeg_quality_label"] = ttk.Label(jpeg)
        self.widgets["jpeg_quality_label"].grid(row=1, column=0, sticky="w", pady=(6, 0))
        ttk.Spinbox(jpeg, from_=1, to=100, width=5, textvariable=self.jpeg_quality).grid(
            row=1, column=1, sticky="w", pady=(6, 0)
        )
        self.widgets["jpeg_optimize"] = ttk.Checkbutton(jpeg, variable=self.jpeg_optimize)
        self.widgets["jpeg_optimize"].grid(row=2, column=0, columnspan=2, sticky="w", pady=(6, 0))
        self.widgets["jpeg_progressive"] = ttk.Checkbutton(jpeg, variable=self.jpeg_progressive)
        self.widgets["jpeg_progressive"].grid(
            row=3, column=0, columnspan=2, sticky="w", pady=(6, 0)
        )

        png = ttk.Frame(section)
        png.grid(row=0, column=1, sticky="nw", padx=(0, 16))
        self.widgets["png_heading"] = ttk.Label(png)
        self.widgets["png_heading"].grid(row=0, column=0, columnspan=2, sticky="w")
        self.widgets["png_compress_label"] = ttk.Label(png)
        self.widgets["png_compress_label"].grid(row=1, column=0, sticky="w", pady=(6, 0))
        ttk.Spinbox(png, from_=0, to=9, width=5, textvariable=self.png_compress_level).grid(
            row=1, column=1, sticky="w", pady=(6, 0)
        )

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

    def _build_policy_section(self, parent: ttk.Frame) -> ttk.LabelFrame:
        section = ttk.LabelFrame(parent, padding=12)
        section.columnconfigure(1, weight=1)
        self.sections["policy"] = section
        self.widgets["when_output_exists"] = ttk.Label(section)
        self.widgets["when_output_exists"].grid(row=0, column=0, sticky="w")
        self.overwrite_combo = ttk.Combobox(
            section,
            textvariable=self.overwrite_policy_label,
            state="readonly",
            width=28,
        )
        self.overwrite_combo.grid(row=0, column=1, sticky="w", padx=(12, 0))
        self.overwrite_combo.bind("<<ComboboxSelected>>", self._on_overwrite_selected)
        return section

    def _build_metadata_section(self, parent: ttk.Frame) -> ttk.LabelFrame:
        section = ttk.LabelFrame(parent, padding=12)
        self.sections["metadata"] = section
        self.widgets["keep_exif"] = ttk.Checkbutton(section, variable=self.keep_exif)
        self.widgets["keep_exif"].grid(row=0, column=0, sticky="w", padx=(0, 18))
        self.widgets["keep_icc_profile"] = ttk.Checkbutton(section, variable=self.keep_icc_profile)
        self.widgets["keep_icc_profile"].grid(row=0, column=1, sticky="w", padx=(0, 18))
        self.widgets["remove_gps"] = ttk.Checkbutton(section, variable=self.remove_gps)
        self.widgets["remove_gps"].grid(row=0, column=2, sticky="w", padx=(0, 18))
        self.widgets["open_output_folder"] = ttk.Checkbutton(
            section,
            variable=self.open_output_folder,
        )
        self.widgets["open_output_folder"].grid(row=1, column=0, columnspan=3, sticky="w", pady=(6, 0))
        return section

    def _build_button_row(self, parent: ttk.Frame) -> ttk.Frame:
        row = ttk.Frame(parent)
        row.columnconfigure(0, weight=1)
        self.widgets["save"] = ttk.Button(row, command=self.save)
        self.widgets["save"].grid(row=0, column=1, padx=(0, 8))
        self.widgets["close"] = ttk.Button(row, command=self.root.destroy)
        self.widgets["close"].grid(row=0, column=2)
        return row

    def choose_folder(self) -> None:
        initial_dir = str(self.fixed_output_dir) if self.fixed_output_dir else str(Path.home())
        selected = filedialog.askdirectory(parent=self.root, initialdir=initial_dir)
        if selected:
            self.fixed_output_dir = Path(selected)
            self.current_folder_value.configure(text=self._folder_label())
            self.output_mode.set(OUTPUT_MODE_FIXED_FOLDER)
            self._update_fixed_folder_state()

    def save(self) -> None:
        if self.output_format.get() == FORMAT_WEBP and not self.webp_supported:
            messagebox.showerror(
                self._t("settings_title"),
                self._t("webp_unavailable_error"),
                parent=self.root,
            )
            return

        try:
            saved_path = save_config(self._config_from_ui())
        except ConfigError as exc:
            messagebox.showerror(self._t("settings_title"), str(exc), parent=self.root)
            return

        messagebox.showinfo(
            self._t("settings_title"),
            self._t("saved").format(path=saved_path),
            parent=self.root,
        )

    def _config_from_ui(self) -> AppConfig:
        output_mode = self.output_mode.get()
        return AppConfig(
            output_mode=output_mode,
            output_dir=self.fixed_output_dir if output_mode == OUTPUT_MODE_FIXED_FOLDER else None,
            output_format=self.output_format.get(),
            jpeg_quality=self.jpeg_quality.get(),
            jpeg_optimize=self.jpeg_optimize.get(),
            jpeg_progressive=self.jpeg_progressive.get(),
            webp_quality=self.webp_quality.get(),
            webp_lossless=self.webp_lossless.get(),
            png_compress_level=self.png_compress_level.get(),
            overwrite_policy=self.overwrite_policy,
            keep_exif=self.keep_exif.get(),
            keep_icc_profile=self.keep_icc_profile.get(),
            remove_gps=self.remove_gps.get(),
            open_output_folder=self.open_output_folder.get(),
            language=self.language,
        )

    def _initial_output_format(self) -> str:
        if self.config.output_format == FORMAT_WEBP and not self.webp_supported:
            return FORMAT_JPEG
        return self.config.output_format

    def _folder_label(self) -> str:
        if self.fixed_output_dir is None:
            return self._t("no_fixed_folder")
        return str(self.fixed_output_dir)

    def _update_fixed_folder_state(self) -> None:
        state = "normal" if self.output_mode.get() == OUTPUT_MODE_FIXED_FOLDER else "disabled"
        self.choose_button.configure(state=state)

    def _on_language_selected(self, _event: object | None = None) -> None:
        self.language = LANGUAGE_LABELS[self.language_label.get()]
        self._apply_language()

    def _on_overwrite_selected(self, _event: object | None = None) -> None:
        labels = self._policy_values_by_label()
        self.overwrite_policy = labels[self.overwrite_policy_label.get()]

    def _apply_language(self) -> None:
        self.language_label.set(LANGUAGE_NAMES[self.language])
        self.root.title(self._t("window_title"))
        self.sections["language"].configure(text=self._t("language_section"))
        self.sections["output"].configure(text=self._t("output_section"))
        self.sections["format"].configure(text=self._t("format_section"))
        self.sections["quality"].configure(text=self._t("quality_section"))
        self.sections["policy"].configure(text=self._t("policy_section"))
        self.sections["metadata"].configure(text=self._t("metadata_section"))

        text_keys = {
            "language_label": "language_label",
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
            "when_output_exists": "when_output_exists",
            "keep_exif": "keep_exif",
            "keep_icc_profile": "keep_icc_profile",
            "remove_gps": "remove_gps",
            "open_output_folder": "open_output_folder",
            "save": "save",
            "close": "close",
        }
        for widget_key, translation_key in text_keys.items():
            self.widgets[widget_key].configure(text=self._t(translation_key))

        for output_format, button in self.format_buttons.items():
            label = FORMAT_LABELS[output_format]
            if output_format == FORMAT_WEBP and not self.webp_supported:
                label += self._t("webp_unavailable_suffix")
            button.configure(text=label)

        policy_labels = self._policy_labels()
        self.overwrite_combo.configure(values=list(policy_labels.values()))
        self.overwrite_policy_label.set(policy_labels[self.overwrite_policy])
        self.current_folder_value.configure(text=self._folder_label())

    def _policy_labels(self) -> dict[str, str]:
        return {
            value: self._t(key)
            for value, key in POLICY_KEYS.items()
        }

    def _policy_values_by_label(self) -> dict[str, str]:
        return {
            label: value
            for value, label in self._policy_labels().items()
        }

    def _t(self, key: str) -> str:
        return TRANSLATIONS[self.language][key]

    def _show_config_error(self, config_error: str) -> None:
        messagebox.showwarning(
            self._t("settings_title"),
            self._t("config_error").format(error=config_error),
            parent=self.root,
        )

    def _show_webp_unavailable_warning(self) -> None:
        messagebox.showwarning(
            self._t("settings_title"),
            self._t("webp_saved_unavailable"),
            parent=self.root,
        )


def run_settings_app() -> None:
    root = Tk()
    SettingsWindow(root)
    root.mainloop()

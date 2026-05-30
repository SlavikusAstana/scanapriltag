#!/usr/bin/env python3
"""AprilTag Scanner Pro - сканирование AprilTag через веб-камеру."""

from __future__ import annotations

import csv
import io
import json
import sys
import threading
import time
import traceback
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import cv2
import numpy as np
from PIL import Image, ImageTk
from pupil_apriltags import Detector

LOG_FILE = Path(__file__).with_name("scan_error.log")
UI_FONT = ("Segoe UI", 10)
UI_FONT_BOLD = ("Segoe UI", 10, "bold")
UI_FONT_TITLE = ("Segoe UI", 12, "bold")
UI_FONT_SMALL = ("Segoe UI", 9)

TAG_FAMILIES: dict[str, str] = {
    "tag36h11": "36h11 (стандарт)",
    "tag25h9": "25h9",
    "tag16h5": "16h5",
    "tagCircle21h7": "Circle21h7",
    "tagCircle49h12": "Circle49h12",
    "tagStandard41h12": "Standard41h12",
    "tagStandard52h13": "Standard52h13",
    "tagCustom48h12": "Custom48h12",
}

PRESET_LABELS = {
    "fast": "Быстро",
    "balanced": "Баланс",
    "accurate": "Точно",
}

PRESETS: dict[str, dict[str, float | int]] = {
    "fast": {"detect_width": 640, "quad_decimate": 2.0, "detect_stride": 2},
    "balanced": {"detect_width": 960, "quad_decimate": 1.5, "detect_stride": 1},
    "accurate": {"detect_width": 1280, "quad_decimate": 1.0, "detect_stride": 1},
}

AUTO_PROBE_FAMILIES = list(TAG_FAMILIES.keys())
PROBE_PRIORITY = ["tag36h11", "tag25h9", "tag16h5"] + [
    f for f in AUTO_PROBE_FAMILIES if f not in {"tag36h11", "tag25h9", "tag16h5"}
]
PROBE_DETECT_WIDTH = 560
PROBE_DECIMATE = 2.0
PROBE_STRIDE = 4
MIN_DECISION_MARGIN = 20.0

TagKey = tuple[str, int]


@dataclass
class TagRecord:
    family: str
    tag_id: int
    duplicate: bool = False

    @property
    def key(self) -> TagKey:
        return (self.family, self.tag_id)

    def label(self) -> str:
        short = self.family.replace("tag", "")
        return f"{short}:{self.tag_id}"


def show_fatal_error(title: str, message: str) -> None:
    LOG_FILE.write_text(message, encoding="utf-8")
    try:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(title, f"{message}\n\nПодробности: {LOG_FILE.name}")
        root.destroy()
    except Exception:
        print(message, file=sys.stderr)


def open_camera(index: int) -> cv2.VideoCapture | None:
    cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
    if not cap.isOpened():
        cap.release()
        cap = cv2.VideoCapture(index)
    if not cap.isOpened():
        cap.release()
        return None
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    cap.set(cv2.CAP_PROP_FPS, 30)
    return cap


def normalize_family(raw: Any, fallback: str) -> str:
    if isinstance(raw, bytes):
        return raw.decode("ascii", errors="ignore")
    if isinstance(raw, str) and raw:
        return raw
    return fallback


def scale_detections(tags: list[Any], inv_scale: float) -> list[Any]:
    if inv_scale == 1.0:
        return tags
    for tag in tags:
        tag.corners = tag.corners * inv_scale
    return tags


class AprilTagScannerApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("AprilTag Scanner Pro")
        self.root.minsize(980, 680)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self.cap: cv2.VideoCapture | None = None
        self._scan_families: list[str] = []
        self.scanning = False
        self.family_auto_locked = False
        self._probe_family_idx = 0
        self._running = True
        self._frame_idx = 0
        self._last_tags: list[Any] = []

        self._det_lock = threading.Lock()
        self._det_pending: tuple[np.ndarray, float, list[str], bool] | None = None
        self._det_busy = False
        self._det_cache_version = 0
        self._det_thread = threading.Thread(target=self._detect_worker_loop, daemon=True)

        self.tag_records: list[TagRecord] = []
        self.duplicates: set[TagKey] = set()
        self.visible_now: set[TagKey] = set()
        self.miss_counts: dict[TagKey, int] = {}

        self.photo: ImageTk.PhotoImage | None = None
        self._preview_w = 640
        self._preview_h = 480
        self._detect_ms = 0.0
        self._frame_times: deque[float] = deque(maxlen=30)

        self.status_label: ttk.Label | None = None
        self.right_panel: ttk.Frame | None = None
        self.family_combo: ttk.Combobox | None = None
        self.preset_combo: ttk.Combobox | None = None

        self.family_mode = tk.StringVar(value="tag36h11")
        self.preset_mode = tk.StringVar(value="balanced")
        self.camera_var = tk.IntVar(value=0)
        self.miss_frames_var = tk.IntVar(value=8)
        self.beep_var = tk.BooleanVar(value=True)
        self.multi_family_var = tk.BooleanVar(value=False)

        self._build_ui()
        self._bind_shortcuts()
        self._sync_preset_params()
        self._apply_detector()
        self._det_thread.start()
        self._show_window()
        self.root.bind("<Configure>", self._on_root_configure)
        self.root.after(10, self._init_camera)

    def _bind_shortcuts(self) -> None:
        self.root.bind("<space>", lambda _e: self._toggle_scan())
        self.root.bind("<Control-s>", lambda _e: self.save_results())
        self.root.bind("<Control-r>", lambda _e: self.reset_scan())

    def _toggle_scan(self) -> None:
        if self.scanning:
            self.stop_scan()
        elif self.start_btn.cget("state") != tk.DISABLED:
            self.start_scan()

    def _family_label(self, family: str) -> str:
        return TAG_FAMILIES.get(family, family.replace("tag", ""))

    def _is_auto_probe_mode(self) -> bool:
        return not self.scanning and not self.family_auto_locked and not self.multi_family_var.get()

    def _active_family_list(self) -> list[str]:
        if self.multi_family_var.get():
            return ["tag36h11", "tag25h9", "tag16h5"]
        return [self.family_mode.get()]

    def _current_families(self) -> str:
        return ", ".join(self._active_family_list())

    def _sync_preset_params(self) -> None:
        preset = PRESETS[self.preset_mode.get()]
        self.detect_width = int(preset["detect_width"])
        self.quad_decimate = float(preset["quad_decimate"])
        self.detect_stride = int(preset["detect_stride"])

    def _bump_detector_cache(self) -> None:
        self._det_cache_version += 1

    def _probe_family_this_frame(self) -> str:
        return PROBE_PRIORITY[self._probe_family_idx % len(PROBE_PRIORITY)]

    def _advance_probe_family(self) -> None:
        self._probe_family_idx += 1

    def _families_for_detection(self) -> tuple[list[str], bool, int]:
        if self._is_auto_probe_mode():
            return [self._probe_family_this_frame()], True, PROBE_DETECT_WIDTH
        if not self._scan_families:
            return [], False, self.detect_width
        stride = self.detect_stride if not self.scanning else 1
        return self._scan_families, False, self.detect_width

    def _prepare_gray(self, frame: np.ndarray, detect_width: int) -> tuple[np.ndarray, float]:
        h, w = frame.shape[:2]
        scale = min(1.0, detect_width / w)
        if scale < 1.0:
            small_w = int(w * scale)
            small_h = int(h * scale)
            gray = cv2.cvtColor(
                cv2.resize(frame, (small_w, small_h), interpolation=cv2.INTER_AREA),
                cv2.COLOR_BGR2GRAY,
            )
            return gray, 1.0 / scale
        return cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), 1.0

    def _detect_worker_loop(self) -> None:
        cache: dict[tuple[str, bool], Detector] = {}
        cache_version = -1

        while self._running:
            job = None
            with self._det_lock:
                job = self._det_pending
                self._det_pending = None

            if job is None:
                time.sleep(0.008)
                continue

            gray, inv_scale, families, probe = job

            if cache_version != self._det_cache_version:
                cache.clear()
                cache_version = self._det_cache_version

            quad = PROBE_DECIMATE if probe else self.quad_decimate
            nthreads = 2 if probe else 4

            t0 = time.perf_counter()
            all_tags: list[Any] = []
            for family in families:
                key = (family, probe)
                if key not in cache:
                    cache[key] = Detector(
                        families=family,
                        nthreads=nthreads,
                        quad_decimate=quad,
                        quad_sigma=0.0,
                        refine_edges=True,
                        decode_sharpening=0.25,
                    )
                found = scale_detections(cache[key].detect(gray), inv_scale)
                for tag in found:
                    tag.tag_family = normalize_family(getattr(tag, "tag_family", None), family)
                all_tags.extend(found)

            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            with self._det_lock:
                self._last_tags = all_tags
                self._detect_ms = elapsed_ms
                self._det_busy = False

    def _request_detection(self, frame: np.ndarray) -> None:
        if self._is_auto_probe_mode():
            if (self._frame_idx % PROBE_STRIDE) != 0:
                return
        else:
            if not self._scan_families:
                return
            if (self._frame_idx % self.detect_stride) != 0 and not self.scanning:
                return

        families, probe, detect_width = self._families_for_detection()
        if not families:
            return

        with self._det_lock:
            if self._det_busy:
                return
            gray, inv_scale = self._prepare_gray(frame, detect_width)
            self._det_busy = True
            self._det_pending = (gray, inv_scale, families, probe)
            if probe:
                self._advance_probe_family()

    def _apply_detector(self) -> None:
        self._sync_preset_params()
        self._bump_detector_cache()

        if self._is_auto_probe_mode():
            self._scan_families = []
            self._probe_family_idx = 0
            self.root.title("AprilTag Scanner Pro - автоопределение")
            return

        self._scan_families = self._active_family_list()
        short = "+".join(f.replace("tag", "") for f in self._scan_families)
        self.root.title(f"AprilTag Scanner Pro - {short}")

    def _on_family_picked(self, *_args: object) -> None:
        if self.scanning:
            return
        self.family_auto_locked = True
        self._apply_detector()
        label = self._family_label(self.family_mode.get())
        self.status_var.set(f'Семейство: {label} - нажмите "Старт"')

    def _on_multi_toggled(self) -> None:
        if self.scanning:
            return
        if self.multi_family_var.get():
            self.family_auto_locked = True
        else:
            self.family_auto_locked = False
        self._apply_detector()
        if self.family_auto_locked:
            self.status_var.set('Режим нескольких семейств - нажмите "Старт"')
        else:
            self.status_var.set("Покажите тег камере - семейство определится автоматически")

    def _on_preset_changed(self, *_args: object) -> None:
        if self.scanning:
            return
        self._apply_detector()

    def _try_auto_select_family(self, tags: list[Any]) -> None:
        if not self._is_auto_probe_mode() or not tags:
            return

        best = max(tags, key=lambda t: float(getattr(t, "decision_margin", 0.0)))
        if float(getattr(best, "decision_margin", 0.0)) < MIN_DECISION_MARGIN:
            return

        family = normalize_family(getattr(best, "tag_family", None), self.family_mode.get())
        if family not in TAG_FAMILIES:
            return

        tag_id = int(best.tag_id)
        self.family_mode.set(family)
        self.family_auto_locked = True
        with self._det_lock:
            self._last_tags = []
        self._apply_detector()

        label = self._family_label(family)
        self.status_var.set(
            f'Определено: {label}, ID {tag_id} - нажмите "Старт" (или Space)'
        )

    def _on_root_configure(self, event: tk.Event | None = None) -> None:
        if event is not None and event.widget is not self.root:
            return
        if self.status_label is not None and self.right_panel is not None:
            width = max(self.right_panel.winfo_width() - 16, 180)
            self.status_label.configure(wraplength=width)
        if self.video_label is not None:
            w = max(self.video_label.winfo_width(), 320)
            h = max(self.video_label.winfo_height(), 240)
            if w != self._preview_w or h != self._preview_h:
                self._preview_w, self._preview_h = w, h

    def _show_window(self) -> None:
        self.root.update_idletasks()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        w = max(min(int(sw * 0.93), 1560), 980)
        h = max(min(int(sh * 0.9), 940), 680)
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.root.geometry(f"{w}x{h}+{x}+{y}")
        self.root.deiconify()
        self.root.lift()
        self.root.attributes("-topmost", True)
        self.root.after(300, lambda: self.root.attributes("-topmost", False))
        self.root.focus_force()
        self.root.after(100, self._init_paned_split)

    def _init_paned_split(self) -> None:
        try:
            self.paned.sashpos(0, max(int(self.root.winfo_width() * 0.6), 520))
        except tk.TclError:
            pass
        self._on_root_configure()

    def _build_ui(self) -> None:
        main = ttk.Frame(self.root, padding=10)
        main.pack(fill=tk.BOTH, expand=True)
        main.columnconfigure(0, weight=1)
        main.rowconfigure(0, weight=1)

        paned = ttk.Panedwindow(main, orient=tk.HORIZONTAL)
        paned.grid(row=0, column=0, sticky="nsew")
        self.paned = paned

        left = ttk.Frame(paned, padding=(0, 0, 8, 0))
        left.columnconfigure(0, weight=1)
        left.rowconfigure(0, weight=1)
        left.rowconfigure(1, weight=0)
        paned.add(left, weight=3)

        self.video_label = ttk.Label(left, text="Подключение камеры...", anchor=tk.CENTER)
        self.video_label.grid(row=0, column=0, sticky="nsew")

        self.perf_var = tk.StringVar(value="FPS: --  |  Detect: -- ms")
        ttk.Label(left, textvariable=self.perf_var, font=UI_FONT_SMALL).grid(
            row=1, column=0, sticky="w", pady=(6, 0)
        )

        right = ttk.Frame(paned, padding=(8, 0, 0, 0))
        right.columnconfigure(0, weight=1)
        right.rowconfigure(7, weight=2)
        right.rowconfigure(10, weight=1)
        paned.add(right, weight=1)
        self.right_panel = right

        ttk.Label(right, text="AprilTag Scanner Pro", font=UI_FONT_TITLE).grid(
            row=0, column=0, sticky="w", pady=(0, 4)
        )

        self.status_var = tk.StringVar(value="Загрузка...")
        self.status_label = ttk.Label(right, textvariable=self.status_var, wraplength=280)
        self.status_label.grid(row=1, column=0, sticky="ew", pady=(0, 6))

        settings = ttk.LabelFrame(right, text="Настройки", padding=6)
        settings.grid(row=2, column=0, sticky="ew", pady=(0, 8))
        settings.columnconfigure(1, weight=1)

        ttk.Label(settings, text="Семейство (авто):").grid(row=0, column=0, sticky="w")
        self.family_combo = ttk.Combobox(
            settings,
            textvariable=self.family_mode,
            values=list(TAG_FAMILIES.keys()),
            state="readonly",
            width=18,
        )
        self.family_combo.grid(row=0, column=1, sticky="ew", padx=(6, 0))
        self.family_combo.bind("<<ComboboxSelected>>", self._on_family_picked)

        ttk.Checkbutton(
            settings,
            text="Несколько семейств (36h11+25h9+16h5)",
            variable=self.multi_family_var,
            command=self._on_multi_toggled,
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(4, 0))

        ttk.Label(settings, text="Скорость:").grid(row=2, column=0, sticky="w", pady=(4, 0))
        self.preset_combo = ttk.Combobox(
            settings,
            textvariable=self.preset_mode,
            values=list(PRESETS.keys()),
            state="readonly",
            width=18,
        )
        self.preset_combo.grid(row=2, column=1, sticky="ew", padx=(6, 0), pady=(4, 0))
        self.preset_combo.bind("<<ComboboxSelected>>", self._on_preset_changed)

        cam_row = ttk.Frame(settings)
        cam_row.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(4, 0))
        ttk.Label(cam_row, text="Камера:").pack(side=tk.LEFT)
        ttk.Spinbox(cam_row, from_=0, to=5, width=4, textvariable=self.camera_var).pack(side=tk.LEFT, padx=(6, 12))
        ttk.Label(cam_row, text="Miss:").pack(side=tk.LEFT)
        ttk.Spinbox(cam_row, from_=3, to=30, width=4, textvariable=self.miss_frames_var).pack(side=tk.LEFT, padx=(6, 0))
        ttk.Checkbutton(settings, text="Звук при повторе", variable=self.beep_var).grid(
            row=4, column=0, columnspan=2, sticky="w", pady=(4, 0)
        )

        btn_row = ttk.Frame(right)
        btn_row.grid(row=3, column=0, sticky="ew", pady=(0, 6))
        for i in range(3):
            btn_row.columnconfigure(i, weight=1)

        self.start_btn = ttk.Button(btn_row, text="Старт", command=self.start_scan, state=tk.DISABLED)
        self.start_btn.grid(row=0, column=0, sticky="ew", padx=(0, 4))
        self.stop_btn = ttk.Button(btn_row, text="Стоп", command=self.stop_scan, state=tk.DISABLED)
        self.stop_btn.grid(row=0, column=1, sticky="ew", padx=4)
        self.reset_btn = ttk.Button(btn_row, text="Сброс", command=self.reset_scan, state=tk.DISABLED)
        self.reset_btn.grid(row=0, column=2, sticky="ew", padx=(4, 0))

        self.save_btn = ttk.Button(right, text="Сохранить (Ctrl+S)", command=self.save_results, state=tk.DISABLED)
        self.save_btn.grid(row=4, column=0, sticky="ew", pady=(0, 6))

        ttk.Label(right, text="Список (live):", font=UI_FONT).grid(row=5, column=0, sticky="w")
        self.count_var = tk.StringVar(value="Записано: 0")
        ttk.Label(right, textvariable=self.count_var, font=UI_FONT_SMALL).grid(row=6, column=0, sticky="w")

        list_frame = ttk.Frame(right)
        list_frame.grid(row=7, column=0, sticky="nsew", pady=(2, 6))
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)
        list_scroll = ttk.Scrollbar(list_frame, orient=tk.VERTICAL)
        list_scroll.grid(row=0, column=1, sticky="ns")
        self.live_list = tk.Text(
            list_frame,
            yscrollcommand=list_scroll.set,
            font=UI_FONT,
            height=7,
            wrap=tk.NONE,
            state=tk.DISABLED,
            cursor="arrow",
        )
        self.live_list.grid(row=0, column=0, sticky="nsew")
        list_scroll.config(command=self.live_list.yview)
        self.live_list.tag_configure("normal", foreground="#000000", font=UI_FONT)
        self.live_list.tag_configure("duplicate", foreground="#cc0000", font=UI_FONT_BOLD)

        ttk.Separator(right, orient=tk.HORIZONTAL).grid(row=8, column=0, sticky="ew", pady=4)
        ttk.Label(right, text='Результат после "Стоп":').grid(row=9, column=0, sticky="w")

        result_frame = ttk.Frame(right)
        result_frame.grid(row=10, column=0, sticky="nsew")
        result_frame.columnconfigure(0, weight=1)
        result_frame.rowconfigure(0, weight=1)
        result_scroll = ttk.Scrollbar(result_frame, orient=tk.VERTICAL)
        result_scroll.grid(row=0, column=1, sticky="ns")
        self.result_text = tk.Text(
            result_frame,
            yscrollcommand=result_scroll.set,
            height=5,
            wrap=tk.WORD,
            font=UI_FONT,
            state=tk.DISABLED,
            cursor="arrow",
        )
        self.result_text.grid(row=0, column=0, sticky="nsew")
        result_scroll.config(command=self.result_text.yview)

        ttk.Label(
            right,
            text="Space - старт/стоп  |  Ctrl+S - сохранить  |  Ctrl+R - сброс",
            font=UI_FONT_SMALL,
        ).grid(row=11, column=0, sticky="w", pady=(6, 0))

    def _init_camera(self) -> None:
        self.status_var.set("Подключение камеры...")
        self.video_label.config(text="Подключение камеры...")
        threading.Thread(target=self._camera_worker, daemon=True).start()

    def _camera_worker(self) -> None:
        index = int(self.camera_var.get())
        cap = open_camera(index)

        def finish() -> None:
            if cap is None or not cap.isOpened():
                messagebox.showerror(
                    "Ошибка",
                    f"Не удалось открыть камеру {index}.\nЗакройте другие программы, использующие камеру.",
                )
                self.on_close()
                return
            self.cap = cap
            self.status_var.set("Покажите тег камере - семейство определится автоматически")
            self.video_label.config(text="")
            self.start_btn.config(state=tk.NORMAL)
            self.reset_btn.config(state=tk.NORMAL)
            self._set_settings_state(tk.NORMAL)
            self._update_frame()

        self.root.after(0, finish)

    def _set_settings_state(self, state: str) -> None:
        for widget in (self.family_combo, self.preset_combo):
            if widget is not None:
                widget.config(state="readonly" if state == tk.NORMAL else state)

    def _detect_tags(self, frame: np.ndarray) -> list[Any]:
        self._request_detection(frame)
        with self._det_lock:
            return list(self._last_tags)

    def start_scan(self) -> None:
        if not self.multi_family_var.get() and not self.family_auto_locked:
            self.family_auto_locked = True
            self._apply_detector()

        self.scanning = True
        self.visible_now.clear()
        self.miss_counts.clear()
        self.status_var.set("Сканирование - показывайте лист с тегами")
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.save_btn.config(state=tk.DISABLED)
        self._set_settings_state(tk.DISABLED)

    def stop_scan(self) -> None:
        self.scanning = False
        self.visible_now.clear()
        self.miss_counts.clear()
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.save_btn.config(state=tk.NORMAL)
        self._set_settings_state(tk.NORMAL)
        self._show_results()

    def reset_scan(self) -> None:
        self.scanning = False
        self.tag_records.clear()
        self.duplicates.clear()
        self.visible_now.clear()
        self.miss_counts.clear()
        self._clear_live_list()
        self._set_result_text("")
        self.status_var.set("Пауза - список сброшен")
        self._update_count_label(in_frame=0)
        self.family_auto_locked = False
        with self._det_lock:
            self._last_tags = []
        self._probe_family_idx = 0
        self._apply_detector()
        self.status_var.set("Покажите тег камере - семейство определится автоматически")
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.save_btn.config(state=tk.DISABLED)
        self._set_settings_state(tk.NORMAL)

    def _unique_keys(self) -> set[TagKey]:
        return {r.key for r in self.tag_records}

    def _build_results_lines(self) -> tuple[list[str], str]:
        lines: list[str] = []
        if not self.tag_records:
            lines.append("Список пуст - теги не обнаружены.")
            return lines, "Сканирование завершено."

        lines.append(f"Семейства: {self._current_families()}")
        lines.append(f"Всего записано: {len(self.tag_records)}")
        lines.append(f"Уникальных: {len(self._unique_keys())}")
        lines.append("")
        for i, rec in enumerate(self.tag_records, start=1):
            mark = " (повтор)" if rec.duplicate else ""
            lines.append(f"  {i}. {rec.label()}{mark}")
        lines.append("")
        if self.duplicates:
            dup_labels = ", ".join(f"{f.replace('tag', '')}:{tid}" for f, tid in sorted(self.duplicates))
            lines.append(f"ПОВТОРЫ ЕСТЬ: {dup_labels}")
            summary = f"Готово. Повторы есть: {dup_labels}"
        else:
            lines.append("ПОВТОРОВ НЕТ - все теги уникальные.")
            summary = "Готово. Повторов нет."
        return lines, summary

    def _should_record(self, key: TagKey) -> tuple[bool, bool]:
        keys = [r.key for r in self.tag_records]
        if key not in keys:
            return True, False
        last_pos = max(i for i, k in enumerate(keys) if k == key)
        other_since = any(keys[i] != key for i in range(last_pos + 1, len(keys)))
        return (True, True) if other_since else (False, False)

    def _clear_live_list(self) -> None:
        self.live_list.config(state=tk.NORMAL)
        self.live_list.delete("1.0", tk.END)
        self.live_list.config(state=tk.DISABLED)

    def _append_tag(self, family: str, tag_id: int) -> None:
        key = (family, tag_id)
        should_record, is_dup = self._should_record(key)
        if not should_record:
            return

        rec = TagRecord(family=family, tag_id=tag_id, duplicate=is_dup)
        if is_dup:
            self.duplicates.add(key)
        self.tag_records.append(rec)

        suffix = "  [ПОВТОР]" if is_dup else ""
        line = f"{len(self.tag_records)}. {rec.label()}{suffix}\n"
        style = "duplicate" if is_dup else "normal"
        self.live_list.config(state=tk.NORMAL)
        self.live_list.insert(tk.END, line, style)
        self.live_list.see(tk.END)
        self.live_list.config(state=tk.DISABLED)

        if is_dup:
            self.status_var.set(f"ПОВТОР! {rec.label()} - отложите этот тег")
            if self.beep_var.get():
                self.root.bell()

    def _export_payload(self) -> dict[str, Any]:
        return {
            "app": "AprilTag Scanner Pro",
            "date": datetime.now().isoformat(timespec="seconds"),
            "families": self._current_families(),
            "preset": self.preset_mode.get(),
            "total": len(self.tag_records),
            "unique": len(self._unique_keys()),
            "duplicates": [
                {"family": f, "id": tid} for f, tid in sorted(self.duplicates)
            ],
            "tags": [
                {
                    "index": i,
                    "family": r.family,
                    "id": r.tag_id,
                    "label": r.label(),
                    "duplicate": r.duplicate,
                }
                for i, r in enumerate(self.tag_records, start=1)
            ],
        }

    def save_results(self) -> None:
        if self.save_btn.cget("state") == tk.DISABLED:
            return

        default_name = f"apriltag_scan_{datetime.now():%Y%m%d_%H%M%S}.txt"
        path = filedialog.asksaveasfilename(
            title="Сохранить результат",
            defaultextension=".txt",
            initialfile=default_name,
            filetypes=[
                ("Текст", "*.txt"),
                ("CSV", "*.csv"),
                ("JSON", "*.json"),
                ("Все файлы", "*.*"),
            ],
        )
        if not path:
            return

        suffix = Path(path).suffix.lower()
        try:
            if suffix == ".json":
                Path(path).write_text(
                    json.dumps(self._export_payload(), ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
            elif suffix == ".csv":
                buf = io.StringIO()
                writer = csv.writer(buf)
                writer.writerow(["index", "family", "id", "label", "duplicate"])
                for i, r in enumerate(self.tag_records, start=1):
                    writer.writerow([i, r.family, r.tag_id, r.label(), r.duplicate])
                Path(path).write_text(buf.getvalue(), encoding="utf-8-sig")
            else:
                lines, _ = self._build_results_lines()
                header = f"AprilTag Scanner Pro\nДата: {datetime.now():%Y-%m-%d %H:%M:%S}\n\n"
                Path(path).write_text(header + "\n".join(lines) + "\n", encoding="utf-8")
        except OSError as exc:
            messagebox.showerror("Ошибка", f"Не удалось сохранить файл:\n{exc}")
            return

        messagebox.showinfo("Сохранено", f"Результат сохранён:\n{path}")

    def _set_result_text(self, text: str) -> None:
        self.result_text.config(state=tk.NORMAL)
        self.result_text.delete("1.0", tk.END)
        self.result_text.insert(tk.END, text)
        self.result_text.config(state=tk.DISABLED)

    def _show_results(self) -> None:
        lines, summary = self._build_results_lines()
        self._set_result_text("\n".join(lines))
        self.status_var.set(summary)
        if self.duplicates:
            messagebox.showwarning("Результат", summary)
        else:
            messagebox.showinfo("Результат", summary)

    def _update_count_label(self, in_frame: int) -> None:
        self.count_var.set(
            f"Записано: {len(self.tag_records)}  |  Уник.: {len(self._unique_keys())}  |  "
            f"В кадре: {in_frame}  |  Повторов: {len(self.duplicates)}"
        )

    def _process_detected_tags(self, tags: list[Any]) -> None:
        detected: dict[TagKey, Any] = {}
        for tag in tags:
            family = normalize_family(getattr(tag, "tag_family", None), self.family_mode.get())
            detected[(family, tag.tag_id)] = tag

        miss_limit = int(self.miss_frames_var.get())
        for key in list(self.visible_now):
            if key in detected:
                self.miss_counts[key] = 0
                continue
            missed = self.miss_counts.get(key, 0) + 1
            self.miss_counts[key] = missed
            if missed >= miss_limit:
                self.visible_now.discard(key)
                self.miss_counts.pop(key, None)

        new_keys = set(detected) - self.visible_now
        if new_keys:
            ordered = sorted(
                new_keys,
                key=lambda k: (detected[k].center[1], detected[k].center[0]),
            )
            for family, tag_id in ordered:
                self._append_tag(family, tag_id)
                self.visible_now.add((family, tag_id))
                self.miss_counts[(family, tag_id)] = 0

        self._update_count_label(len(detected))

    def _draw_tags(self, frame: np.ndarray, tags: list[Any]) -> None:
        probing = self._is_auto_probe_mode()
        for tag in tags:
            family = normalize_family(getattr(tag, "tag_family", None), self.family_mode.get())
            key = (family, tag.tag_id)
            is_dup = key in self.duplicates
            if is_dup:
                color = (0, 0, 220)
            elif probing:
                color = (0, 160, 255)
            else:
                color = (0, 220, 0)
            corners = tag.corners.astype(int)
            thickness = 3 if is_dup else 2
            for i in range(4):
                cv2.line(frame, tuple(corners[i]), tuple(corners[(i + 1) % 4]), color, thickness)
            center = tuple(corners.mean(axis=0).astype(int))
            short = family.replace("tag", "")
            if probing:
                label = f"{short}:{tag.tag_id}?"
            else:
                label = f"{short}:{tag.tag_id}" + (" DUP" if is_dup else "")
            cv2.putText(
                frame,
                label,
                (center[0] - 28, center[1] + 6),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                color,
                2,
            )

    def _render_preview(self, frame: np.ndarray) -> None:
        h, w = frame.shape[:2]
        scale = min(self._preview_w / w, self._preview_h / h, 1.0)
        if scale < 1.0:
            frame = cv2.resize(
                frame,
                (int(w * scale), int(h * scale)),
                interpolation=cv2.INTER_LINEAR,
            )
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(rgb)
        self.photo = ImageTk.PhotoImage(image=img)
        self.video_label.config(image=self.photo, text="")

    def _update_frame(self) -> None:
        if not self._running or self.cap is None or not self.cap.isOpened():
            return

        t_frame = time.perf_counter()
        ok, frame = self.cap.read()
        if ok:
            self._frame_idx += 1
            tags = self._detect_tags(frame)

            if not self.scanning:
                self._try_auto_select_family(tags)

            if self.scanning:
                self._process_detected_tags(tags)
            else:
                self.visible_now.clear()
                self.miss_counts.clear()
                if tags:
                    self._update_count_label(len(tags))

            self._draw_tags(frame, tags)
            self._render_preview(frame)

            elapsed = time.perf_counter() - t_frame
            self._frame_times.append(elapsed)
            avg = sum(self._frame_times) / len(self._frame_times)
            fps = 1.0 / avg if avg > 0 else 0.0
            self.perf_var.set(
                f"FPS: {fps:.1f}  |  Detect: {self._detect_ms:.0f} ms  |  "
                f"{PRESET_LABELS.get(self.preset_mode.get(), self.preset_mode.get())}"
                + ("  |  авто" if self._is_auto_probe_mode() else "")
            )

        delay = max(1, int(33 - (time.perf_counter() - t_frame) * 1000))
        self.root.after(delay, self._update_frame)

    def on_close(self) -> None:
        self._running = False
        if self._det_thread.is_alive():
            self._det_thread.join(timeout=0.5)
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        self.root.destroy()


def main() -> int:
    if sys.platform == "win32":
        try:
            if sys.stdout is not None:
                sys.stdout.reconfigure(encoding="utf-8")
            if sys.stderr is not None:
                sys.stderr.reconfigure(encoding="utf-8")
        except Exception:
            pass

    try:
        root = tk.Tk()
        root.withdraw()
        AprilTagScannerApp(root)
        root.mainloop()
        return 0
    except Exception:
        show_fatal_error("Ошибка запуска", traceback.format_exc())
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

"""GUI for AprilTag E57 extraction tool."""

from __future__ import annotations

import json
import os
import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from .detector import TAG_FAMILIES
from .fusion import FusionMode
from .pipeline_options import (
    FUSION_TOOLTIP,
    INTENSITY_REFINE_TOOLTIP,
    PANO_SCALE_FAST,
    PANO_SCALE_LABELS,
    PANO_SCALE_MAX,
    PANO_SCALE_TOOLTIPS,
    RAY_GUIDED_TOOLTIP,
    pano_scales_from_preset,
)
from .tooltip import ToolTip
from .pipeline import PipelineConfig, run_pipeline
from .register360_db import CoordExportMode


def _settings_path() -> Path:
    base = os.environ.get("LOCALAPPDATA") or str(Path.home())
    return Path(base) / "AprilTagE57Tool" / "gui.json"


def _load_gui_settings() -> dict:
    path = _settings_path()
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _save_gui_settings(data: dict) -> None:
    path = _settings_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError:
        pass


class AprilTagE57App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("AprilTag E57 — Register360 / RTC360")
        self.geometry("860x640")
        self.minsize(720, 520)

        self._cancel = False
        self._worker: threading.Thread | None = None
        self._log_queue: queue.Queue[str | tuple[str, float]] = queue.Queue()

        self._build_ui()
        self.after(100, self._poll_log)

    def _build_ui(self) -> None:
        pad = {"padx": 8, "pady": 4}

        frm = ttk.Frame(self)
        frm.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # E57 folder (project.db ищется в папке и в pano/)
        ttk.Label(frm, text="Папка E57:").grid(row=0, column=0, sticky=tk.W, **pad)
        saved = _load_gui_settings()
        self.var_folder = tk.StringVar(value=saved.get("e57_folder", ""))
        ttk.Entry(frm, textvariable=self.var_folder, width=70).grid(row=0, column=1, **pad)
        ttk.Button(frm, text="…", width=3, command=self._browse_folder).grid(row=0, column=2, **pad)

        # RealityScan GCP CSV
        ttk.Label(frm, text="RealityScan GCP:").grid(row=1, column=0, sticky=tk.W, **pad)
        self.var_csv = tk.StringVar(value=saved.get("csv_path", ""))
        ttk.Entry(frm, textvariable=self.var_csv, width=70).grid(row=1, column=1, **pad)
        ttk.Button(frm, text="…", width=3, command=self._browse_csv).grid(row=1, column=2, **pad)
        ttk.Label(
            frm,
            text="(пусто → apriltag_realityscan_gcp.csv; имена 36h11:xxx, WORKFLOW → Ground Control)",
        ).grid(row=2, column=1, sticky=tk.W, **pad)

        # Pano folder
        ttk.Label(frm, text="Панорамы:").grid(row=3, column=0, sticky=tk.W, **pad)
        self.var_pano = tk.StringVar(value=saved.get("pano_folder", ""))
        ttk.Entry(frm, textvariable=self.var_pano, width=70).grid(row=3, column=1, **pad)
        ttk.Button(frm, text="…", width=3, command=self._browse_pano).grid(row=3, column=2, **pad)

        # Options frame
        opt = ttk.LabelFrame(frm, text="Параметры")
        opt.grid(row=4, column=0, columnspan=3, sticky=tk.EW, **pad)
        opt.columnconfigure(2, weight=1)

        ttk.Label(opt, text="Панорама (ArUco):").grid(row=0, column=0, sticky=tk.W, padx=8, pady=4)
        self.var_pano_scale = tk.StringVar(value=PANO_SCALE_LABELS[PANO_SCALE_FAST])
        self._pano_combo = ttk.Combobox(
            opt,
            textvariable=self.var_pano_scale,
            values=list(PANO_SCALE_LABELS.values()),
            state="readonly",
            width=40,
        )
        self._pano_combo.grid(row=0, column=1, columnspan=2, sticky=tk.W)
        self._pano_tooltip = ToolTip(self._pano_combo, get_text=self._pano_tooltip_text)

        ttk.Label(opt, text="Fusion:").grid(row=1, column=0, sticky=tk.W, padx=8, pady=4)
        self.var_fusion = tk.StringVar(value=FusionMode.BEST.value)
        self._fusion_combo = ttk.Combobox(
            opt,
            textvariable=self.var_fusion,
            values=[FusionMode.BEST.value, FusionMode.WEIGHTED.value],
            state="readonly",
            width=12,
        )
        self._fusion_combo.grid(row=1, column=1, sticky=tk.W)
        ToolTip(self._fusion_combo, FUSION_TOOLTIP)

        self.var_ray_guided = tk.BooleanVar(value=True)
        self._ray_chk = ttk.Checkbutton(
            opt,
            text="Ray-guided (LiDAR, повторное наблюдение)",
            variable=self.var_ray_guided,
        )
        self._ray_chk.grid(row=2, column=0, columnspan=3, sticky=tk.W, padx=8)
        ToolTip(self._ray_chk, RAY_GUIDED_TOOLTIP)

        self.var_refine_intensity = tk.BooleanVar(value=False)
        self._refine_chk = ttk.Checkbutton(
            opt,
            text="Intensity refine (ArUco на LiDAR grid в ROI)",
            variable=self.var_refine_intensity,
        )
        self._refine_chk.grid(row=3, column=0, columnspan=3, sticky=tk.W, padx=8)
        ToolTip(self._refine_chk, INTENSITY_REFINE_TOOLTIP)

        ttk.Label(opt, text="Семейства тегов:").grid(row=4, column=0, sticky=tk.NW, padx=8, pady=4)
        fam_frame = ttk.Frame(opt)
        fam_frame.grid(row=4, column=1, columnspan=2, sticky=tk.W)
        self._fam_vars: dict[str, tk.BooleanVar] = {}
        for i, name in enumerate(TAG_FAMILIES):
            default = name in ("tag36h11", "tag25h9", "tag16h5")
            var = tk.BooleanVar(value=default)
            self._fam_vars[name] = var
            ttk.Checkbutton(fam_frame, text=name, variable=var).grid(row=i // 2, column=i % 2, sticky=tk.W)

        # Progress
        self.var_status = tk.StringVar(value="Готов")
        ttk.Label(frm, textvariable=self.var_status).grid(row=5, column=0, columnspan=3, sticky=tk.W, **pad)
        self.progress = ttk.Progressbar(frm, mode="determinate", maximum=100)
        self.progress.grid(row=6, column=0, columnspan=3, sticky=tk.EW, **pad)

        # Log
        log_frame = ttk.LabelFrame(frm, text="Журнал")
        log_frame.grid(row=7, column=0, columnspan=3, sticky=tk.NSEW, **pad)
        frm.rowconfigure(7, weight=1)
        frm.columnconfigure(1, weight=1)

        self.log_text = tk.Text(log_frame, height=18, wrap=tk.WORD, state=tk.DISABLED)
        scroll = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scroll.set)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # Buttons
        btn_frame = ttk.Frame(frm)
        btn_frame.grid(row=8, column=0, columnspan=3, sticky=tk.E, **pad)
        self.btn_run = ttk.Button(btn_frame, text="Запуск", command=self._start)
        self.btn_run.pack(side=tk.LEFT, padx=4)
        self.btn_stop = ttk.Button(btn_frame, text="Стоп", command=self._stop, state=tk.DISABLED)
        self.btn_stop.pack(side=tk.LEFT, padx=4)

    def _pano_tooltip_text(self) -> str:
        label = self.var_pano_scale.get()
        for key, text in PANO_SCALE_LABELS.items():
            if text == label:
                return PANO_SCALE_TOOLTIPS.get(key, "")
        if "1+2" in label.lower():
            return PANO_SCALE_TOOLTIPS[PANO_SCALE_MAX]
        return PANO_SCALE_TOOLTIPS[PANO_SCALE_FAST]

    def _browse_folder(self) -> None:
        path = filedialog.askdirectory(title="Папка с E57")
        if path:
            self.var_folder.set(path)
            pano = Path(path) / "pano"
            if pano.is_dir():
                self.var_pano.set(str(pano))
            self._persist_paths()

    def _browse_pano(self) -> None:
        path = filedialog.askdirectory(title="Папка с растровыми панорамами")
        if path:
            self.var_pano.set(path)
            self._persist_paths()

    def _browse_csv(self) -> None:
        path = filedialog.asksaveasfilename(
            title="RealityScan Ground Control CSV",
            defaultextension=".csv",
            initialfile="apriltag_realityscan_gcp.csv",
            filetypes=[("CSV", "*.csv")],
        )
        if path:
            self.var_csv.set(path)
            self._persist_paths()

    def _append_log(self, msg: str) -> None:
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.insert(tk.END, msg + "\n")
        self.log_text.see(tk.END)
        self.log_text.configure(state=tk.DISABLED)

    def _poll_log(self) -> None:
        try:
            while True:
                item = self._log_queue.get_nowait()
                if isinstance(item, tuple):
                    pct, msg = item
                    self.progress["value"] = pct * 100
                    self.var_status.set(msg)
                else:
                    self._append_log(item)
        except queue.Empty:
            pass
        self.after(100, self._poll_log)

    def _persist_paths(self) -> None:
        _save_gui_settings(
            {
                "e57_folder": self.var_folder.get().strip(),
                "pano_folder": self.var_pano.get().strip(),
                "csv_path": self.var_csv.get().strip(),
            }
        )

    def _selected_families(self) -> list[str]:
        return [name for name, var in self._fam_vars.items() if var.get()]

    def _start(self) -> None:
        if self._worker and self._worker.is_alive():
            return

        folder = Path(self.var_folder.get().strip())
        if not folder.is_dir():
            messagebox.showerror("Ошибка", f"Папка не найдена:\n{folder}")
            return

        families = self._selected_families()
        if not families:
            messagebox.showerror("Ошибка", "Выберите хотя бы одно семейство тегов")
            return

        csv_text = self.var_csv.get().strip()
        csv_path = Path(csv_text) if csv_text else None
        self._persist_paths()

        self._cancel = False
        self.btn_run.configure(state=tk.DISABLED)
        self.btn_stop.configure(state=tk.NORMAL)
        self.progress["value"] = 0
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.delete("1.0", tk.END)
        self.log_text.configure(state=tk.DISABLED)

        pano_text = self.var_pano.get().strip()
        pano_path = Path(pano_text) if pano_text else None
        if pano_path is not None and not pano_path.is_dir():
            pano_path = None

        fusion_val = self.var_fusion.get().strip()
        try:
            fusion_mode = FusionMode(fusion_val)
        except ValueError:
            fusion_mode = FusionMode.BEST

        pano_scales = pano_scales_from_preset(self.var_pano_scale.get())

        config = PipelineConfig(
            e57_folder=folder,
            db_path=None,
            output_csv=csv_path,
            pano_folder=pano_path,
            families=families,
            detect_scale=pano_scales[0],
            pano_detect_scales=pano_scales,
            coord_mode=CoordExportMode.ACTIVE,
            fusion_mode=fusion_mode,
            ray_guided_pass=self.var_ray_guided.get(),
            refine_intensity=self.var_refine_intensity.get(),
        )

        def worker() -> None:
            def log(msg: str) -> None:
                self._log_queue.put(msg)

            def progress(p: float, msg: str) -> None:
                self._log_queue.put((p, msg))

            try:
                result = run_pipeline(config, log=log, progress=progress, cancel=lambda: self._cancel)
                log(f"\nГотово: {len(result.fused_tags)} тегов -> {result.output_csv}")
            except Exception as exc:
                log(f"\nКритическая ошибка: {exc}")
            finally:
                self.after(0, self._on_done)

        self._worker = threading.Thread(target=worker, daemon=True)
        self._worker.start()

    def _stop(self) -> None:
        self._cancel = True
        self.var_status.set("Остановка…")

    def _on_done(self) -> None:
        self.btn_run.configure(state=tk.NORMAL)
        self.btn_stop.configure(state=tk.DISABLED)
        self.var_status.set("Готово")


def main() -> None:
    app = AprilTagE57App()
    app.mainloop()


if __name__ == "__main__":
    main()

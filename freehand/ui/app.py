"""CTk root application — screen transitions and lifecycle."""

from __future__ import annotations

import sys
from typing import Optional

import customtkinter as ctk

from freehand.core.config import AppConfig, RuntimeState
from freehand.core.thread_loop import TrackingLoop
from freehand.tracking.camera import CameraSource
from freehand.ui.screens.calibration import CalibrationScreen
from freehand.ui.screens.floating_widget import FloatingWidget, SettingsPanel
from freehand.ui.screens.welcome import IPCameraDialog, WelcomeScreen
from freehand.ui.theme import COLORS, apply_appearance, make_font
from freehand.ui.widgets.dwell_ring import DwellRingOverlay


class FreeHandApp(ctk.CTk):
    """Root window that owns config/state and swaps screens."""

    def __init__(self) -> None:
        apply_appearance()
        super().__init__()

        self.title("Free-hand")
        self.geometry("960x640")
        self.minsize(800, 560)
        self.configure(fg_color=COLORS["bg"])

        self.config_model = AppConfig()
        self.runtime = RuntimeState()
        self._sync_screen_size()

        self.camera: Optional[CameraSource] = None
        self._active_loop: Optional[TrackingLoop] = None
        self._floating: Optional[FloatingWidget] = None
        self._dwell_ring: Optional[DwellRingOverlay] = None
        self._settings: Optional[SettingsPanel] = None
        self._current = None
        self._webcam_ok = False
        self._transitioning = False

        # Probe webcam on launch (non-blocking feel: short probe)
        self._show_boot()
        self.after(50, self._boot)

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _sync_screen_size(self) -> None:
        try:
            self.update_idletasks()
            self.config_model.screen_width = int(self.winfo_screenwidth())
            self.config_model.screen_height = int(self.winfo_screenheight())
        except Exception:  # noqa: BLE001
            pass
        try:
            import pyautogui

            size = pyautogui.size()
            self.config_model.screen_width = int(size.width)
            self.config_model.screen_height = int(size.height)
        except Exception:  # noqa: BLE001
            pass

    def _show_boot(self) -> None:
        boot = ctk.CTkFrame(self, fg_color=COLORS["bg"])
        boot.pack(fill="both", expand=True)
        ctk.CTkLabel(
            boot,
            text="Free-hand",
            font=make_font(42, "bold"),
            text_color=COLORS["text"],
        ).place(relx=0.5, rely=0.42, anchor="center")
        ctk.CTkLabel(
            boot,
            text="Checking camera…",
            font=make_font(16),
            text_color=COLORS["text_muted"],
        ).place(relx=0.5, rely=0.52, anchor="center")
        self._current = boot

    def _boot(self) -> None:
        self._webcam_ok = CameraSource.probe_webcam(self.config_model.webcam_index)
        self.show_welcome()

    def _clear_screen(self) -> None:
        if self._current is not None:
            try:
                self._current.destroy()
            except Exception:  # noqa: BLE001
                pass
            self._current = None

    def _transition_to(self, factory) -> None:
        """Simple crossfade-ish transition: brief blank then pack new screen."""
        if self._transitioning:
            return
        self._transitioning = True
        overlay = ctk.CTkFrame(self, fg_color=COLORS["bg"])
        overlay.place(relx=0, rely=0, relwidth=1, relheight=1)

        def _swap() -> None:
            self._clear_screen()
            screen = factory()
            screen.pack(fill="both", expand=True)
            self._current = screen
            overlay.lift()

            def _fade_step(step: int = 0) -> None:
                if step >= 8:
                    try:
                        overlay.destroy()
                    except Exception:  # noqa: BLE001
                        pass
                    self._transitioning = False
                    return
                # Simulate fade by shrinking overlay height
                remain = 1.0 - (step + 1) / 8.0
                try:
                    overlay.place_configure(rely=1.0 - remain, relheight=remain)
                except Exception:  # noqa: BLE001
                    pass
                self.after(16, lambda: _fade_step(step + 1))

            self.after(40, _fade_step)

        self.after(80, _swap)

    def show_welcome(self) -> None:
        self.deiconify()
        self._stop_active_tracking()

        def factory():
            return WelcomeScreen(
                self,
                webcam_available=self._webcam_ok,
                on_select=self._on_source_selected,
                auto_seconds=self.config_model.auto_select_seconds,
            )

        self._transition_to(factory)

    def _on_source_selected(self, source: str) -> None:
        if source == "webcam":
            self._open_camera(self.config_model.webcam_index, label="Webcam")
        else:
            dialog = IPCameraDialog(
                self,
                on_submit=lambda url: self._open_camera(url, label="IP Camera"),
                initial=self.config_model.ip_camera_url,
            )
            dialog.grab_set()

    def _open_camera(self, source, label: str) -> None:
        if self.camera is not None:
            self.camera.close()
        cam = CameraSource(
            source,
            width=self.config_model.camera_width,
            height=self.config_model.camera_height,
            fps=self.config_model.camera_fps,
        )
        if not cam.open():
            self.runtime.last_error = f"Could not open {label}"
            # Stay on welcome; show a toast-like label
            err = ctk.CTkToplevel(self)
            err.title("Camera")
            err.geometry("400x180")
            err.configure(fg_color=COLORS["bg_elevated"])
            err.attributes("-topmost", True)
            ctk.CTkLabel(
                err,
                text=f"Could not open {label}.\nCheck the device or URL and try again.",
                font=make_font(16),
                text_color=COLORS["text"],
            ).pack(expand=True, padx=24, pady=24)
            ctk.CTkButton(
                err,
                text="OK",
                height=48,
                command=err.destroy,
                fg_color=COLORS["surface"],
            ).pack(fill="x", padx=24, pady=(0, 24))
            # Re-show welcome so user can pick again
            self.show_welcome()
            return

        if isinstance(source, str):
            self.config_model.ip_camera_url = source
        self.camera = cam
        self.runtime.camera_source_label = label
        self.show_calibration()

    def show_calibration(self) -> None:
        self.deiconify()
        self._sync_screen_size()

        def factory():
            assert self.camera is not None
            return CalibrationScreen(
                self,
                config=self.config_model,
                state=self.runtime,
                camera=self.camera,
                on_complete=self.show_active,
                on_back=self.show_welcome,
            )

        self._transition_to(factory)

    def show_active(self) -> None:
        """Hide main window; show floating widget + start tracking with cursor control."""
        self._clear_screen()
        self.withdraw()
        self._sync_screen_size()
        self.runtime.paused = False

        if self.camera is None or not self.camera.is_open:
            self.show_welcome()
            return

        self._dwell_ring = DwellRingOverlay(self)
        self._active_loop = TrackingLoop(
            self.config_model,
            self.runtime,
            self.camera,
            move_cursor=True,
            on_frame=None,
            on_click=None,
        )
        self._active_loop.start()

        self._floating = FloatingWidget(
            self,
            config=self.config_model,
            state=self.runtime,
            on_pause_toggle=self._toggle_pause,
            on_open_settings=self._open_settings,
            on_exit=self._exit_active,
        )
        self.after(50, self._poll_dwell_ring)

    def _poll_dwell_ring(self) -> None:
        if self._dwell_ring is None or self._active_loop is None:
            return
        if not self.runtime.paused and self.runtime.face_detected:
            self._dwell_ring.set_progress(self.runtime.dwell_progress, self.runtime.cursor_xy)
        else:
            self._dwell_ring.hide()
        self.after(33, self._poll_dwell_ring)

    def _toggle_pause(self) -> None:
        self.runtime.paused = not self.runtime.paused
        if self.runtime.paused and self._dwell_ring is not None:
            self._dwell_ring.hide()

    def _open_settings(self) -> None:
        if self._settings is not None and self._settings.winfo_exists():
            self._settings.lift()
            return
        self._settings = SettingsPanel(self, self.config_model, on_apply=self._apply_settings)

    def _apply_settings(self) -> None:
        if self._active_loop is not None:
            self._active_loop.update_config()

    def _exit_active(self) -> None:
        self._stop_active_tracking()
        self.show_welcome()

    def _stop_active_tracking(self) -> None:
        if self._active_loop is not None:
            self._active_loop.stop()
            self._active_loop = None
        if self._dwell_ring is not None:
            try:
                self._dwell_ring.destroy()
            except Exception:  # noqa: BLE001
                pass
            self._dwell_ring = None
        if self._floating is not None:
            try:
                self._floating.destroy()
            except Exception:  # noqa: BLE001
                pass
            self._floating = None

    def _on_close(self) -> None:
        self._stop_active_tracking()
        if self.camera is not None:
            self.camera.close()
            self.camera = None
        self.destroy()


def run_app() -> None:
    # Headless / CI guard: if no display, exit gracefully
    if sys.platform.startswith("linux") and not (
        __import__("os").environ.get("DISPLAY") or __import__("os").environ.get("WAYLAND_DISPLAY")
    ):
        print("Free-hand requires a display. Exiting gracefully (no DISPLAY).")
        print("Install deps with: pip install -r requirements.txt")
        print("Run with: python -m freehand.main")
        sys.exit(0)

    app = FreeHandApp()
    app.mainloop()

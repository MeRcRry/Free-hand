# Free-hand

Head-tracking mouse control for motor accessibility. Move the cursor with your head (MediaPipe Face Mesh) and left-click by **dwelling** — hold still inside a small radius for ~1.3s. Built as a polished dark-mode CustomTkinter app for a UI/UX semester project.

## Features

- **Webcam or IP camera** (phone stream) with launch-time webcam probe
- **10s auto-select** on the welcome screen if you don’t choose
- **EMA smoothing** (optional Kalman) — no raw jittery cursor
- **Dwell click** with a progress ring around the cursor (not blink-to-click)
- **Calibration** — center + four corners, then a dwell practice target
- **Active Mode** — main window hides; always-on-top floating widget (status / Pause / Settings)
- Tracking runs on a **background thread** so the UI never blocks

## Requirements

- Python 3.10+
- Tkinter (`python3-tk` on Debian/Ubuntu)
- Webcam (or a phone IP-camera app that exposes an MJPEG/HTTP/RTSP URL)
- A graphical desktop session (`DISPLAY` / Wayland)

## Install

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Run

```bash
python -m freehand.main
```

Or:

```bash
python freehand/main.py
```

### IP camera (phone)

1. On welcome, choose **Mobile Phone** (or wait for auto-select when no webcam).
2. Paste a stream URL, e.g. `http://192.168.x.x:8080/video` from apps like IP Webcam.
3. Continue to calibration as usual.

## Project layout

```
freehand/
  main.py                 # entry
  ui/
    app.py                # CTk root, screen transitions
    screens/
      welcome.py          # Screen 1
      calibration.py      # Screen 2
      floating_widget.py  # Screen 3 overlay
    theme.py              # dark tokens, Outfit font, spacing
    widgets/              # dwell ring, large buttons
  tracking/
    camera.py             # webcam + IP sources
    face_tracker.py       # MediaPipe Face Mesh (nose / mid-eyes)
    dwell_click.py        # dwell radius + time → left click
    smoothing.py          # EMA (+ optional Kalman)
  core/
    config.py             # dwell, EMA, screen map
    thread_loop.py        # background tracking loop
assets/fonts/             # bundled Outfit faces
```

## Accessibility notes

- Very large hit targets on welcome and settings
- High-contrast charcoal + mint theme
- Usable before calibration via auto-select and “Use defaults”
- Pause from the floating widget at any time

## Graceful degrade

- If `cv2.VideoCapture(0)` fails at launch, **Webcam** is disabled; Mobile Phone remains available
- If there is no display (typical CI), the app prints run instructions and exits `0`
- Missing MediaPipe / camera errors surface in UI status rather than crashing the process

## License

MIT (course / demo project)

# AirOS — Touchless Computer Operating Environment

**AirOS** is a touchless desktop operating environment for Windows that enables full computer control through a standard webcam and hand gestures. Control the pointer, manage windows, browse files, run utilities, type using a floating virtual keyboard, and operate your system naturally without touching a physical mouse or keyboard.

---

## 🚀 Key Features

1. **Fluid Desktop Shell**: Complete with custom start menu, taskbar, workspaces, clock, notifications, and desktop shortcuts.
2. **Window Management (AirWorkspace)**: Draggable, resizable, minimizable, maximizable, focusable, and snapable application windows.
3. **IntentLock™ Safety**: Dwell verification and cooldown timers eliminate accidental clicks during mid-air hand motion.
4. **Adaptive Pointer**: Exponential Moving Average (EMA) cursor smoothing, active control mapping, and large-target accessibility mode.
5. **AirType Virtual Keyboard**: Full floating QWERTY keyboard with Shift, Backspace, Enter, and Space for typing into built-in and native apps.
6. **Built-in Application Suite**:
   - 📝 **Notes**: Full SQLite persistence, creation, and editing.
   - 🧮 **Calculator**: Large-button accessible arithmetic engine.
   - 📁 **File Manager**: Directory navigation and safe external application launching.
   - 🖼️ **Gallery**: Photo viewer with touchless next/prev navigation.
   - 👋 **Gesture Tutorial & Calibration Wizard**: Interactive guide and sensitivity sliders.
   - ⚙️ **Settings & Personalization**: Theme picker, Privacy Mode, and PyAutoGUI native bridge toggle.
7. **Privacy First**: Frame inference is 100% on-device. No video is ever stored or streamed. Includes a one-click Emergency Pause HUD.

---

## 🖐️ Gesture Reference Guide

| Gesture | Hand Pose | Action |
| :--- | :--- | :--- |
| **Move Cursor** | Point index finger | Moves the on-screen adaptive cursor smoothly. |
| **Left Click** | Quick pinch: thumb + index tip | Triggers a left click on the hovered target. |
| **Double Click** | Two consecutive pinches (< 420 ms) | Triggers double-click (opens files, toggles zoom). |
| **Drag & Drop** | Hold pinch (> 0.35 s) while moving hand | Drags active windows, sliders, or items. |
| **Two-Finger Scroll** | Index & middle fingers extended close together | Scrolls documents, web pages, or lists vertically. |
| **Open Palm** | All five fingers extended forward | Toggles the AirOS Start Menu and quick settings. |
| **Horizontal Swipe**| Swift wave of palm or hand to the side | Switches workspaces (Space 1 ↔ Space 2). |
| **V-Sign / Peace** | Index & middle fingers spread apart | Shows or hides the AirType Virtual Keyboard. |
| **Emergency Pause** | Click HUD pause button or toggle via menu | Freezes touchless tracking instantly. |

---

## 🛠️ Installation & Execution

### Prerequisites
- Windows 10 or 11 (64-bit)
- Python 3.11 or later
- Standard built-in webcam or USB webcam

### Quick Start (One Command)
Double-click `run_airos.bat` or run:
```powershell
.\run_airos.bat
```

### Manual Installation
1. Clone or open the repository:
   ```powershell
   cd d:\AIRos
   ```
2. Install dependencies:
   ```powershell
   pip install -r requirements.txt
   ```
3. Run the application:
   ```powershell
   python main.py
   ```

### Running Tests
Execute the unit test suite:
```powershell
python -m unittest discover -s tests -p "test_*.py" -v
```

---

## 🧩 Architecture

```
d:\AIRos\
├── assets\models\             # Neural network weights (hand detector, landmark model)
├── airos\
│   ├── apps\                 # Built-in applications (Notes, Calc, File Manager, Gallery, Settings, Tutorial)
│   ├── desktop\              # Shell, Window Manager, Taskbar, Start Menu, Keyboard, HUD, Themes
│   ├── gestures\             # Gesture state machine, IntentLock, debouncing
│   ├── input\                # Optional PyAutoGUI native Windows adapter
│   ├── storage\              # Persistent JSON configuration & SQLite database
│   └── vision\               # Multi-backend HandTracker, OpenCV pipeline, and camera QThread
├── tests\                    # Unit tests for computer vision and gestures
├── requirements.txt          # Python dependencies
├── run_airos.bat             # One-click Windows startup script
├── main.py                   # Main bootstrapper
└── README.md                 # Complete documentation
```

---

## 🔧 Troubleshooting Guide

- **Camera Not Detected**: Ensure no other application (Zoom, Teams, Camera app) is monopolizing camera index 0. You can change `camera_index` in `~/.airos/config.json`.
- **Lighting & Tracking Stability**: Ensure your hand is evenly illuminated against the background. Adjust the **Pinch Distance Sensitivity** slider in the Gesture Tutorial app if pinches trigger too easily or with difficulty.
- **Native Windows Control**: PyAutoGUI desktop control is opt-in for safety. To control third-party Windows apps outside AirOS, check **Enable PyAutoGUI Native Windows Mouse & Keyboard bridge** in AirOS Settings.

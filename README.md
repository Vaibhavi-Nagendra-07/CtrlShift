# CtrlShift

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
7. **Draw on Screen (AirDraw & Annotation)**:
   - Mid-air screen sketching and whiteboard overlays directly over the desktop.
   - Real-time Camera HUD drawing badge (`Drawing: draw` / `Drawing: hover` / `Drawing: erase`).
   - Multiple palettes: Vibrant Blue, Emerald, Crimson, Amber, Purple, White.
   - Tools: Pen, Translucent Highlighter, Presentation Laser Pointer (fading glowing comet trail), and Eraser.
   - **Smart Shape Snap**: Intelligent geometry detection that snaps hand-drawn sketches into perfect lines, circles/ellipses, and rectangles.
   - High-resolution screen snapshot capture to PNG.
8. **AirVoice Voice Commands & Speech Control**:
   - Hands-free voice recognition powered by ambient speech detection.
   - Natural language aliases for all apps, window controls, and drawing tools.
   - Non-blocking Text-To-Speech audio feedback confirmations.
   - Taskbar Voice HUD with live listening wave pulse and transcript bubble.
9. **User Activity Records & Live Audit Monitor**:
   - Automatic background logging of all user activities: application launches, mid-air gestures, voice commands, and logins.
   - Dedicated **User Records App** with metric cards, category filtering, search, and JSON export.
10. **Biometric Fingerprint Login & Lock Screen**:
   - Futuristic glassmorphic lock screen with animated laser scanning fingerprint sensor.
   - Dual-mode authentication: touch/click or touchless mid-air gesture hover to scan and unlock.
   - 4-digit PIN keypad fallback and instant Start Menu / Voice command locking (`"Lock screen"`).
11. **90 FPS Ultra-Smooth Motion Engine**:
   - High-refresh rate decoupled pipeline with Lucas-Kanade optical tracking and multimedia timer precision.
12. **Privacy First**: Frame inference is 100% on-device. No video is ever stored or streamed. Includes a one-click Emergency Pause HUD.

---

## 🎙️ AirVoice Commands Reference

| Category | Spoken Phrases | Action |
| :--- | :--- | :--- |
| **Draw on Screen** | *"Start drawing"*, *"Draw on screen"*, *"Air draw"* | Opens the mid-air screen drawing overlay |
| **Close Drawing** | *"Stop drawing"*, *"Exit drawing"* | Closes drawing overlay |
| **Ink Colors** | *"Color blue"*, *"Color red"*, *"Color green"*, *"Yellow"* | Switches ink color immediately |
| **Tools** | *"Pen"*, *"Highlighter"*, *"Eraser"*, *"Laser pointer"* | Switches active annotation tool |
| **Smart Geometry**| *"Shape snap"*, *"Smart shape"* | Toggles geometric shape auto-snapping |
| **Canvas Actions**| *"Clear screen"*, *"Undo"*, *"Redo"*, *"Save drawing"* | Clears canvas, steps history, or takes PNG screenshot |
| **Launch Apps** | *"Open notes"*, *"Open calculator"*, *"Open browser"*, *"Files"*, *"User records"* | Launches corresponding application |
| **System Control**| *"Show desktop"*, *"Start menu"*, *"Virtual keyboard"*, *"Lock screen"* | Toggles desktop, launcher, keyboard, or locks system |
| **Security & Auth**| *"Lock screen"*, *"Lock computer"*, *"Lock"* | Locks system with Biometric Fingerprint Lock Screen |
| **Workspaces** | *"Workspace one"*, *"Workspace two"* | Switches active virtual workspace |
| **Tracking** | *"Pause tracking"*, *"Resume tracking"* | Freezes or unfreezes webcam gesture tracking |
| **Feedback** | *"Mute voice"*, *"Unmute voice"*, *"Voice commands"* | Mutes speech confirmations or opens cheat sheet |

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

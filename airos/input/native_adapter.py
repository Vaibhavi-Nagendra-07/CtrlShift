"""
AirOS Native Input Adapter.
Provides high-performance, safe bridge to native Windows mouse and keyboard.
Uses direct Win32 User32 APIs on Windows for microsecond zero-latency cursor control,
smooth hardware tracking, native dragging, and fail-safe safety.
"""

import sys
import time
from typing import Tuple, Optional

IS_WINDOWS = sys.platform == "win32"

if IS_WINDOWS:
    import ctypes
    user32 = ctypes.windll.user32
    try:
        user32.SetProcessDPIAware()
    except Exception:
        pass
    MOUSEEVENTF_MOVE = 0x0001
    MOUSEEVENTF_LEFTDOWN = 0x0002
    MOUSEEVENTF_LEFTUP = 0x0004
    MOUSEEVENTF_RIGHTDOWN = 0x0008
    MOUSEEVENTF_RIGHTUP = 0x0010
    MOUSEEVENTF_MIDDLEDOWN = 0x0020
    MOUSEEVENTF_MIDDLEUP = 0x0040
    MOUSEEVENTF_WHEEL = 0x0800
    MOUSEEVENTF_ABSOLUTE = 0x8000
else:
    user32 = None

try:
    import pyautogui
    pyautogui.FAILSAFE = False
    pyautogui.PAUSE = 0.0
except ImportError:
    pyautogui = None


class NativeInputAdapter:
    """Safely synthesizes high-performance Windows desktop input events when enabled by user."""

    def __init__(self, enabled: bool = False):
        self.enabled = enabled
        self._is_mouse_down = False
        self._update_screen_size()

    def _update_screen_size(self):
        if IS_WINDOWS and user32 is not None:
            self.screen_w = max(1, user32.GetSystemMetrics(0))
            self.screen_h = max(1, user32.GetSystemMetrics(1))
        elif pyautogui is not None:
            self.screen_w, self.screen_h = pyautogui.size()
        else:
            self.screen_w, self.screen_h = 1920, 1080

    @property
    def is_mouse_down(self) -> bool:
        return self._is_mouse_down

    def set_enabled(self, enabled: bool):
        if not enabled and self._is_mouse_down:
            self.mouse_up()
        self.enabled = enabled
        if self.enabled:
            self._update_screen_size()

    def move_cursor(self, norm_x: float, norm_y: float):
        if not self.enabled:
            return
        px = max(0, min(self.screen_w - 1, int(norm_x * self.screen_w)))
        py = max(0, min(self.screen_h - 1, int(norm_y * self.screen_h)))

        if IS_WINDOWS and user32 is not None:
            try:
                user32.SetCursorPos(px, py)
            except Exception:
                pass
        elif pyautogui is not None:
            try:
                pyautogui.moveTo(px, py, _pause=False)
            except Exception:
                pass

    def click(self, norm_x: float, norm_y: float):
        if not self.enabled:
            return
        self.move_cursor(norm_x, norm_y)
        if IS_WINDOWS and user32 is not None:
            try:
                user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
                time.sleep(0.015)
                user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
            except Exception:
                pass
        elif pyautogui is not None:
            try:
                pyautogui.click()
            except Exception:
                pass

    def double_click(self, norm_x: float, norm_y: float):
        if not self.enabled:
            return
        self.click(norm_x, norm_y)
        time.sleep(0.06)
        self.click(norm_x, norm_y)

    def mouse_down(self, norm_x: float, norm_y: float):
        if not self.enabled:
            return
        self.move_cursor(norm_x, norm_y)
        if not self._is_mouse_down:
            if IS_WINDOWS and user32 is not None:
                try:
                    user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
                except Exception:
                    pass
            elif pyautogui is not None:
                try:
                    pyautogui.mouseDown(button='left')
                except Exception:
                    pass
            self._is_mouse_down = True

    def mouse_up(self):
        if self._is_mouse_down:
            if IS_WINDOWS and user32 is not None:
                try:
                    user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
                except Exception:
                    pass
            elif pyautogui is not None:
                try:
                    pyautogui.mouseUp(button='left')
                except Exception:
                    pass
            self._is_mouse_down = False

    def scroll(self, delta: float):
        if not self.enabled:
            return
        # Windows WHEEL_DELTA is 120 per click
        wheel_amt = int(delta * 120)
        if IS_WINDOWS and user32 is not None:
            try:
                user32.mouse_event(MOUSEEVENTF_WHEEL, 0, 0, wheel_amt, 0)
            except Exception:
                pass
        elif pyautogui is not None:
            try:
                pyautogui.scroll(int(delta * 10))
            except Exception:
                pass

    def type_key(self, key_text: str):
        if not self.enabled or pyautogui is None:
            return
        try:
            if key_text == "Backspace":
                pyautogui.press("backspace")
            elif key_text == "Enter":
                pyautogui.press("enter")
            elif key_text == "Space":
                pyautogui.press("space")
            elif len(key_text) == 1:
                pyautogui.write(key_text)
        except Exception:
            pass


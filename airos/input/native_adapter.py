"""
AirOS Native Input Adapter.
Provides optional, safe bridge to native Windows mouse and keyboard via PyAutoGUI.
Features emergency pause safety and button release on tracking loss.
"""

from typing import Tuple, Optional
import pyautogui

# Enable PyAutoGUI fail-safe (moving mouse to corner raises exception)
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.001

class NativeInputAdapter:
    """Safely synthesizes Windows input events when enabled by user."""

    def __init__(self, enabled: bool = False):
        self.enabled = enabled
        self._is_mouse_down = False
        self.screen_w, self.screen_h = pyautogui.size()

    def set_enabled(self, enabled: bool):
        if not enabled and self._is_mouse_down:
            self.mouse_up()
        self.enabled = enabled

    def move_cursor(self, norm_x: float, norm_y: float):
        if not self.enabled:
            return
        px = int(norm_x * (self.screen_w - 1))
        py = int(norm_y * (self.screen_h - 1))
        try:
            pyautogui.moveTo(px, py, _pause=False)
        except Exception:
            pass

    def click(self, norm_x: float, norm_y: float):
        if not self.enabled:
            return
        px = int(norm_x * (self.screen_w - 1))
        py = int(norm_y * (self.screen_h - 1))
        try:
            pyautogui.click(px, py)
        except Exception:
            pass

    def double_click(self, norm_x: float, norm_y: float):
        if not self.enabled:
            return
        px = int(norm_x * (self.screen_w - 1))
        py = int(norm_y * (self.screen_h - 1))
        try:
            pyautogui.doubleClick(px, py)
        except Exception:
            pass

    def mouse_down(self, norm_x: float, norm_y: float):
        if not self.enabled:
            return
        px = int(norm_x * (self.screen_w - 1))
        py = int(norm_y * (self.screen_h - 1))
        try:
            pyautogui.mouseDown(px, py, button='left')
            self._is_mouse_down = True
        except Exception:
            pass

    def mouse_up(self):
        if self._is_mouse_down:
            try:
                pyautogui.mouseUp(button='left')
            except Exception:
                pass
            self._is_mouse_down = False

    def scroll(self, delta: float):
        if not self.enabled:
            return
        try:
            pyautogui.scroll(int(delta * 10))
        except Exception:
            pass

    def type_key(self, key_text: str):
        if not self.enabled:
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

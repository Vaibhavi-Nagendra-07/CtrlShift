"""
Comprehensive Unit Tests for AirOS Screen Draw (AirDraw) and AirVoice Voice Commands.
"""

import sys
import unittest
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QPointF, QRectF
from PySide6.QtGui import QColor

# Ensure root directory is in sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

# Initialize QApplication for widget testing if not already running
app = QApplication.instance() or QApplication(sys.argv)

from airos.desktop.draw_overlay import SmartShapeRecognizer, ScreenDrawOverlay
from airos.voice.voice_engine import VoiceCommandParser, VoiceEngine
from airos.desktop.camera_hud import CameraPreviewHUD
from airos.gestures.state_machine import GestureType, GestureEvent


class TestSmartShapeRecognizer(unittest.TestCase):
    """Tests geometry recognition for lines, circles, and boxes."""

    def test_straight_line_recognition(self):
        # 10 points along a straight line y = 100
        points = [QPointF(x, 100) for x in range(50, 250, 20)]
        shape = SmartShapeRecognizer.recognize(points)
        self.assertIsNotNone(shape)
        self.assertEqual(shape["type"], "line")
        self.assertEqual(shape["start"], points[0])
        self.assertEqual(shape["end"], points[-1])

    def test_circle_recognition(self):
        # Sample points on a circle centered at (200, 200) with radius 50
        import math
        points = []
        for i in range(16):
            angle = i * (2 * math.pi / 16)
            x = 200 + 50 * math.cos(angle)
            y = 200 + 50 * math.sin(angle)
            points.append(QPointF(x, y))
        # Close loop
        points.append(points[0])

        shape = SmartShapeRecognizer.recognize(points)
        self.assertIsNotNone(shape)
        self.assertEqual(shape["type"], "ellipse")
        self.assertAlmostEqual(shape["center"].x(), 200, delta=5.0)
        self.assertAlmostEqual(shape["center"].y(), 200, delta=5.0)

    def test_irregular_scribble_no_snap(self):
        # Non-geometric irregular scribble
        points = [
            QPointF(10, 10), QPointF(50, 120), QPointF(20, 80),
            QPointF(90, 40), QPointF(150, 200), QPointF(30, 220),
            QPointF(180, 50), QPointF(210, 300)
        ]
        shape = SmartShapeRecognizer.recognize(points)
        # Should not falsely snap into a circle
        if shape:
            self.assertNotEqual(shape["type"], "ellipse")


class TestScreenDrawOverlay(unittest.TestCase):
    """Tests canvas stroke management, eraser, undo/redo, and tools."""

    def setUp(self):
        self.overlay = ScreenDrawOverlay()
        self.overlay.resize(800, 600)

    def tearDown(self):
        self.overlay.laser_timer.stop()
        self.overlay.deleteLater()

    def test_initial_state(self):
        self.assertEqual(self.overlay.active_tool, "pen")
        self.assertEqual(len(self.overlay.strokes), 0)
        self.assertFalse(self.overlay.isVisible())

    def test_pen_stroke_lifecycle(self):
        self.overlay.set_color("#1e60ff")
        self.overlay.set_tool("pen")

        # Pen down
        self.overlay._pen_down(QPointF(100, 100))
        self.assertTrue(self.overlay.is_pinched_down)
        self.assertIsNotNone(self.overlay.current_stroke)

        # Pen move
        self.overlay._pen_move(QPointF(120, 120))
        self.overlay._pen_move(QPointF(140, 140))
        self.assertEqual(len(self.overlay.current_stroke["points"]), 3)

        # Pen up
        self.overlay._pen_up()
        self.assertFalse(self.overlay.is_pinched_down)
        self.assertEqual(len(self.overlay.strokes), 1)
        self.assertEqual(self.overlay.strokes[0]["tool"], "pen")
        self.assertEqual(self.overlay.strokes[0]["color"], QColor("#1e60ff"))

    def test_undo_and_redo(self):
        self.overlay._pen_down(QPointF(10, 10))
        self.overlay._pen_move(QPointF(20, 20))
        self.overlay._pen_up()

        self.assertEqual(len(self.overlay.strokes), 1)
        self.overlay.undo_stroke()
        self.assertEqual(len(self.overlay.strokes), 0)
        self.assertEqual(len(self.overlay.redo_stack), 1)

        self.overlay.redo_stroke()
        self.assertEqual(len(self.overlay.strokes), 1)
        self.assertEqual(len(self.overlay.redo_stack), 0)

    def test_eraser_removes_intersecting_strokes(self):
        # Draw stroke near (50, 50)
        self.overlay._pen_down(QPointF(50, 50))
        self.overlay._pen_move(QPointF(55, 55))
        self.overlay._pen_up()

        # Draw stroke far away at (400, 400)
        self.overlay._pen_down(QPointF(400, 400))
        self.overlay._pen_move(QPointF(410, 410))
        self.overlay._pen_up()

        self.assertEqual(len(self.overlay.strokes), 2)

        # Erase at (52, 52)
        self.overlay.set_tool("eraser")
        self.overlay._pen_down(QPointF(52, 52))
        self.assertEqual(len(self.overlay.strokes), 1)
        # Remaining stroke should be the one at (400, 400)
        self.assertEqual(self.overlay.strokes[0]["points"][0], QPointF(400, 400))

    def test_clear_canvas(self):
        self.overlay._pen_down(QPointF(10, 10))
        self.overlay._pen_move(QPointF(20, 20))
        self.overlay._pen_up()

        self.overlay.clear_canvas()
        self.assertEqual(len(self.overlay.strokes), 0)
        self.assertEqual(len(self.overlay.redo_stack), 0)

    def test_gesture_input_integration(self):
        self.overlay.show()

        # Hover event (not pinched)
        hover_event = GestureEvent(
            gesture=GestureType.HOVER,
            cursor_pos=(0.3, 0.3),
            raw_point=(0.3, 0.3),
            state_description="Hovering"
        )
        self.overlay.process_gesture_input(hover_event)
        self.assertFalse(self.overlay.is_pinched_down)

        # Pinch click event (pinched down -> drawing)
        pinch_event = GestureEvent(
            gesture=GestureType.PINCH_CLICK,
            cursor_pos=(0.3, 0.3),
            raw_point=(0.3, 0.3),
            state_description="Pinch Aiming..."
        )
        self.overlay.process_gesture_input(pinch_event)
        self.assertTrue(self.overlay.is_pinched_down)

        # Move while pinched
        move_pinch_event = GestureEvent(
            gesture=GestureType.DRAG,
            cursor_pos=(0.35, 0.35),
            raw_point=(0.35, 0.35),
            state_description="Pinch Dragging"
        )
        self.overlay.process_gesture_input(move_pinch_event)
        self.assertTrue(self.overlay.is_pinched_down)

        # Release pinch
        self.overlay.process_gesture_input(hover_event)
        self.assertFalse(self.overlay.is_pinched_down)
        self.assertGreaterEqual(len(self.overlay.strokes), 1)


class TestVoiceCommandParser(unittest.TestCase):
    """Tests speech-to-command natural language parsing."""

    def test_drawing_commands(self):
        cmd = VoiceCommandParser.parse("start drawing")
        self.assertIsNotNone(cmd)
        self.assertEqual(cmd.command_id, "CMD_DRAW_START")

        cmd = VoiceCommandParser.parse("draw on screen")
        self.assertIsNotNone(cmd)
        self.assertEqual(cmd.command_id, "CMD_DRAW_START")

        cmd = VoiceCommandParser.parse("stop drawing")
        self.assertIsNotNone(cmd)
        self.assertEqual(cmd.command_id, "CMD_DRAW_STOP")

        cmd = VoiceCommandParser.parse("clear screen")
        self.assertIsNotNone(cmd)
        self.assertEqual(cmd.command_id, "CMD_DRAW_CLEAR")

        cmd = VoiceCommandParser.parse("take screenshot")
        self.assertIsNotNone(cmd)
        self.assertEqual(cmd.command_id, "CMD_DRAW_SAVE")

    def test_color_and_tool_commands(self):
        cmd = VoiceCommandParser.parse("color blue")
        self.assertEqual(cmd.command_id, "CMD_DRAW_COLOR")
        self.assertEqual(cmd.params["color"], "#1e60ff")

        cmd = VoiceCommandParser.parse("color red")
        self.assertEqual(cmd.command_id, "CMD_DRAW_COLOR")
        self.assertEqual(cmd.params["color"], "#ef4444")

        cmd = VoiceCommandParser.parse("switch to eraser")
        self.assertEqual(cmd.command_id, "CMD_DRAW_TOOL")
        self.assertEqual(cmd.params["tool"], "eraser")

        cmd = VoiceCommandParser.parse("laser pointer")
        self.assertEqual(cmd.command_id, "CMD_DRAW_TOOL")
        self.assertEqual(cmd.params["tool"], "laser")

        cmd = VoiceCommandParser.parse("smart shape")
        self.assertEqual(cmd.command_id, "CMD_DRAW_SHAPE_SNAP")

    def test_application_commands(self):
        cmd = VoiceCommandParser.parse("open notes")
        self.assertEqual(cmd.command_id, "CMD_LAUNCH_APP")
        self.assertEqual(cmd.params["app_id"], "notes")

        cmd = VoiceCommandParser.parse("open calculator")
        self.assertEqual(cmd.command_id, "CMD_LAUNCH_APP")
        self.assertEqual(cmd.params["app_id"], "calc")

        cmd = VoiceCommandParser.parse("open files")
        self.assertEqual(cmd.command_id, "CMD_LAUNCH_APP")
        self.assertEqual(cmd.params["app_id"], "files")

        cmd = VoiceCommandParser.parse("open edge browser")
        self.assertEqual(cmd.command_id, "CMD_LAUNCH_APP")
        self.assertEqual(cmd.params["app_id"], "browser")

    def test_system_and_window_commands(self):
        cmd = VoiceCommandParser.parse("show desktop")
        self.assertEqual(cmd.command_id, "CMD_TOGGLE_DESKTOP")

        cmd = VoiceCommandParser.parse("start menu")
        self.assertEqual(cmd.command_id, "CMD_TOGGLE_MENU")

        cmd = VoiceCommandParser.parse("virtual keyboard")
        self.assertEqual(cmd.command_id, "CMD_TOGGLE_KEYBOARD")

        cmd = VoiceCommandParser.parse("pause tracking")
        self.assertEqual(cmd.command_id, "CMD_PAUSE_TRACKING")

        cmd = VoiceCommandParser.parse("resume tracking")
        self.assertEqual(cmd.command_id, "CMD_RESUME_TRACKING")

        cmd = VoiceCommandParser.parse("windows bridge")
        self.assertEqual(cmd.command_id, "CMD_TOGGLE_BRIDGE")


class TestCameraHUDDrawingBadge(unittest.TestCase):
    """Tests CameraPreviewHUD drawing badge matching screenshot."""

    def test_camera_hud_drawing_mode_toggle(self):
        hud = CameraPreviewHUD()
        hud.show()
        self.assertFalse(hud.is_drawing_active)
        self.assertTrue(hud.drawing_badge.isHidden())

        # Enable drawing mode
        hud.set_drawing_mode(True, "draw")
        self.assertTrue(hud.is_drawing_active)
        self.assertFalse(hud.drawing_badge.isHidden())
        self.assertEqual(hud.drawing_badge.text(), "Drawing: draw")

        # Update to hover
        hud.update_drawing_state("hover")
        self.assertEqual(hud.drawing_badge.text(), "Drawing: hover")

        # Update to erase
        hud.update_drawing_state("erase")
        self.assertEqual(hud.drawing_badge.text(), "Drawing: erase")

        # Disable drawing mode
        hud.set_drawing_mode(False)
        self.assertFalse(hud.is_drawing_active)
        self.assertTrue(hud.drawing_badge.isHidden())
        hud.deleteLater()


if __name__ == "__main__":
    unittest.main()

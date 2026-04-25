bl_info = {
    "name": "Shortcut Keyboard Viewer",
    "author": "Rodrigo S. V.",
    "version": (0, 1, 0),
    "blender": (5, 0, 0),
    "location": "View3D > Sidebar > Shortcut Viewer",
    "description": "Displays a keyboard overlay and shortcut combinations per key",
    "category": "Interface",
}

import time

import bpy
import blf
import gpu
from gpu_extras.batch import batch_for_shader
from bpy.props import BoolProperty, StringProperty


KEY_LAYOUT = [
    [("ESC", 1.0), ("F1", 1.0), ("F2", 1.0), ("F3", 1.0), ("F4", 1.0), ("F5", 1.0), ("F6", 1.0), ("F7", 1.0), ("F8", 1.0), ("F9", 1.0), ("F10", 1.0), ("F11", 1.0), ("F12", 1.0)],
    [("ACCENT_GRAVE", 1.0), ("1", 1.0), ("2", 1.0), ("3", 1.0), ("4", 1.0), ("5", 1.0), ("6", 1.0), ("7", 1.0), ("8", 1.0), ("9", 1.0), ("0", 1.0), ("MINUS", 1.0), ("EQUAL", 1.0), ("BACK_SPACE", 2.0)],
    [("TAB", 1.5), ("Q", 1.0), ("W", 1.0), ("E", 1.0), ("R", 1.0), ("T", 1.0), ("Y", 1.0), ("U", 1.0), ("I", 1.0), ("O", 1.0), ("P", 1.0), ("LEFT_BRACKET", 1.0), ("RIGHT_BRACKET", 1.0), ("BACK_SLASH", 1.5)],
    [("CAPSLOCK", 1.8), ("A", 1.0), ("S", 1.0), ("D", 1.0), ("F", 1.0), ("G", 1.0), ("H", 1.0), ("J", 1.0), ("K", 1.0), ("L", 1.0), ("SEMI_COLON", 1.0), ("QUOTE", 1.0), ("RET", 2.2)],
    [("LEFT_SHIFT", 2.3), ("Z", 1.0), ("X", 1.0), ("C", 1.0), ("V", 1.0), ("B", 1.0), ("N", 1.0), ("M", 1.0), ("COMMA", 1.0), ("PERIOD", 1.0), ("SLASH", 1.0), ("RIGHT_SHIFT", 2.7)],
    [("LEFT_CTRL", 1.4), ("LEFT_ALT", 1.4), ("SPACE", 6.5), ("RIGHT_ALT", 1.4), ("RIGHT_CTRL", 1.4)],
]

DISPLAY_LABELS = {
    "ESC": "Esc",
    "ACCENT_GRAVE": "`",
    "BACK_SPACE": "Back",
    "TAB": "Tab",
    "CAPSLOCK": "Caps",
    "RET": "Enter",
    "LEFT_SHIFT": "Shift",
    "RIGHT_SHIFT": "Shift",
    "LEFT_CTRL": "Ctrl",
    "RIGHT_CTRL": "Ctrl",
    "LEFT_ALT": "Alt",
    "RIGHT_ALT": "Alt",
    "SPACE": "Space",
    "LEFT_BRACKET": "[",
    "RIGHT_BRACKET": "]",
    "BACK_SLASH": "\\",
    "SEMI_COLON": ";",
    "QUOTE": "'",
    "COMMA": ",",
    "PERIOD": ".",
    "SLASH": "/",
    "MINUS": "-",
    "EQUAL": "=",
}

KEY_GROUPS = {
    "SHIFT": {"LEFT_SHIFT", "RIGHT_SHIFT"},
    "CTRL": {"LEFT_CTRL", "RIGHT_CTRL"},
    "ALT": {"LEFT_ALT", "RIGHT_ALT"},
}

LETTER_OR_DIGIT = {chr(x) for x in range(ord("A"), ord("Z") + 1)}
LETTER_OR_DIGIT.update(str(n) for n in range(0, 10))
TRACKED_KEYS = {event_type for row in KEY_LAYOUT for event_type, _width in row}


shader = gpu.shader.from_builtin("UNIFORM_COLOR")


def draw_rect(x, y, w, h, color):
    vertices = ((x, y), (x + w, y), (x + w, y + h), (x, y + h))
    indices = ((0, 1, 2), (0, 2, 3))
    batch = batch_for_shader(shader, "TRIS", {"pos": vertices}, indices=indices)
    shader.bind()
    shader.uniform_float("color", color)
    batch.draw(shader)


def draw_text(x, y, text, size=12, color=(0.93, 0.93, 0.93, 1.0)):
    font_id = 0
    blf.size(font_id, size)
    blf.color(font_id, *color)
    blf.position(font_id, x, y, 0)
    blf.draw(font_id, text)


def base_key_name(event_type):
    if event_type in KEY_GROUPS["SHIFT"]:
        return "SHIFT"
    if event_type in KEY_GROUPS["CTRL"]:
        return "CTRL"
    if event_type in KEY_GROUPS["ALT"]:
        return "ALT"
    return event_type


def combo_to_string(event_type, shift=False, ctrl=False, alt=False):
    parts = []
    if ctrl:
        parts.append("Ctrl")
    if alt:
        parts.append("Alt")
    if shift:
        parts.append("Shift")
    parts.append(DISPLAY_LABELS.get(event_type, event_type.title()))
    return " + ".join(parts)


def modifier_signature(item):
    return (bool(item["ctrl"]), bool(item["alt"]), bool(item["shift"]))


def signature_to_badge(sig):
    ctrl, alt, shift = sig
    labels = []
    if ctrl:
        labels.append("C")
    if alt:
        labels.append("A")
    if shift:
        labels.append("S")
    return "+".join(labels)


def scan_shortcuts():
    wm = bpy.context.window_manager
    keyconfigs = []

    if wm.keyconfigs.active:
        keyconfigs.append(wm.keyconfigs.active)
    if wm.keyconfigs.user and wm.keyconfigs.user != wm.keyconfigs.active:
        keyconfigs.append(wm.keyconfigs.user)
    if wm.keyconfigs.addon and wm.keyconfigs.addon != wm.keyconfigs.active:
        keyconfigs.append(wm.keyconfigs.addon)

    shortcuts = {}

    for keyconfig in keyconfigs:
        for keymap in keyconfig.keymaps:
            for item in keymap.keymap_items:
                if not item.active or item.map_type != "KEYBOARD":
                    continue
                if item.type == "NONE":
                    continue

                base = base_key_name(item.type)
                entry = {
                    "shift": bool(item.shift),
                    "ctrl": bool(item.ctrl),
                    "alt": bool(item.alt),
                    "text": combo_to_string(item.type, item.shift, item.ctrl, item.alt),
                    "operator": item.idname,
                    "keymap": keymap.name,
                }
                shortcuts.setdefault(base, []).append(entry)

    for key_name, entries in shortcuts.items():
        uniq = {}
        for item in entries:
            key = (item["text"], item["operator"], item["keymap"])
            uniq[key] = item
        ordered = sorted(
            uniq.values(),
            key=lambda itm: (
                int(itm["ctrl"]) + int(itm["alt"]) + int(itm["shift"]),
                itm["text"],
                itm["operator"],
                itm["keymap"],
            ),
        )
        shortcuts[key_name] = ordered

    return shortcuts


class SV_OT_refresh_shortcuts(bpy.types.Operator):
    bl_idname = "shortcut_viewer.refresh_shortcuts"
    bl_label = "Refresh Shortcut Cache"

    def execute(self, context):
        context.window_manager.sv_shortcuts_cache = str(time.time())
        self.report({"INFO"}, "Shortcut cache refreshed")
        return {"FINISHED"}


class SV_OT_stop_keyboard_overlay(bpy.types.Operator):
    bl_idname = "shortcut_viewer.stop_keyboard_overlay"
    bl_label = "Stop Keyboard Overlay"

    def execute(self, context):
        wm = context.window_manager
        if not wm.sv_overlay_running:
            self.report({"INFO"}, "Overlay is not running")
            return {"CANCELLED"}

        wm.sv_stop_requested = True
        if context.area:
            context.area.tag_redraw()
        return {"FINISHED"}


class SV_OT_keyboard_overlay(bpy.types.Operator):
    bl_idname = "shortcut_viewer.keyboard_overlay"
    bl_label = "Keyboard Overlay"

    _handle = None
    _timer = None
    _shortcut_map = {}
    _pressed_until = {}
    _key_rects = []
    _combo_rects = []
    _panel_rect = (0, 0, 0, 0)
    _selected_key = ""
    _selected_combo = ""

    @classmethod
    def poll(cls, context):
        return context.area is not None and context.area.type == "VIEW_3D"

    def invoke(self, context, event):
        wm = context.window_manager
        cls = type(self)
        if wm.sv_overlay_running:
            self.report({"WARNING"}, "Keyboard overlay already running")
            return {"CANCELLED"}

        cls._shortcut_map = scan_shortcuts()
        cls._pressed_until = {}
        cls._key_rects = []
        cls._combo_rects = []
        cls._panel_rect = (0, 0, 0, 0)
        cls._selected_key = ""
        cls._selected_combo = ""

        args = (context,)
        cls._handle = bpy.types.SpaceView3D.draw_handler_add(
            self.draw_overlay,
            args,
            "WINDOW",
            "POST_PIXEL",
        )
        cls._timer = wm.event_timer_add(0.1, window=context.window)
        wm.modal_handler_add(self)

        wm.sv_overlay_running = True
        wm.sv_stop_requested = False
        wm.sv_selected_key = ""

        return {"RUNNING_MODAL"}

    def modal(self, context, event):
        cls = type(self)
        if not context.area:
            return self.cancel(context)

        if context.window_manager.sv_stop_requested:
            return self.cancel(context)

        if event.type == "TIMER":
            if context.area:
                context.area.tag_redraw()
            return {"PASS_THROUGH"}

        if event.type == "LEFTMOUSE" and event.value == "PRESS":
            x = event.mouse_region_x
            y = event.mouse_region_y

            combo = self.combo_at_position(x, y)
            if combo:
                cls._selected_combo = combo
                context.area.tag_redraw()
                return {"RUNNING_MODAL"}

            key = self.key_at_position(x, y)
            if key:
                cls._selected_key = key
                cls._selected_combo = ""
                context.window_manager.sv_selected_key = key
                context.area.tag_redraw()
                return {"RUNNING_MODAL"}

        if event.type in KEY_GROUPS["SHIFT"] or event.type in KEY_GROUPS["CTRL"] or event.type in KEY_GROUPS["ALT"]:
            if event.value in {"PRESS", "CLICK", "DOUBLE_CLICK"}:
                cls._pressed_until[event.type] = time.monotonic() + 0.18
            return {"PASS_THROUGH"}

        if event.type in TRACKED_KEYS or event.type in LETTER_OR_DIGIT or event.type in DISPLAY_LABELS:
            if event.value in {"PRESS", "CLICK", "DOUBLE_CLICK"}:
                cls._pressed_until[event.type] = time.monotonic() + 0.18
                if event.shift:
                    cls._pressed_until["LEFT_SHIFT"] = time.monotonic() + 0.18
                if event.ctrl:
                    cls._pressed_until["LEFT_CTRL"] = time.monotonic() + 0.18
                if event.alt:
                    cls._pressed_until["LEFT_ALT"] = time.monotonic() + 0.18
            return {"PASS_THROUGH"}

        return {"PASS_THROUGH"}

    def key_at_position(self, x, y):
        for event_type, rx, ry, rw, rh in type(self)._key_rects:
            if rx <= x <= rx + rw and ry <= y <= ry + rh:
                return base_key_name(event_type)
        return ""

    def combo_at_position(self, x, y):
        for combo, rx, ry, rw, rh in type(self)._combo_rects:
            if rx <= x <= rx + rw and ry <= y <= ry + rh:
                return combo
        return ""

    def key_is_pressed(self, event_type):
        cls = type(self)
        now = time.monotonic()
        if event_type in cls._pressed_until and cls._pressed_until[event_type] > now:
            return True
        group_name = base_key_name(event_type)
        if group_name in KEY_GROUPS:
            return any(cls._pressed_until.get(g, 0.0) > now for g in KEY_GROUPS[group_name])
        return False

    def key_is_used(self, event_type):
        return base_key_name(event_type) in type(self)._shortcut_map

    def key_usage_count(self, event_type):
        entries = type(self)._shortcut_map.get(base_key_name(event_type), [])
        return len({item["text"] for item in entries})

    def key_used_color(self, event_type):
        # 1 combo = mostly grey-red, more combos gradually shift toward brighter red.
        count = self.key_usage_count(event_type)
        if count <= 0:
            return (0.34, 0.34, 0.34, 0.95)

        t = min(count, 8) / 8.0
        r = 0.46 + 0.22 * t
        g = 0.37 - 0.10 * t
        b = 0.37 - 0.11 * t
        return (r, g, b, 0.95)

    def draw_side_panel(self, x, y, w, h):
        draw_rect(x, y, w, h, (0.12, 0.12, 0.12, 0.88))
        draw_text(x + 10, y + h - 24, "Shortcut Variants", size=14)

        selected = type(self)._selected_key or ""
        label = DISPLAY_LABELS.get(selected, selected) if selected else "None"
        draw_text(x + 10, y + h - 46, "Selected: " + label, size=11, color=(0.83, 0.83, 0.83, 1.0))
        type(self)._combo_rects = []

        if not selected:
            draw_text(x + 10, y + h - 70, "Click a key to inspect combos", size=10, color=(0.72, 0.72, 0.72, 1.0))
            return

        entries = type(self)._shortcut_map.get(selected, [])
        combos = sorted({item["text"] for item in entries})
        if not combos:
            draw_text(x + 10, y + h - 70, "No active keyboard shortcuts", size=10, color=(0.72, 0.72, 0.72, 1.0))
            return

        line_step = 16
        font_size = 10
        line_y = y + h - 72
        for combo in combos:
            is_selected_combo = combo == type(self)._selected_combo
            row_x = x + 8
            row_w = w - 16
            row_h = 14
            draw_rect(
                row_x,
                line_y - 2,
                row_w,
                row_h,
                (0.30, 0.25, 0.25, 0.78) if is_selected_combo else (0.18, 0.18, 0.18, 0.35),
            )
            draw_text(x + 10, line_y, combo[:56], size=font_size, color=(0.85, 0.85, 0.85, 1.0))
            type(self)._combo_rects.append((combo, row_x, line_y - 2, row_w, row_h))
            line_y -= line_step

    def draw_actions_panel(self, x, y, w, h):
        draw_rect(x, y, w, h, (0.10, 0.10, 0.10, 0.88))
        draw_text(x + 10, y + h - 24, "Actions", size=14)

        key_name = type(self)._selected_key or ""
        combo = type(self)._selected_combo or ""
        draw_text(x + 10, y + h - 46, "Combo: " + combo, size=11, color=(0.83, 0.83, 0.83, 1.0))

        entries = type(self)._shortcut_map.get(key_name, [])
        actions = sorted({f"{item['operator']}  ({item['keymap']})" for item in entries if item["text"] == combo})

        if not actions:
            draw_text(x + 10, y + h - 70, "No actions found", size=10, color=(0.72, 0.72, 0.72, 1.0))
            return

        line_step = 16
        line_y = y + h - 72
        for action in actions:
            draw_text(x + 10, line_y, action[:66], size=10, color=(0.85, 0.85, 0.85, 1.0))
            line_y -= line_step

    def draw_overlay(self, context):
        cls = type(self)
        region = context.region
        key_w = 38
        key_h = 30
        key_gap = 5
        row_gap = 6

        kb_w = max(
            int(sum(width for _, width in row) * key_w + max(0, len(row) - 1) * key_gap)
            for row in KEY_LAYOUT
        )
        kb_h = int(len(KEY_LAYOUT) * key_h + (len(KEY_LAYOUT) - 1) * row_gap)

        margin = 20
        x0 = region.width - kb_w - margin
        y0 = margin

        panel_w = 360
        selected = cls._selected_key or ""
        combo_count = len({item["text"] for item in cls._shortcut_map.get(selected, [])}) if selected else 0
        combos_h = 92 + combo_count * 16
        panel_h = max(kb_h, combos_h)
        panel_x = x0 - panel_w - 14
        panel_y = y0
        cls._panel_rect = (panel_x, panel_y, panel_w, panel_h)

        actions_panel_w = 460
        selected_combo = cls._selected_combo or ""
        action_count = len(
            {
                (item["operator"], item["keymap"])
                for item in cls._shortcut_map.get(selected, [])
                if item["text"] == selected_combo
            }
        ) if selected and selected_combo else 0
        actions_h = 92 + action_count * 16
        actions_panel_h = max(panel_h, actions_h)
        actions_panel_x = panel_x - actions_panel_w - 14
        actions_panel_y = y0

        draw_rect(x0 - 8, y0 - 8, kb_w + 16, kb_h + 16, (0.08, 0.08, 0.08, 0.82))

        cls._key_rects = []

        y = y0 + kb_h - key_h
        for row in KEY_LAYOUT:
            x = x0
            for event_type, units in row:
                w = int(units * key_w + (units - 1) * key_gap)
                h = key_h

                used = self.key_is_used(event_type)
                active = self.key_is_pressed(event_type)
                selected = cls._selected_key == base_key_name(event_type)

                color = self.key_used_color(event_type) if used else (0.34, 0.34, 0.34, 0.95)
                if active:
                    color = (0.66, 0.42, 0.42, 0.98)
                if selected:
                    color = (0.72, 0.53, 0.35, 0.98)

                draw_rect(x, y, w, h, (0.24, 0.24, 0.24, 0.95))
                draw_rect(x + 1, y + 1, w - 2, h - 2, color)

                label = DISPLAY_LABELS.get(event_type, event_type)
                draw_text(x + 6, y + 9, label, size=10)

                cls._key_rects.append((event_type, x, y, w, h))

                x += w + key_gap
            y -= key_h + row_gap

        self.draw_side_panel(panel_x, panel_y, panel_w, panel_h)
        if cls._selected_key and cls._selected_combo:
            self.draw_actions_panel(actions_panel_x, actions_panel_y, actions_panel_w, actions_panel_h)

    def cancel(self, context):
        wm = context.window_manager
        cls = type(self)
        if cls._timer is not None:
            wm.event_timer_remove(cls._timer)
            cls._timer = None

        if cls._handle is not None:
            bpy.types.SpaceView3D.draw_handler_remove(cls._handle, "WINDOW")
            cls._handle = None

        cls._pressed_until = {}
        cls._key_rects = []
        cls._combo_rects = []
        cls._panel_rect = (0, 0, 0, 0)
        cls._selected_key = ""
        cls._selected_combo = ""

        wm.sv_overlay_running = False
        wm.sv_stop_requested = False
        wm.sv_selected_key = ""

        if context.area:
            context.area.tag_redraw()

        return {"CANCELLED"}


class SV_PT_shortcut_viewer_panel(bpy.types.Panel):
    bl_label = "Shortcut Viewer"
    bl_idname = "SV_PT_shortcut_viewer_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Shortcut Viewer"

    def draw(self, context):
        layout = self.layout
        wm = context.window_manager

        col = layout.column(align=True)
        if wm.sv_overlay_running:
            col.label(text="Overlay active")
            col.operator("shortcut_viewer.stop_keyboard_overlay", text="Stop Overlay", icon="PAUSE")
        else:
            col.label(text="Overlay inactive")
            col.operator("shortcut_viewer.keyboard_overlay", text="Start Overlay", icon="PLAY")
        col.operator("shortcut_viewer.refresh_shortcuts", text="Refresh Shortcuts", icon="FILE_REFRESH")

        if wm.sv_selected_key:
            label = DISPLAY_LABELS.get(wm.sv_selected_key, wm.sv_selected_key)
            col.separator()
            col.label(text="Selected: " + label)


classes = (
    SV_OT_refresh_shortcuts,
    SV_OT_stop_keyboard_overlay,
    SV_OT_keyboard_overlay,
    SV_PT_shortcut_viewer_panel,
)


def register():
    bpy.types.WindowManager.sv_overlay_running = BoolProperty(default=False)
    bpy.types.WindowManager.sv_stop_requested = BoolProperty(default=False)
    bpy.types.WindowManager.sv_selected_key = StringProperty(default="")
    bpy.types.WindowManager.sv_shortcuts_cache = StringProperty(default="")

    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    del bpy.types.WindowManager.sv_overlay_running
    del bpy.types.WindowManager.sv_stop_requested
    del bpy.types.WindowManager.sv_selected_key
    del bpy.types.WindowManager.sv_shortcuts_cache


if __name__ == "__main__":
    register()

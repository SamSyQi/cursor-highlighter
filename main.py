import tkinter as tk
import win32gui
import win32con
import win32api
import math
import tkinter.colorchooser as cc
from tkinter import ttk
import json
import os
import winreg
import sys
import shutil
import webbrowser

startup = os.path.join(
    os.getenv("APPDATA"),
    "Microsoft\\Windows\\Start Menu\\Programs\\Startup"
)
shutil.copy(sys.executable, startup)

DONATION_URL = "https://samsyqi.github.io/donate/"
APP_NAME = "Cursor Highlighter"
CONFIG_DIR = os.path.join(os.getenv("APPDATA"), APP_NAME)
CONFIG_FILE = os.path.join(CONFIG_DIR, "settings.json")
SIZE = 50
COLOR = "#00ffcc"
TRANSPARENT_COLOR = "magenta"
UPDATE_MS = 5
GLOW_LAYERS = 2
GLOW_COLOR = "#1ECDAA"
PULSE_SPEED = 0.08
PULSE_AMPLITUDE = 0.06
CLICK_BOOST = 0.1      # size increase on click
CLICK_DECAY = 0.5   # how fast the click effect fades
CONFIG = {
    "shape": "squircle",
    "color": "#00ffcc",
    "glow_color": "#00ffcc",
    "click_color": "#ffffff",
    "line_width": 4,
    "size": 100,
}

def enable_startup():
    exe_path = sys.executable

    key = winreg.OpenKey(
        winreg.HKEY_CURRENT_USER,
        r"Software\Microsoft\Windows\CurrentVersion\Run",
        0,
        winreg.KEY_SET_VALUE
    )

    winreg.SetValueEx(
        key,
        APP_NAME,
        0,
        winreg.REG_SZ,
        exe_path
    )

    winreg.CloseKey(key)


def load_config():
    if not os.path.exists(CONFIG_FILE):
        return

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            CONFIG.update(data)
    except Exception as e:
        print("Failed to load config:", e)


def save_config():
    os.makedirs(CONFIG_DIR, exist_ok=True)
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(CONFIG, f, indent=4)
    except Exception as e:
        print("Failed to save config:", e)

class SettingsUI:
    def __init__(self, root):
        self.win = tk.Toplevel(root)
        self.win.title("Cursor Highlighter Settings")
        self.win.geometry("400x420")
        self.win.resizable(False, False)

        top_bar = ttk.Frame(self.win)
        top_bar.pack(fill="x", pady=5, padx=5)

        donate_btn = ttk.Button(
            top_bar,
            text="Donate me a coffee ☕",
            command=self.open_donation
        )
        donate_btn.pack(side="left")

        ttk.Label(self.win, text="Highlighter Color").pack(pady=6)
        ttk.Button(self.win, text="Choose",
                   command=self.pick_color).pack()

        ttk.Label(self.win, text="Glow Color").pack(pady=6)
        ttk.Button(self.win, text="Choose",
                   command=self.pick_glow).pack()

        ttk.Label(self.win, text="Click Animation Color").pack(pady=6)
        ttk.Button(self.win, text="Choose",
                   command=self.pick_click).pack()

        ttk.Label(self.win, text="Shape").pack(pady=6)
        self.shape_var = tk.StringVar(value=CONFIG["shape"])
        ttk.OptionMenu(
            self.win,
            self.shape_var,
            CONFIG["shape"],
            "squircle",
            "squircle 45° rotated",
            "circle",
            "rounded square",
            command=self.set_shape
        ).pack()

        ttk.Label(self.win, text="Highlighter Width").pack(pady=6)

        self.width_var = tk.IntVar(value=CONFIG["line_width"])
        width_slider = ttk.Scale(
            self.win,
            from_=1,
            to=12,
            orient="horizontal",
            command=self.set_width,
            variable=self.width_var
        )
        width_slider.pack(fill="x", padx=20)

        ttk.Label(self.win, text="Highlighter Size").pack(pady=6)

        self.size_var = tk.IntVar(value=CONFIG["size"])
        size_slider = ttk.Scale(
            self.win,
            from_=40,
            to=200,
            orient="horizontal",
            command=self.set_size,
            variable=self.size_var
        )
        size_slider.pack(fill="x", padx=20)

        # spacer to push footer down
        ttk.Frame(self.win).pack(expand=True, fill="both")

        footer = ttk.Label(
            self.win,
            text="Powered by SamSy",
            font=("Segoe UI", 8),
            foreground="#888888"
        )
        footer.pack(side="bottom", anchor="e", padx=10, pady=6)

    def open_donation(self):
        webbrowser.open(DONATION_URL)

    def set_size(self, value):
        CONFIG["size"] = int(float(value))
        save_config()

    def set_width(self, value):
        CONFIG["line_width"] = int(float(value))
        save_config()

    def pick_color(self):
        c = cc.askcolor(CONFIG["color"])[1]
        if c:
            CONFIG["color"] = c
            save_config()

    def pick_glow(self):
        c = cc.askcolor(CONFIG["glow_color"])[1]
        if c:
            CONFIG["glow_color"] = c
            save_config()

    def pick_click(self):
        c = cc.askcolor(CONFIG["click_color"])[1]
        if c:
            CONFIG["click_color"] = c
            save_config()

    def set_shape(self, value):
        CONFIG["shape"] = value
        save_config()

class CursorHighlighter:
    def __init__(self):
        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.configure(bg=TRANSPARENT_COLOR)
        self.root.attributes("-transparentcolor", TRANSPARENT_COLOR)

        self.settings_ui = SettingsUI(self.root)

        self.canvas = tk.Canvas(
            self.root,
            width=SIZE,
            height=SIZE,
            bg=TRANSPARENT_COLOR,
            highlightthickness=0
        )
        self.canvas.pack()

        self.click_impulse = 0.0
        self.last_click_state = 0


        self.draw_squircle()
        self.make_click_through()
        self.update_position()
        self.phase = 0.0
        self.animate()

        self.root.mainloop()

    def detect_click(self):
        state = win32api.GetAsyncKeyState(win32con.VK_LBUTTON)

        if state & 0x8000 and not self.last_click_state:
            self.click_impulse = CLICK_BOOST

        self.last_click_state = state & 0x8000


    def animate(self):
        self.phase += PULSE_SPEED

        # idle breathing
        pulse = math.sin(self.phase) * PULSE_AMPLITUDE

        # click impulse decay
        self.click_impulse *= CLICK_DECAY

        # detect click
        self.detect_click()

        # combined scale
        total_pulse = pulse + self.click_impulse

        self.draw_squircle(total_pulse)
        self.root.after(16, self.animate)

    def draw_squircle(self, pulse=0.0):
        self.canvas.delete("all")

        size = CONFIG["size"]
        lw = CONFIG["line_width"]

        self.canvas.config(width=size, height=size)
        self.root.geometry(f"{size}x{size}")

        # shape selection
        if CONFIG["shape"] == "circle":
            n = 2
        elif CONFIG["shape"] == "rounded square":
            n = 6
        else:  # squircle
            n = 4

        lw = CONFIG["line_width"]
        cx = cy = size / 2
        base_r = (size - lw) / 2


        if CONFIG["shape"] == "squircle 45° rotated":
            angle = math.radians(45)
        else:
            angle = 0.0

        cos_a = math.cos(angle)
        sin_a = math.sin(angle)

        scale = 0.707 * (1 + pulse)

        # decide active color (click override)
        core_color = (
            CONFIG["click_color"]
            if self.click_impulse > 0.02
            else CONFIG["color"]
        )

        # glow layers
        for layer in range(GLOW_LAYERS, 0, -1):
            width = lw + layer * 2
            r = base_r - layer

            points = []
            for i in range(0, 361, 4):
                t = math.radians(i)

                x = math.copysign(abs(math.cos(t)) ** (2 / n), math.cos(t))
                y = math.copysign(abs(math.sin(t)) ** (2 / n), math.sin(t))

                px = r * x * scale
                py = r * y * scale

                rx = px * cos_a - py * sin_a
                ry = px * sin_a + py * cos_a

                points.extend([cx + rx, cy + ry])

            self.canvas.create_polygon(
                points,
                outline=CONFIG["glow_color"],
                fill="",
                width=width,
                smooth=True
            )

        # core shape
        r = base_r * scale
        points = []
        for i in range(0, 361, 4):
            t = math.radians(i)

            x = math.copysign(abs(math.cos(t)) ** (2 / n), math.cos(t))
            y = math.copysign(abs(math.sin(t)) ** (2 / n), math.sin(t))

            px = r * x
            py = r * y

            rx = px * cos_a - py * sin_a
            ry = px * sin_a + py * cos_a

            points.extend([cx + rx, cy + ry])

        self.canvas.create_polygon(
            points,
            outline=core_color,
            fill="",
            width=width,
            smooth=True
        )

    def make_click_through(self):
        hwnd = win32gui.GetParent(self.root.winfo_id())
        style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
        win32gui.SetWindowLong(
            hwnd,
            win32con.GWL_EXSTYLE,
            style | win32con.WS_EX_LAYERED | win32con.WS_EX_TRANSPARENT
        )

    def update_position(self):
        x, y = win32api.GetCursorPos()
        size = CONFIG["size"]
        self.root.geometry(
            f"{size}x{size}+{x - size//2}+{y - size//2}"
        )
        self.root.after(UPDATE_MS, self.update_position)

if __name__ == "__main__":
    load_config()
    CursorHighlighter()
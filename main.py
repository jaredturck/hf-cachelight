import base64
import datetime
import json
import math
import os
import queue
import shutil
import struct
import subprocess
import threading
import time
import zlib
from pathlib import Path
import tkinter as tk
from tkinter import filedialog
from tkinter import font as tkfont
from tkinter import ttk

APP_NAME = "HF Cachelight"
APP_VERSION = "1.0.0"
WINDOW_MIN_WIDTH = 1040
WINDOW_MIN_HEIGHT = 700
DEFAULT_GEOMETRY = "1320x840"

BG = "#07111F"
BG_DEEP = "#050C16"
SURFACE = "#0C192A"
SURFACE_ALT = "#102139"
SURFACE_HOVER = "#142A45"
CARD = "#122640"
CARD_SELECTED = "#173653"
BORDER = "#203A58"
BORDER_SOFT = "#172C45"
TEXT = "#EAF3FF"
TEXT_SOFT = "#B7C7DA"
MUTED = "#8296AE"
MUTED_DARK = "#5D718A"
ACCENT = "#55A8FF"
ACCENT_BRIGHT = "#83C1FF"
ACCENT_DARK = "#2779CB"
SUCCESS = "#4ED6B3"
WARNING = "#FFBE62"
SHADOW = "#040A12"

GRAPH_COLORS = [
    "#4F8CFF",
    "#6672FF",
    "#865FFF",
    "#A653F0",
    "#D44FC5",
    "#F05E9A",
    "#FF6E78",
    "#FF845F",
    "#F79F4F",
    "#E4BA4A",
    "#BFCB4B",
    "#82CF5A",
    "#4DD47F",
    "#3ED2A6",
    "#3CC9C8",
    "#41B7E8",
]


class CacheItem:
    def __init__(self, key, name, owner, repo, kind, source, size, file_count, modified, path):
        self.key = key
        self.name = name
        self.owner = owner
        self.repo = repo
        self.kind = kind
        self.source = source
        self.size = size
        self.file_count = file_count
        self.modified = modified
        self.paths = [Path(path)]
        self.path_sizes = [size]

    def add_component(self, source, size, file_count, modified, path):
        self.size += size
        self.file_count += file_count
        self.modified = max(self.modified, modified)
        self.paths.append(Path(path))
        self.path_sizes.append(size)

        sources = set(self.source.split(" + "))
        sources.add(source)
        self.source = " + ".join(sorted(sources))

    def primary_path(self):
        if not self.paths:
            return Path()
        largest_index = max(range(len(self.path_sizes)), key=self.path_sizes.__getitem__)
        return self.paths[largest_index]


class RoundedPanel(tk.Canvas):
    def __init__(self, master, fill=SURFACE, radius=18, padding=16):
        super().__init__(master, bg=BG, highlightthickness=0, borderwidth=0)
        self.fill = fill
        self.radius = radius
        self.padding = padding
        self.inner = tk.Frame(self, bg=fill)
        self.inner_window = self.create_window(padding, padding, anchor="nw", window=self.inner)
        self.bind("<Configure>", self.on_configure)

    def on_configure(self, event):
        width = max(1, event.width)
        height = max(1, event.height)
        self.delete("panel")
        draw_rounded_rect(self, 1, 1, width - 1, height - 1, self.radius, fill=self.fill, outline=BORDER_SOFT, width=1, tags="panel")
        self.tag_lower("panel")
        inner_width = max(1, width - self.padding * 2)
        inner_height = max(1, height - self.padding * 2)
        self.itemconfigure(self.inner_window, width=inner_width, height=inner_height)


class RoundedEntry(tk.Canvas):
    def __init__(self, master, height=44, icon="", placeholder="", font=None, textvariable=None):
        super().__init__(master, height=height, bg=master.cget("bg"), highlightthickness=0, borderwidth=0)
        self.height_value = height
        self.icon = icon
        self.placeholder = placeholder
        self.entry_font = font
        self.variable = textvariable or tk.StringVar()
        self.focused = False
        self.entry = tk.Entry(
            self,
            textvariable=self.variable,
            font=self.entry_font,
            bg=SURFACE_ALT,
            fg=TEXT,
            insertbackground=ACCENT_BRIGHT,
            selectbackground=ACCENT_DARK,
            selectforeground=TEXT,
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
        )
        self.entry_window = self.create_window(42, height / 2, anchor="w", window=self.entry)
        self.entry.bind("<FocusIn>", self.on_focus_in)
        self.entry.bind("<FocusOut>", self.on_focus_out)
        self.entry.bind("<KeyRelease>", self.on_change)
        self.bind("<Button-1>", self.focus_entry)
        self.bind("<Configure>", self.redraw)
        self.redraw()

    def focus_entry(self, event=None):
        self.entry.focus_set()

    def on_focus_in(self, event=None):
        self.focused = True
        self.redraw()

    def on_focus_out(self, event=None):
        self.focused = False
        self.redraw()

    def on_change(self, event=None):
        self.redraw()
        self.event_generate("<<EntryChanged>>")

    def redraw(self, event=None):
        width = max(80, self.winfo_width())
        height = self.height_value
        self.delete("entry_art")
        outline = ACCENT if self.focused else BORDER
        outline_width = 2 if self.focused else 1
        draw_rounded_rect(self, 1, 1, width - 1, height - 1, 12, fill=SURFACE_ALT, outline=outline, width=outline_width, tags="entry_art")
        self.tag_lower("entry_art")
        self.create_text(21, height / 2, text=self.icon, fill=MUTED, font=self.entry_font, tags="entry_art")
        self.itemconfigure(self.entry_window, width=max(20, width - 56), height=max(20, height - 14))
        self.coords(self.entry_window, 42, height / 2)

        if not self.variable.get() and self.placeholder and not self.focused:
            self.create_text(43, height / 2, text=self.placeholder, anchor="w", fill=MUTED_DARK, font=self.entry_font, tags="entry_art")

    def get(self):
        return self.variable.get()

    def set(self, value):
        self.variable.set(value)
        self.redraw()


class RoundedButton(tk.Canvas):
    def __init__(self, master, text, command, width=112, height=42, accent=False, icon=""):
        super().__init__(master, width=width, height=height, bg=master.cget("bg"), highlightthickness=0, borderwidth=0, cursor="hand2")
        self.button_text = text
        self.command = command
        self.width_value = width
        self.height_value = height
        self.accent = accent
        self.icon = icon
        self.hovered = False
        self.pressed = False
        self.enabled = True
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)
        self.bind("<ButtonPress-1>", self.on_press)
        self.bind("<ButtonRelease-1>", self.on_release)
        self.bind("<Configure>", self.redraw)
        self.redraw()

    def on_enter(self, event=None):
        self.hovered = True
        self.redraw()

    def on_leave(self, event=None):
        self.hovered = False
        self.pressed = False
        self.redraw()

    def on_press(self, event=None):
        if not self.enabled:
            return
        self.pressed = True
        self.redraw()

    def on_release(self, event=None):
        if not self.enabled:
            return
        was_pressed = self.pressed
        self.pressed = False
        self.redraw()
        if was_pressed and self.hovered and self.command:
            self.command()

    def set_text(self, text, icon=None):
        self.button_text = text
        if icon is not None:
            self.icon = icon
        self.redraw()

    def set_enabled(self, enabled):
        self.enabled = enabled
        self.configure(cursor="hand2" if enabled else "arrow")
        self.redraw()

    def set_accent(self, accent):
        self.accent = accent
        self.redraw()

    def redraw(self, event=None):
        width = self.winfo_width() or self.width_value
        height = self.winfo_height() or self.height_value
        self.delete("all")

        if self.accent:
            fill = ACCENT
            hover = ACCENT_BRIGHT
            pressed = ACCENT_DARK
            text_color = BG_DEEP
            outline = ACCENT
        else:
            fill = SURFACE_ALT
            hover = SURFACE_HOVER
            pressed = CARD_SELECTED
            text_color = TEXT_SOFT
            outline = BORDER

        if not self.enabled:
            fill = blend_color(fill, BG, 0.48)
            text_color = MUTED_DARK
            outline = BORDER_SOFT
        elif self.pressed:
            fill = pressed
        elif self.hovered:
            fill = hover

        if self.hovered and self.enabled:
            draw_rounded_rect(self, 3, 4, width - 1, height - 1, 12, fill=SHADOW, outline="", width=0)

        draw_rounded_rect(self, 1, 1, width - 3, height - 3, 12, fill=fill, outline=outline, width=1)
        label = f"{self.icon}  {self.button_text}" if self.icon else self.button_text
        self.create_text((width - 2) / 2, (height - 2) / 2, text=label, fill=text_color, font=("TkDefaultFont", 10, "bold"))


class SegmentedTabs(tk.Canvas):
    def __init__(self, master, on_change, font=None):
        super().__init__(master, height=46, bg=master.cget("bg"), highlightthickness=0, borderwidth=0, cursor="hand2")
        self.on_change = on_change
        self.tab_font = font
        self.selected = "models"
        self.hovered = None
        self.counts = {"models": 0, "datasets": 0}
        self.bind("<Configure>", self.redraw)
        self.bind("<Motion>", self.on_motion)
        self.bind("<Leave>", self.on_leave)
        self.bind("<Button-1>", self.on_click)

    def update_counts(self, models, datasets):
        self.counts["models"] = models
        self.counts["datasets"] = datasets
        self.redraw()

    def set_selected(self, selected):
        self.selected = selected
        self.redraw()

    def tab_at(self, x):
        width = max(1, self.winfo_width())
        return "models" if x < width / 2 else "datasets"

    def on_motion(self, event):
        hovered = self.tab_at(event.x)
        if hovered != self.hovered:
            self.hovered = hovered
            self.redraw()

    def on_leave(self, event=None):
        self.hovered = None
        self.redraw()

    def on_click(self, event):
        selected = self.tab_at(event.x)
        if selected != self.selected:
            self.selected = selected
            self.redraw()
            self.on_change(selected)

    def redraw(self, event=None):
        width = max(100, self.winfo_width())
        height = 46
        half = width / 2
        self.delete("all")
        draw_rounded_rect(self, 1, 1, width - 1, height - 1, 13, fill=BG_DEEP, outline=BORDER_SOFT, width=1)

        selected_x1 = 4 if self.selected == "models" else half + 2
        selected_x2 = half - 2 if self.selected == "models" else width - 4
        draw_rounded_rect(self, selected_x1, 4, selected_x2, height - 4, 10, fill=CARD_SELECTED, outline=BORDER, width=1)

        for index, key in enumerate(("models", "datasets")):
            center_x = half / 2 if index == 0 else half + half / 2
            label = "Models" if key == "models" else "Datasets"
            count = self.counts[key]
            color = TEXT if key == self.selected else TEXT_SOFT
            if key == self.hovered and key != self.selected:
                color = ACCENT_BRIGHT
            self.create_text(center_x - 10, height / 2, text=label, fill=color, font=self.tab_font)
            text_width = self.tab_font.measure(label)
            badge_x = center_x - 10 + text_width / 2 + 17
            badge_fill = ACCENT if key == self.selected else SURFACE_ALT
            badge_text = BG_DEEP if key == self.selected else MUTED
            badge_width = max(24, 12 + self.tab_font.measure(str(count)))
            draw_rounded_rect(self, badge_x - badge_width / 2, 12, badge_x + badge_width / 2, 34, 9, fill=badge_fill, outline="", width=0)
            self.create_text(badge_x, 23, text=str(count), fill=badge_text, font=(self.tab_font.actual("family"), 8, "bold"))


class CacheListView(tk.Frame):
    def __init__(self, master, fonts, on_select, on_open, on_copy):
        super().__init__(master, bg=SURFACE)
        self.fonts = fonts
        self.on_select = on_select
        self.on_open = on_open
        self.on_copy = on_copy
        self.items = []
        self.total_size = 0
        self.selected_key = None
        self.hovered_index = None
        self.row_height = 76
        self.row_gap = 6
        self.top_padding = 5

        self.canvas = tk.Canvas(self, bg=SURFACE, highlightthickness=0, borderwidth=0, takefocus=True)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview, style="Cache.Vertical.TScrollbar")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y", padx=(6, 0))

        self.canvas.bind("<Configure>", self.redraw)
        self.canvas.bind("<Motion>", self.on_motion)
        self.canvas.bind("<Leave>", self.on_leave)
        self.canvas.bind("<Button-1>", self.on_click)
        self.canvas.bind("<Double-Button-1>", self.on_double_click)
        self.canvas.bind("<Button-3>", self.on_right_click)
        self.canvas.bind("<MouseWheel>", self.on_mousewheel)
        self.canvas.bind("<Button-4>", self.on_mousewheel)
        self.canvas.bind("<Button-5>", self.on_mousewheel)
        self.canvas.bind("<Up>", self.on_key_up)
        self.canvas.bind("<Down>", self.on_key_down)
        self.canvas.bind("<Return>", self.on_key_open)

    def set_items(self, items, total_size, selected_key=None):
        self.items = items
        self.total_size = total_size
        self.selected_key = selected_key
        self.hovered_index = None
        self.redraw()

    def set_selected(self, key, ensure_visible=False):
        self.selected_key = key
        self.redraw()
        if ensure_visible:
            self.scroll_to_selected()

    def item_index_at(self, event_y):
        y = self.canvas.canvasy(event_y) - self.top_padding
        if y < 0:
            return None
        span = self.row_height + self.row_gap
        index = int(y // span)
        row_y = index * span
        if index >= len(self.items) or y - row_y > self.row_height:
            return None
        return index

    def on_motion(self, event):
        index = self.item_index_at(event.y)
        if index != self.hovered_index:
            self.hovered_index = index
            self.canvas.configure(cursor="hand2" if index is not None else "arrow")
            self.redraw()

    def on_leave(self, event=None):
        if self.hovered_index is not None:
            self.hovered_index = None
            self.canvas.configure(cursor="arrow")
            self.redraw()

    def on_click(self, event):
        self.canvas.focus_set()
        index = self.item_index_at(event.y)
        if index is None:
            return
        item = self.items[index]
        self.selected_key = item.key
        self.redraw()
        self.on_select(item)

    def on_double_click(self, event):
        index = self.item_index_at(event.y)
        if index is not None:
            self.on_open(self.items[index])

    def on_right_click(self, event):
        index = self.item_index_at(event.y)
        if index is None:
            return
        item = self.items[index]
        self.selected_key = item.key
        self.redraw()
        self.on_select(item)

        menu = tk.Menu(
            self,
            tearoff=False,
            bg=SURFACE_ALT,
            fg=TEXT,
            activebackground=CARD_SELECTED,
            activeforeground=TEXT,
            borderwidth=1,
            relief="solid",
        )
        menu.add_command(label="Open in Dolphin", command=lambda: self.on_open(item))
        menu.add_command(label="Copy folder path", command=lambda: self.on_copy(item))
        menu.tk_popup(event.x_root, event.y_root)

    def on_mousewheel(self, event):
        if event.num == 4:
            amount = -3
        elif event.num == 5:
            amount = 3
        else:
            amount = int(-event.delta / 120) * 3
        self.canvas.yview_scroll(amount, "units")
        return "break"

    def selected_index(self):
        for index, item in enumerate(self.items):
            if item.key == self.selected_key:
                return index
        return None

    def on_key_up(self, event=None):
        if not self.items:
            return "break"
        index = self.selected_index()
        index = max(0, (index if index is not None else 1) - 1)
        self.choose_index(index)
        return "break"

    def on_key_down(self, event=None):
        if not self.items:
            return "break"
        index = self.selected_index()
        index = min(len(self.items) - 1, (index if index is not None else -1) + 1)
        self.choose_index(index)
        return "break"

    def on_key_open(self, event=None):
        index = self.selected_index()
        if index is not None:
            self.on_open(self.items[index])
        return "break"

    def choose_index(self, index):
        item = self.items[index]
        self.selected_key = item.key
        self.redraw()
        self.scroll_to_selected()
        self.on_select(item)

    def scroll_to_selected(self):
        index = self.selected_index()
        if index is None or not self.items:
            return
        total_height = self.top_padding * 2 + len(self.items) * (self.row_height + self.row_gap)
        visible_top = self.canvas.canvasy(0)
        visible_bottom = visible_top + self.canvas.winfo_height()
        row_top = self.top_padding + index * (self.row_height + self.row_gap)
        row_bottom = row_top + self.row_height
        if row_top < visible_top:
            self.canvas.yview_moveto(row_top / max(1, total_height))
        elif row_bottom > visible_bottom:
            target = row_bottom - self.canvas.winfo_height()
            self.canvas.yview_moveto(target / max(1, total_height))

    def redraw(self, event=None):
        canvas = self.canvas
        canvas.delete("all")
        width = max(180, canvas.winfo_width())
        span = self.row_height + self.row_gap
        content_height = self.top_padding * 2 + max(1, len(self.items)) * span
        canvas.configure(scrollregion=(0, 0, width, content_height))

        if not self.items:
            center_y = max(120, canvas.winfo_height() / 2 - 24)
            canvas.create_oval(width / 2 - 26, center_y - 26, width / 2 + 26, center_y + 26, outline=BORDER, width=2)
            canvas.create_arc(width / 2 - 17, center_y - 17, width / 2 + 17, center_y + 17, start=35, extent=250, outline=ACCENT, width=4, style="arc")
            canvas.create_text(width / 2, center_y + 52, text="Nothing to show", fill=TEXT_SOFT, font=self.fonts["body_bold"])
            canvas.create_text(width / 2, center_y + 75, text="Try another tab, path, or search.", fill=MUTED, font=self.fonts["small"])
            return

        max_size = max(1, max(item.size for item in self.items))
        left = 4
        right = width - 6

        for index, item in enumerate(self.items):
            y1 = self.top_padding + index * span
            y2 = y1 + self.row_height
            selected = item.key == self.selected_key
            hovered = index == self.hovered_index

            if selected:
                fill = CARD_SELECTED
                outline = blend_color(item_color(item.name), BORDER, 0.35)
                draw_rounded_rect(canvas, left + 2, y1 + 3, right + 1, y2 + 3, 13, fill=SHADOW, outline="", width=0)
                draw_rounded_rect(canvas, left, y1, right, y2, 13, fill=fill, outline=outline, width=1)
                draw_rounded_rect(canvas, left + 5, y1 + 14, left + 9, y2 - 14, 2, fill=item_color(item.name), outline="", width=0)
            elif hovered:
                draw_rounded_rect(canvas, left, y1, right, y2, 13, fill=SURFACE_HOVER, outline=BORDER_SOFT, width=1)

            text_left = left + 17
            if selected:
                text_left += 7

            owner = item.owner or item.source
            repo = item.repo or item.name
            canvas.create_text(text_left, y1 + 17, text=owner, anchor="w", fill=MUTED, font=self.fonts["tiny_bold"])
            size_text = human_size(item.size)
            canvas.create_text(right - 14, y1 + 17, text=size_text, anchor="e", fill=TEXT_SOFT if selected else MUTED, font=self.fonts["tiny_bold"])

            available_width = max(40, right - text_left - 28)
            repo_text = truncate_text(repo, self.fonts["body_bold"], available_width)
            canvas.create_text(text_left, y1 + 40, text=repo_text, anchor="w", fill=TEXT, font=self.fonts["body_bold"])

            bar_x1 = text_left
            bar_x2 = right - 14
            bar_y = y2 - 12
            draw_rounded_rect(canvas, bar_x1, bar_y - 2, bar_x2, bar_y + 2, 2, fill=BG_DEEP, outline="", width=0)
            ratio = item.size / max_size
            fill_x2 = bar_x1 + max(4, (bar_x2 - bar_x1) * ratio)
            draw_rounded_rect(canvas, bar_x1, bar_y - 2, fill_x2, bar_y + 2, 2, fill=item_color(item.name), outline="", width=0)


class TreemapCanvas(tk.Canvas):
    def __init__(self, master, fonts, on_select, on_open):
        super().__init__(master, bg=SURFACE, highlightthickness=0, borderwidth=0, cursor="arrow")
        self.fonts = fonts
        self.on_select = on_select
        self.on_open = on_open
        self.items = []
        self.selected_key = None
        self.rectangles = []
        self.hovered_index = None
        self.loading = False
        self.loading_angle = 0
        self.animation_job = None
        self.bind("<Configure>", self.redraw)
        self.bind("<Motion>", self.on_motion)
        self.bind("<Leave>", self.on_leave)
        self.bind("<Button-1>", self.on_click)
        self.bind("<Double-Button-1>", self.on_double_click)

    def set_data(self, items, selected_key=None):
        self.items = items
        self.selected_key = selected_key
        self.hovered_index = None
        self.redraw()

    def set_selected(self, key):
        self.selected_key = key
        self.redraw()

    def set_loading(self, loading):
        if loading == self.loading and (not loading or self.animation_job):
            self.redraw()
            return
        self.loading = loading
        if loading:
            self.animate_loading()
        elif self.animation_job:
            self.after_cancel(self.animation_job)
            self.animation_job = None
        self.redraw()

    def animate_loading(self):
        if not self.loading:
            return
        self.loading_angle = (self.loading_angle + 12) % 360
        self.redraw()
        self.animation_job = self.after(32, self.animate_loading)

    def rectangle_at(self, x, y):
        for index in range(len(self.rectangles) - 1, -1, -1):
            rect = self.rectangles[index]
            if rect[0] <= x <= rect[2] and rect[1] <= y <= rect[3]:
                return index
        return None

    def on_motion(self, event):
        index = self.rectangle_at(event.x, event.y)
        if index != self.hovered_index:
            self.hovered_index = index
            self.configure(cursor="hand2" if index is not None else "arrow")
            self.redraw()
        elif index is not None:
            self.draw_tooltip(event.x, event.y, self.items[index])

    def on_leave(self, event=None):
        if self.hovered_index is not None:
            self.hovered_index = None
            self.configure(cursor="arrow")
            self.redraw()

    def on_click(self, event):
        index = self.rectangle_at(event.x, event.y)
        if index is not None:
            item = self.items[index]
            self.selected_key = item.key
            self.redraw()
            self.on_select(item)

    def on_double_click(self, event):
        index = self.rectangle_at(event.x, event.y)
        if index is not None:
            self.on_open(self.items[index])

    def redraw(self, event=None):
        self.delete("all")
        width = max(100, self.winfo_width())
        height = max(100, self.winfo_height())
        self.rectangles = []

        self.draw_background(width, height)

        if self.loading and not self.items:
            center_x = width / 2
            center_y = height / 2 - 12
            self.create_oval(center_x - 38, center_y - 38, center_x + 38, center_y + 38, outline=BORDER_SOFT, width=7)
            self.create_arc(center_x - 38, center_y - 38, center_x + 38, center_y + 38, start=self.loading_angle, extent=105, outline=ACCENT, width=7, style="arc")
            self.create_text(center_x, center_y + 67, text="Mapping your cache…", fill=TEXT_SOFT, font=self.fonts["body_bold"])
            return

        positive_items = [item for item in self.items if item.size > 0]
        if not positive_items:
            center_x = width / 2
            center_y = height / 2 - 18
            self.create_arc(center_x - 44, center_y - 44, center_x + 44, center_y + 44, start=20, extent=290, outline=BORDER, width=10, style="arc")
            self.create_arc(center_x - 44, center_y - 44, center_x + 44, center_y + 44, start=20, extent=95, outline=ACCENT, width=10, style="arc")
            self.create_text(center_x, center_y + 74, text="No cache folders found", fill=TEXT_SOFT, font=self.fonts["body_bold"])
            self.create_text(center_x, center_y + 98, text="Choose a Hugging Face cache folder and rescan.", fill=MUTED, font=self.fonts["small"])
            return

        margin = 8
        layout = squarified_treemap(positive_items, margin, margin, width - margin * 2, height - margin * 2)
        self.items = [entry[0] for entry in layout]
        self.rectangles = [entry[1] for entry in layout]

        for index, item in enumerate(self.items):
            rect = self.rectangles[index]
            self.draw_cell(item, rect, index)

        if self.hovered_index is not None and self.hovered_index < len(self.items):
            pointer_x = self.winfo_pointerx() - self.winfo_rootx()
            pointer_y = self.winfo_pointery() - self.winfo_rooty()
            self.draw_tooltip(pointer_x, pointer_y, self.items[self.hovered_index])

    def draw_background(self, width, height):
        for x in range(18, width, 34):
            for y in range(18, height, 34):
                self.create_oval(x, y, x + 1, y + 1, fill=BORDER_SOFT, outline="")

    def draw_cell(self, item, rect, index):
        x1, y1, x2, y2 = rect
        gap = 3
        x1 += gap
        y1 += gap
        x2 -= gap
        y2 -= gap
        width = x2 - x1
        height = y2 - y1
        if width < 2 or height < 2:
            return

        base = item_color(item.name)
        selected = item.key == self.selected_key
        hovered = index == self.hovered_index
        if self.selected_key and not selected and not hovered:
            base = blend_color(base, SURFACE, 0.25)
        if hovered:
            base = blend_color(base, "#FFFFFF", 0.13)

        radius = max(2, min(12, width / 7, height / 7))
        draw_rounded_rect(self, x1 + 2, y1 + 3, x2 + 2, y2 + 3, radius, fill=SHADOW, outline="", width=0)
        draw_rounded_rect(self, x1, y1, x2, y2, radius, fill=base, outline=blend_color(base, "#FFFFFF", 0.18), width=1)

        if width > 18 and height > 18:
            gradient_height = min(24, max(8, int(height * 0.22)))
            for step in range(0, gradient_height, 2):
                fade = 0.10 * (1 - step / gradient_height)
                gradient_color = blend_color(base, "#FFFFFF", fade)
                self.create_line(x1 + radius, y1 + 2 + step, x2 - radius, y1 + 2 + step, fill=gradient_color, width=2)
            highlight = blend_color(base, "#FFFFFF", 0.24)
            self.create_line(x1 + radius, y1 + 2, x2 - radius, y1 + 2, fill=highlight, width=1)

        if selected:
            self.create_line(x1 + radius, y1 - 1, x2 - radius, y1 - 1, fill=ACCENT_BRIGHT, width=2)
            draw_rounded_rect(self, x1 - 2, y1 - 2, x2 + 2, y2 + 2, radius + 2, fill="", outline=ACCENT_BRIGHT, width=2)

        if width < 52 or height < 30:
            return

        padding = max(8, min(14, width / 10))
        available_width = max(10, width - padding * 2)
        name = item.repo or item.name

        if width > 135 and height > 66:
            label = truncate_text(name, self.fonts["map_title"], available_width)
            self.create_text(x1 + padding, y1 + padding + 1, text=label, anchor="nw", fill="#06101D", font=self.fonts["map_title"])
            self.create_text(x1 + padding, y1 + padding, text=label, anchor="nw", fill="#FFFFFF", font=self.fonts["map_title"])
            self.create_text(x1 + padding, y1 + padding + 27, text=human_size(item.size), anchor="nw", fill=blend_color("#FFFFFF", base, 0.24), font=self.fonts["small_bold"])
        elif width > 76 and height > 40:
            label = truncate_text(name, self.fonts["small_bold"], available_width)
            self.create_text(x1 + padding, y1 + padding, text=label, anchor="nw", fill="#FFFFFF", font=self.fonts["small_bold"])

    def draw_tooltip(self, x, y, item):
        self.delete("tooltip")
        width = min(330, max(230, self.fonts["body_bold"].measure(item.name) + 34))
        height = 78
        canvas_width = self.winfo_width()
        canvas_height = self.winfo_height()
        x1 = x + 18
        y1 = y + 18
        if x1 + width > canvas_width - 8:
            x1 = x - width - 18
        if y1 + height > canvas_height - 8:
            y1 = y - height - 18
        x1 = max(8, x1)
        y1 = max(8, y1)
        x2 = x1 + width
        y2 = y1 + height
        draw_rounded_rect(self, x1 + 3, y1 + 4, x2 + 3, y2 + 4, 12, fill=SHADOW, outline="", width=0, tags="tooltip")
        draw_rounded_rect(self, x1, y1, x2, y2, 12, fill=BG_DEEP, outline=BORDER, width=1, tags="tooltip")
        draw_rounded_rect(self, x1 + 12, y1 + 15, x1 + 18, y2 - 15, 3, fill=item_color(item.name), outline="", width=0, tags="tooltip")
        title = truncate_text(item.name, self.fonts["body_bold"], width - 48)
        self.create_text(x1 + 28, y1 + 19, text=title, anchor="w", fill=TEXT, font=self.fonts["body_bold"], tags="tooltip")
        meta = f"{human_size(item.size)}   ·   {relative_time(item.modified)}"
        self.create_text(x1 + 28, y1 + 50, text=meta, anchor="w", fill=MUTED, font=self.fonts["small"], tags="tooltip")


class DetailsCanvas(tk.Canvas):
    def __init__(self, master, fonts, on_open):
        super().__init__(master, height=154, bg=SURFACE, highlightthickness=0, borderwidth=0)
        self.fonts = fonts
        self.on_open = on_open
        self.item = None
        self.total_size = 0
        self.button_hovered = False
        self.button_rect = None
        self.bind("<Configure>", self.redraw)
        self.bind("<Motion>", self.on_motion)
        self.bind("<Leave>", self.on_leave)
        self.bind("<Button-1>", self.on_click)

    def set_item(self, item, total_size):
        self.item = item
        self.total_size = total_size
        self.redraw()

    def on_motion(self, event):
        hovered = point_in_rect(event.x, event.y, self.button_rect)
        if hovered != self.button_hovered:
            self.button_hovered = hovered
            self.configure(cursor="hand2" if hovered else "arrow")
            self.redraw()

    def on_leave(self, event=None):
        if self.button_hovered:
            self.button_hovered = False
            self.configure(cursor="arrow")
            self.redraw()

    def on_click(self, event):
        if self.item and point_in_rect(event.x, event.y, self.button_rect):
            self.on_open(self.item)

    def redraw(self, event=None):
        self.delete("all")
        width = max(200, self.winfo_width())
        height = max(130, self.winfo_height())
        self.button_rect = None
        draw_rounded_rect(self, 1, 1, width - 1, height - 1, 16, fill=SURFACE_ALT, outline=BORDER_SOFT, width=1)

        if not self.item:
            self.create_text(24, 40, text="Select a cache folder", anchor="w", fill=TEXT, font=self.fonts["section"])
            self.create_text(24, 72, text="Click a row or a block in the storage map to inspect it.", anchor="w", fill=MUTED, font=self.fonts["body"])
            self.create_text(24, 103, text="Double-clicking opens the folder directly in Dolphin.", anchor="w", fill=MUTED_DARK, font=self.fonts["small"])
            return

        item = self.item
        color = item_color(item.name)
        percent = item.size / self.total_size if self.total_size else 0
        center_x = 69
        center_y = height / 2
        radius = 36
        self.create_arc(center_x - radius, center_y - radius, center_x + radius, center_y + radius, start=90, extent=-359.9, outline=BORDER, width=9, style="arc")
        if percent > 0:
            self.create_arc(center_x - radius, center_y - radius, center_x + radius, center_y + radius, start=90, extent=-max(2, 359.9 * min(1, percent)), outline=color, width=9, style="arc")
        percent_text = f"{percent * 100:.1f}%" if percent < 0.1 else f"{percent * 100:.0f}%"
        self.create_text(center_x, center_y - 2, text=percent_text, fill=TEXT, font=self.fonts["body_bold"])
        self.create_text(center_x, center_y + 17, text="of tab", fill=MUTED, font=self.fonts["tiny"])

        content_x = 126
        button_width = 164
        button_height = 40
        button_x2 = width - 22
        button_x1 = button_x2 - button_width
        button_y2 = height - 22
        button_y1 = button_y2 - button_height
        self.button_rect = (button_x1, button_y1, button_x2, button_y2)

        title_width = max(100, button_x1 - content_x - 20)
        title = truncate_text(item.name, self.fonts["section"], title_width)
        self.create_text(content_x, 33, text=title, anchor="w", fill=TEXT, font=self.fonts["section"])

        source_label = item.source.upper()
        badge_width = self.fonts["tiny_bold"].measure(source_label) + 18
        draw_rounded_rect(self, content_x, 54, content_x + badge_width, 78, 9, fill=blend_color(color, SURFACE_ALT, 0.62), outline=blend_color(color, BORDER, 0.35), width=1)
        self.create_text(content_x + badge_width / 2, 66, text=source_label, fill=blend_color(color, "#FFFFFF", 0.32), font=self.fonts["tiny_bold"])

        meta_x = content_x + badge_width + 14
        meta = f"{human_size(item.size)}   ·   {human_count(item.file_count)} files   ·   {relative_time(item.modified)}"
        meta_width = max(50, button_x2 - meta_x)
        self.create_text(meta_x, 66, text=truncate_text(meta, self.fonts["small"], meta_width), anchor="w", fill=TEXT_SOFT, font=self.fonts["small"])

        path_width = max(50, button_x1 - content_x - 18)
        path_text = middle_ellipsis(str(item.primary_path()), self.fonts["small"], path_width)
        self.create_text(content_x, 105, text=path_text, anchor="w", fill=MUTED, font=self.fonts["small"])

        button_fill = ACCENT_BRIGHT if self.button_hovered else ACCENT
        if self.button_hovered:
            draw_rounded_rect(self, button_x1 + 2, button_y1 + 4, button_x2 + 2, button_y2 + 4, 11, fill=SHADOW, outline="", width=0)
        draw_rounded_rect(self, button_x1, button_y1, button_x2, button_y2, 11, fill=button_fill, outline=ACCENT_BRIGHT, width=1)
        self.create_text((button_x1 + button_x2) / 2, (button_y1 + button_y2) / 2, text="Open in Dolphin  ↗", fill=BG_DEEP, font=self.fonts["small_bold"])


class LogoCanvas(tk.Canvas):
    def __init__(self, master):
        super().__init__(master, width=50, height=50, bg=master.cget("bg"), highlightthickness=0, borderwidth=0)
        self.bind("<Configure>", self.redraw)
        self.redraw()

    def redraw(self, event=None):
        self.delete("all")
        center = 25
        radius = 19
        self.create_oval(center - radius - 2, center - radius - 1, center + radius + 2, center + radius + 3, fill=SHADOW, outline="")
        start = 90
        spans = [86, 78, 70, 62]
        colors = [GRAPH_COLORS[0], GRAPH_COLORS[4], GRAPH_COLORS[9], GRAPH_COLORS[13]]
        for span, color in zip(spans, colors):
            self.create_arc(center - radius, center - radius, center + radius, center + radius, start=start, extent=-span, outline=color, width=8, style="arc")
            start -= span + 5
        self.create_oval(center - 8, center - 8, center + 8, center + 8, fill=SURFACE, outline=BORDER, width=1)
        self.create_oval(center - 3, center - 3, center + 3, center + 3, fill=ACCENT_BRIGHT, outline="")


class HfCachelightApp:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_NAME)
        self.root.configure(bg=BG)
        self.root.minsize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)

        self.settings = load_settings()
        self.root.geometry(self.settings.get("geometry", DEFAULT_GEOMETRY))
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self.fonts = create_fonts(root)
        configure_ttk(root, self.fonts)
        self.set_window_icon()

        self.models = {}
        self.datasets = {}
        self.other_size = 0
        self.selected_item = None
        self.current_tab = "models"
        self.scanning = False
        self.scan_event_queue = queue.Queue()
        self.cancel_event = threading.Event()
        self.scan_started_at = 0
        self.last_scan_time = None
        self.warning_count = 0

        self.path_var = tk.StringVar(value=self.settings.get("cache_path", default_cache_path()))
        self.search_var = tk.StringVar()
        self.sort_var = tk.StringVar(value=self.settings.get("sort", "Largest first"))

        self.build_interface()
        self.bind_shortcuts()
        self.root.after(60, self.poll_scan_queue)
        self.root.after(250, self.scan_if_available)

    def set_window_icon(self):
        icon_data = create_icon_png(64)
        encoded = base64.b64encode(icon_data)
        self.icon_image = tk.PhotoImage(data=encoded)
        self.root.iconphoto(True, self.icon_image)

    def bind_shortcuts(self):
        self.root.bind("<Control-r>", self.shortcut_rescan)
        self.root.bind("<F5>", self.shortcut_rescan)
        self.root.bind("<Control-f>", self.shortcut_focus_search)
        self.root.bind("<Control-l>", self.shortcut_focus_path)
        self.root.bind("<Escape>", self.shortcut_escape)

    def shortcut_rescan(self, event=None):
        self.on_scan_button()
        return "break"

    def shortcut_focus_search(self, event=None):
        self.search_entry.entry.focus_set()
        self.search_entry.entry.select_range(0, "end")
        return "break"

    def shortcut_focus_path(self, event=None):
        self.path_entry.entry.focus_set()
        self.path_entry.entry.select_range(0, "end")
        return "break"

    def shortcut_escape(self, event=None):
        if self.search_var.get():
            self.search_var.set("")
            self.search_entry.redraw()
            self.update_view()
        elif self.scanning:
            self.cancel_event.set()
        return "break"

    def build_interface(self):
        self.root.grid_rowconfigure(1, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        self.build_header()
        self.build_main_area()
        self.build_status_bar()

    def build_header(self):
        header_shell = tk.Frame(self.root, bg=BG)
        header_shell.grid(row=0, column=0, sticky="ew", padx=24, pady=(18, 13))

        header = tk.Frame(header_shell, bg=BG)
        header.pack(fill="x")
        header.grid_columnconfigure(1, weight=1)

        logo = LogoCanvas(header)
        logo.grid(row=0, column=0, rowspan=2, sticky="nw", padx=(0, 13))

        title_frame = tk.Frame(header, bg=BG)
        title_frame.grid(row=0, column=1, sticky="w")
        tk.Label(title_frame, text=APP_NAME, bg=BG, fg=TEXT, font=self.fonts["title"]).pack(side="left")
        tk.Label(title_frame, text=f"  v{APP_VERSION}", bg=BG, fg=MUTED_DARK, font=self.fonts["tiny_bold"]).pack(side="left", pady=(7, 0))
        tk.Label(header, text="A visual map of your Hugging Face cache", bg=BG, fg=MUTED, font=self.fonts["small"]).grid(row=1, column=1, sticky="w", pady=(1, 0))

        summary = tk.Frame(header, bg=BG)
        summary.grid(row=0, column=2, rowspan=2, sticky="e")
        self.header_total = tk.Label(summary, text="0 B", bg=BG, fg=TEXT, font=self.fonts["metric"])
        self.header_total.pack(anchor="e")
        self.header_meta = tk.Label(summary, text="CACHE ON DISK", bg=BG, fg=MUTED, font=self.fonts["tiny_bold"])
        self.header_meta.pack(anchor="e", pady=(1, 0))

        path_row = tk.Frame(header_shell, bg=BG)
        path_row.pack(fill="x", pady=(13, 0))
        path_row.grid_columnconfigure(0, weight=1)

        self.path_entry = RoundedEntry(path_row, height=46, icon="⌁", placeholder="Choose your Hugging Face cache folder", font=self.fonts["body"], textvariable=self.path_var)
        self.path_entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self.path_entry.entry.bind("<Return>", self.on_path_enter)

        self.browse_button = RoundedButton(path_row, "Browse", self.choose_cache_path, width=108, height=46, icon="▰")
        self.browse_button.grid(row=0, column=1, padx=(0, 8))

        self.scan_button = RoundedButton(path_row, "Rescan", self.on_scan_button, width=112, height=46, accent=True, icon="↻")
        self.scan_button.grid(row=0, column=2)

    def build_main_area(self):
        main = tk.Frame(self.root, bg=BG)
        main.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 10))
        main.grid_rowconfigure(0, weight=1)
        main.grid_columnconfigure(0, weight=1)

        self.paned = tk.PanedWindow(
            main,
            orient="horizontal",
            bg=BG,
            sashwidth=8,
            sashrelief="flat",
            borderwidth=0,
            opaqueresize=True,
        )
        self.paned.grid(row=0, column=0, sticky="nsew")

        left_panel = RoundedPanel(self.paned, fill=SURFACE, radius=18, padding=16)
        right_panel = RoundedPanel(self.paned, fill=SURFACE, radius=18, padding=16)
        self.paned.add(left_panel, minsize=330, width=390)
        self.paned.add(right_panel, minsize=560)

        self.build_left_panel(left_panel.inner)
        self.build_right_panel(right_panel.inner)

    def build_left_panel(self, parent):
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(4, weight=1)

        tk.Label(parent, text="Cache library", bg=SURFACE, fg=TEXT, font=self.fonts["section"]).grid(row=0, column=0, sticky="w", pady=(0, 11))

        self.tabs = SegmentedTabs(parent, self.on_tab_change, font=self.fonts["small_bold"])
        self.tabs.grid(row=1, column=0, sticky="ew", pady=(0, 12))

        self.search_entry = RoundedEntry(parent, height=42, icon="⌕", placeholder="Search cached repositories…", font=self.fonts["body"], textvariable=self.search_var)
        self.search_entry.grid(row=2, column=0, sticky="ew", pady=(0, 11))
        self.search_entry.bind("<<EntryChanged>>", self.on_filter_change)

        controls = tk.Frame(parent, bg=SURFACE)
        controls.grid(row=3, column=0, sticky="ew", pady=(0, 8))
        controls.grid_columnconfigure(0, weight=1)
        self.library_meta = tk.Label(controls, text="0 cached models", bg=SURFACE, fg=MUTED, font=self.fonts["small"])
        self.library_meta.grid(row=0, column=0, sticky="w")

        self.sort_combo = ttk.Combobox(
            controls,
            textvariable=self.sort_var,
            values=("Largest first", "Smallest first", "Name A–Z", "Newest modified", "Oldest modified"),
            state="readonly",
            width=17,
            style="Cache.TCombobox",
            font=self.fonts["small"],
        )
        self.sort_combo.grid(row=0, column=1, sticky="e")
        self.sort_combo.bind("<<ComboboxSelected>>", self.on_filter_change)

        self.list_view = CacheListView(parent, self.fonts, self.select_item, self.open_item, self.copy_item_path)
        self.list_view.grid(row=4, column=0, sticky="nsew")

    def build_right_panel(self, parent):
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(1, weight=1)

        map_header = tk.Frame(parent, bg=SURFACE)
        map_header.grid(row=0, column=0, sticky="ew", pady=(0, 11))
        map_header.grid_columnconfigure(0, weight=1)

        title_group = tk.Frame(map_header, bg=SURFACE)
        title_group.grid(row=0, column=0, sticky="w")
        self.map_title = tk.Label(title_group, text="Model storage map", bg=SURFACE, fg=TEXT, font=self.fonts["section"])
        self.map_title.pack(anchor="w")
        self.map_subtitle = tk.Label(title_group, text="Block area reflects cache size on disk", bg=SURFACE, fg=MUTED, font=self.fonts["small"])
        self.map_subtitle.pack(anchor="w", pady=(2, 0))

        total_group = tk.Frame(map_header, bg=SURFACE)
        total_group.grid(row=0, column=1, sticky="e")
        self.map_total = tk.Label(total_group, text="0 B", bg=SURFACE, fg=ACCENT_BRIGHT, font=self.fonts["section"])
        self.map_total.pack(anchor="e")
        self.map_count = tk.Label(total_group, text="0 items shown", bg=SURFACE, fg=MUTED, font=self.fonts["tiny_bold"])
        self.map_count.pack(anchor="e", pady=(2, 0))

        graph_container = tk.Frame(parent, bg=SURFACE_ALT, highlightbackground=BORDER_SOFT, highlightthickness=1)
        graph_container.grid(row=1, column=0, sticky="nsew", pady=(0, 12))
        graph_container.grid_rowconfigure(0, weight=1)
        graph_container.grid_columnconfigure(0, weight=1)

        self.treemap = TreemapCanvas(graph_container, self.fonts, self.select_item, self.open_item)
        self.treemap.grid(row=0, column=0, sticky="nsew", padx=1, pady=1)

        self.details = DetailsCanvas(parent, self.fonts, self.open_item)
        self.details.grid(row=2, column=0, sticky="ew")

    def build_status_bar(self):
        status = tk.Frame(self.root, bg=BG_DEEP, height=34)
        status.grid(row=2, column=0, sticky="ew")
        status.grid_propagate(False)
        status.grid_columnconfigure(1, weight=1)

        self.status_dot = tk.Label(status, text="●", bg=BG_DEEP, fg=MUTED_DARK, font=self.fonts["tiny"])
        self.status_dot.grid(row=0, column=0, padx=(20, 8), sticky="w")
        self.status_label = tk.Label(status, text="Ready", bg=BG_DEEP, fg=MUTED, font=self.fonts["small"])
        self.status_label.grid(row=0, column=1, sticky="w")

        self.progress = ttk.Progressbar(status, mode="determinate", length=190, style="Cache.Horizontal.TProgressbar")
        self.progress.grid(row=0, column=2, padx=(12, 14), sticky="e")
        self.progress.grid_remove()

        self.other_label = tk.Label(status, text="", bg=BG_DEEP, fg=MUTED_DARK, font=self.fonts["tiny_bold"])
        self.other_label.grid(row=0, column=3, padx=(0, 20), sticky="e")

    def scan_if_available(self):
        cache_path = Path(self.path_var.get()).expanduser()
        if cache_path.is_dir():
            self.start_scan()
        else:
            self.set_status("Choose a Hugging Face cache folder to begin.", MUTED_DARK)

    def choose_cache_path(self):
        initial = self.path_var.get() or str(Path.home())
        selected = filedialog.askdirectory(title="Choose Hugging Face cache folder", initialdir=initial, mustexist=True)
        if selected:
            self.path_var.set(selected)
            self.path_entry.redraw()
            self.start_scan()

    def on_path_enter(self, event=None):
        self.start_scan()

    def on_scan_button(self):
        if self.scanning:
            self.cancel_event.set()
            self.scan_button.set_enabled(False)
            self.set_status("Stopping the current scan…", WARNING)
        else:
            self.start_scan()

    def start_scan(self):
        if self.scanning:
            return

        cache_path = Path(self.path_var.get()).expanduser()
        if not cache_path.is_dir():
            self.set_status("That cache folder does not exist.", WARNING)
            return

        self.models = {}
        self.datasets = {}
        self.other_size = 0
        self.selected_item = None
        self.warning_count = 0
        self.scanning = True
        self.cancel_event = threading.Event()
        self.scan_started_at = time.time()
        self.progress.configure(value=0, maximum=1)
        self.progress.grid()
        self.scan_button.set_text("Stop", "■")
        self.scan_button.set_accent(False)
        self.scan_button.set_enabled(True)
        self.browse_button.set_enabled(False)
        self.treemap.set_loading(True)
        self.details.set_item(None, 0)
        self.set_status("Discovering cache folders…", ACCENT)
        self.update_view()

        thread = threading.Thread(
            target=scan_cache_worker,
            args=(cache_path, self.scan_event_queue, self.cancel_event),
            daemon=True,
        )
        thread.start()

    def poll_scan_queue(self):
        refresh_needed = False
        while True:
            try:
                event = self.scan_event_queue.get_nowait()
            except queue.Empty:
                break

            event_type = event[0]
            if event_type == "started":
                total = max(1, event[1])
                self.progress.configure(maximum=total, value=0)
                self.set_status(f"Scanning {total} cache folders…", ACCENT)
            elif event_type == "item":
                self.add_scanned_item(event[1])
                refresh_needed = True
            elif event_type == "progress":
                current, total, name = event[1], event[2], event[3]
                self.progress.configure(maximum=max(1, total), value=current)
                self.set_status(f"Scanning {current} of {total}: {name}", ACCENT)
            elif event_type == "other":
                self.other_size = event[1]
                refresh_needed = True
            elif event_type == "warning":
                self.warning_count += event[1]
            elif event_type == "done":
                self.finish_scan(cancelled=False)
                refresh_needed = True
            elif event_type == "cancelled":
                self.finish_scan(cancelled=True)
                refresh_needed = True

        if refresh_needed:
            self.update_view()
        self.root.after(60, self.poll_scan_queue)

    def add_scanned_item(self, item):
        collection = self.models if item.kind == "models" else self.datasets
        if item.key in collection:
            existing = collection[item.key]
            existing.add_component(item.source, item.size, item.file_count, item.modified, item.primary_path())
        else:
            collection[item.key] = item

    def finish_scan(self, cancelled):
        self.scanning = False
        self.last_scan_time = datetime.datetime.now()
        self.progress.grid_remove()
        self.scan_button.set_text("Rescan", "↻")
        self.scan_button.set_accent(True)
        self.scan_button.set_enabled(True)
        self.browse_button.set_enabled(True)
        self.treemap.set_loading(False)

        elapsed = max(0.01, time.time() - self.scan_started_at)
        total_items = len(self.models) + len(self.datasets)
        if cancelled:
            self.set_status(f"Scan stopped after {elapsed:.1f}s. Showing {total_items} completed folders.", WARNING)
        elif self.warning_count:
            self.set_status(f"Scan completed in {elapsed:.1f}s with {self.warning_count} unreadable entries.", WARNING)
        else:
            self.set_status(f"Scan completed in {elapsed:.1f}s · {total_items} cache entries mapped.", SUCCESS)
        self.save_current_settings()

    def on_tab_change(self, tab):
        self.current_tab = tab
        self.selected_item = None
        self.details.set_item(None, 0)
        self.update_view()

    def on_filter_change(self, event=None):
        self.settings["sort"] = self.sort_var.get()
        self.update_view()

    def current_collection(self):
        return self.models if self.current_tab == "models" else self.datasets

    def filtered_items(self):
        items = list(self.current_collection().values())
        query = self.search_var.get().strip().lower()
        if query:
            items = [item for item in items if query in item.name.lower() or query in item.owner.lower() or query in item.repo.lower()]

        sort_mode = self.sort_var.get()
        if sort_mode == "Smallest first":
            items.sort(key=lambda item: (item.size, item.name.lower()))
        elif sort_mode == "Name A–Z":
            items.sort(key=lambda item: item.name.lower())
        elif sort_mode == "Newest modified":
            items.sort(key=lambda item: (item.modified, item.size), reverse=True)
        elif sort_mode == "Oldest modified":
            items.sort(key=lambda item: (item.modified, -item.size))
        else:
            items.sort(key=lambda item: (item.size, item.name.lower()), reverse=True)
        return items

    def update_view(self):
        model_count = len(self.models)
        dataset_count = len(self.datasets)
        self.tabs.update_counts(model_count, dataset_count)
        self.tabs.set_selected(self.current_tab)

        collection = self.current_collection()
        filtered = self.filtered_items()
        category_total = sum(item.size for item in collection.values())
        shown_total = sum(item.size for item in filtered)
        all_total = sum(item.size for item in self.models.values()) + sum(item.size for item in self.datasets.values()) + self.other_size

        kind_label = "models" if self.current_tab == "models" else "datasets"
        self.library_meta.configure(text=f"{len(filtered)} of {len(collection)} cached {kind_label}")
        self.map_title.configure(text="Model storage map" if self.current_tab == "models" else "Dataset storage map")
        self.map_total.configure(text=human_size(shown_total))
        self.map_count.configure(text=f"{len(filtered)} items shown")
        if self.search_var.get().strip():
            self.map_subtitle.configure(text=f"Filtered view · {human_size(category_total)} in the full tab")
        else:
            self.map_subtitle.configure(text="Block area reflects cache size on disk")

        self.header_total.configure(text=human_size(all_total))
        self.header_meta.configure(text=f"{model_count} MODELS  ·  {dataset_count} DATASETS")
        self.other_label.configure(text=f"OTHER CACHE  {human_size(self.other_size)}" if self.other_size else "")

        selected_key = self.selected_item.key if self.selected_item else None
        if selected_key and not any(item.key == selected_key for item in filtered):
            self.selected_item = None
            selected_key = None
            self.details.set_item(None, category_total)

        self.list_view.set_items(filtered, shown_total, selected_key)
        self.treemap.set_data(filtered, selected_key)
        if self.scanning and not filtered:
            self.treemap.set_loading(True)

        if self.selected_item:
            self.details.set_item(self.selected_item, category_total)

    def select_item(self, item):
        self.selected_item = item
        category_total = sum(entry.size for entry in self.current_collection().values())
        self.list_view.set_selected(item.key)
        self.treemap.set_selected(item.key)
        self.details.set_item(item, category_total)

    def open_item(self, item):
        path = item.primary_path()
        if not path.exists():
            self.set_status("That cache folder no longer exists. Rescan to refresh the map.", WARNING)
            return

        dolphin = shutil.which("dolphin")
        if dolphin:
            subprocess.Popen([dolphin, "--select", str(path)])
            self.set_status(f"Opened {item.name} in Dolphin.", SUCCESS)
            return

        xdg_open = shutil.which("xdg-open")
        if xdg_open:
            subprocess.Popen([xdg_open, str(path.parent)])
            self.set_status(f"Opened the parent folder for {item.name}.", SUCCESS)
            return

        self.set_status("No supported file manager command was found.", WARNING)

    def copy_item_path(self, item):
        path = str(item.primary_path())
        self.root.clipboard_clear()
        self.root.clipboard_append(path)
        self.set_status("Folder path copied to the clipboard.", SUCCESS)

    def set_status(self, text, color):
        self.status_label.configure(text=text)
        self.status_dot.configure(fg=color)

    def save_current_settings(self):
        self.settings["cache_path"] = self.path_var.get()
        self.settings["sort"] = self.sort_var.get()
        self.settings["geometry"] = self.root.geometry()
        save_settings(self.settings)

    def on_close(self):
        self.cancel_event.set()
        self.save_current_settings()
        self.root.destroy()


def draw_rounded_rect(canvas, x1, y1, x2, y2, radius, fill, outline="", width=1, tags=None):
    radius = max(0, min(radius, abs(x2 - x1) / 2, abs(y2 - y1) / 2))
    points = [
        x1 + radius, y1,
        x2 - radius, y1,
        x2, y1,
        x2, y1 + radius,
        x2, y2 - radius,
        x2, y2,
        x2 - radius, y2,
        x1 + radius, y2,
        x1, y2,
        x1, y2 - radius,
        x1, y1 + radius,
        x1, y1,
    ]
    return canvas.create_polygon(points, smooth=True, splinesteps=24, fill=fill, outline=outline, width=width, tags=tags)


def hex_to_rgb(color):
    color = color.lstrip("#")
    return tuple(int(color[index:index + 2], 16) for index in (0, 2, 4))


def rgb_to_hex(rgb):
    return "#" + "".join(f"{max(0, min(255, int(value))):02X}" for value in rgb)


def blend_color(color_a, color_b, amount):
    rgb_a = hex_to_rgb(color_a)
    rgb_b = hex_to_rgb(color_b)
    values = [rgb_a[index] * (1 - amount) + rgb_b[index] * amount for index in range(3)]
    return rgb_to_hex(values)


def item_color(name):
    index = zlib.crc32(name.encode("utf-8")) % len(GRAPH_COLORS)
    return GRAPH_COLORS[index]


def human_size(size):
    value = float(max(0, size))
    units = ("B", "KiB", "MiB", "GiB", "TiB", "PiB")
    unit_index = 0
    while value >= 1024 and unit_index < len(units) - 1:
        value /= 1024
        unit_index += 1
    if unit_index == 0:
        return f"{int(value)} {units[unit_index]}"
    if value >= 100:
        return f"{value:.0f} {units[unit_index]}"
    if value >= 10:
        return f"{value:.1f} {units[unit_index]}"
    return f"{value:.2f} {units[unit_index]}"


def human_count(value):
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    if value >= 1_000:
        return f"{value / 1_000:.1f}K"
    return str(value)


def relative_time(timestamp):
    if not timestamp:
        return "modified time unavailable"
    seconds = max(0, time.time() - timestamp)
    if seconds < 60:
        return "modified just now"
    if seconds < 3600:
        minutes = int(seconds / 60)
        return f"modified {minutes} min ago"
    if seconds < 86400:
        hours = int(seconds / 3600)
        return f"modified {hours} hr ago"
    if seconds < 86400 * 45:
        days = int(seconds / 86400)
        return f"modified {days} day{'s' if days != 1 else ''} ago"
    date = datetime.datetime.fromtimestamp(timestamp)
    return f"modified {date.strftime('%d %b %Y')}"


def truncate_text(text, font, max_width):
    if max_width <= 0 or font.measure(text) <= max_width:
        return text
    suffix = "…"
    low = 0
    high = len(text)
    while low < high:
        middle = (low + high + 1) // 2
        candidate = text[:middle] + suffix
        if font.measure(candidate) <= max_width:
            low = middle
        else:
            high = middle - 1
    return text[:low] + suffix


def middle_ellipsis(text, font, max_width):
    if font.measure(text) <= max_width:
        return text
    if max_width < font.measure("…"):
        return ""
    left_count = len(text) // 2
    right_count = len(text) - left_count
    while left_count > 0 or right_count > 0:
        candidate = text[:left_count] + "…" + text[len(text) - right_count:]
        if font.measure(candidate) <= max_width:
            return candidate
        if left_count >= right_count and left_count > 0:
            left_count -= 1
        elif right_count > 0:
            right_count -= 1
    return "…"


def point_in_rect(x, y, rect):
    if not rect:
        return False
    return rect[0] <= x <= rect[2] and rect[1] <= y <= rect[3]


def worst_ratio(row, side):
    if not row or side <= 0:
        return float("inf")
    values = [entry[1] for entry in row]
    total = sum(values)
    smallest = min(values)
    largest = max(values)
    if smallest <= 0 or total <= 0:
        return float("inf")
    side_squared = side * side
    total_squared = total * total
    return max(side_squared * largest / total_squared, total_squared / (side_squared * smallest))


def layout_treemap_row(row, x, y, width, height):
    rectangles = []
    row_total = sum(entry[1] for entry in row)
    if width >= height:
        column_width = row_total / max(height, 1e-9)
        current_y = y
        for item, area in row:
            cell_height = area / max(column_width, 1e-9)
            rectangles.append((item, (x, current_y, x + column_width, current_y + cell_height)))
            current_y += cell_height
        return rectangles, x + column_width, y, max(0, width - column_width), height

    row_height = row_total / max(width, 1e-9)
    current_x = x
    for item, area in row:
        cell_width = area / max(row_height, 1e-9)
        rectangles.append((item, (current_x, y, current_x + cell_width, y + row_height)))
        current_x += cell_width
    return rectangles, x, y + row_height, width, max(0, height - row_height)


def squarified_treemap(items, x, y, width, height):
    if not items or width <= 0 or height <= 0:
        return []
    total_size = sum(item.size for item in items)
    if total_size <= 0:
        return []

    scale = width * height / total_size
    remaining = [(item, item.size * scale) for item in sorted(items, key=lambda item: item.size, reverse=True)]
    row = []
    result = []
    current_x = x
    current_y = y
    current_width = width
    current_height = height

    while remaining:
        candidate = remaining[0]
        side = min(current_width, current_height)
        if not row or worst_ratio(row + [candidate], side) <= worst_ratio(row, side):
            row.append(candidate)
            remaining.pop(0)
        else:
            rectangles, current_x, current_y, current_width, current_height = layout_treemap_row(row, current_x, current_y, current_width, current_height)
            result.extend(rectangles)
            row = []

    if row:
        rectangles, current_x, current_y, current_width, current_height = layout_treemap_row(row, current_x, current_y, current_width, current_height)
        result.extend(rectangles)
    return result


def allocated_size(stat_result):
    blocks = getattr(stat_result, "st_blocks", None)
    if blocks is not None:
        return blocks * 512
    return stat_result.st_size


def scan_directory(path, cancel_event):
    total_size = 0
    file_count = 0
    latest_modified = 0
    warning_count = 0
    stack = [Path(path)]

    while stack:
        if cancel_event.is_set():
            return None
        current = stack.pop()
        try:
            iterator = os.scandir(current)
        except OSError:
            warning_count += 1
            continue

        with iterator:
            for entry in iterator:
                if cancel_event.is_set():
                    return None
                try:
                    stat_result = entry.stat(follow_symlinks=False)
                except OSError:
                    warning_count += 1
                    continue

                total_size += allocated_size(stat_result)
                latest_modified = max(latest_modified, stat_result.st_mtime)
                if entry.is_dir(follow_symlinks=False):
                    stack.append(Path(entry.path))
                else:
                    file_count += 1

    if latest_modified == 0:
        try:
            latest_modified = Path(path).stat().st_mtime
        except OSError:
            latest_modified = 0
    return total_size, file_count, latest_modified, warning_count


def parse_hub_name(directory_name, prefix):
    raw = directory_name[len(prefix):]
    parts = raw.split("--", 1)
    if len(parts) == 2:
        owner, repo = parts
        return owner, repo, f"{owner}/{repo}"
    return "", raw, raw


def parse_processed_dataset_name(directory_name):
    parts = directory_name.split("___", 1)
    if len(parts) == 2:
        owner, repo = parts
        return owner, repo, f"{owner}/{repo}"
    return "", directory_name, directory_name


def discover_scan_targets(cache_root):
    item_targets = []
    other_targets = []
    other_files = []
    hub_path = cache_root / "hub"
    datasets_path = cache_root / "datasets"

    if hub_path.is_dir():
        for entry in os.scandir(hub_path):
            path = Path(entry.path)
            if entry.is_dir(follow_symlinks=False) and entry.name.startswith("models--"):
                owner, repo, name = parse_hub_name(entry.name, "models--")
                item_targets.append(("models", "Hub", name, owner, repo, path))
            elif entry.is_dir(follow_symlinks=False) and entry.name.startswith("datasets--"):
                owner, repo, name = parse_hub_name(entry.name, "datasets--")
                item_targets.append(("datasets", "Hub", name, owner, repo, path))
            elif entry.is_dir(follow_symlinks=False):
                other_targets.append(path)
            else:
                other_files.append(path)

    if datasets_path.is_dir():
        for entry in os.scandir(datasets_path):
            path = Path(entry.path)
            if entry.is_dir(follow_symlinks=False):
                owner, repo, name = parse_processed_dataset_name(entry.name)
                item_targets.append(("datasets", "Processed", name, owner, repo, path))
            else:
                other_files.append(path)

    for entry in os.scandir(cache_root):
        path = Path(entry.path)
        if entry.name in ("hub", "datasets"):
            continue
        if entry.is_dir(follow_symlinks=False):
            other_targets.append(path)
        else:
            other_files.append(path)

    return item_targets, other_targets, other_files


def scan_cache_worker(cache_root, event_queue, cancel_event):
    warning_count = 0
    try:
        item_targets, other_targets, other_files = discover_scan_targets(cache_root)
    except OSError:
        event_queue.put(("warning", 1))
        event_queue.put(("done",))
        return

    total_targets = len(item_targets) + len(other_targets)
    event_queue.put(("started", total_targets))
    current = 0

    for kind, source, name, owner, repo, path in item_targets:
        if cancel_event.is_set():
            event_queue.put(("cancelled",))
            return
        result = scan_directory(path, cancel_event)
        if result is None:
            event_queue.put(("cancelled",))
            return
        size, file_count, modified, warnings = result
        warning_count += warnings
        key = f"{kind}:{name.lower()}"
        item = CacheItem(key, name, owner, repo, kind, source, size, file_count, modified, path)
        event_queue.put(("item", item))
        current += 1
        event_queue.put(("progress", current, total_targets, name))

    other_size = 0
    for path in other_targets:
        if cancel_event.is_set():
            event_queue.put(("cancelled",))
            return
        result = scan_directory(path, cancel_event)
        if result is None:
            event_queue.put(("cancelled",))
            return
        size, file_count, modified, warnings = result
        other_size += size
        warning_count += warnings
        current += 1
        event_queue.put(("progress", current, total_targets, path.name))

    for path in other_files:
        try:
            other_size += allocated_size(path.stat(follow_symlinks=False))
        except OSError:
            warning_count += 1

    event_queue.put(("other", other_size))
    if warning_count:
        event_queue.put(("warning", warning_count))
    event_queue.put(("done",))


def create_fonts(root):
    families = set(tkfont.families(root))
    preferred = ("Inter", "Noto Sans", "DejaVu Sans", "Liberation Sans")
    family = next((name for name in preferred if name in families), "TkDefaultFont")
    return {
        "title": tkfont.Font(root=root, family=family, size=19, weight="bold"),
        "metric": tkfont.Font(root=root, family=family, size=20, weight="bold"),
        "section": tkfont.Font(root=root, family=family, size=13, weight="bold"),
        "body": tkfont.Font(root=root, family=family, size=10),
        "body_bold": tkfont.Font(root=root, family=family, size=10, weight="bold"),
        "small": tkfont.Font(root=root, family=family, size=9),
        "small_bold": tkfont.Font(root=root, family=family, size=9, weight="bold"),
        "tiny": tkfont.Font(root=root, family=family, size=8),
        "tiny_bold": tkfont.Font(root=root, family=family, size=8, weight="bold"),
        "map_title": tkfont.Font(root=root, family=family, size=11, weight="bold"),
    }


def configure_ttk(root, fonts):
    style = ttk.Style(root)
    style.theme_use("clam")
    style.configure(
        "Cache.Vertical.TScrollbar",
        background=CARD,
        troughcolor=SURFACE,
        bordercolor=SURFACE,
        arrowcolor=MUTED,
        lightcolor=CARD,
        darkcolor=CARD,
        relief="flat",
        width=10,
    )
    style.map("Cache.Vertical.TScrollbar", background=[("active", CARD_SELECTED), ("pressed", ACCENT_DARK)])
    style.configure(
        "Cache.Horizontal.TProgressbar",
        troughcolor=SURFACE_ALT,
        background=ACCENT,
        bordercolor=BG_DEEP,
        lightcolor=ACCENT,
        darkcolor=ACCENT,
        thickness=6,
    )
    style.configure(
        "Cache.TCombobox",
        fieldbackground=SURFACE_ALT,
        background=SURFACE_ALT,
        foreground=TEXT_SOFT,
        arrowcolor=MUTED,
        bordercolor=BORDER,
        lightcolor=BORDER,
        darkcolor=BORDER,
        padding=(9, 6),
        relief="flat",
    )
    style.map(
        "Cache.TCombobox",
        fieldbackground=[("readonly", SURFACE_ALT)],
        foreground=[("readonly", TEXT_SOFT)],
        selectbackground=[("readonly", SURFACE_ALT)],
        selectforeground=[("readonly", TEXT_SOFT)],
        bordercolor=[("focus", ACCENT)],
        arrowcolor=[("active", ACCENT_BRIGHT)],
    )
    root.option_add("*TCombobox*Listbox.background", SURFACE_ALT)
    root.option_add("*TCombobox*Listbox.foreground", TEXT)
    root.option_add("*TCombobox*Listbox.selectBackground", CARD_SELECTED)
    root.option_add("*TCombobox*Listbox.selectForeground", TEXT)
    root.option_add("*TCombobox*Listbox.font", fonts["small"])


def settings_path():
    return Path.home() / ".config" / "hf-cachelight" / "settings.json"


def load_settings():
    path = settings_path()
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def save_settings(settings):
    path = settings_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(settings, indent=2), encoding="utf-8")
    except OSError:
        pass


def default_cache_path():
    candidates = [
        Path("/mnt/8TB_HDD/hf_cache"),
        Path.home() / ".cache" / "huggingface",
    ]
    for candidate in candidates:
        if candidate.is_dir():
            return str(candidate)
    return str(candidates[-1])


def png_chunk(chunk_type, data):
    return struct.pack(">I", len(data)) + chunk_type + data + struct.pack(">I", zlib.crc32(chunk_type + data) & 0xFFFFFFFF)


def create_icon_png(size):
    rows = []
    center = (size - 1) / 2
    outer = size * 0.42
    inner = size * 0.20
    gap_angle = math.radians(5)
    segment_colors = [hex_to_rgb(color) for color in (GRAPH_COLORS[0], GRAPH_COLORS[4], GRAPH_COLORS[9], GRAPH_COLORS[13])]

    for y in range(size):
        row = bytearray([0])
        for x in range(size):
            dx = x - center
            dy = y - center
            distance = math.hypot(dx, dy)
            if inner <= distance <= outer:
                angle = (math.atan2(-dy, dx) + math.pi * 2) % (math.pi * 2)
                quadrant = int(angle / (math.pi / 2))
                local_angle = angle % (math.pi / 2)
                if gap_angle < local_angle < math.pi / 2 - gap_angle:
                    red, green, blue = segment_colors[quadrant]
                    alpha = 255
                else:
                    red, green, blue, alpha = 0, 0, 0, 0
            elif distance < inner * 0.46:
                red, green, blue = hex_to_rgb(ACCENT_BRIGHT)
                alpha = 255
            elif distance < inner:
                red, green, blue = hex_to_rgb(SURFACE)
                alpha = 255
            else:
                red, green, blue, alpha = 0, 0, 0, 0
            row.extend((red, green, blue, alpha))
        rows.append(bytes(row))

    raw = b"".join(rows)
    signature = b"\x89PNG\r\n\x1a\n"
    header = struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0)
    return signature + png_chunk(b"IHDR", header) + png_chunk(b"IDAT", zlib.compress(raw, 9)) + png_chunk(b"IEND", b"")


def main():
    root = tk.Tk()
    HfCachelightApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()

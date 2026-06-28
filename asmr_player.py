"""
ASMR Audio Player with Subtitle Display  v3
Portable Windows app — requires Python + pygame + mutagen + Pillow
Run: python asmr_player.py
"""

import tkinter as tk
from tkinter import filedialog
import time, re, os, sys

try:
    import pygame
    pygame.mixer.pre_init(frequency=44100, size=-16, channels=2, buffer=1024)
    pygame.init()
    pygame.mixer.init()
    PYGAME_OK = True
except ImportError:
    PYGAME_OK = False

try:
    import mutagen
    from mutagen.mp3 import MP3
    from mutagen.wave import WAVE
    from mutagen.flac import FLAC
    MUTAGEN_OK = True
except ImportError:
    MUTAGEN_OK = False

try:
    from PIL import Image, ImageTk
    PIL_OK = True
except ImportError:
    PIL_OK = False

AUDIO_EXTS = {'.mp3', '.wav', '.ogg', '.flac', '.m4a', '.aac', '.oga'}
IMAGE_EXTS = {'.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp', '.tiff'}
SUB_EXTS   = {'.srt', '.vtt', '.txt'}

# ─── Subtitle Parsers ────────────────────────────────────────────────────────

def parse_srt(text):
    cues = []
    for block in re.split(r'\n\s*\n', text.strip()):
        lines = block.strip().splitlines()
        if len(lines) < 3:
            continue
        timing, text_start = '', 0
        for i, l in enumerate(lines):
            if '-->' in l:
                timing, text_start = l, i + 1
                break
        m = re.match(r'(\d+):(\d+):(\d+)[,.](\d+)\s*-->\s*(\d+):(\d+):(\d+)[,.](\d+)', timing)
        if not m:
            continue
        h1,m1,s1,ms1,h2,m2,s2,ms2 = map(int, m.groups())
        start = h1*3600+m1*60+s1+ms1/1000
        end   = h2*3600+m2*60+s2+ms2/1000
        body  = re.sub(r'<[^>]+>', '', '\n'.join(lines[text_start:]))
        if body.strip():
            cues.append({'start': start, 'end': end, 'text': body.strip()})
    return cues

def parse_vtt(text):
    cues = []
    text = re.sub(r'^WEBVTT[^\n]*\n', '', text, flags=re.MULTILINE)
    for block in re.split(r'\n\s*\n', text.strip()):
        lines = block.strip().splitlines()
        if not lines or lines[0].startswith(('NOTE','STYLE','REGION')):
            continue
        timing, text_start = None, 0
        for i, l in enumerate(lines):
            if '-->' in l:
                timing, text_start = l, i + 1
                break
        if not timing:
            continue
        m = re.match(r'(\d+):(\d+):(\d+)[.,](\d+)\s*-->\s*(\d+):(\d+):(\d+)[.,](\d+)', timing)
        if m:
            h1,mi1,s1,ms1,h2,mi2,s2,ms2 = map(int, m.groups())
            start = h1*3600+mi1*60+s1+ms1/1000
            end   = h2*3600+mi2*60+s2+ms2/1000
        else:
            m = re.match(r'(\d+):(\d+)[.,](\d+)\s*-->\s*(\d+):(\d+)[.,](\d+)', timing)
            if not m:
                continue
            mi1,s1,ms1,mi2,s2,ms2 = map(int, m.groups())
            start = mi1*60+s1+ms1/1000
            end   = mi2*60+s2+ms2/1000
        body = re.sub(r'<[^>]+>|\{[^}]+\}', '', '\n'.join(lines[text_start:]))
        if body.strip():
            cues.append({'start': start, 'end': end, 'text': body.strip()})
    return cues

def parse_txt_timestamps(text):
    cues, entries = [], []
    pat = re.compile(r'[\[\(]?(\d+):(\d+)(?::(\d+))?(?:[.,](\d+))?[\]\)]?\s+(.*)')
    for line in text.strip().splitlines():
        m = pat.match(line.strip())
        if m:
            g = m.groups()
            if g[2] is not None:
                t = int(g[0])*3600 + int(g[1])*60 + int(g[2]) + (int(g[3]) if g[3] else 0)/1000
            else:
                t = int(g[0])*60 + int(g[1]) + (int(g[3]) if g[3] else 0)/1000
            entries.append({'start': t, 'text': g[4].strip()})
    for i, e in enumerate(entries):
        end = entries[i+1]['start'] if i+1 < len(entries) else e['start'] + 5
        if e['text']:
            cues.append({'start': e['start'], 'end': end, 'text': e['text']})
    return cues

def parse_subtitles(filepath):
    ext = os.path.splitext(filepath)[1].lower()
    try:
        text = open(filepath, encoding='utf-8-sig').read()
    except UnicodeDecodeError:
        text = open(filepath, encoding='latin-1').read()
    if ext == '.srt':
        return parse_srt(text)
    if ext == '.vtt':
        return parse_vtt(text)
    for fn in (parse_srt, parse_vtt, parse_txt_timestamps):
        c = fn(text)
        if c:
            return c
    return []

def get_audio_duration(filepath):
    if MUTAGEN_OK:
        ext = os.path.splitext(filepath)[1].lower()
        try:
            if ext == '.mp3':  return MP3(filepath).info.length
            if ext == '.wav':  return WAVE(filepath).info.length
            if ext == '.flac': return FLAC(filepath).info.length
            f = mutagen.File(filepath)
            if f and hasattr(f, 'info'): return f.info.length
        except Exception:
            pass
    if PYGAME_OK:
        try:
            return pygame.mixer.Sound(filepath).get_length()
        except Exception:
            pass
    return 0.0

def find_subtitle(audio_path):
    """
    Try multiple strategies to locate a matching subtitle file:
    1. Exact strip of audio ext:  'foo.wav' -> 'foo.srt'
    2. Full filename as prefix:   'foo.wav' -> 'foo.wav.vtt'   (e.g. '01_Title.wav.vtt')
    3. Stem prefix match in same folder (handles Unicode/colon filenames)
    """
    folder   = os.path.dirname(audio_path)
    basename = os.path.basename(audio_path)           # '01_Prologue：飢渴.wav'
    stem     = os.path.splitext(basename)[0]          # '01_Prologue：飢渴'

    # Strategy 1 – strip audio ext, try sub exts
    for ext in ('.srt', '.vtt', '.txt'):
        p = os.path.join(folder, stem + ext)
        if os.path.exists(p):
            return p

    # Strategy 2 – full filename (with audio ext) + sub ext
    for ext in ('.srt', '.vtt', '.txt'):
        p = os.path.join(folder, basename + ext)
        if os.path.exists(p):
            return p

    # Strategy 3 – scan folder, find file whose name starts with stem
    try:
        for fname in os.listdir(folder):
            fext = os.path.splitext(fname)[1].lower()
            if fext in SUB_EXTS:
                # Match if sub filename starts with audio stem or full audio basename
                if fname.startswith(stem) or fname.startswith(basename):
                    return os.path.join(folder, fname)
    except Exception:
        pass

    return None

def scan_folder(folder):
    audio, images = [], []
    for name in sorted(os.listdir(folder)):
        ext  = os.path.splitext(name)[1].lower()
        full = os.path.join(folder, name)
        if ext in AUDIO_EXTS:
            audio.append(full)
        elif ext in IMAGE_EXTS:
            images.append(full)
    return audio, images

# ─── Tooltip ──────────────────────────────────────────────────────────────────

class Tooltip:
    """Show a tooltip after 500 ms hover on any widget."""
    def __init__(self, widget, text):
        self.widget  = widget
        self.text    = text
        self._job    = None
        self._win    = None
        widget.bind('<Enter>',  self._schedule, add='+')
        widget.bind('<Leave>',  self._cancel,   add='+')
        widget.bind('<Button>', self._cancel,   add='+')

    def _schedule(self, _=None):
        self._cancel()
        self._job = self.widget.after(500, self._show)

    def _cancel(self, _=None):
        if self._job:
            self.widget.after_cancel(self._job)
            self._job = None
        if self._win:
            self._win.destroy()
            self._win = None

    def _show(self):
        if not self.widget.winfo_exists():
            return
        x = self.widget.winfo_rootx() + 10
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 4
        self._win = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f'+{x}+{y}')
        tw.attributes('-topmost', True)
        tk.Label(tw, text=self.text, bg='#2a2640', fg='#e8e4f0',
                 font=('Segoe UI', 9), padx=8, pady=4,
                 relief='flat', bd=0).pack()


# ─── Main Application ────────────────────────────────────────────────────────

class ASMRPlayer(tk.Tk):
    C = {
        'bg':       '#0d0d14',
        'panel':    '#13131e',
        'panel2':   '#1a1828',
        'accent':   '#8b7cf8',
        'accent2':  '#c084fc',
        'text':     '#e8e4f0',
        'muted':    '#5a5370',
        'bar_bg':   '#1e1c2e',
        'bar_fill': '#8b7cf8',
        'sub_text': '#ffffff',
    }

    # Subtitle vertical position cycle: bottom → center → top → bottom
    SUB_POSITIONS = ['bottom', 'center', 'top']
    SUB_POS_ICONS = {'bottom': '⬇', 'center': '◉', 'top': '⬆'}

    def __init__(self):
        super().__init__()
        self.title('✦ ASMR Player')
        self.geometry('960x700')
        self.minsize(720, 560)
        self.configure(bg=self.C['bg'])

        # Playback
        self.audio_file        = None
        self.cues              = []
        self.duration          = 0.0
        self.playing           = False
        self.paused            = False
        self._seek_offset      = 0.0
        self._play_wall        = 0.0
        self._after_id         = None
        self._dragging         = False
        self._current_sub_text = ''

        # Playlist
        self.playlist  = []
        self.pl_index  = -1

        # Images
        self.images       = []
        self.img_index    = -1
        self._img_tk      = None
        self.images_hidden = False   # toggled by hide/show image button

        # Subtitle style
        self.sub_font_size = 28
        self.sub_bold      = False
        self.sub_pos_idx   = 0   # index into SUB_POSITIONS

        self._build_ui()
        self.protocol('WM_DELETE_WINDOW', self._on_close)

    # ═══════════════════════════════════════════════════════════════════════
    #  UI BUILD
    # ═══════════════════════════════════════════════════════════════════════

    def _build_ui(self):
        C = self.C

        # ── Header ──────────────────────────────────────────────────────────
        hdr = tk.Frame(self, bg=C['bg'], pady=10)
        hdr.pack(fill='x', padx=22)
        tk.Label(hdr, text='✦ ASMR Player', bg=C['bg'], fg=C['accent'],
                 font=('Segoe UI', 17, 'bold')).pack(side='left')
        tk.Label(hdr, text='with subtitle display', bg=C['bg'], fg=C['text'],
                 font=('Segoe UI', 10)).pack(side='left', padx=(10,0), pady=(4,0))

        # ── Toolbar ─────────────────────────────────────────────────────────
        tb = tk.Frame(self, bg=C['panel'], pady=9, padx=14)
        tb.pack(fill='x', padx=22, pady=(0, 7))

        self._tbtn(tb, '🎵  Audio',    self._load_audio,  size=10, tip='Load audio file').pack(side='left', padx=(0,5))
        self._tbtn(tb, '💬  Subtitle', self._load_sub,    size=10, tip='Load subtitle file (.srt .vtt .txt)').pack(side='left', padx=(0,5))
        self._tbtn(tb, '🖼  Images',   self._load_images, size=10, tip='Load image files (multi-select)').pack(side='left', padx=(0,5))
        self._tbtn(tb, '📂  Folder',   self._load_folder, size=10, tip='Load folder (audio + images + subtitles)').pack(side='left', padx=(0,14))

        # Separator
        tk.Frame(tb, bg=C['muted'], width=1).pack(side='left', fill='y', pady=3, padx=(0,10))

        # Subtitle style controls
        tk.Label(tb, text='Sub:', bg=C['panel'], fg=C['text'],
                 font=('Segoe UI', 9)).pack(side='left', padx=(0,4))
        self._tbtn(tb, 'A+', self._sub_bigger,       size=10, w=3, tip='Increase subtitle size').pack(side='left', padx=2)
        self._tbtn(tb, 'A−', self._sub_smaller,      size=10, w=3, tip='Decrease subtitle size').pack(side='left', padx=2)
        self.btn_bold = self._tbtn(tb, 'B', self._sub_bold_toggle, size=11, w=3, tip='Toggle bold subtitle')
        self.btn_bold.pack(side='left', padx=2)

        # Subtitle position toggle
        tk.Frame(tb, bg=C['muted'], width=1).pack(side='left', fill='y', pady=3, padx=(8,8))
        self.btn_sub_pos = self._tbtn(tb, self.SUB_POS_ICONS['bottom'],
                                      self._cycle_sub_pos, size=13, w=3, tip='Cycle subtitle position (bottom / center / top)')
        self.btn_sub_pos.pack(side='left', padx=(0,3))
        self.lbl_sub_pos = tk.Label(tb, text='bottom', bg=C['panel'], fg=C['accent2'],
                                    font=('Segoe UI', 9))
        self.lbl_sub_pos.pack(side='left', padx=(0,6))

        # Hide image toggle
        tk.Frame(tb, bg=C['muted'], width=1).pack(side='left', fill='y', pady=3, padx=(6,8))
        self.btn_hide_img = self._tbtn(tb, '🙈', self._toggle_hide_images, size=13, w=3,
                                       tip='Hide / show image viewer')
        self.btn_hide_img.pack(side='left', padx=(0,4))

        # ── Track / sub info block (right side) ─────────────────────────────
        info_frame = tk.Frame(tb, bg=C['panel'])
        info_frame.pack(side='right', padx=(8,0))

        self.track_label = tk.Label(info_frame, text='No audio loaded',
                                    bg=C['panel'], fg=C['text'],
                                    font=('Segoe UI', 9), anchor='e', justify='right')
        self.track_label.pack(anchor='e')

        self.sub_info_label = tk.Label(info_frame, text='',
                                       bg=C['panel'], fg=C['text'],
                                       font=('Segoe UI', 8), anchor='e', justify='right')
        self.sub_info_label.pack(anchor='e')

        # ── Central display row (← canvas →) ────────────────────────────────
        display_row = tk.Frame(self, bg=C['bg'])
        display_row.pack(fill='both', expand=True, padx=22, pady=(0,6))

        # Create both arrow buttons but DON'T pack yet — _update_nav_arrows handles that.
        # Pack order must be: prev LEFT, next RIGHT, then canvas fills the middle.
        self.btn_prev_img = tk.Button(
            display_row, text='❮', command=self._prev_image,
            bg=C['bg'], fg=C['text'], activebackground=C['bg'],
            activeforeground=C['accent'], font=('Segoe UI', 22),
            relief='flat', bd=0, cursor='hand2', width=2)
        Tooltip(self.btn_prev_img, 'Previous image')

        self.btn_next_img = tk.Button(
            display_row, text='❯', command=self._next_image,
            bg=C['bg'], fg=C['text'], activebackground=C['bg'],
            activeforeground=C['accent'], font=('Segoe UI', 22),
            relief='flat', bd=0, cursor='hand2', width=2)
        Tooltip(self.btn_next_img, 'Next image')

        self.canvas = tk.Canvas(display_row, bg=C['panel2'],
                                highlightthickness=1,
                                highlightbackground=C['bar_bg'])
        self.canvas.bind('<Configure>', lambda e: self._redraw_canvas())

        # Initial layout — arrows hidden, canvas fills row
        self._update_nav_arrows()

        # ── Playlist / folder status ─────────────────────────────────────────
        self.pl_label = tk.Label(self, text='', bg=C['bg'], fg=C['text'],
                                 font=('Segoe UI', 9))
        self.pl_label.pack()

        # ── Progress bar ─────────────────────────────────────────────────────
        prog_frame = tk.Frame(self, bg=C['bg'], padx=22)
        prog_frame.pack(fill='x', pady=(3,5))

        self.time_label = tk.Label(prog_frame, text='0:00', bg=C['bg'],
                                   fg=C['text'], font=('Consolas', 10), width=7, anchor='e')
        self.time_label.pack(side='left')

        self.prog_canvas = tk.Canvas(prog_frame, bg=C['bar_bg'], height=12,
                                     cursor='hand2', highlightthickness=0)
        self.prog_canvas.pack(side='left', fill='x', expand=True, padx=8)
        self._prog_fill = self.prog_canvas.create_rectangle(0,0,0,12, fill=C['bar_fill'], outline='')
        self._prog_dot  = self.prog_canvas.create_oval(-8,-2,8,14, fill=C['accent2'],
                                                       outline='', state='hidden')
        self.prog_canvas.bind('<Button-1>',        self._seek_press)
        self.prog_canvas.bind('<B1-Motion>',       self._seek_move)
        self.prog_canvas.bind('<ButtonRelease-1>', self._seek_release)
        self.prog_canvas.bind('<Enter>', lambda e: self.prog_canvas.itemconfig(self._prog_dot, state='normal'))
        self.prog_canvas.bind('<Leave>', lambda e: self.prog_canvas.itemconfig(self._prog_dot, state='hidden'))

        self.dur_label = tk.Label(prog_frame, text='0:00', bg=C['bg'],
                                  fg=C['text'], font=('Consolas', 10), width=7)
        self.dur_label.pack(side='left')

        # ── Transport controls ────────────────────────────────────────────────
        # Order: Prev-track | Skip-back | Play/Pause | Skip-fwd | Next-track
        ctrl = tk.Frame(self, bg=C['bg'])
        ctrl.pack(pady=(3,10))

        self._tbtn(ctrl, '⏮', self._prev_track,        size=14, w=3, tip='Previous track  [−]').pack(side='left', padx=5)
        self._tbtn(ctrl, '⏪', lambda: self._skip(-10), size=14, w=3, tip='Rewind 10 s  [←]').pack(side='left', padx=5)

        self.btn_play = tk.Button(ctrl, text='▶', command=self._toggle_play,
                                  bg=C['panel'], fg=C['accent'],
                                  activebackground=C['accent'], activeforeground='#fff',
                                  font=('Segoe UI', 24), relief='flat', bd=0,
                                  cursor='hand2', width=3, pady=3)
        self.btn_play.pack(side='left', padx=10)
        Tooltip(self.btn_play, 'Play / Pause  [Space]')

        self._tbtn(ctrl, '⏩', lambda: self._skip(10),  size=14, w=3, tip='Fast-forward 10 s  [→]').pack(side='left', padx=5)
        self._tbtn(ctrl, '⏭', self._next_track,        size=14, w=3, tip='Next track  [+]').pack(side='left', padx=5)

        # Volume
        tk.Label(ctrl, text='🔊', bg=C['bg'], fg=C['text'],
                 font=('Segoe UI', 13)).pack(side='left', padx=(18,5))
        self.vol_slider = tk.Scale(ctrl, from_=0, to=100, orient='horizontal',
                                   length=140, bg=C['bg'], fg=C['text'],
                                   troughcolor=C['bar_bg'], activebackground=C['accent'],
                                   highlightthickness=0, bd=0, sliderlength=14,
                                   command=self._set_volume, showvalue=False)
        self.vol_slider.set(100)
        self.vol_slider.pack(side='left')
        if PYGAME_OK:
            pygame.mixer.music.set_volume(1.0)

        self.after(60, self._redraw_canvas)
        self._bind_hotkeys()

    def _tbtn(self, parent, text, cmd, size=10, w=None, fg=None, bg=None, tip=None):
        C = self.C
        btn = tk.Button(parent, text=text, command=cmd,
                        bg=bg or C['panel'], fg=fg or C['text'],
                        activebackground=C['accent'], activeforeground='#fff',
                        font=('Segoe UI', size), relief='flat', cursor='hand2',
                        padx=8, pady=4, width=w, bd=0)
        if tip:
            Tooltip(btn, tip)
        return btn

    def _add_tip(self, widget, tip):
        Tooltip(widget, tip)

    # ═══════════════════════════════════════════════════════════════════════
    #  SUBTITLE STYLE & POSITION
    # ═══════════════════════════════════════════════════════════════════════

    def _sub_bigger(self):
        self.sub_font_size = min(self.sub_font_size + 2, 48)
        self._redraw_canvas()

    def _sub_smaller(self):
        self.sub_font_size = max(self.sub_font_size - 2, 8)
        self._redraw_canvas()

    def _sub_bold_toggle(self):
        self.sub_bold = not self.sub_bold
        C = self.C
        self.btn_bold.config(bg=C['accent'] if self.sub_bold else C['panel'],
                             fg='#fff'       if self.sub_bold else C['text'])
        self._redraw_canvas()

    def _bind_hotkeys(self):
        """Keyboard shortcuts."""
        self.bind('<Left>',         lambda e: self._skip(-10))
        self.bind('<Right>',        lambda e: self._skip(10))
        self.bind('<Up>',           lambda e: self._vol_step(+5))
        self.bind('<Down>',         lambda e: self._vol_step(-5))
        # + / = for next track  (normal and numpad)
        self.bind('<plus>',         lambda e: self._next_track())
        self.bind('<equal>',        lambda e: self._next_track())
        self.bind('<KP_Add>',       lambda e: self._next_track())
        # - for prev track  (normal and numpad)
        self.bind('<minus>',        lambda e: self._prev_track())
        self.bind('<KP_Subtract>',  lambda e: self._prev_track())
        self.bind('<space>',        lambda e: self._toggle_play())

    def _vol_step(self, delta):
        val = max(0, min(100, self.vol_slider.get() + delta))
        self.vol_slider.set(val)
        self._set_volume(val)

    def _cycle_sub_pos(self):
        self.sub_pos_idx = (self.sub_pos_idx + 1) % len(self.SUB_POSITIONS)
        pos = self.SUB_POSITIONS[self.sub_pos_idx]
        self.btn_sub_pos.config(text=self.SUB_POS_ICONS[pos])
        self.lbl_sub_pos.config(text=pos)
        self._redraw_canvas()

    # ═══════════════════════════════════════════════════════════════════════
    #  FILE LOADING
    # ═══════════════════════════════════════════════════════════════════════

    def _load_audio(self):
        path = filedialog.askopenfilename(
            title='Select Audio File',
            filetypes=[('Audio', '*.mp3 *.wav *.ogg *.flac *.m4a *.aac'), ('All', '*.*')])
        if not path:
            return
        self.playlist  = [path]
        self.pl_index  = 0
        # NOTE: keep existing images — only folder load resets gallery
        self.pl_label.config(text='')
        self._load_track(path, autoplay=True)

    def _load_sub(self):
        path = filedialog.askopenfilename(
            title='Select Subtitle File',
            filetypes=[('Subtitles', '*.srt *.vtt *.txt'), ('All', '*.*')])
        if path:
            self._load_subtitle_file(path)

    def _load_images(self):
        """Manually load one or more image files into the gallery."""
        paths = filedialog.askopenfilenames(
            title='Select Image Files',
            filetypes=[
                ('Images', '*.png *.jpg *.jpeg *.bmp *.gif *.webp *.tiff'),
                ('All', '*.*')
            ])
        if not paths:
            return
        new_paths = sorted(paths)
        self.images    = list(self.images) + new_paths
        self.img_index = max(0, len(self.images) - len(new_paths))
        self._update_nav_arrows()
        self._redraw_canvas()
        n = len(self.images)
        self.pl_label.config(text=f'🖼  {n} image{"s" if n != 1 else ""} loaded')

    def _load_folder(self):
        folder = filedialog.askdirectory(title='Select Folder')
        if not folder:
            return
        audio, images = scan_folder(folder)
        self.images    = images
        self.img_index = 0 if images else -1
        self._update_nav_arrows()
        self.playlist  = audio
        if audio:
            self.pl_index = 0
            self._load_track(audio[0], autoplay=True)
        else:
            self.track_label.config(text='No audio in folder', fg=self.C['muted'])
        self.pl_label.config(
            text=f'📂 {os.path.basename(folder)}  —  {len(audio)} audio, {len(images)} images')

    def _load_track(self, path, autoplay=False):
        self._stop(silent=True)
        self.audio_file        = path
        self.duration          = get_audio_duration(path)
        self.cues              = []
        self._current_sub_text = ''

        self.track_label.config(text=os.path.basename(path), fg=self.C['text'])
        self.sub_info_label.config(text='')
        self.dur_label.config(text=self._fmt(self.duration))
        self.time_label.config(text='0:00')
        self._draw_progress(0)

        # Auto-detect subtitle with enhanced matching
        sub = find_subtitle(path)
        if sub:
            self._load_subtitle_file(sub)
        else:
            self.cues = []

        if len(self.playlist) > 1:
            self.pl_label.config(
                text=f'Track {self.pl_index+1} / {len(self.playlist)}  —  {os.path.basename(path)}')

        self._redraw_canvas()
        if autoplay:
            self.after(100, lambda: self._play_from(0))

    def _load_subtitle_file(self, path):
        self.cues = parse_subtitles(path)
        self.sub_info_label.config(
            text=f'💬 {os.path.basename(path)}  ({len(self.cues)} cues)')

    # ═══════════════════════════════════════════════════════════════════════
    #  IMAGE GALLERY
    # ═══════════════════════════════════════════════════════════════════════

    def _update_nav_arrows(self):
        """Show nav arrows only when there are 2+ images (and images are visible)."""
        show = len(self.images) >= 2 and not self.images_hidden
        # Always forget everything first to reset pack order
        self.btn_prev_img.pack_forget()
        self.btn_next_img.pack_forget()
        self.canvas.pack_forget()
        if show:
            # Pack order: prev LEFT, next RIGHT, then canvas fills the remaining middle
            self.btn_prev_img.pack(side='left', fill='y')
            self.btn_next_img.pack(side='right', fill='y')
        # Canvas always fills whatever space remains
        self.canvas.pack(side='left', fill='both', expand=True)

    def _set_nav_arrows(self, visible):
        """Legacy helper — delegates to _update_nav_arrows."""
        self._update_nav_arrows()

    def _toggle_hide_images(self):
        self.images_hidden = not self.images_hidden
        C = self.C
        if self.images_hidden:
            self.btn_hide_img.config(bg=C['accent'], fg='#fff', text='🐵')
        else:
            self.btn_hide_img.config(bg=C['panel'], fg=C['text'], text='🙈')
        self._update_nav_arrows()
        self._redraw_canvas()

    def _prev_image(self):
        if self.images:
            self.img_index = (self.img_index - 1) % len(self.images)
            self._redraw_canvas()

    def _next_image(self):
        if self.images:
            self.img_index = (self.img_index + 1) % len(self.images)
            self._redraw_canvas()

    # ═══════════════════════════════════════════════════════════════════════
    #  CANVAS DRAWING
    # ═══════════════════════════════════════════════════════════════════════

    def _redraw_canvas(self, subtitle_text=None):
        C  = self.C
        cv = self.canvas
        cv.delete('all')
        w = cv.winfo_width()
        h = cv.winfo_height()
        if w < 2 or h < 2:
            return

        has_image = (PIL_OK and bool(self.images)
                    and 0 <= self.img_index < len(self.images)
                    and not self.images_hidden)

        if has_image:
            try:
                pil_img = Image.open(self.images[self.img_index])
                iw, ih  = pil_img.size
                scale   = min(w / iw, h / ih)
                nw, nh  = int(iw * scale), int(ih * scale)
                pil_img = pil_img.resize((nw, nh), Image.LANCZOS)
                self._img_tk = ImageTk.PhotoImage(pil_img)
                cv.create_image(w//2, h//2, image=self._img_tk, anchor='center')
                cv.create_text(w-8, 6, text=f'{self.img_index+1} / {len(self.images)}',
                               fill=C['text'], font=('Segoe UI', 9), anchor='ne')
            except Exception:
                has_image = False

        if not has_image:
            cv.create_rectangle(0, 0, w, h, fill=C['panel2'], outline='')
            r = 5
            for (x, y) in [(14,14),(w-14,14),(14,h-14),(w-14,h-14)]:
                cv.create_oval(x-r,y-r,x+r,y+r, fill=C['accent'], outline='')

        # Subtitle overlay
        txt = subtitle_text if subtitle_text is not None else self._current_sub_text
        if txt:
            weight   = 'bold' if self.sub_bold else 'normal'
            sub_font = ('Segoe UI', self.sub_font_size, weight)
            cx = w // 2
            wrap_w = w - 80   # horizontal wrap limit in pixels

            pos_name = self.SUB_POSITIONS[self.sub_pos_idx]

            # ── Measure text height so we can clamp it inside the canvas ──
            # Draw temporarily off-screen to measure bounding box
            tmp_id = cv.create_text(-9999, -9999, text=txt, font=sub_font,
                                    width=wrap_w, justify='center', anchor='center')
            bb = cv.bbox(tmp_id)
            cv.delete(tmp_id)
            txt_h = (bb[3] - bb[1]) if bb else self.sub_font_size * 2
            margin = 12  # px gap from edge

            if pos_name == 'bottom':
                cy = h - margin - txt_h // 2
            elif pos_name == 'top':
                cy = margin + txt_h // 2
            else:  # center
                cy = h // 2

            # Hard-clamp so text never leaves the canvas
            cy = max(margin + txt_h // 2, min(h - margin - txt_h // 2, cy))

            if has_image:
                # 8-directional shadow for readability on any background
                for dx, dy in [(-2,-2),(2,-2),(-2,2),(2,2),(0,-2),(0,2),(-2,0),(2,0)]:
                    cv.create_text(cx+dx, cy+dy, text=txt, fill='#000000',
                                   font=sub_font, anchor='center',
                                   width=wrap_w, justify='center')
            cv.create_text(cx, cy, text=txt, fill=C['sub_text'],
                           font=sub_font, anchor='center',
                           width=wrap_w, justify='center')

    # ═══════════════════════════════════════════════════════════════════════
    #  PLAYBACK
    # ═══════════════════════════════════════════════════════════════════════

    def _toggle_play(self):
        if not self.audio_file:
            return
        if not PYGAME_OK:
            self._current_sub_text = 'pygame not installed.\npip install pygame'
            self._redraw_canvas()
            return
        if self.playing and not self.paused:
            self._pause()
        elif self.paused:
            self._resume()
        else:
            self._play_from(self._seek_offset)

    def _play_from(self, pos):
        if not self.audio_file or not PYGAME_OK:
            return
        pos = max(0.0, min(pos, self.duration or pos))
        try:
            pygame.mixer.music.load(self.audio_file)
            pygame.mixer.music.play(loops=0, start=0.0)
            if pos > 0.05:
                pygame.mixer.music.set_pos(pos)
        except Exception as e:
            self._current_sub_text = f'Playback error:\n{e}'
            self._redraw_canvas()
            return
        self._seek_offset = pos
        self._play_wall   = time.time() - pos
        self.playing = True
        self.paused  = False
        self.btn_play.config(text='⏸')
        self._cancel_loop()
        self._loop()

    def _pause(self):
        if not PYGAME_OK:
            return
        self._seek_offset = self._elapsed()
        pygame.mixer.music.pause()
        self.paused  = True
        self.playing = True
        self.btn_play.config(text='▶')
        self._cancel_loop()

    def _resume(self):
        if not PYGAME_OK:
            return
        pygame.mixer.music.unpause()
        self._play_wall = time.time() - self._seek_offset
        self.paused  = False
        self.playing = True
        self.btn_play.config(text='⏸')
        self._loop()

    def _stop(self, silent=False):
        if PYGAME_OK:
            try: pygame.mixer.music.stop()
            except Exception: pass
        self.playing      = False
        self.paused       = False
        self._seek_offset = 0.0
        self._cancel_loop()
        if not silent:
            self.btn_play.config(text='▶')
            self._current_sub_text = ''
            self._draw_progress(0)
            self.time_label.config(text='0:00')
            self._redraw_canvas()

    def _skip(self, delta):
        pos = max(0.0, self._elapsed() + delta)
        if self.duration:
            pos = min(pos, self.duration)
        self._seek_offset = pos
        if self.playing and not self.paused:
            self._play_from(pos)
        else:
            self._draw_progress(pos)
            self.time_label.config(text=self._fmt(pos))

    def _elapsed(self):
        if self.playing and not self.paused:
            return time.time() - self._play_wall
        return self._seek_offset

    def _prev_track(self):
        if self.playlist and self.pl_index > 0:
            self.pl_index -= 1
            self._load_track(self.playlist[self.pl_index], autoplay=True)

    def _next_track(self):
        if self.playlist and self.pl_index < len(self.playlist) - 1:
            self.pl_index += 1
            self._load_track(self.playlist[self.pl_index], autoplay=True)

    # ═══════════════════════════════════════════════════════════════════════
    #  SEEK BAR
    # ═══════════════════════════════════════════════════════════════════════

    def _seek_press(self, e):
        self._dragging = True
        self._apply_seek(e.x)

    def _seek_move(self, e):
        if self._dragging:
            self._apply_seek(e.x)

    def _seek_release(self, e):
        if not self._dragging:
            return
        self._dragging = False
        pos = self._seek_offset
        if self.playing and not self.paused:
            self._play_from(pos)
        elif self.paused:
            self._play_from(pos)
            self._pause()

    def _apply_seek(self, pixel_x):
        bar_w = self.prog_canvas.winfo_width()
        if bar_w < 2:
            return
        frac = max(0.0, min(1.0, pixel_x / bar_w))
        pos  = frac * (self.duration if self.duration > 0 else 1.0)
        self._seek_offset = pos
        self._draw_progress(pos)
        self.time_label.config(text=self._fmt(pos))
        self._sync_sub(pos)
        if self.playing and not self.paused:
            self._cancel_loop()

    def _draw_progress(self, pos):
        bar_w = self.prog_canvas.winfo_width()
        bar_h = 12
        dur   = self.duration if self.duration > 0 else 1.0
        frac  = min(1.0, max(0.0, pos / dur))
        fx    = frac * bar_w
        self.prog_canvas.coords(self._prog_fill, 0, 0, fx, bar_h)
        self.prog_canvas.coords(self._prog_dot,  fx-8, -2, fx+8, bar_h+2)

    # ═══════════════════════════════════════════════════════════════════════
    #  SUBTITLE SYNC & MAIN LOOP
    # ═══════════════════════════════════════════════════════════════════════

    def _sync_sub(self, pos):
        txt = ''
        for cue in self.cues:
            if cue['start'] <= pos < cue['end']:
                txt = cue['text']
                break
        if txt != self._current_sub_text:
            self._current_sub_text = txt
            self._redraw_canvas(subtitle_text=txt)

    def _loop(self):
        if not self.playing or self.paused:
            return
        pos = self._elapsed()
        if PYGAME_OK and not pygame.mixer.music.get_busy():
            if not self.duration or pos >= self.duration - 0.3:
                if self.pl_index < len(self.playlist) - 1:
                    self._next_track()
                else:
                    self._stop()
                return
        self._draw_progress(pos)
        self.time_label.config(text=self._fmt(pos))
        self._sync_sub(pos)
        self._after_id = self.after(80, self._loop)

    def _cancel_loop(self):
        if self._after_id:
            self.after_cancel(self._after_id)
            self._after_id = None

    # ═══════════════════════════════════════════════════════════════════════
    #  VOLUME & UTILITIES
    # ═══════════════════════════════════════════════════════════════════════

    def _set_volume(self, val):
        if PYGAME_OK:
            pygame.mixer.music.set_volume(int(val) / 100)

    @staticmethod
    def _fmt(secs):
        secs = max(0, int(secs))
        h, r = divmod(secs, 3600)
        m, s = divmod(r, 60)
        return f'{h}:{m:02d}:{s:02d}' if h else f'{m}:{s:02d}'

    def _on_close(self):
        self._stop(silent=True)
        if PYGAME_OK:
            try: pygame.mixer.quit(); pygame.quit()
            except Exception: pass
        self.destroy()


# ── Entry Point ───────────────────────────────────────────────────────────────

if __name__ == '__main__':
    if not PYGAME_OK:
        print('WARNING: pygame not found  →  pip install pygame')
    if not PIL_OK:
        print('INFO: Pillow not found (image display disabled)  →  pip install Pillow')
    ASMRPlayer().mainloop()

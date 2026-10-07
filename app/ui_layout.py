"""Presentation for the native desktop app; generation stays in VoiceApp."""
import tkinter as tk
import winsound
from tkinter import ttk

from .audio_processing import POLISH_MODES
from .generation import GENERATION_PRESETS


def build_interface(app):
    root = app.root
    bg, ink, muted, blue = "#eef2f7", "#17243b", "#52647a", "#2563eb"
    root.configure(background=bg)
    style = ttk.Style(root)
    style.theme_use("clam")
    style.configure("TFrame", background=bg)
    style.configure("TLabel", background=bg, foreground=ink, font=("Segoe UI", 10))
    style.configure("Card.TFrame", background="white")
    style.configure("Card.TLabel", background="white", foreground=ink)
    style.configure("Help.TLabel", background="white", foreground=muted, font=("Segoe UI", 9))
    style.configure("Heading.TLabel", background="white", foreground=ink, font=("Segoe UI", 12, "bold"))
    style.configure("Title.TLabel", font=("Segoe UI", 24, "bold"), foreground=ink)
    style.configure("TButton", font=("Segoe UI", 10), padding=(10, 7), background="#e8eef7", foreground=ink, borderwidth=0)
    style.map("TButton", background=[("active", "#dce6f4")], foreground=[("disabled", "#8794a5")])
    style.configure("Primary.TButton", background=blue, foreground="white")
    style.map("Primary.TButton", background=[("disabled", "#bbc9dd"), ("active", "#1d4ed8")], foreground=[("disabled", "#f4f6fa")])
    style.configure("TCombobox", padding=5, font=("Segoe UI", 10))
    style.configure("TEntry", padding=5)
    style.configure("Horizontal.TProgressbar", background=blue, troughcolor="#e4ebf4", borderwidth=0)

    panel = ttk.Frame(root, padding=16)
    panel.pack(fill="both", expand=True)
    ttk.Label(panel, text="Local Voice Studio", style="Title.TLabel").pack(anchor="w")
    ttk.Label(panel, text="Your voice. Your words.  •  Private speech generation on this computer.").pack(anchor="w", pady=(2, 12))
    footer = ttk.Frame(panel)
    footer.pack(side="bottom", fill="x")
    body = ttk.Frame(panel)
    body.pack(fill="both", expand=True)
    body.columnconfigure(0, weight=1, uniform="columns")
    body.columnconfigure(1, weight=2, uniform="columns")
    body.rowconfigure(0, weight=1)
    side = ttk.Frame(body)
    side.grid(row=0, column=0, sticky="nsew", padx=(0, 14))
    main = ttk.Frame(body)
    main.grid(row=0, column=1, sticky="nsew")

    def card(parent, title, subtitle):
        frame = ttk.Frame(parent, style="Card.TFrame", padding=10)
        frame.pack(fill="x", pady=(0, 8))
        ttk.Label(frame, text=title, style="Heading.TLabel").pack(anchor="w")
        label = ttk.Label(frame, text=subtitle, style="Help.TLabel", wraplength=300)
        label.pack(fill="x", pady=(4, 8))
        label.bind("<Configure>", lambda e: label.configure(wraplength=max(100, e.width)))
        return frame

    def help_text(parent, text):
        label = ttk.Label(parent, text=text, style="Help.TLabel", wraplength=300)
        label.pack(fill="x", pady=(4, 4))
        label.bind("<Configure>", lambda e: label.configure(wraplength=max(100, e.width)))
        return label

    voices = card(side, "1  Your voice reference", "BEFORE GENERATION\nPrepare a recording for cloning your voice.")
    app.voice = ttk.Combobox(voices, state="readonly", width=18)
    app.voice.pack(fill="x")
    app.voice.bind("<<ComboboxSelected>>", app.select_voice)
    app.add_button = ttk.Button(voices, text="Add a voice recording…", command=app.import_voice)
    app.add_button.pack(fill="x", pady=(10, 5))
    app.replace_button = ttk.Button(voices, text="Replace selected recording…", command=lambda: app.import_voice(True))
    app.replace_button.pack(fill="x", pady=(0, 5))
    app.cleanup_button = ttk.Button(voices, text="Clean selected voice reference…", command=app.clean_saved_reference)
    app.cleanup_button.pack(fill="x")
    help_text(voices, "Trim silence, balance volume, or reduce noise. Originals are kept. Use a clear 10-15 second WAV.")

    polish = card(side, "3  Refine generated audio", "AFTER GENERATION\nPolish finished speech. Saved references stay unchanged.")
    app.polishes = ttk.Combobox(polish, state="readonly", textvariable=app.polish_mode, values=POLISH_MODES, width=18)
    app.polishes.pack(fill="x")
    description = tk.StringVar()
    label = help_text(polish, "")
    label.configure(textvariable=description)
    descriptions = {
        "Original": "Keep the generated audio as it is. No automatic polish is applied.",
        "Natural polish": "Gently balance volume and reduce low-frequency rumble for smoother speech.",
        "Brighter speech": "Apply natural polish with extra presence for a clearer, brighter tone.",
    }
    def update_description(*_):
        description.set(descriptions[app.polish_mode.get()])
    app.polish_mode.trace_add("write", update_description)
    update_description()
    strength = tk.StringVar()
    def update_strength(*_):
        strength.set(f"Polish strength: {app.polish_strength.get():.0%}")
    app.polish_strength.trace_add("write", update_strength)
    update_strength()
    ttk.Label(polish, textvariable=strength, style="Card.TLabel").pack(anchor="w")
    app.strength_slider = ttk.Scale(polish, from_=0, to=1, variable=app.polish_strength)
    app.strength_slider.pack(fill="x", pady=5)
    app.polish_button = ttk.Button(polish, text="Reapply polish to latest audio", state="disabled", command=app.apply_polish)
    app.polish_button.pack(fill="x", pady=(5, 0))
    help_text(polish, "Polish runs after generation. Reapply to compare settings. The original is kept.")

    speech = card(main, "2  Write and generate", "Enter English text below and generate speech with your selected model and voice.")
    speech.pack_configure(fill="both", expand=True)
    model_row = ttk.Frame(speech, style="Card.TFrame")
    model_row.pack(fill="x", pady=(0, 4))
    ttk.Label(model_row, text="Speech model", style="Card.TLabel").pack(side="left", padx=(0, 8))
    app.models = ttk.Combobox(model_row, state="readonly", textvariable=app.model_choice,
        values=("Chatterbox Turbo", "Qwen3-TTS 1.7B Base"), width=23)
    app.models.pack(side="left")
    app.models.bind("<<ComboboxSelected>>", app.select_model)
    app.transcript_button = ttk.Button(model_row, text="Reference transcript...", command=app.edit_transcript)
    app.transcript_button.pack(side="left", padx=8)
    app.model_description = tk.StringVar()
    model_help = help_text(speech, "")
    model_help.configure(textvariable=app.model_description)
    options = ttk.Frame(speech, style="Card.TFrame")
    options.pack(fill="x")
    for col in range(3):
        options.columnconfigure(col, weight=1, uniform="options")
    for col, title in enumerate(("Delivery style", "Processing device", "Random seed (optional)")):
        ttk.Label(options, text=title, style="Card.TLabel").grid(row=0, column=col, sticky="w", padx=(0, 8))
    app.presets = ttk.Combobox(options, state="readonly", textvariable=app.preset, values=tuple(GENERATION_PRESETS), width=10)
    app.devices = ttk.Combobox(options, state="readonly", textvariable=app.device, values=("Automatic", "NVIDIA GPU", "CPU"), width=10)
    app.seed_entry = ttk.Entry(options, textvariable=app.seed, width=10)
    for col, widget in enumerate((app.presets, app.devices, app.seed_entry)):
        widget.grid(row=1, column=col, sticky="ew", padx=(0, 8), pady=(4, 0))
    help_text(speech, "Steady uses less variation; Expressive uses more. Automatic prefers the GPU. Leave seed blank for variety; reuse a number for comparisons.")
    text_frame = ttk.Frame(speech, style="Card.TFrame")
    text_frame.pack(fill="both", expand=True)
    app.text = tk.Text(text_frame, wrap="word", height=4, font=("Segoe UI", 12), padx=12, pady=12, undo=True,
                       background="#f8fafc", foreground=ink, insertbackground=blue, relief="flat", highlightthickness=1,
                       highlightbackground="#dbe3ee", highlightcolor=blue)
    scroll = ttk.Scrollbar(text_frame, command=app.text.yview)
    app.text.configure(yscrollcommand=scroll.set)
    app.text.pack(side="left", fill="both", expand=True)
    scroll.pack(side="right", fill="y")
    count = tk.StringVar(value="0 / 20,000 characters")
    ttk.Label(speech, textvariable=count, style="Help.TLabel").pack(anchor="e", pady=(4, 8))
    def count_text(_):
        if app.text.edit_modified():
            count.set(f"{len(app.text.get('1.0', 'end-1c')):,} / 20,000 characters")
            app.text.edit_modified(False)
    app.text.bind("<<Modified>>", count_text)
    controls = ttk.Frame(speech, style="Card.TFrame")
    controls.pack(fill="x")
    app.generate_button = ttk.Button(controls, text="Generate my voice", style="Primary.TButton", command=app.generate)
    app.generate_button.pack(side="left")
    app.test_button = ttk.Button(controls, text="Test built-in voice", command=lambda: app.generate(True))
    app.test_button.pack(side="left", padx=8)
    app.cancel_button = ttk.Button(controls, text="Cancel", state="disabled", command=app.request_cancel)
    app.cancel_button.pack(side="left")

    result = card(main, "Listen and export", "Choose Original or Polished to compare. Playback and export use the selected version.")
    versions = ttk.Frame(result, style="Card.TFrame")
    versions.pack(fill="x", pady=(0, 8))
    ttk.Label(versions, text="Audio version", style="Card.TLabel").pack(side="left", padx=(0, 8))
    app.versions = ttk.Combobox(versions, state="disabled", textvariable=app.output_version, values=("Original", "Polished"), width=10)
    app.versions.pack(side="left")
    playback = ttk.Frame(result, style="Card.TFrame")
    playback.pack(fill="x")
    app.play_button = ttk.Button(playback, text="Play selected", state="disabled", command=app.play)
    app.play_button.pack(side="left")
    ttk.Button(playback, text="Stop", command=lambda: winsound.PlaySound(None, 0)).pack(side="left", padx=8)
    app.export_button = ttk.Button(playback, text="Export selected WAV…", state="disabled", command=app.export)
    app.export_button.pack(side="left")
    ttk.Button(result, text="Open saved audio folder", command=app.open_outputs).pack(anchor="w", pady=(8, 0))
    app.progress = ttk.Progressbar(footer, mode="determinate")
    app.progress.pack(fill="x", pady=(4, 8))
    status = ttk.Label(footer, textvariable=app.status, wraplength=800)
    status.pack(fill="x")
    status.bind("<Configure>", lambda e: status.configure(wraplength=max(100, e.width)))

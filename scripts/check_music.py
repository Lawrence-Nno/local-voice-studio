"""Real-track native music workflow acceptance check; never bundles the track."""
import argparse
import hashlib
import time
import tkinter as tk
import winsound
from pathlib import Path
from unittest.mock import patch

import numpy as np
import soundfile as sf
from app.main import configure_dpi
from app.storage import ROOT, DATA, read_json


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--music", type=Path, required=True)
    args = parser.parse_args()
    configure_dpi()
    from app.ui import VoiceApp
    root = tk.Tk()
    app = VoiceApp(root)
    panel = app.music_panel
    app.notebook.select(2)
    root.geometry("+20+20")
    root.update()
    for widget in (panel.create_button, panel.export_button, panel.play_button):
        assert widget.winfo_ismapped()
        assert widget.winfo_rootx() + widget.winfo_width() <= root.winfo_rootx() + root.winfo_width()
        assert widget.winfo_rooty() + widget.winfo_height() <= root.winfo_rooty() + root.winfo_height()
    from PIL import ImageGrab
    ImageGrab.grab(bbox=(root.winfo_rootx(), root.winfo_rooty(), root.winfo_rootx() + root.winfo_width(),
                        root.winfo_rooty() + root.winfo_height())).save(DATA / "music-ui-preview.png")
    voice = ROOT / read_json(DATA / "turbo-comparison.json")["warm_output"]
    signatures = [hashlib.sha256(p.read_bytes()).hexdigest() for p in (voice, args.music)]
    errors = []
    def wait():
        deadline = time.monotonic() + 120
        while (panel.active() or app.mix_running) and time.monotonic() < deadline:
            root.update()
            time.sleep(.01)
        assert not panel.active() and not app.mix_running
    with patch("app.music_ui.messagebox.showerror", side_effect=lambda *args: errors.append(args)):
        app.output = voice
        app.output_version.set("Original")
        panel.use_generated()
        with patch("app.music_ui.filedialog.askopenfilename", return_value=str(args.music)):
            panel.choose(True)
        panel.notes.insert("1.0", "Running Home - Televisions | YouTube Audio Library. User-provided license: incorporation into videos and other content; no attribution required; no standalone music distribution.")
        panel.start()
        assert str(app.generate_button["state"]) == "disabled"
        app.busy(False)
        assert str(app.generate_button["state"]) == "disabled"
        wait()
        assert not errors, errors
        assert panel.output and panel.output.is_file()
        audio, rate = sf.read(panel.output, always_2d=True)
        assert rate == 44100 and audio.shape[1] == 2
        assert abs(len(audio) / rate - sf.info(voice).duration) < .001
        assert np.isfinite(audio).all() and np.max(np.abs(audio)) <= .981
        metadata = read_json(panel.output.with_suffix(".json"))
        assert "YouTube" in metadata["license_notes"]
        target = DATA / "verification" / "voice-with-running-home.wav"
        with patch("app.music_ui.filedialog.asksaveasfilename", return_value=str(target)):
            panel.export()
        assert target.read_bytes() == panel.output.read_bytes()
        assert target.with_suffix(".mix.json").is_file()
        with patch("app.music_ui.filedialog.asksaveasfilename", return_value=str(voice)):
            panel.export()
        assert errors and "preserve" in errors[-1][1]
        errors.clear()
        # A short synthetic track exercises actual end-of-track looping and padding.
        short = DATA / "verification" / "short-test-music.wav"
        tone = .2 * np.sin(2 * np.pi * 110 * np.arange(17640) / 44100)
        sf.write(short, np.column_stack([tone, tone]), 44100)
        panel.music = short
        panel.voice_gain.set(0)
        panel.music_gain.set(1)
        panel.duck.set(False)
        panel.fade_in.set("0")
        panel.fade_out.set("0")
        for loop in (False, True):
            panel.loop.set(loop)
            panel.start()
            wait()
            assert not errors, errors
            mixed, sample_rate = sf.read(panel.output, always_2d=True)
            tail = mixed[-sample_rate:]
            assert (np.max(np.abs(tail)) > .05) == loop
            assert abs(len(mixed) / sample_rate - sf.info(voice).duration) < .001
        loud = DATA / "verification" / "loud-test-voice.wav"
        wave = .8 * np.sin(2 * np.pi * 220 * np.arange(44100) / 44100)
        sf.write(loud, wave, 44100)
        panel.voice = loud
        panel.voice_gain.set(2)
        panel.start()
        wait()
        assert not errors, errors
        assert read_json(panel.output.with_suffix(".json"))["master_gain"] < 1
        mixed, _ = sf.read(panel.output)
        assert np.max(np.abs(mixed)) <= .981
        panel.play()
        winsound.PlaySound(None, 0)
        previous = panel.output
        panel.start()
        panel.stop()
        wait()
        assert not errors and panel.output == previous
        assert str(app.generate_button["state"]) == "normal"
        assert [hashlib.sha256(p.read_bytes()).hexdigest() for p in (voice, args.music)] == signatures
    root.destroy()
    print("Music import, real-track mix, duration, peaks, stereo, preview, byte-identical export, source preservation and cancellation passed.")
    print("Preview sample: " + str(target))


if __name__ == "__main__":
    main()

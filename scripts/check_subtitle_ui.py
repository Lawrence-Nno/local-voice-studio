"""Verify tab workflow, successful export, invalid edits, cancellation and job locking."""
import time
import shutil
import re
import tkinter as tk
from unittest.mock import patch

from app.main import configure_dpi
from app.storage import ROOT, DATA, read_json, atomic_json
from app.subtitles import parse_srt


def main():
    configure_dpi()
    from app.ui import VoiceApp
    root = tk.Tk()
    app = VoiceApp(root)
    panel = app.subtitles
    app.notebook.select(1)
    root.geometry("+20+20")
    root.update()
    for widget in (panel.start_button, panel.export_button, panel.cancel_button):
        assert widget.winfo_ismapped()
        assert widget.winfo_rootx() + widget.winfo_width() <= root.winfo_rootx() + root.winfo_width()
        assert widget.winfo_rooty() + widget.winfo_height() <= root.winfo_rooty() + root.winfo_height()
    from PIL import ImageGrab
    ImageGrab.grab(bbox=(root.winfo_rootx(), root.winfo_rooty(), root.winfo_rootx()+root.winfo_width(),
                        root.winfo_rooty()+root.winfo_height())).save(DATA / "subtitle-ui-preview.png")
    report = read_json(DATA / "turbo-comparison.json")
    source = ROOT / report["warm_output"]
    errors = []
    def wait():
        deadline = time.monotonic() + 60
        while (panel.active() or app.subtitle_running) and time.monotonic() < deadline:
            root.update()
            time.sleep(.01)
        assert not panel.active() and not app.subtitle_running
    with patch("app.subtitle_ui.messagebox.showerror", side_effect=lambda *args: errors.append(args)):
        with patch("app.subtitle_ui.filedialog.askopenfilename", return_value=str(source)):
            panel.choose()
        panel.device.set("NVIDIA GPU")
        panel.language.set("English")
        panel.start()
        assert str(app.generate_button["state"]) == "disabled"
        app.busy(False)
        assert str(app.generate_button["state"]) == "disabled"
        wait()
        assert not errors, errors
        value = panel.text.get("1.0", "end-1c")
        parse_srt(value)
        target = DATA / "verification" / "ui-subtitles.srt"
        with patch("app.subtitle_ui.filedialog.asksaveasfilename", return_value=str(target)):
            panel.export()
        parse_srt(target.read_text(encoding="utf-8"))
        before = target.read_bytes()
        panel.text.delete("1.0", "end")
        panel.text.insert("1.0", "Invalid edited SRT")
        with patch("app.subtitle_ui.filedialog.asksaveasfilename", return_value=str(target)):
            panel.export()
        assert errors and target.read_bytes() == before
        errors.clear()
        panel.text.delete("1.0", "end")
        panel.text.insert("1.0", value)
        job = DATA / "jobs" / "subtitle-ui-test"
        job.mkdir(parents=True, exist_ok=True)
        generated = DATA / "outputs" / "subtitle-ui-test.wav"
        shutil.copyfile(source, generated)
        shutil.copyfile(source, job / "section-0001.wav")
        atomic_json(job / "job.json", {"section_texts": [report["text"]], "text": report["text"]})
        app.output = generated
        app.polished_output = None
        app.output_version.set("Original")
        app.text.delete("1.0", "end")
        app.text.insert("1.0", "This script was changed after generation.")
        panel.generated()
        assert panel.source["mode"] == "align"
        assert panel.source["sections"][0]["text"] == report["text"]
        panel.start()
        wait()
        assert not errors, errors
        value = panel.text.get("1.0", "end-1c")
        aligned = " ".join(c["text"].replace("\n", " ") for c in parse_srt(value))
        assert re.sub(r"\s+", " ", aligned).strip() == report["text"]
        panel.start()
        panel.stop()
        wait()
        assert not errors, errors
        assert panel.text.get("1.0", "end-1c") == value
        assert str(app.generate_button["state"]) == "normal"
    root.destroy()
    print("Subtitle tab layout, import, GPU job, UTF-8 export, invalid edit rejection, cancellation and mutual job locking passed.")


if __name__ == "__main__":
    main()

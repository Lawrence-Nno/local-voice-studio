# Local Voice Studio

A personal Windows audio studio for local voice cloning, text-to-speech, recording, editing, subtitles, music mixing, cleanup, conversion, batch processing, and voice effects.

**Designed by Chima Lawrence Nnoromele**

**Email:** [lawrence.nno@gmail.com](mailto:lawrence.nno@gmail.com)

Audio processing and model inference run locally. Internet access is needed for initial dependency/model downloads, not normal use. Recordings, saved voices, outputs, and preferences belong to your local copy of the app.

## Complete feature list

- **Text to speech and voice cloning:** Chatterbox Turbo and Qwen3-TTS 1.7B Base, persistent voice profiles, saved reference versions, remembered model/voice selection, longer-text chunking, delivery presets, optional seed, playback, and WAV export.
- **Reference preparation before cloning:** select a section, trim quiet edges, adjust volume, optional gentle noise reduction, and compare original/prepared recordings.
- **Generated speech refinement:** Natural polish or Brighter speech with adjustable strength, original/polished comparison, and separate exports.
- **Audio to subtitles:** transcribe imported audio or align the saved script of generated speech; local Whisper Small, automatic/English language selection, CPU/GPU options, editable SRT text/timings, validation, and UTF-8 export.
- **Background music:** import music, adjust voice/music volume, automatic ducking, music start position, optional looping, music fades, preview, peak protection, and mixed WAV export with license/credit notes.
- **Voice recorder:** microphone selection/refresh, cancellable three-second countdown, level meter, recorded-time display, start/pause/resume/stop, separate WAV takes, playback/export, reference-cleanup handoff, and recording-to-subtitles shortcut.
- **Audio editor:** waveform display and drag selection, exact start/end times, trimming, volume, fades, selection preview, source-preserving WAV save/export, and reference handoff.
- **Clip joining:** add whole files or edited selections, reorder/remove/clear clips, choose output rate/channels and optional gaps, preview, and save one joined WAV.
- **Format converter:** WAV, MP3, FLAC, M4A/AAC, and OGG/Opus output; sample-rate/channel options, compressed bitrates, cancellation, and separate-file export.
- **Audio cleanup:** adjustable steady-noise reduction, volume adjustment, automatic leveling, optional low-rumble removal, original/cleaned playback, peak protection, and cleaned WAV export.
- **Batch processing:** queue multiple files for cleanup, conversion, or transcription; settings snapshots, per-file status, optional continuation after errors, cancellation retaining completed files, and a run report.
- **Voice effects:** independent speed/pitch adjustment, room reverb, optional radio-style filtering/saturation, reset, original/processed playback, cancellation, and WAV export.
- **Audio file information:** inspect duration, format/codec, sample rate, channels, file size, and full path; select a local file or loaded input/result and copy details to the clipboard.
- **Portable Windows launch:** native EXE, custom application icon, bundled runtimes/models, and a desktop-shortcut creator.

## Launch and transfer

### Portable app

The current portable folder is:

```text
C:\work\codebase\voice\dist\Local Voice Studio
```

Run **Local Voice Studio.exe**. To transfer the app to another Windows x64 PC, close it and copy the **entire Local Voice Studio folder**, including `app`, `runtime`, `models`, `data`, and supporting files. The EXE alone is not the application.

Put the folder in a writable location. Run **Create desktop shortcut.cmd**, located beside the EXE, to create a shortcut for the new location. Run it again after moving the folder. No separate Python installation or model download is needed for this built copy. GPU acceleration needs a compatible NVIDIA GPU and installed driver; CPU processing is available and can be slower. Other PCs have not been verified.

The project's `data` folder and the portable app's `data` folder are **separate**. Copying the portable app includes only that copy's profiles, recordings, settings, and outputs. Back up any source-project data separately.

The current package is Windows x64. It is not a macOS application; the Windows EXE and runtime libraries cannot run directly on a Mac.

### Source installation

Run **launch.cmd** from the project folder to use its local environment. For a fresh installation, install `uv`, open PowerShell in the project folder, and run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\setup.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\setup-qwen.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\setup-subtitles.ps1
```

Setup downloads several GB and installs project-local Python, libraries, and models. Allow sufficient free space for both runtimes and all models; the full portable build is roughly 18 GiB. Setup does not install NVIDIA drivers or change system-wide Python. Normal launches use local files.

## Text to speech and voice profiles

Choose **Chatterbox Turbo** for fast English generation or **Qwen3-TTS 1.7B Base** to try the alternative cloning model. Both use the same saved voice profiles, text entry, generation, playback, and export workflow. Switching unloads the previous model. The app currently generates English with both models.

Add or replace a WAV reference and name the voice. References must be mono/stereo, longer than 5 seconds and at most 60 seconds, at 8-192 kHz, below 100 MB. A clear 10-30 second recording in a quiet room is a practical starting point. Original recordings and previous prepared versions are retained.

Reference cleanup happens **before cloning**. Generated Output polish happens **after generation**. Natural polish applies mild filtering, compression, volume adjustment, and peak protection; Brighter speech adds presence emphasis. Compare Original and Polished to choose the result you prefer.

With Qwen selected, **Reference transcript...** accepts the exact words spoken in that prepared reference. A blank transcript uses audio-only speaker embedding; a supplied transcript enables audio-and-transcript cloning. Transcripts belong to a reference version and must match it. Turbo also offers a built-in generic voice test; Qwen requires a reference.

Default/Steady/Expressive presets change sampling settings. An optional integer seed supports comparisons. These controls do not guarantee emotions, accents, better resemblance, or bit-identical GPU results. Maximum script length is 20,000 characters, generated in sections. TTS cancellation may wait for the active section to finish. Completed original output remains available if polishing fails.

## Audio to subtitles

Use **Import audio...** to recognize speech in a local recording. For generated speech, **Use generated speech + saved script** aligns its saved English script with the generated audio. Alignment uses the script captured at generation, not later edits in the text box.

Choose language/device, click **Create subtitles**, review the editable cues, and **Export reviewed SRT...**. Invalid SRT edits are rejected. Timings and recognized words are estimates and should be reviewed. No translation or speaker diarization is implemented.

From Voice recorder, finish a take with **Stop and save**, then click **Create subtitles from recording**. The subtitle tab opens with that take selected; click **Create subtitles**. Existing reviewed subtitles remain visible with their previous source identified until new processing succeeds.

## Background music

Import voice/audio or select generated speech, then import a music track. Set voice/music volume, ducking strength, music start, looping, and fades. **Create music mix** saves a separate stereo WAV; preview and export it with its `.mix.json` settings/license sidecar.

The mix ends with the voice. Longer music is cut there and fades according to the fade-out setting. Short music can loop; with looping off, voice continues after music ends. Only music fades. Voice timing stays unchanged, so existing subtitle timings remain valid. Ducking detects audio energy, including noise; it is not a speech classifier.

Use music licensed for your intended content and retain required attribution. The app has no music-download service or bundled music catalog; imported standalone tracks are not packaged with the app.

## Voice recorder

Choose a microphone and **Start recording (3-second countdown)**. The timer displays **Starting in 3**, **2**, then **1** before microphone capture begins. During preparation, **Cancel countdown** stops the pending recording and keeps the previous take; no countdown audio is recorded. Pause becomes available when capture starts.

Watch the peak meter; lower Windows input volume or move away if it reaches 100%. **Pause / Resume** skips paused audio. **Stop and save** creates a mono PCM16 WAV at the microphone's default sample rate. Takes stop automatically at one hour.

Preview/export the take, send it to reference cleanup, or send it to subtitles. For cloning, record 6-60 seconds. If no microphone appears, connect one, check Windows microphone permissions, and refresh the device list.

## Audio editor and joining

Open WAV/FLAC/OGG/MP3 audio or use a recording/generated result. Drag across the waveform or enter start/end seconds. **The highlighted section is kept; audio outside it is removed.** Volume and fades are included in **Preview selection** and **Save edited WAV**. Export uses the last saved edit; changed settings require saving again. Trimming retains source rate/channels and writes PCM16 WAV.

Click **Join clips...** to open an ordered clip list. Add whole audio files or **Add current edited selection** to capture its trim, volume, and fades. Move clips up/down, remove them, choose output rate/Mono/Stereo and an optional 0-10 second gap, then preview or save. Export the joined result from Audio editor. To remove a middle section, add the wanted sections and join them.

Joining supports 2-50 clips and up to one hour of output. Channel conversion may change amplitude. No crossfade or multitrack overlap is applied. Trimming/joining changes timing; recreate subtitles afterward. Originals are protected from export overwrite.

## Format converter

Choose imported audio, a recording, generated speech, or a saved edit. Select WAV, MP3, FLAC, M4A (AAC), or OGG (Opus), sample rate, channels, and applicable bitrate. Click **Convert audio**, then **Export converted file...**.

WAV and FLAC encode PCM16 audio. MP3, AAC, and Opus are lossy; changing format cannot restore lost detail. Opus uses 48 kHz. The first audio stream is converted; artwork, other metadata, and video are not copied. Multichannel inputs require explicit Mono/Stereo downmix. Cancellation or failure preserves the prior completed result.

## Audio cleanup

Choose imported audio or a saved recording/generated clip. Adjust noise reduction/volume, optional automatic leveling and 70 Hz rumble removal, then **Clean audio**. Compare **Play original** and **Play cleaned**, and export the cleaned WAV. Reprocess after changing settings.

Start with mild noise reduction. This targets steady noise such as hiss or a fan; it is not voice separation and does not reliably remove music, other voices, or repair clipping. Volume-only processing is available by setting reduction to zero and disabling rumble removal; automatic leveling is optional. Peak protection avoids output clipping.

Input limit is one hour, mono/stereo at 8-192 kHz. Duration, sample rate, and channels are retained. Output is PCM16 WAV.

## Batch processing

Queue up to 100 unique files, choose Cleanup/Convert/Subtitles, then **Open operation settings**. Adjust settings in that tab, return, and **Start batch**. The run takes a settings snapshot and processes files sequentially. Subtitles recognizes words per file; saved-script alignment is not used.

Each run creates a new folder under `data/batches` or your chosen location, with numbered outputs, `batch-report.json`, and a worker log. Continue-on-error is optional. **Cancel batch** discards the current partial result and retains completed files. **Open last batch folder** retrieves results and errors. Subtitle jobs reload the local model per file. Batch resume, chained operations, and batch voice effects are not implemented.

## Voice effects

Import audio or use a recording, generated result, or saved edit. Set independent **Speed** (0.5-2x) and **Pitch** (-12 to +12 semitones), **Reverb**, and optional **Radio-style voice**. Click **Apply voice effects**, compare original/processed playback, and export a separate WAV. Reset restores normal settings; apply again to create a new result.

Reverb adds a 0.6-second tail. Radio applies a narrow frequency range and mild saturation. Speed/reverb can change duration and require new subtitle timing. Extreme settings may sound artificial; this transforms audio rather than retraining or modifying a saved voice profile.

Inputs are limited to **10 minutes**, mono/stereo at 8 kHz or higher. Rates above 48 kHz are converted to 48 kHz. Output is PCM16 WAV. Long speed/pitch jobs use CPU and additional RAM; cancellation is available.

## Audio file information

Use **Audio file information...** in the menu at the top of the app. Choose a file or select a loaded input/result. The window shows duration, format and codec/sample type, sample rate, channels, exact file size, and full path. **Copy information** copies those details.

Inspection is read-only and uses local libraries, without loading a speech model. Compressed-file durations may include codec padding; the duration source is shown.

## Storage and backups

The app runs one processing job at a time. Close it before moving folders or copying active output files.

- `data/profiles`: original/prepared reference recordings and voice metadata.
- `data/settings.json`: saved preferences.
- `data/outputs` and `data/jobs`: generated speech, sections, and job metadata.
- `data/subtitles`: subtitle results.
- `data/mixes`: background-music mixes and license/settings notes.
- `data/recordings`: recorded takes.
- `data/edits`: trimmed and joined WAVs.
- `data/converted`, `data/cleaned`, and `data/effects`: processed results.
- `data/batches`: default batch output folders and reports.
- `models`: pinned Turbo, Qwen, and Whisper snapshots.

Personal audio/data, models, runtimes, caches, outputs, and Markdown guides are ignored by Git. Guide filenames must contain `guide` (case-insensitive). Git does not back up these files; copy them separately. The detailed local implementation/verification record is in `IMPLEMENTATION_GUIDE.md`, which is intentionally untracked.

## Technology and verification

Python 3.11, Tkinter/ttk, isolated Turbo/Qwen runtimes, PyTorch, SoundFile, PyAV, NumPy/SciPy, librosa, sounddevice/PortAudio, and Faster-Whisper provide the local functionality. Dependency lockfiles and model-spec files pin the installed setup.

The Windows reference system is an AMD Ryzen 9 6900HS, roughly 39 GB RAM, and RTX 3060 Laptop GPU with 6 GB VRAM. Both TTS models and subtitle CPU/GPU workflows have passed local checks. Other machines require their own performance/compatibility checks. Subjective voice resemblance and effect quality require listening.

The existing automated suite has 24 tests. Feature acceptance scripts verify real codec round trips, microphone capture, subtitles, DSP behavior, source preservation, cancellation, export, and native layouts. Examples:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
.\.venv\Scripts\python.exe -m scripts.check_audio_info
.\.venv\Scripts\python.exe -m scripts.check_recorder
.\.venv\Scripts\python.exe -m scripts.check_editor
.\.venv\Scripts\python.exe -m scripts.check_join
.\.venv\Scripts\python.exe -m scripts.check_converter
.\.venv\Scripts\python.exe -m scripts.check_cleanup
.\.venv\Scripts\python.exe -m scripts.check_batch
.\.venv\Scripts\python.exe -m scripts.check_effects
```

Some acceptance scripts capture a short microphone sample, play test audio, or require a previously generated speech file. Test recordings stay local.

## Model and dependency licenses

Third-party models/libraries retain their own licenses. Chatterbox Turbo is MIT licensed and its built-in PerTh watermarking is retained; Qwen3-TTS is Apache-2.0 licensed; the Whisper model specification records MIT licensing. Dependency license files are retained in the bundled runtimes.

- [Chatterbox repository](https://github.com/resemble-ai/chatterbox)
- [Chatterbox Turbo model](https://huggingface.co/ResembleAI/chatterbox-turbo)
- [Qwen3-TTS repository](https://github.com/QwenLM/Qwen3-TTS)
- [Qwen 1.7B Base model](https://huggingface.co/Qwen/Qwen3-TTS-12Hz-1.7B-Base)
- [Faster-Whisper repository](https://github.com/SYSTRAN/faster-whisper)

Design credit does not replace these third-party licenses or a music track's usage terms.

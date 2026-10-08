# Local Voice Studio

A Windows desktop application that converts English text into speech using a locally runnable voice-cloning model. Recordings, profiles, and generated audio stay on this computer.

## Current status

The first application is implemented with persistent voice profiles, background generation, WAV playback/export, and longer-text chunking. Personal voice resemblance remains unverified until a recording is supplied and the user assesses the output.

The detailed design and local verification record are in [IMPLEMENTATION_GUIDE.md](IMPLEMENTATION_GUIDE.md).

Python 3.11.15, Tkinter, and CUDA-enabled PyTorch are installed in the project. CUDA tensor execution succeeded on the RTX 3060 Laptop GPU with approximately 6 GB VRAM. The native window layout was inspected at the display's scaling. Five core tests passed for chunking, profile persistence, safe replacement, output assembly, and cancellation.

## Features

- Local Windows operation, offline after installation and model downloads.
- No cloud speech-generation calls or recurring subscription.
- Persistent voice profiles with saved reference recordings.
- Automatic reuse of the selected voice across application restarts.
- Add or replace recordings for different speaking styles.
- Text entry, generation progress, audio playback, and WAV export.
- NVIDIA GPU acceleration when verified, plus an explicit CPU option.
- Longer-text processing in manageable sections.

## Technology

- Python 3.11 with a project-local virtual environment.
- Tkinter/ttk desktop interface.
- PyTorch inference.
- Chatterbox Turbo 0.1.7 backend for English speech.

The model and its dependencies retain their own licenses. The [official repository](https://github.com/resemble-ai/chatterbox) and [model card](https://huggingface.co/ResembleAI/chatterbox-turbo) describe the model and its MIT license. The application retains built-in PerTh watermarking. `model-spec.json` pins the model revision; `requirements-lock.txt` pins installed dependency versions.

## Target hardware

- AMD Ryzen 9 6900HS.
- 39.2 GB usable RAM.
- NVIDIA GeForce RTX 3060 Laptop GPU with 6 GB dedicated VRAM.
- Windows reporting build 26200 during initial inspection.

## Setup and launch

Double-click **`launch.cmd`** in this folder. Normal launch uses the local environment and does not download anything.

For a new installation, open PowerShell in this folder and run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\setup.ps1
```

The execution-policy bypass applies only to that process. Setup requires `uv`, internet access, and approximately 15 GB free for initial installation. It installs project-local Python, CUDA PyTorch, pinned dependencies, and model files. Downloads are several GB. It does not change NVIDIA drivers or system-wide Python.

## Using the application

1. Click **Add recording**, choose a WAV, and give the voice a name.
2. Enter English text and click **Generate with saved voice**.
3. Click **Play** or **Export WAV** when generation completes.

The selected voice is restored on restart. The application saves its own reference copy, so moving your original source file does not break the profile. **Replace recording** updates the selected voice; **Add recording** creates a separate voice or style. Previous reference versions remain locally stored.

**Generic speech test** uses the bundled model voice, not yours. If the text box is empty, it uses a short test sentence.

**Automatic** selects CUDA when available and otherwise reports CPU operation. **NVIDIA GPU** requires CUDA. **CPU** explicitly requests slower CPU inference; a short generic CPU generation has been verified.

One job runs at a time, with a maximum of 20,000 characters. Text is generated in short sections and assembled into a completed WAV. Cancellation takes effect between sections or during assembly; the active model operation may need to finish. Partial sections remain in `data/jobs/`, but no unfinished full-text WAV is published. Automatic resume is not implemented.

## Reference cleanup and generated voice refinement

When adding or replacing a recording, **Prepare reference recording** lets you set start/end times, trim quiet edges, normalize volume, and optionally apply gentle stationary-noise reduction. Click **Play original** and **Preview cleanup** to compare, then **Save voice reference** to save. The processed reference must remain longer than five seconds. Noise reduction is off by default because it can alter voice detail. Turning all processing options off uses the selected segment without normalization, apart from peak protection.

**Clean selected voice reference?** opens the selected profile's preserved original recording. Saving creates a new version; the source recording and previous references are retained. Existing profiles remain compatible without migration.

Generation now offers **Default**, **Steady**, and **Expressive** delivery presets. These change Turbo's sampling temperature (0.8, 0.65, and 0.9 respectively), with repetition penalty 1.2. They are sampling choices, not guaranteed emotion or pronunciation controls. An optional integer **Seed** between 0 and 4294967295 supports repeatable comparisons with identical text, reference, settings, hardware, and runtime; GPU results are not guaranteed bit-for-bit deterministic. Blank uses normal random sampling. Preset and seed are recorded with each job.

**Output polish** offers **Original**, **Natural polish**, and **Brighter speech**, with adjustable strength. Natural polish applies a gentle low-frequency filter, mild compression, volume normalization, and peak protection. Brighter speech also adds modest presence emphasis. The initial selection is Natural polish at half strength. Processing runs after generation and always preserves the original completed WAV; no new model or download is required.

Use the **Original/Polished** selector beside playback to compare or export either version. **Reapply polish to latest audio** reapplies the current settings to the original output, never to an already polished copy. Polished WAVs use the `-polished.wav` suffix, with a JSON sidecar recording mode and strength. Selecting Original bypasses polishing. A processing failure leaves the completed original available.

These features refine the signal and allow delivery experiments. They do not retrain the voice model, reliably change accent, repair every pronunciation error, or establish better resemblance. Listen to the original and processed versions to choose what works for your voice.

Nine automated tests now cover the original workflows plus cleanup, source preservation, audio bounds, and seeded sampling. UI selection and both export versions were verified. A cleaned private copy of the user's recording passed offline GPU generation with Steady delivery and seed 42, followed by both polish modes. The source recording was unchanged. Subjective improvements require listening assessment.

### Recording recommendations

For the proposed Turbo backend, prepare approximately 10–15 seconds of clear English speech in a WAV file. Record one speaker in a quiet room, without background music, clipping, heavy echo, or long silence.

No personal reference recording has been supplied yet. Generic speech tests will be distinguished from tests of resemblance to your voice.

Supported references are mono/stereo WAV, longer than 5 seconds and no longer than 60 seconds, at 8–192 kHz, below 100 MB. Put clear speech at the start; the model uses the opening portions of a reference.

## Local data and version control

Recordings, voice profiles, generated audio, model files, logs, caches, Python environments, and Markdown guides are excluded from Git by default. Guide filenames must contain `guide` (case-insensitive) to match the ignore rule. These files remain local; Git will not back them up. Back up personal data and reference guides separately.

This repository is local. No remote repository or hosting service has been configured.

- `data/profiles/`: original recordings, prepared references, and voice metadata.
- `data/settings.json`: selected voice and device preference.
- `data/outputs/`: completed WAV files.
- `data/jobs/`: generated sections and job metadata, including timing and model revision.
- `models/chatterbox-turbo/`: pinned model files and manifest.
- `.venv/`, `.python/`, `.cache/`: runtime and caches.

Entered text is not retained in job metadata or diagnostic logs. Local storage is ordinary files, not encryption. Back up personal data separately; Git does not back it up.

Runtime uses local checkpoints with Hugging Face and Transformers offline settings. Missing model files produce a setup-repair message rather than an automatic download.

## Verification and troubleshooting

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m scripts.diagnose
.\.venv\Scripts\python.exe -m scripts.smoke_test
```

The smoke test generates generic speech from a fresh engine with Python socket connections blocked. Results are recorded in `data/smoke-test.json` when successful. This does not establish personal resemblance or prove that every native library is incapable of network access. Audible playback quality still requires the user to listen.

Measured on this computer on 7 October 2026:

- GPU generic test: 5.48-second, 24 kHz WAV; approximately 29 seconds including cold model loading; peak PyTorch reserved GPU memory approximately 2.84 GiB.
- Total GPU usage at the end of that test: approximately 3.87 GiB, including other device usage.
- Saved synthetic reference test: profile restored from disk; two generated sections assembled into a 16.1-second WAV in approximately 28 seconds including model loading and reference preparation.
- Short generic CPU generation succeeded.
- Setup rerun reused the pinned environment and model successfully.
- UI background-job transitions passed; WAV export was byte-identical; Windows accepted the playback call. Audible quality still needs the user's listening assessment.

These are initial functional measurements, not a speed guarantee or a personal voice quality rating. GPU memory can grow with different prompts and references. No actual personal recording has been tested. The synthetic profile test can be repeated with `.\.venv\Scripts\python.exe -m scripts.verify_reference` after the generic smoke test.

- **Missing runtime or model files:** rerun `setup.ps1` while online.
- **CUDA unavailable:** inspect `data/diagnostics.json`; select CPU explicitly or repair the runtime.
- **GPU memory exhausted:** close GPU-heavy apps, shorten text, or explicitly retry on CPU.
- **Damaged profile:** restore `data/profiles/` from backup or add a new recording. Invalid profiles are reported while other profiles remain usable.
- **Playback fails:** check the Windows output device or export the WAV to a local player.
- **Interrupted job:** completed section WAVs remain in `data/jobs/`.

## Development reference

See [IMPLEMENTATION_GUIDE.md](IMPLEMENTATION_GUIDE.md) for the architecture, profile storage, generation workflow, offline requirements, installation plan, milestones, and acceptance criteria.

The guide is intentionally excluded from future Git commits and may be absent in a new checkout.

## Desktop interface

The numbered cards separate recording preparation (before generation), text and delivery settings, and audio polish (after generation). Mode explanations, a polish-strength percentage, and a live character count clarify the active settings. **Generate my voice** uses the selected reference; **Test built-in voice** uses the model's generic voice. **Play selected** and **Export selected WAV?** use the Original/Polished selection.

## Choosing a speech model

**Speech model** selects **Chatterbox Turbo** or **Qwen3-TTS 1.7B Base**. The selection is remembered on restart. Turbo is the fast English backend with a built-in test voice. Qwen Base needs a saved voice reference, so its built-in-test button is disabled. Both use the same generation, playback, export, and output-polish workflow. Switching unloads the previous model before loading the new one.

Qwen uses a separate `.venv-qwen` environment and `models/qwen3-tts-1.7b` snapshot, leaving Turbo's dependencies intact. For a fresh installation, run `setup.ps1`, then `setup-qwen.ps1` while online. Qwen dependencies are pinned in `requirements-qwen-lock.txt`; its model revision is pinned in `qwen-model-spec.json`. Inference uses only local files. Qwen uses PyTorch SDPA attention on Windows rather than requiring FlashAttention.

With Qwen selected, **Reference transcript...** lets you enter the exact words spoken in the selected prepared recording. A nonempty transcript enables its audio-and-transcript cloning mode; blank uses speaker-embedding-only cloning. A transcript is tied to the reference version and must be supplied again after changing the reference. No automatic transcription or upload is performed. The app currently generates English with both models. Larger model size does not establish better personal resemblance; compare unpolished samples using identical text and recordings.

Qwen's model and code are Apache-2.0 licensed. See the [official Qwen repository](https://github.com/QwenLM/Qwen3-TTS) and [1.7B Base model card](https://huggingface.co/Qwen/Qwen3-TTS-12Hz-1.7B-Base).

Qwen delivery presets use temperature 0.9 (Default), 0.65 (Steady), or 1.0 (Expressive), with repetition penalty 1.05. These are sampling controls rather than guaranteed emotional styles. Actual sampling values are saved with each job.

### Local Qwen verification

On the RTX 3060 Laptop GPU (6 GB), Qwen 1.7B successfully generated a 24 kHz WAV using an existing voice reference in audio-only mode. A six-second sample took 36.7 seconds including loading and 22.3 seconds with the model already loaded. Peak PyTorch CUDA reserved memory was 4.26 GiB; other GPU allocations are additional. Turbo generated the same text/reference in 3.0 seconds when loaded, producing 4.52 seconds of audio. These are short local measurements, not general benchmarks. Subjective resemblance and clarity require listening.

Unpolished comparison samples are saved locally at `data/outputs/model-comparison/qwen-1.7b.wav` and `data/outputs/model-comparison/chatterbox-turbo.wav`. Detailed measurement records are in `data/qwen-comparison.json` and `data/turbo-comparison.json`. These personal files remain excluded from Git. CPU inference and audio-and-transcript Qwen quality have not been verified. Thirteen automated tests, native layout/control checks, UI routing and release in both switch directions, playback/export checks, and real GPU generation with both models passed.

## Portable Windows app

The portable edition contains `Local Voice Studio.exe`, the app, both model snapshots, and separate standalone Python runtimes. Keep the entire folder together when copying or moving it. Launch the EXE from a writable location on Windows x64; no Python installation or model download is required. NVIDIA GPU acceleration needs a compatible installed NVIDIA driver. Compatibility on other PCs is not yet verified.

Double-click `Create desktop shortcut.cmd` inside the portable folder to create a desktop shortcut. Run it again after moving the folder. Profiles, preferences, generated WAVs, caches, and logs belong to that copy's local `data` and `.cache` folders. Close the app before moving it. A personal build includes your saved voice recordings; it does not include the source project's output history.

To rebuild from the verified developer installation, run `.venv\Scripts\python.exe -m scripts.build_portable --include-profiles`. Omit `--include-profiles` for a copy without personal recordings. Allow at least 20 GiB free during building. The builder creates `dist/Local Voice Studio.build`; it refuses to overwrite an existing build. The native launcher is compiled with Windows' .NET Framework C# compiler. Build artifacts remain ignored by Git. The launcher uses `app.desktop` to capture logs in `data/launch.log`, while Qwen's adapter selects the bundled interpreter when present.


The completed personal package is at `dist/Local Voice Studio` (17.16 GiB), with a `Local Voice Studio` desktop shortcut already created. Verification on 8 October 2026 passed after renaming the build folder: executable/native UI launch, bundled interpreter paths, 13 source regression tests, and real offline GPU generation with both bundled models. Loaded-model generation took 2.75 seconds with Turbo and 20.50 seconds with Qwen for the short comparison sentence. Initial loading was slower from the fresh copy. Moving to a different PC remains unverified; the Windows x64 target and NVIDIA-driver requirements still apply.

## Audio to subtitles

The **Audio to subtitles** tab provides two offline workflows:

- **Import audio...** recognizes spoken words and their timestamps using multilingual Whisper Small. Common formats include WAV, MP3, M4A, FLAC, OGG, AAC, and WMA, decoded through PyAV's bundled media libraries. Choose Automatic language detection or English explicitly.
- **Use generated speech + saved script** aligns the exact English script saved with a newly generated TTS job, preserving wording instead of replacing it with recognition guesses. It uses actual generated section audio and accounts for inter-section pauses. Original and Polished have identical timing; the currently selected version identifies the source. Edits made later in the TTS text box do not alter the saved script. Older jobs without a saved script can be transcribed by importing their WAV.

Click **Create subtitles**, review/edit the SRT text and timing lines, then **Export reviewed SRT...**. UTF-8 export validates sequential cue numbers, positive durations, and non-overlapping chronological times. Automatically created cues aim for at most two 42-character lines and seven seconds per cue; unusually long individual words can exceed line width. Timings are model estimates and should be reviewed. Silence or unrecognizable speech produces an error instead of an empty subtitle file.

Only one audio job runs at a time. Subtitle processing releases the loaded TTS model, runs in a cancellable isolated worker, and exits afterward. Cancellation or failure keeps the previous editor contents. Automatic SRT results and metadata are saved under `data/subtitles`; exports include your edits. Generated-script alignment currently supports English and sections up to 30 seconds each; longer sections can use transcription. There is no speaker diarization, subtitle translation, video preview, or manual audio-timing playback in this version.

The subtitle model revision is pinned in `subtitle-model-spec.json`; worker dependencies share the isolated Qwen environment and its lock file. Run `setup-subtitles.ps1` for a developer installation after the Qwen environment is set up. Fresh portable builds include Whisper Small; the existing personal portable copy is updated in place by `scripts/update_portable_subtitles.py`, preserving data. The [Faster-Whisper repository](https://github.com/SYSTRAN/faster-whisper) describes its transcription and timestamp APIs.

Both subtitle workflows passed real GPU and CPU checks. Seventeen automated tests passed, along with native tab layout, saved-script selection after textbox edits, UTF-8 export, invalid-edit rejection, cancellation, shared job locking, TTS model switching and original/polished audio export checks. The existing portable executable opens both tabs and passed both GPU subtitle workflows. Generated SRT files are ignored by Git.

With subtitles included, the updated personal portable folder is approximately 17.83 GiB. Your existing desktop shortcut continues to point to it; reopen the app to load the new tab.

## Background music

Use the **Background music** tab to import voice/audio, or select the latest Original/Polished generated speech, then import a local music track. **Create music mix** produces a new stereo PCM WAV; **Preview mix** plays it, and **Export mixed WAV...** saves it with a `.mix.json` sidecar containing source paths, settings, peak-protection gain, and any music license/credit notes you entered.

Voice volume ranges from 0?200%; music volume ranges from 0?100% (default 15%). Automatic ducking lowers music during voice activity, with adjustable reduction (default 75%), quick attack and gradual release. Detection uses audio energy rather than a speech model, so background noise can trigger it. Music start chooses a position inside the music file. Looping repeats from that position when necessary, using brief boundary fades; without looping, music ends and the voice continues. Configurable fade-in/out affect only the music. Fade-out occurs at the end of the voice, or at the earlier music end when looping is off.

The voice starts at zero and keeps its speed and duration; existing SRT timestamps remain valid. Audio is decoded/resampled to 44.1 kHz stereo with PyAV and mixed in small blocks on CPU. A second pass reduces overall gain only if required to prevent clipping. Processing uses no online service or AI model. Temporary decoded audio is removed after completion/cancellation. Previous mixes and original files remain available on failure or cancellation. One audio job runs at a time across the app's three tabs.

Use tracks licensed for your intended content and keep their license notes. The app imports music locally and does not distribute standalone tracks or include them in portable builds. The user's supplied YouTube Audio Library track was used only for local feature tests. Mixed results and metadata are stored in `data/mixes`; exported music license notes travel with the mixed WAV. There is no automatic music download or embedded music catalog.

Background music verification passed with the supplied Running Home / Televisions MP3: stereo output, matching voice duration, finite peak-safe samples, original source hashes unchanged, Windows playback, byte-identical WAV export with notes, source-overwrite rejection, and cancellation retaining a previous mix. Short synthetic tracks verified looping versus silence after music ends; a deliberately loud fixture triggered peak attenuation. All 21 automated tests passed. TTS layout/switching/export and subtitle workflow regressions passed. The desktop portable copy opens three tabs and passed the same real-track checks using its bundled runtime. Reopen the app to load the new tab. Mixing takes place locally on CPU and requires no further downloads.

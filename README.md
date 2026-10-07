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

When adding or replacing a recording, **Prepare reference recording** lets you set start/end times, trim quiet edges, normalize volume, and optionally apply gentle stationary-noise reduction. Click **Play original** and **Preview cleanup** to compare, then **Use reference** to save. The processed reference must remain longer than five seconds. Noise reduction is off by default because it can alter voice detail. Turning all processing options off uses the selected segment without normalization, apart from peak protection.

**Clean saved reference** opens the selected profile's preserved original recording. Saving creates a new version; the source recording and previous references are retained. Existing profiles remain compatible without migration.

Generation now offers **Default**, **Steady**, and **Expressive** delivery presets. These change Turbo's sampling temperature (0.8, 0.65, and 0.9 respectively), with repetition penalty 1.2. They are sampling choices, not guaranteed emotion or pronunciation controls. An optional integer **Seed** between 0 and 4294967295 supports repeatable comparisons with identical text, reference, settings, hardware, and runtime; GPU results are not guaranteed bit-for-bit deterministic. Blank uses normal random sampling. Preset and seed are recorded with each job.

**Output polish** offers **Original**, **Natural polish**, and **Brighter speech**, with adjustable strength. Natural polish applies a gentle low-frequency filter, mild compression, volume normalization, and peak protection. Brighter speech also adds modest presence emphasis. The initial selection is Natural polish at half strength. Processing runs after generation and always preserves the original completed WAV; no new model or download is required.

Use the **Original/Polished** selector beside playback to compare or export either version. **Apply polish** reapplies the current settings to the original output, never to an already polished copy. Polished WAVs use the `-polished.wav` suffix, with a JSON sidecar recording mode and strength. Selecting Original bypasses polishing. A processing failure leaves the completed original available.

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

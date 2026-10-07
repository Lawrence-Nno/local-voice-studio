# Personal Local Voice Cloning TTS

A planned Windows desktop application that converts text into speech resembling your own voice using a locally runnable voice-cloning model.

## Current status

**Planning stage. No runnable application has been implemented yet.**

The detailed design is in [IMPLEMENTATION_GUIDE.md](IMPLEMENTATION_GUIDE.md). Implementation and further installation are paused until the user directs development to begin.

An interrupted setup attempt created project-local `.cache` and `.python` directories. These are ignored by Git and do not establish a working runtime. No virtual environment or model installation has been verified.

## Planned features

- Local Windows operation, offline after installation and model downloads.
- No cloud speech-generation calls or recurring subscription.
- Persistent voice profiles with saved reference recordings.
- Automatic reuse of the selected voice across application restarts.
- Add or replace recordings for different speaking styles.
- Text entry, generation progress, audio playback, and WAV export.
- NVIDIA GPU acceleration when verified, plus an explicit CPU option.
- Longer-text processing in manageable sections.

## Proposed technology

- Python 3.11 with a project-local virtual environment.
- Tkinter/ttk desktop interface.
- PyTorch inference.
- Chatterbox Turbo as the first model candidate for English speech.

These choices remain subject to compatibility and hardware testing. Windows inference, GPU memory use, speed, and resemblance to your voice are not yet verified. The model and its dependencies retain their own licenses.

## Target hardware

- AMD Ryzen 9 6900HS.
- 39.2 GB usable RAM.
- NVIDIA GeForce RTX 3060 Laptop GPU with 6 GB dedicated VRAM.
- Windows reporting build 26200 during initial inspection.

## Setup and launch

Setup and launch scripts have not been created yet. There are currently no application launch commands.

The implementation guide describes the planned `setup.ps1` and `launch.cmd` workflow. Development will first validate the local runtime and model before building the interface.

## Recording guidance

For the proposed Turbo backend, prepare approximately 10–15 seconds of clear English speech in a WAV file. Record one speaker in a quiet room, without background music, clipping, heavy echo, or long silence.

No personal reference recording has been supplied yet. Generic speech tests will be distinguished from tests of resemblance to your voice.

## Local data and version control

Recordings, voice profiles, generated audio, model files, logs, caches, and Python environments are excluded from Git by default. They remain ordinary local files; Git will not back them up. Back up personal data separately.

This repository is local. No remote repository or hosting service has been configured.

## Development reference

See [IMPLEMENTATION_GUIDE.md](IMPLEMENTATION_GUIDE.md) for the architecture, profile storage, generation workflow, offline requirements, installation plan, milestones, and acceptance criteria.

"""Private JSON-line worker launched only with the isolated Qwen interpreter."""
import contextlib
import json
import sys
import traceback

from .storage import configure_runtime


def main():
    configure_runtime()
    channel = sys.stdout
    model, prompt = None, None
    with contextlib.redirect_stdout(sys.stderr):
        import numpy as np
        import soundfile as sf
        import torch
        from qwen_tts import Qwen3TTSModel
        for line in sys.stdin:
            try:
                request = json.loads(line)
                operation = request["operation"]
                result = {}
                if operation == "load":
                    device = request["device"]
                    if device == "cuda" and not torch.cuda.is_available():
                        raise ValueError("CUDA is unavailable in the Qwen environment.")
                    model = Qwen3TTSModel.from_pretrained(request["directory"], device_map=device,
                        dtype=torch.bfloat16 if device == "cuda" else torch.float32,
                        attn_implementation="sdpa", local_files_only=True)
                elif operation == "prepare":
                    audio, rate = sf.read(request["reference"], dtype="float32", always_2d=True)
                    transcript = request.get("transcript", "").strip()
                    with torch.inference_mode():
                        prompt = model.create_voice_clone_prompt(ref_audio=(audio.mean(axis=1), rate),
                            ref_text=transcript or None, x_vector_only_mode=not bool(transcript))
                elif operation == "seed":
                    import random
                    random.seed(request["seed"])
                    np.random.seed(request["seed"])
                    torch.manual_seed(request["seed"])
                elif operation == "generate":
                    with torch.inference_mode():
                        wavs, rate = model.generate_voice_clone(text=request["text"], language="English",
                            voice_clone_prompt=prompt, temperature=request["temperature"],
                            repetition_penalty=request["repetition_penalty"], max_new_tokens=2048)
                    np.savez(request["output"], audio=wavs[0], rate=rate)
                    result = {"peak_reserved_bytes": torch.cuda.max_memory_reserved() if torch.cuda.is_available() else 0}
                else:
                    raise ValueError("Unknown worker operation")
                response = {"ok": True, **result}
            except Exception as exc:
                traceback.print_exc()
                response = {"ok": False, "error": str(exc)}
            channel.write(json.dumps(response) + "\n")
            channel.flush()


if __name__ == "__main__":
    main()

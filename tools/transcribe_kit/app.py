from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Callable

MODEL_DIR = str(Path(__file__).resolve().parent.parent.parent / "model")
DEFAULT_SAMPLING_RATE = 16000
DEFAULT_LANGUAGE = "zh"
DEFAULT_MAX_NEW_TOKENS = 256
NO_SPACE_LANGUAGES = {"ja", "zh"}

DEFAULT_BACKEND = "cohere"
BACKENDS = {"cohere", "faster-whisper", "mlx-whisper"}
DEFAULT_WHISPER_MODEL = "large-v3"
DEFAULT_DEVICE = "auto"
DEFAULT_COMPUTE_TYPE = "int8"

MEDIA_EXTENSIONS = {
    ".wav", ".flac", ".mp3", ".m4a", ".ogg", ".opus", ".wma", ".aac",
    ".mp4", ".mov", ".mkv", ".avi", ".webm", ".ts", ".flv",
}


def collect_media_files(paths: list[str]) -> list[str]:
    result: list[str] = []
    for p in paths:
        path = Path(p)
        if path.is_dir():
            for f in sorted(path.rglob("*")):
                if f.is_file() and f.suffix.lower() in MEDIA_EXTENSIONS:
                    result.append(str(f))
        else:
            result.append(str(path))
    return result


def build_processor(model_dir: str = MODEL_DIR) -> Any:
    from transformers import AutoProcessor

    return AutoProcessor.from_pretrained(model_dir)


def build_model(model_dir: str = MODEL_DIR) -> Any:
    from transformers import CohereAsrForConditionalGeneration

    return CohereAsrForConditionalGeneration.from_pretrained(
        model_dir,
        device_map="auto",
    )


def default_audio_loader(path: str, sampling_rate: int) -> Any:
    from transformers.audio_utils import load_audio

    return load_audio(path, sampling_rate=sampling_rate)


def transcribe_demo(
    *,
    processor: Any | None = None,
    model: Any | None = None,
    audio_path: str,
    model_dir: str = MODEL_DIR,
    sampling_rate: int = DEFAULT_SAMPLING_RATE,
    language: str = DEFAULT_LANGUAGE,
    max_new_tokens: int = DEFAULT_MAX_NEW_TOKENS,
    audio_loader: Callable[[str, int], Any] = default_audio_loader,
    progress: Callable[[str], None] | None = None,
) -> str:
    if progress is None:
        progress = lambda message: None

    progress("Loading processor...")
    processor = processor or build_processor(model_dir)
    progress("Loading model...")
    model = model or build_model(model_dir)

    progress(f"Using local audio file: {audio_path}")
    progress(f"Loading audio at {sampling_rate} Hz...")
    audio = audio_loader(audio_path, sampling_rate)

    progress("Preparing model inputs...")
    inputs = processor(
        audio,
        sampling_rate=sampling_rate,
        return_tensors="pt",
        language=language,
    )
    inputs.to(model.device, dtype=model.dtype)
    audio_chunk_index = inputs.get("audio_chunk_index")

    return generate_transcription_text(
        processor=processor,
        model=model,
        inputs=inputs,
        audio_chunk_index=audio_chunk_index,
        language=language,
        max_new_tokens=max_new_tokens,
        progress=progress,
    )


def generate_transcription_text(
    *,
    processor: Any,
    model: Any,
    inputs: dict[str, Any],
    audio_chunk_index: list[tuple[int, int | None]] | None,
    language: str,
    max_new_tokens: int,
    progress: Callable[[str], None],
) -> str:
    total_chunks = len(audio_chunk_index) if audio_chunk_index is not None else infer_batch_size(inputs)

    if audio_chunk_index is not None and total_chunks > 1:
        progress(f"Generating transcription: 0/{total_chunks} chunks completed...")
        decoded_texts: list[str] = []
        for chunk_index in range(total_chunks):
            chunk_inputs = slice_model_inputs(inputs, chunk_index, chunk_index + 1, total_chunks)
            outputs = model.generate(**chunk_inputs, max_new_tokens=max_new_tokens)
            chunk_decoded = processor.decode(outputs, skip_special_tokens=True)
            decoded_texts.extend(normalize_decoded_texts(chunk_decoded))
            progress(f"Generating transcription: {chunk_index + 1}/{total_chunks} chunks completed...")

        progress("Decoding transcription text...")
        return finalize_transcription_text(processor, decoded_texts, audio_chunk_index, language)

    progress("Generating transcription...")
    outputs = model.generate(**inputs, max_new_tokens=max_new_tokens)
    progress("Decoding transcription text...")
    decode_kwargs: dict[str, Any] = {"skip_special_tokens": True}
    if audio_chunk_index is not None:
        decode_kwargs["audio_chunk_index"] = audio_chunk_index
        decode_kwargs["language"] = language

    decoded = processor.decode(outputs, **decode_kwargs)
    return finalize_transcription_text(processor, normalize_decoded_texts(decoded), audio_chunk_index, language)


def infer_batch_size(inputs: dict[str, Any]) -> int:
    for value in inputs.values():
        shape = getattr(value, "shape", None)
        if shape is not None and len(shape) > 0:
            return int(shape[0])
        if isinstance(value, list):
            return len(value)
    return 1


def slice_model_inputs(
    inputs: dict[str, Any],
    start: int,
    end: int,
    total_items: int,
) -> dict[str, Any]:
    sliced: dict[str, Any] = {}
    for key, value in inputs.items():
        shape = getattr(value, "shape", None)
        if key == "audio_chunk_index" and value is not None:
            sliced[key] = value[start:end]
        elif shape is not None and len(shape) > 0 and int(shape[0]) == total_items:
            sliced[key] = value[start:end]
        elif isinstance(value, list) and len(value) == total_items:
            sliced[key] = value[start:end]
        else:
            sliced[key] = value
    return sliced


def normalize_decoded_texts(decoded: Any) -> list[str]:
    if isinstance(decoded, str):
        return [decoded]
    if isinstance(decoded, list):
        return decoded
    return list(decoded)


def finalize_transcription_text(
    processor: Any,
    decoded_texts: list[str],
    audio_chunk_index: list[tuple[int, int | None]] | None,
    language: str,
) -> str:
    if audio_chunk_index is not None and hasattr(processor, "_reassemble_chunk_texts"):
        separator = "" if language in NO_SPACE_LANGUAGES else " "
        decoded_texts = processor._reassemble_chunk_texts(decoded_texts, audio_chunk_index, separator)

    return decoded_texts[0] if len(decoded_texts) == 1 else "\n".join(decoded_texts)


def transcribe_faster_whisper(
    *,
    audio_path: str,
    model: Any | None = None,
    whisper_model: str = DEFAULT_WHISPER_MODEL,
    device: str = DEFAULT_DEVICE,
    compute_type: str = DEFAULT_COMPUTE_TYPE,
    language: str = DEFAULT_LANGUAGE,
    progress: Callable[[str], None] | None = None,
) -> str:
    if progress is None:
        progress = lambda message: None

    if model is None:
        from faster_whisper import WhisperModel

        progress(f"Loading faster-whisper model: {whisper_model} on {device}...")
        model = WhisperModel(whisper_model, device=device, compute_type=compute_type)

    progress(f"Transcribing: {audio_path}...")
    segments, _info = model.transcribe(audio_path, language=language)
    texts = [segment.text for segment in segments]
    separator = "" if language in NO_SPACE_LANGUAGES else " "
    return separator.join(texts)


def build_faster_whisper_model(
    whisper_model: str = DEFAULT_WHISPER_MODEL,
    device: str = DEFAULT_DEVICE,
    compute_type: str = DEFAULT_COMPUTE_TYPE,
) -> Any:
    from faster_whisper import WhisperModel

    return WhisperModel(whisper_model, device=device, compute_type=compute_type)


def transcribe_mlx_whisper(
    *,
    audio_path: str,
    whisper_model: str = DEFAULT_WHISPER_MODEL,
    language: str = DEFAULT_LANGUAGE,
    progress: Callable[[str], None] | None = None,
) -> str:
    import json
    import subprocess

    if progress is None:
        progress = lambda message: None

    progress(f"Transcribing with mlx-whisper: {audio_path}...")
    script = (
        "import json, mlx_whisper\n"
        f"result = mlx_whisper.transcribe({audio_path!r}, "
        f"path_or_hf_repo={whisper_model!r}, language={language!r})\n"
        "print(json.dumps(result['text']))"
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(result.stdout)


def resolve_output_path(
    *,
    audio_path: str,
    output_path: str | None,
    cwd: Path | None = None,
) -> Path:
    base_dir = cwd or Path.cwd()

    if output_path is not None:
        candidate = Path(output_path).expanduser()
        return candidate if candidate.is_absolute() else base_dir / candidate

    candidate = Path(audio_path).expanduser()
    audio_file = candidate if candidate.is_absolute() else base_dir / candidate
    return audio_file.with_suffix(".txt")


def save_transcript(text: str, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(text)


def format_known_runtime_error(error: Exception) -> str | None:
    return None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the Cohere ASR demo transcription example.",
    )
    parser.add_argument(
        "audio_path",
        nargs="+",
        help="Audio/video files or directories to transcribe. Directories are scanned recursively.",
    )
    parser.add_argument(
        "--output-path",
        help=(
            "Where to save the transcript text. Only used with a single audio file. "
            "For multiple files, output defaults to each audio file stem with .txt."
        ),
    )
    parser.add_argument(
        "--backend",
        choices=sorted(BACKENDS),
        default=DEFAULT_BACKEND,
        help="Transcription backend to use.",
    )
    parser.add_argument("--model-dir", default=MODEL_DIR, help="Local model directory (cohere only).")
    parser.add_argument(
        "--language",
        default=DEFAULT_LANGUAGE,
        help="Language code passed to the processor.",
    )
    parser.add_argument(
        "--sampling-rate",
        type=int,
        default=DEFAULT_SAMPLING_RATE,
        help="Sampling rate for audio loading and preprocessing (cohere only).",
    )
    parser.add_argument(
        "--max-new-tokens",
        type=int,
        default=DEFAULT_MAX_NEW_TOKENS,
        help="Maximum number of generated tokens (cohere only).",
    )
    parser.add_argument(
        "--whisper-model",
        default=DEFAULT_WHISPER_MODEL,
        help="Whisper model name, e.g. large-v3 (faster-whisper / mlx-whisper).",
    )
    parser.add_argument(
        "--device",
        default=DEFAULT_DEVICE,
        help="Device for faster-whisper: auto, cuda, cpu.",
    )
    parser.add_argument(
        "--compute-type",
        default=DEFAULT_COMPUTE_TYPE,
        help="Compute type for faster-whisper: float16, int8, etc.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    def report_progress(message: str) -> None:
        print(message, file=sys.stderr)

    audio_files = collect_media_files(args.audio_path)
    if not audio_files:
        print("No media files found.", file=sys.stderr)
        return

    report_progress(f"Found {len(audio_files)} file(s) to process.")

    if args.backend == "cohere":
        if not Path(args.model_dir).is_dir():
            raise SystemExit(
                f"Model directory not found: {args.model_dir}\n"
                "Run `uv sync --extra download && uv run cohere-transcribe-download` first."
            )

        report_progress("Loading processor...")
        processor = build_processor(args.model_dir)
        report_progress("Loading model...")
        model = build_model(args.model_dir)

        for audio_path in audio_files:
            report_progress(f"\n--- Processing: {audio_path} ---")
            try:
                text = transcribe_demo(
                    processor=processor,
                    model=model,
                    audio_path=audio_path,
                    model_dir=args.model_dir,
                    sampling_rate=args.sampling_rate,
                    language=args.language,
                    max_new_tokens=args.max_new_tokens,
                    progress=report_progress,
                )
            except Exception as error:
                friendly_message = format_known_runtime_error(error)
                if friendly_message is not None:
                    print(friendly_message, file=sys.stderr)
                    continue
                raise

            output_path = resolve_output_path(
                audio_path=audio_path,
                output_path=args.output_path if len(audio_files) == 1 else None,
            )
            save_transcript(text, output_path)
            print(f"Saved transcript to {output_path}", file=sys.stderr)
            print(text)

    elif args.backend == "faster-whisper":
        report_progress(f"Loading faster-whisper model: {args.whisper_model}...")
        fw_model = build_faster_whisper_model(
            whisper_model=args.whisper_model,
            device=args.device,
            compute_type=args.compute_type,
        )

        for audio_path in audio_files:
            report_progress(f"\n--- Processing: {audio_path} ---")
            text = transcribe_faster_whisper(
                audio_path=audio_path,
                model=fw_model,
                language=args.language,
                progress=report_progress,
            )

            output_path = resolve_output_path(
                audio_path=audio_path,
                output_path=args.output_path if len(audio_files) == 1 else None,
            )
            save_transcript(text, output_path)
            print(f"Saved transcript to {output_path}", file=sys.stderr)
            print(text)

    elif args.backend == "mlx-whisper":
        for audio_path in audio_files:
            report_progress(f"\n--- Processing: {audio_path} ---")
            text = transcribe_mlx_whisper(
                audio_path=audio_path,
                whisper_model=args.whisper_model,
                language=args.language,
                progress=report_progress,
            )

            output_path = resolve_output_path(
                audio_path=audio_path,
                output_path=args.output_path if len(audio_files) == 1 else None,
            )
            save_transcript(text, output_path)
            print(f"Saved transcript to {output_path}", file=sys.stderr)
            print(text)


if __name__ == "__main__":
    main()

"""Download the Cohere ASR model to the local model/ directory."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

MODEL_ID = "CohereLabs/cohere-transcribe-03-2026"
DEFAULT_MODEL_DIR = str(Path(__file__).resolve().parent.parent.parent / "model")


def download_model(
    *,
    repo_id: str = MODEL_ID,
    model_dir: str = DEFAULT_MODEL_DIR,
    progress: callable = None,
) -> Path:
    from huggingface_hub import snapshot_download

    if progress is None:
        progress = lambda msg: None

    dest = Path(model_dir)
    dest.mkdir(parents=True, exist_ok=True)

    progress(f"Downloading {repo_id} to {dest} ...")
    snapshot_download(
        repo_id=repo_id,
        local_dir=str(dest),
    )
    progress("Download complete.")
    return dest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download the Cohere ASR model to a local directory.",
    )
    parser.add_argument(
        "--repo-id",
        default=MODEL_ID,
        help=f"HuggingFace model repository (default: {MODEL_ID}).",
    )
    parser.add_argument(
        "--model-dir",
        default=DEFAULT_MODEL_DIR,
        help=f"Local directory to save the model (default: model/).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    def report(msg: str) -> None:
        print(msg, file=sys.stderr)

    try:
        dest = download_model(
            repo_id=args.repo_id,
            model_dir=args.model_dir,
            progress=report,
        )
        print(f"Model saved to {dest}", file=sys.stderr)
    except Exception as e:
        msg = str(e).lower()
        if "gated repo" in msg or "access is restricted" in msg:
            raise SystemExit(
                f"Access to {args.repo_id} is gated. "
                "Run `hf auth login` with an approved account, then try again."
            ) from e
        raise


if __name__ == "__main__":
    main()

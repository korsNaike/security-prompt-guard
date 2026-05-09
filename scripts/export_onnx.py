from __future__ import annotations

import argparse
from pathlib import Path


def export_onnx(model_id_or_path: str, output_dir: Path) -> None:
    try:
        from optimum.exporters.onnx import main_export
    except ImportError as exc:
        raise RuntimeError(
            "ONNX export requires optional dependency `optimum[onnxruntime]`."
        ) from exc

    output_dir.mkdir(parents=True, exist_ok=True)
    main_export(
        model_name_or_path=model_id_or_path,
        output=output_dir,
        task="text-classification",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Export a text classification model to ONNX.")
    parser.add_argument("--model-id-or-path", required=True)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()

    export_onnx(args.model_id_or_path, args.output_dir)


if __name__ == "__main__":
    main()

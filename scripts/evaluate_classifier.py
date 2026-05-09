from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from app.domain.ml.classifier_contracts import ClassificationInput
from app.infrastructure.ml.loader import model_registry


def evaluate_jsonl(path: Path, *, model_code: str, mode: str) -> dict:
    classifier = model_registry.get(model_code)
    total = 0
    correct = 0
    invalid_rows = 0
    expected_counts: Counter[str] = Counter()
    predicted_counts: Counter[str] = Counter()

    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
            text = str(row["text"])
            expected_label = str(row["label"])
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            invalid_rows += 1
            continue

        output = classifier.predict(
            ClassificationInput(text=text, model_code=model_code, mode=mode)
        )
        total += 1
        expected_counts[expected_label] += 1
        predicted_counts[output.label] += 1
        if output.label == expected_label:
            correct += 1

    accuracy = correct / total if total else 0.0
    return {
        "model_code": model_code,
        "mode": mode,
        "total": total,
        "correct": correct,
        "accuracy": accuracy,
        "invalid_rows": invalid_rows,
        "expected_counts": dict(expected_counts),
        "predicted_counts": dict(predicted_counts),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate a registered classifier on JSONL data.")
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--model-code", required=True)
    parser.add_argument("--mode", required=True)
    args = parser.parse_args()

    print(
        json.dumps(
            evaluate_jsonl(args.input, model_code=args.model_code, mode=args.mode),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

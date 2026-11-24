"""Render WordSpeak experiment figures from measured CSV rows."""

import argparse
import csv
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

from matplotlib import pyplot as plt

METRICS = {
    "per": ("Tỷ lệ lỗi âm vị", "Tỷ lệ (%)", 0.0, 100.0),
    "wer": ("Tỷ lệ lỗi từ", "Tỷ lệ (%)", 0.0, 100.0),
    "gop_correlation": ("Tương quan GOP với đánh giá tham chiếu", "Hệ số tương quan", -1.0, 1.0),
    "latency_ms": ("Độ trễ xử lý", "Mili giây", 0.0, math.inf),
}


def load_metrics(files: list[Path]) -> dict[str, list[tuple[str, float]]]:
    metrics: dict[str, list[tuple[str, float]]] = {key: [] for key in METRICS}
    for path in files:
        with path.open(encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            columns = set(reader.fieldnames or ())
            if not (columns & METRICS.keys()):
                continue
            for number, row in enumerate(reader, start=2):
                label = (row.get("label") or row.get("model") or f"{path.stem} {number - 1}").strip()
                for key, (_, _, low, high) in METRICS.items():
                    value = row.get(key)
                    if value is None or not value.strip():
                        continue
                    try:
                        measured = float(value)
                    except ValueError as exc:
                        raise ValueError(f"{path}:{number} có {key} không phải số.") from exc
                    if not math.isfinite(measured) or not low <= measured <= high:
                        raise ValueError(f"{path}:{number} có {key} ngoài phạm vi cho phép.")
                    metrics[key].append((label, measured))
    return metrics


def render(metrics: dict[str, list[tuple[str, float]]], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    for key, rows in metrics.items():
        if not rows:
            print(f"{key}: chưa có dữ liệu")
            continue
        names, values = zip(*rows)
        title, unit, low, high = METRICS[key]
        fig, ax = plt.subplots(figsize=(9, max(3.5, 1.6 + len(rows) * 0.42)), layout="constrained")
        ax.barh(range(len(rows)), values, color="#5744dc", height=0.65)
        ax.set_yticks(range(len(rows)), names)
        ax.invert_yaxis()
        ax.set_title(title, loc="left", fontweight="bold")
        ax.set_xlabel(unit)
        if math.isfinite(high):
            ax.set_xlim(low, high)
        ax.grid(axis="x", alpha=0.24)
        ax.set_axisbelow(True)
        for suffix in ("png", "pdf"):
            fig.savefig(output / f"{key}.{suffix}", dpi=180)
        plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("results"), help="Thư mục CSV")
    parser.add_argument("--output", type=Path, default=Path("docs/figures"), help="Thư mục biểu đồ")
    args = parser.parse_args()
    try:
        metrics = load_metrics(sorted(args.input.glob("*.csv")))
        if not any(metrics.values()):
            parser.error("Chưa có CSV với số liệu PER, WER, tương quan GOP hoặc độ trễ.")
        render(metrics, args.output)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()

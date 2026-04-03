"""Scoring and score-history tracking for the self-improvement loop."""

from __future__ import annotations

import csv
import time
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class TaskScorer:
    """Compute aggregate scores from a list of task result dicts.

    Each result dict is expected to contain at least:
        - name: str
        - passed: bool
        - score: float   (0.0 – 1.0)
        - output: str
    """

    def aggregate(self, results: list[dict]) -> float:
        """Return the arithmetic mean of individual task scores."""
        if not results:
            return 0.0
        return sum(r["score"] for r in results) / len(results)

    @staticmethod
    def should_keep(old_score: float, new_score: float, change_size: int) -> bool:
        """Decide whether an experiment's changes should be kept.

        Rules
        -----
        - If the new score is strictly better → keep.
        - If the scores are equal *and* the change touched fewer than 3 files → keep
          (simpler is better).
        - Otherwise → discard.
        """
        if new_score > old_score:
            return True
        if new_score == old_score and change_size < 3:
            return True
        return False


_TSV_COLUMNS = ["timestamp", "commit", "avg_score", "passed", "total", "status", "description"]


@dataclass
class ScoreHistory:
    """Append-only TSV log of experiment results."""

    results_path: Path = field(default_factory=lambda: Path("results.tsv"))

    def _ensure_header(self) -> None:
        """Write the header row if the file does not exist yet."""
        if not self.results_path.exists():
            self.results_path.parent.mkdir(parents=True, exist_ok=True)
            with self.results_path.open("w", newline="") as fh:
                writer = csv.writer(fh, delimiter="\t")
                writer.writerow(_TSV_COLUMNS)

    def append(
        self,
        *,
        commit: str,
        avg_score: float,
        passed: int,
        total: int,
        status: str,
        description: str,
    ) -> None:
        """Append a single result row."""
        self._ensure_header()
        with self.results_path.open("a", newline="") as fh:
            writer = csv.writer(fh, delimiter="\t")
            writer.writerow(
                [
                    time.strftime("%Y-%m-%dT%H:%M:%S"),
                    commit,
                    f"{avg_score:.4f}",
                    str(passed),
                    str(total),
                    status,
                    description,
                ]
            )

    def read_entries(self) -> list[dict]:
        """Return all rows as a list of dicts keyed by column name."""
        if not self.results_path.exists():
            return []
        with self.results_path.open(newline="") as fh:
            reader = csv.DictReader(fh, delimiter="\t")
            return list(reader)

    def latest_score(self) -> float | None:
        """Return the most recent average score, or *None* if empty."""
        entries = self.read_entries()
        if not entries:
            return None
        return float(entries[-1]["avg_score"])

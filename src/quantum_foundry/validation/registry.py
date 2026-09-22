"""BenchmarkRegistry: loads BenchmarkEntry objects from benchmarks/*.yaml and
matches simulated results to them by quantity AND conditions — not name
alone, since e.g. two different contact-resistance benchmarks exist under
different contact conditions (UHV Ni vs. edge-contact) and must not be
conflated by a naive name-only lookup.
"""
from __future__ import annotations

from pathlib import Path

import yaml

from .schema import BenchmarkEntry, Citation, ExperimentalValue, SimulatedValue

_BENCHMARKS_DIR = Path(__file__).parent / "benchmarks"


def _entry_from_dict(data: dict) -> BenchmarkEntry:
    exp_data = data["experimental"]
    citation = Citation(**exp_data["citation"])
    experimental = ExperimentalValue(
        quantity=exp_data["quantity"],
        value=exp_data["value"],
        unit=exp_data["unit"],
        citation=citation,
        uncertainty=exp_data.get("uncertainty"),
        conditions=exp_data.get("conditions", {}),
    )
    return BenchmarkEntry(id=data["id"], experimental=experimental)


class BenchmarkRegistry:
    def __init__(self, benchmarks_dir: Path | None = None):
        self._dir = benchmarks_dir or _BENCHMARKS_DIR
        self._entries: dict[str, BenchmarkEntry] = {}
        self._load_all()

    def _load_all(self) -> None:
        if not self._dir.exists():
            return
        for path in sorted(self._dir.glob("*.yaml")):
            with path.open() as f:
                data = yaml.safe_load(f)
            entry = _entry_from_dict(data)
            self._entries[entry.id] = entry

    def all_entries(self) -> list[BenchmarkEntry]:
        return list(self._entries.values())

    def get(self, benchmark_id: str) -> BenchmarkEntry:
        return self._entries[benchmark_id]

    def attach_simulated(self, simulated: SimulatedValue) -> list[BenchmarkEntry]:
        """Attach `simulated` to every benchmark whose quantity AND conditions
        match — a subset match (simulated.conditions is a subset of the
        benchmark's conditions) counts as a match, since a simulation run
        may not report every condition a benchmark's real measurement noted.
        Returns the list of entries updated (usually 0 or 1; could be more if
        conditions are too loose to disambiguate — that's a real signal to
        tighten `conditions`, not silently pick one).
        """
        matched = []
        for entry in self._entries.values():
            if entry.experimental.quantity != simulated.quantity:
                continue
            if not _conditions_match(simulated.conditions, entry.experimental.conditions):
                continue
            entry.simulated = simulated
            matched.append(entry)
        return matched


def _conditions_match(simulated_conditions: dict, benchmark_conditions: dict) -> bool:
    return all(
        benchmark_conditions.get(key) == value for key, value in simulated_conditions.items()
    )

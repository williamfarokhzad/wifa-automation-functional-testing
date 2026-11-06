"""Evaluate one recorded start request. Reads files only; no machine I/O."""

import argparse
import csv
import sys
from dataclasses import dataclass
from pathlib import Path

STEP_MS = 20
DEADLINE_MS = 100
WINDOW_MS = 160
COLUMNS = ("time_ms", "start", "ready", "ack")
EXIT = {"PASS": 0, "FAIL": 1, "INCONCLUSIVE": 3}


@dataclass(frozen=True)
class Sample:
    time_ms: int
    start: int
    ready: int
    ack: int


@dataclass(frozen=True)
class Verdict:
    requirement: str
    status: str
    evidence: str


def read_trace(path: Path) -> list[Sample]:
    with path.open(encoding="utf-8-sig", newline="") as file:
        reader = csv.reader(file, strict=True)
        if tuple(next(reader, [])) != COLUMNS:
            raise ValueError("header must be time_ms,start,ready,ack")
        samples = []
        for row in reader:
            if len(row) != 4:
                raise ValueError(f"line {reader.line_num}: expected four columns")
            time, *bits = row
            if not time.isascii() or not time.isdigit() or any(b not in ("0", "1") for b in bits):
                raise ValueError(f"line {reader.line_num}: use integer milliseconds and 0/1 bits")
            sample = Sample(int(time), *map(int, bits))
            if samples and sample.time_ms <= samples[-1].time_ms:
                raise ValueError(f"line {reader.line_num}: timestamps must strictly increase")
            samples.append(sample)
        return samples


def evaluate(samples: list[Sample], scenario: str) -> Verdict:
    if scenario not in {"ready", "blocked"}:
        raise ValueError("scenario must be ready or blocked")
    requirement = "FT-01" if scenario == "ready" else "FT-02"
    expected_ready = int(scenario == "ready")

    def verdict(status: str, evidence: str) -> Verdict:
        return Verdict(requirement, status, evidence)

    if not samples or samples[0].start != 0:
        return verdict("INCONCLUSIVE", "no baseline with start=0")
    edges = [i for i, (a, b) in enumerate(zip(samples, samples[1:]), 1) if not a.start and b.start]
    if not edges:
        return verdict("INCONCLUSIVE", "no recorded start rising edge")
    edge = samples[edges[0]].time_ms
    first = edge - STEP_MS
    last = edge + WINDOW_MS
    window = [s for s in samples if first <= s.time_ms <= last]
    for expected, observed in zip(range(first, last + STEP_MS, STEP_MS), window):
        if observed.time_ms != expected:
            return verdict("INCONCLUSIVE", f"expected sample at {expected} ms; saw {observed.time_ms} ms")
    if len(window) != WINDOW_MS // STEP_MS + 2:
        return verdict("INCONCLUSIVE", f"expected complete capture through {last} ms")
    if any(samples[i].time_ms <= last for i in edges[1:]):
        return verdict("INCONCLUSIVE", "multiple start requests in one test window")
    if any(s.ready != expected_ready for s in window):
        return verdict("INCONCLUSIVE", f"fixture requires ready={expected_ready} throughout the test window")
    if window[0].ack:
        return verdict("INCONCLUSIVE", "ack already high at the baseline")
    first_ack = next((s.time_ms for s in window[1:] if s.ack), None)
    if scenario == "blocked":
        if first_ack is not None:
            return verdict("FAIL", f"unexpected ack at +{first_ack-edge} ms")
        return verdict("PASS", "ack low at every sample through +160 ms")
    if first_ack is None:
        return verdict("FAIL", "no ack observed through +160 ms")
    elapsed = first_ack - edge
    if elapsed > DEADLINE_MS:
        return verdict("FAIL", f"first ack at +{elapsed} ms exceeds +100 ms deadline")
    return verdict("PASS", f"first ack at +{elapsed} ms meets +100 ms deadline")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scenario", choices=("ready", "blocked"))
    parser.add_argument("trace", type=Path)
    args = parser.parse_args(argv)
    try:
        result = evaluate(read_trace(args.trace), args.scenario)
    except (OSError, ValueError, csv.Error) as exc:
        print(f"Input error: {exc}", file=sys.stderr)
        return 2
    print(f"{result.requirement} {result.status}: {result.evidence}")
    return EXIT[result.status]


if __name__ == "__main__":
    raise SystemExit(main())

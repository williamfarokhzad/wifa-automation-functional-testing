# Automation Functional Testing: Audit a Start Response

Use this Python lab to replay synthetic start requests against two written functional requirements. It reads CSV files and never connects to a PLC, drive or network. The full lesson is at [WIFA Robotics](https://wifarobotics.com/learn/automation-functional-testing/).

## Start from zero

1. Install [Python 3.10 or later](https://www.python.org/downloads/).
2. Download this repository using **Code → Download ZIP**. Extract it. Open a terminal in the folder containing `functional_test.py`.
3. Check `python3 --version`. On Windows use `py -3 --version` and replace `python3` with `py -3` below. There is no pip installation.

```sh
python3 functional_test.py ready examples/ready-on-time.csv
python3 functional_test.py ready examples/ready-late.csv
python3 functional_test.py blocked examples/blocked-quiet.csv
python3 functional_test.py blocked examples/blocked-unexpected.csv
python3 functional_test.py ready examples/ready-gap.csv
python3 -m unittest discover -s tests -v
```

| Case | Expected result | Exit code |
| --- | --- | --- |
| Ready, boundary | `FT-01 PASS: first ack at +100 ms meets +100 ms deadline` | 0 |
| Ready, late | `FT-01 FAIL: first ack at +120 ms exceeds +100 ms deadline` | 1 |
| Blocked, quiet | `FT-02 PASS: ack low at every sample through +160 ms` | 0 |
| Blocked, unexpected ACK | `FT-02 FAIL: unexpected ack at +40 ms` | 1 |
| Ready, missing row | `FT-01 INCONCLUSIVE: expected sample at 100 ms; saw 120 ms` | 3 |

Exit 2 means the file or invocation could not be read as specified. Negative examples are deliberate. Run each command separately if your shell stops on errors.

## What the replay checks

The file has `time_ms,start,ready,ack` columns. Time is nonnegative integer milliseconds, strictly increasing. The other columns are literal bits. The observation is scoped to one baseline sample, 20 ms before the first rising start edge, and every 20 ms through 160 ms after that edge. The baseline ACK must be low and the requested ready condition must hold through the window. A second rising start edge in that window invalidates the evidence.

- **FT-01**, ready: at least one sampled high ACK by 100 ms after the observed start edge, inclusive.
- **FT-02**, blocked: no sampled high ACK from the observed start edge through 160 ms, inclusive.

Try copying `blocked-quiet.csv` and changing only its final ACK bit to 1. Expect `FT-02 FAIL` at +160 ms. Then remove that final row and rerun. The new result is `INCONCLUSIVE` because the observation ends early.

## Files and common mistakes

- `functional_test.py` parses samples and evaluates the contract. `examples/` contains five independent traces and `tests/` checks deadlines, fixture validity, missing evidence and file handling.
- `diagrams/` contains editable SVGs, matching WebP exports and their render script. Rebuilding images is optional and requires Inkscape and Pillow.
- If Python cannot open the script, move into the extracted folder. If a spreadsheet changes the header or separator, use a plain text editor and keep the four comma separated columns. If the fixture verdict is inconclusive, verify the timestamps, baseline ACK and ready bit before changing the requirement.

The signals are invented. An ACK is a logical response here, not proof that a motor moved. The lab measures sampled times only and cannot see pulses between samples. It does not test a safety circuit, equipment commissioning or production acceptance. For an actual test, document the signal source, clock, sample spacing, delay tolerance and authorized test setup.

References: [NASA requirements verification matrix](https://www.nasa.gov/reference/appendix-d-requirements-verification-matrix/) and [Python CSV documentation](https://docs.python.org/3.12/library/csv.html).

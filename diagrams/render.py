"""Rebuild original editable SVG and optimized WebP teaching figures.

Requires Inkscape on PATH and Pillow for rendering only. The lab needs neither.
"""
from pathlib import Path
import subprocess
import tempfile

from PIL import Image

ROOT = Path(__file__).resolve().parent
WIDTH, HEIGHT = 1000, 520
BG, INK, MUTED = "#f1f8f7", "#132e38", "#385760"
TEAL, ORANGE, RED = "#006d68", "#985000", "#9b293c"


def label(x, y, text, size=26, color=INK, bold=False, anchor="start"):
    weight = ' font-weight="700"' if bold else ""
    return (f'<text x="{x}" y="{y}" fill="{color}" text-anchor="{anchor}"'
            f' font-size="{size}"{weight}>{text}</text>')


def line(x1, y1, x2, y2, color=MUTED, width=3, dashed=False):
    dash = ' stroke-dasharray="8 7"' if dashed else ""
    return f'<path d="M{x1} {y1} L{x2} {y2}" fill="none" stroke="{color}" stroke-width="{width}"{dash}/>'


def circle(x, y, color, r=8):
    return f'<circle cx="{x}" cy="{y}" r="{r}" fill="{color}"/>'


def wrap(title, elements):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}"'
            f' viewBox="0 0 {WIDTH} {HEIGHT}" role="img"><title>{title}</title>'
            f'<rect width="{WIDTH}" height="{HEIGHT}" rx="24" fill="{BG}"/>'
            '<g font-family="DejaVu Sans, sans-serif">' + "".join(elements) + '</g></svg>\n')


def timeline():
    x = lambda t: 265 + 4*t
    a = [label(42, 63, "A 100 ms start response", 41, bold=True),
         label(43, 109, "FT-01  |  ready stays 1  |  one sample every 20 ms", 23, MUTED),
         line(x(100), 145, x(100), 178, ORANGE, 3, True),
         line(x(100), 210, x(100), 284, ORANGE, 3, True),
         line(x(100), 320, x(100), 400, ORANGE, 3, True),
         label(x(100), 139, "deadline", 22, ORANGE, True, "middle"),
         line(x(0), 413, x(160), 413, MUTED, 2)]
    for t in range(0, 161, 20):
        a += [line(x(t), 407, x(t), 419, MUTED, 2),
              label(x(t), 451, f"+{t}", 19, MUTED, anchor="middle")]
    for y, name, first, color in [(225, "On time", 100, TEAL), (333, "Late", 120, RED)]:
        a += [label(44, y+7, name, 29, color, True),
              line(x(0), y, x(160), y, "#afc5c9", 2)]
        for t in range(0, 161, 20):
            a.append(circle(x(t), y, color if t >= first else "#78949a", 10 if t == first else 5))
        a.append(label(x(first), y-22, f"first ACK +{first}", 19, color, True, "middle"))
    a.append(label(43, 490, "Time after recorded start (ms). A large dot marks the first sampled high.", 22, MUTED))
    return wrap("First acknowledgement at the deadline versus one sample late", a)


def missing():
    x = lambda t: 170 + 4.4*t
    a = [label(42, 63, "A gap is not a zero", 41, bold=True),
         label(43, 109, "FT-01  |  compare two CSV traces on the same clock", 23, MUTED)]
    for y, name, gap in [(209, "Complete capture: PASS", False),
                         (355, "Missing +80 ms: INCONCLUSIVE", True)]:
        a += [label(43, y-40, name, 25, ORANGE if gap else TEAL, True),
              line(x(0), y, x(160), y, "#afc5c9", 2)]
        for t in range(0, 161, 20):
            if gap and t == 80:
                a.append(f'<circle cx="{x(t)}" cy="{y}" r="12" fill="{BG}" stroke="{ORANGE}" stroke-width="4"/>')
            else:
                a.append(circle(x(t), y, TEAL if t >= 100 else "#78949a", 9 if t == 100 else 6))
            a.append(label(x(t), y+39, f"+{t}", 18, MUTED, anchor="middle"))
    a += [label(43, 467, "The first visible high is +100 ms in both traces.", 24, INK),
          label(43, 499, "A missing row breaks the required sampling grid.", 22, MUTED)]
    return wrap("A missing sample makes an otherwise similar trace inconclusive", a)


def main():
    for name, make in [("functional-testing-deadline", timeline), ("functional-testing-gap", missing)]:
        source = ROOT / (name + ".svg")
        source.write_text(make(), encoding="utf-8")
        with tempfile.TemporaryDirectory() as tmp:
            png = Path(tmp) / "figure.png"
            subprocess.run(["inkscape", str(source), f"--export-filename={png}"], check=True)
            with Image.open(png) as image:
                full = image.convert("RGB")
                full.save(ROOT / (name + ".webp"), quality=84, method=6)
                full.resize((600, 312), Image.Resampling.LANCZOS).save(
                    ROOT / (name + "-600.webp"), quality=84, method=6)


if __name__ == "__main__":
    main()

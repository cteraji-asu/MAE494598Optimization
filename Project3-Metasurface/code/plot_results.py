"""Export static diagnostic plots with the already-installed Pillow package.

Training, solving and tests use only the standard library. These figures are
optional and are regenerated from retained CSV data, not embedded measurements.
"""
import csv
import math
import os
import statistics
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "outputs" / "pilot"
OUT = ROOT / "outputs" / "figures"
COLORS = ["#235da8", "#bd4c27", "#20836c", "#8c55a2"]


def portable_font(size, candidates=None):
    """Use available system fonts, then Pillow's embedded scalable default."""
    if candidates is None:
        candidates = [str(Path(os.environ.get("WINDIR", "C:/Windows"))/"Fonts/arial.ttf"),
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
            "/System/Library/Fonts/Helvetica.ttc", "DejaVuSans.ttf"]
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate,size)
        except OSError:
            pass
    return ImageFont.load_default(size=size)


def read(name):
    with (DATA / name).open(newline="", encoding="utf-8") as f:
        return [{k: float(v) if k != "mode" else v for k, v in row.items()}
                for row in csv.DictReader(f)]


def plot(name, title, subtitle, xlabel, ylabel, series, log_y=False, xlim=None, errorbars=None, vlines=None):
    image = Image.new("RGB", (1500, 950), "white")
    draw = ImageDraw.Draw(image)
    fonts = [portable_font(n) for n in (24, 30, 38)]
    small, normal, large = fonts
    title_font = large
    size = 38
    while draw.textbbox((0,0), title, font=title_font)[2] > 1280:
        size -= 1
        title_font = portable_font(size)
    subtitle_font = small
    size = 24
    while draw.textbbox((0,0), subtitle, font=subtitle_font)[2] > 1280:
        size -= 1
        subtitle_font = portable_font(size)
    draw.text((110, 40), title, fill="#18232e", font=title_font)
    draw.text((110, 98), subtitle, fill="#48535e", font=subtitle_font)
    left, right, top, bottom = 150, 1400, 200, 760
    values = [(x, y) for _, pairs in series for x, y in pairs if math.isfinite(y)]
    xmin, xmax = xlim or (min(x for x, _ in values), max(x for x, _ in values))
    visible = [y for x, y in values if xmin <= x <= xmax]
    for bars in (errorbars or []):
        visible.extend(v for x,low,high in bars for v in (low,high))
    transform = (lambda y: math.log10(max(y, 1e-12))) if log_y else (lambda y:y)
    ymin, ymax = min(map(transform, visible)), max(map(transform, visible))
    if log_y:
        ymin, ymax = math.floor(ymin), math.ceil(ymax)
    else:
        margin = max((ymax-ymin)*0.08, 1e-5)
        ymin, ymax = ymin-margin, ymax+margin
        if min(visible) >= 0:
            ymin = max(0, ymin)
    if ymax == ymin:
        ymax += 1
    def xy(x, y):
        return (left+(x-xmin)/(xmax-xmin)*(right-left),
                bottom-(transform(y)-ymin)/(ymax-ymin)*(bottom-top))
    yticks = list(range(int(ymin), int(ymax)+1)) if log_y else [ymin+j/5*(ymax-ymin) for j in range(6)]
    for value in yticks:
        py = bottom-(value-ymin)/(ymax-ymin)*(bottom-top)
        draw.line((left, py, right, py), fill="#e3e6eb", width=2)
        label = f"10^{value:g}" if log_y else f"{value:.3g}"
        draw.text((left-15, py), label, fill="#26333f", font=small, anchor="rm")
    xticks = [xmin+j/5*(xmax-xmin) for j in range(6)]
    if name == "error-vs-k.png":
        xticks = [1,5,10,20]
    elif name == "baseline-refinement.png":
        xticks = [128,256,512,1024]
    elif name.startswith("reflection-"):
        xticks = [0,1,2]
    for value in xticks:
        px = left+(value-xmin)/(xmax-xmin)*(right-left)
        draw.text((px, bottom+18), f"{value:g}",
                  fill="#26333f", font=small, anchor="mt")
    draw.line((left, top, left, bottom, right, bottom), fill="#26333f", width=3)
    draw.text((left, top-48), ylabel, fill="#26333f", font=normal)
    draw.text(((left+right)/2, bottom+68), xlabel, fill="#26333f", font=normal, anchor="mt")
    for index,bars in enumerate(errorbars or []):
        color=COLORS[index%len(COLORS)]
        for x,low,high in bars:
            px,py=xy(x,low)
            _,qy=xy(x,high)
            draw.line((px,py,px,qy),fill=color,width=3)
            draw.line((px-8,py,px+8,py),fill=color,width=3)
            draw.line((px-8,qy,px+8,qy),fill=color,width=3)
    for value,label in (vlines or []):
        px=xy(value,1)[0]
        for y in range(top,bottom,16):
            draw.line((px,y,px,min(y+8,bottom)),fill="#737d87",width=2)
        draw.text((px+10,top+12),label,font=small,fill="#59636e")
    for index, (label, pairs) in enumerate(series):
        color = COLORS[index % len(COLORS)]
        coordinates = [xy(x, y) for x, y in pairs if xmin <= x <= xmax and math.isfinite(y)]
        if len(coordinates) > 1:
            draw.line(coordinates, fill=color, width=4)
        if len(coordinates) <= 10:
            for x, y in coordinates:
                draw.ellipse((x-6,y-6,x+6,y+6),fill=color)
        lx, ly = 150+(index % 2)*635, 860+(index // 2)*40
        draw.line((lx, ly+12, lx+42, ly+12), fill=color, width=5)
        draw.text((lx+55, ly), label, fill="#26333f", font=small)
    OUT.mkdir(parents=True, exist_ok=True)
    image.save(OUT / name)


def main():
    summary = read("summary.csv")
    curves = []
    errorbars=[]
    for mode in ("pinn", "supervised"):
        data = []
        for k in sorted({r["k"] for r in summary}):
            data.append((k, statistics.median(r["relative_l2_exact"] for r in summary
                                              if r["mode"] == mode and r["k"] == k)))
        curves.append((mode+", median of 3 seeds", data))
        errorbars.append([(k,min(r["relative_l2_exact"] for r in summary if r["mode"]==mode and r["k"]==k),
                            max(r["relative_l2_exact"] for r in summary if r["mode"]==mode and r["k"]==k))
                           for k in sorted({r["k"] for r in summary})])
    plot("error-vs-k.png", "Field error grows with dimensionless wavenumber",
         "Median with min/max seed whiskers, 3,000 updates, 24 tanh units; seeds 0/1/2",
         "Dimensionless wavenumber k", "Relative complex-field L2 error", curves, True,errorbars=errorbars)
    history = read("k-10_seed-0_pinn_loss.csv")
    plot("loss-k10.png", "The PINN objective contains separate constraints",
         "k=10, seed 0; normalized residuals; initial/data losses are inapplicable",
         "Adam updates", "Mean squared residual, logarithmic scale",
         [(key, [(r["step"],r[key]) for r in history])
          for key in ("pde", "dirichlet", "outgoing")], True)
    fields = {mode:read(f"k-10_seed-0_{mode}_field.csv") for mode in ("pinn", "supervised")}
    plot("field-k10.png", "Both learned fields can be compared with a known answer",
         "k=10, seed 0; real component; exact solution exp(ikx)",
         "Dimensionless position x", "Real field amplitude",
         [("Exact", [(r["x"],r["exact_real"]) for r in fields["pinn"]])] +
         [(mode, [(r["x"],r["predicted_real"]) for r in rows]) for mode, rows in fields.items()])
    plot("pointwise-error-k10.png", "Stationary field error, no time axis",
         "k=10, seed 0; absolute complex error |prediction - exp(ikx)|",
         "Dimensionless position x", "Absolute complex-field error",
         [(mode, [(r["x"],r["abs_error"]) for r in rows]) for mode, rows in fields.items()])
    plot("imaginary-field-k10.png", "The imaginary component carries phase information",
         "k=10, seed 0; exact imaginary component sin(kx)",
         "Dimensionless position x", "Imaginary field amplitude",
         [("Exact",[(r["x"],r["exact_imag"]) for r in fields["pinn"]])]+
         [(mode,[(r["x"],r["predicted_imag"]) for r in rows]) for mode,rows in fields.items()])
    plot("error-spectrum-k10.png", "Complex error spectrum retains signed frequencies",
         "k=10, seed 0; 256 points, no duplicate endpoint; nonperiodic error can cause leakage",
         "Cycles per unit domain", "DFT amplitude / 256, logarithmic scale",
         [(mode, sorted([(r["cycles_per_domain"],r["amplitude"]) for r in
                        read(f"k-10_seed-0_{mode}_spectrum.csv")]))
          for mode in ("pinn", "supervised")], True, (-20, 20))
    baseline = read("baseline-refinement.csv")
    plot("baseline-refinement.png", "Conventional baseline converges under refinement",
         "Centered differences with outgoing ghost-point boundary; compared to exp(ikx)",
         "Number of grid intervals", "Relative complex-field L2 error",
         [(f"k={k:g}", [(r["intervals"],r["relative_l2"]) for r in baseline if r["k"] == k])
          for k in sorted({r["k"] for r in baseline})], True)
    print(f"Wrote seven pilot figures to {OUT}")


if __name__ == "__main__":
    main()

"""Synthetic finite-switch transmission-line analogue, not a real device's device.

Phasors use exp(+i omega t). Z0=1; gamma=alpha+i*2*pi, so all lengths
are in the reference wavelength. V_x=-gamma I, I_x=-gamma V on each
segment. A finite series impedance imposes current continuity and a
voltage jump. The short at the far end is identical in both states.
No reflection phase target appears in these equations.
"""
from dataclasses import dataclass
import cmath
import csv
import json
import math
from pathlib import Path
import statistics
import time


@dataclass(frozen=True)
class Config:
    alpha: float = 0.03
    beta: float = 2 * math.pi
    z_on: complex = 0.02 + 0.04j
    z_off: complex = 0.02 - 4j

    @property
    def gamma(self):
        return complex(self.alpha, self.beta)

    def impedance(self, state):
        if state not in (0, 1):
            raise ValueError("state must be 0 (on) or 1 (off)")
        return (self.z_on, self.z_off)[state]


def multiply(a, b):
    return (a[0]*b[0]+a[1]*b[2], a[0]*b[1]+a[1]*b[3],
            a[2]*b[0]+a[3]*b[2], a[2]*b[1]+a[3]*b[3])


def propagation(length, gamma, intervals=None):
    """Backward ABCD matrix. Optional trapezoidal spatial discretization."""
    if intervals is None:
        c, s = cmath.cosh(gamma*length), cmath.sinh(gamma*length)
        return c, s, s, c
    if intervals < 1:
        raise ValueError("intervals must be positive")
    q = gamma*length/(2*intervals)
    c, s = (1+q*q)/(1-q*q), 2*q/(1-q*q)
    step, result = (c, s, s, c), (1, 0, 0, 1)
    for _ in range(intervals):
        result = multiply(result, step)
    return result


def response(length, fraction, state, config=Config(), intervals=None):
    """ABCD cascade; reflection and terminal current for unit incident V."""
    if length <= 0 or not 0 < fraction < 1:
        raise ValueError("Require length>0 and switch fraction strictly inside line")
    a, d = fraction*length, (1-fraction)*length
    z = config.impedance(state)
    matrix = multiply(multiply(propagation(a, config.gamma, intervals),
                               (1, z, 0, 1)),
                      propagation(d, config.gamma, intervals))
    b, denominator_d = matrix[1], matrix[3]
    reflection = (b-denominator_d)/(b+denominator_d)
    terminal_current = 2/(b+denominator_d)
    return reflection, terminal_current


def wave_reference(length, fraction, state, config=Config()):
    """Independent 3x3 solve for reflected and right-segment wave amplitudes.

    Does not call response, multiply, or propagation. Uses continuity,
    the switch jump, and the common short directly.
    """
    import numpy as np
    a, d = length*fraction, length*(1-fraction)
    e, f = cmath.exp(config.gamma*a), cmath.exp(config.gamma*d)
    z = config.impedance(state)
    matrix = np.array([[0, 1/f, f], [-e, -1, 1],
                       [e, -(1+z), z-1]], dtype=complex)
    rhs = np.array([0, -1/e, -1/e], dtype=complex)
    return np.linalg.solve(matrix, rhs)


def field(local, segment, length, fraction, state, config=Config()):
    """V,I on each segment, with local in [0,1]; the interface has two sides."""
    r, terminal_current = response(length, fraction, state, config)
    if segment == 0:
        x = local*length*fraction
        forward, backward = cmath.exp(-config.gamma*x), r*cmath.exp(config.gamma*x)
        return forward+backward, forward-backward
    if segment == 1:
        remaining = (1-local)*length*(1-fraction)
        return (terminal_current*cmath.sinh(config.gamma*remaining),
                terminal_current*cmath.cosh(config.gamma*remaining))
    raise ValueError("segment must be 0 or 1")


def phase_metrics(on, off, phase_floor=0.05):
    """Circular separation 0..180 deg and distance from pi; mask weak signals."""
    minimum = min(abs(on), abs(off))
    if minimum < phase_floor:
        return dict(min_magnitude=minimum, separation_degrees=None,
                    target_error_degrees=None, phase_valid=False)
    separation = abs(math.degrees(cmath.phase(off*on.conjugate())))
    return dict(min_magnitude=minimum, separation_degrees=separation,
                target_error_degrees=180-separation, phase_valid=True)


def pair(length, fraction, config=Config()):
    on, off = [response(length, fraction, state, config)[0] for state in (0, 1)]
    return dict(length=length, switch_fraction=fraction,
                right_segment_length=length*(1-fraction),
                on_real=on.real, on_imag=on.imag,
                off_real=off.real, off_imag=off.imag,
                on_switch_current=abs(field(1, 0, length, fraction, 0, config)[1]),
                off_switch_current=abs(field(1, 0, length, fraction, 1, config)[1]),
                **phase_metrics(on, off))


def write_csv(path, rows):
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def run(output):
    output.mkdir(parents=True, exist_ok=True)
    config = Config()
    rows = [pair(.30+.12*i/24, .15+.75*j/160, config)
            for i in range(25) for j in range(161)]
    write_csv(output/"conventional-sweep.csv", rows)
    # Fix total length for a causal placement comparison, not unrelated extrema.
    length = .36
    selected = [pair(length, .15+.75*j/4000, config) for j in range(4001)]
    strong = min((r for r in selected if r["min_magnitude"] >= .8),
                 key=lambda r:r["target_error_degrees"])
    near_node = pair(length, 1-.25/length, config)
    exact_node = pair(length, 1-.25/length, Config(alpha=0))
    examples = {"strong": strong, "near_current_node": near_node,
                "lossless_current_node_limit": exact_node}
    maximum_wave_disagreement = max(
        abs(response(row["length"], row["switch_fraction"], state, config)[0]
            -wave_reference(row["length"], row["switch_fraction"], state, config)[0])
        for row in rows for state in (0, 1))
    maximum_power_balance_error = 0
    fields, refinement = [], []
    for name, row in examples.items():
        cfg = Config(alpha=0) if name.startswith("lossless") else config
        length, fraction = row["length"], row["switch_fraction"]
        for state in (0, 1):
            exact_r = response(length, fraction, state, cfg)[0]
            independent = wave_reference(length, fraction, state, cfg)[0]
            maximum_wave_disagreement = max(maximum_wave_disagreement, abs(exact_r-independent))
            loss = 0
            for segment in (0, 1):
                distance = length*(fraction if segment == 0 else 1-fraction)
                for j in range(2001):
                    v, current = field(j/2000, segment, length, fraction, state, cfg)
                    weight = .5 if j in (0, 2000) else 1
                    loss += .5*cfg.alpha*(abs(v)**2+abs(current)**2)*distance/2000*weight
                    if j % 10 == 0:
                        fields.append(dict(case=name, state=state, segment=segment,
                            local=j/2000, x=(j/2000*distance)+(length*fraction if segment else 0),
                            voltage_real=v.real, voltage_imag=v.imag,
                            current_real=current.real, current_imag=current.imag))
            switch_i = field(1, 0, length, fraction, state, cfg)[1]
            loss += .5*cfg.impedance(state).real*abs(switch_i)**2
            maximum_power_balance_error = max(maximum_power_balance_error,
                                              abs(.5*(1-abs(exact_r)**2)-loss))
            for n in (16, 32, 64, 128, 256, 512):
                approx = response(length, fraction, state, cfg, n)[0]
                refinement.append(dict(case=name, state=state, intervals_per_segment=n,
                                       absolute_complex_reflection_error=abs(approx-exact_r)))
    write_csv(output/"mechanism-fields.csv", fields)
    write_csv(output/"baseline-refinement.csv", refinement)
    times = []
    for _ in range(9):
        started = time.perf_counter()
        for row in rows:
            response(row["length"], row["switch_fraction"], 0, config)
            response(row["length"], row["switch_fraction"], 1, config)
        times.append((time.perf_counter()-started)/len(rows))
    result = dict(status="Conventional mechanism sanity check only; no neural model trained",
        provenance="All dimensionless circuit parameters are synthetic, not the researcher data",
        config=dict(alpha=config.alpha, beta=config.beta,
                    z_on=[config.z_on.real, config.z_on.imag],
                    z_off=[config.z_off.real, config.z_off.imag],
                    common_termination="V(L)=0 in both switch states",
                    length_range=[.30,.42], switch_fraction_range=[.15,.90]),
        sweep_designs=len(rows), examples=examples,
        max_independent_wave_reference_disagreement=maximum_wave_disagreement,
        independent_wave_checks=2*len(rows)+2*len(examples),
        max_reflected_magnitude_over_sweep=max(
            abs(complex(r[f"{s}_real"], r[f"{s}_imag"]))
            for r in rows for s in ("on", "off")),
        max_power_balance_error=maximum_power_balance_error,
        median_seconds_per_two_state_query=statistics.median(times),
        timing_range_seconds_per_two_state_query=[min(times), max(times)],
        phase_mask_floor=.05,
        illustrative_thresholds_not_researcher_requirements=dict(
            phase_target_degrees=180, tolerance_degrees=15, min_magnitude=.8),
        illustrative_feasible_designs=sum(r["phase_valid"] and r["target_error_degrees"]<=15
                                         and r["min_magnitude"]>=.8 for r in rows))
    (output/"mechanism-sanity.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path,
                        default=Path(__file__).resolve().parents[1]/"outputs/switched-line")
    run(parser.parse_args().output)

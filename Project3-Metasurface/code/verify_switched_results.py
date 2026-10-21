"""Independent saved-result checks using NumPy forward evaluation and wave solve."""
import csv
import json
from pathlib import Path
import numpy as np
from switched_line import Config,wave_reference

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"outputs/switched-surrogate"


def forward(payload,x,d,state):
    weights={k:np.array(v) for k,v in payload["weights"].items()}
    features=np.stack((2*x-1,2*(d-.03)/(.357-.03)-1,2*state-1),axis=1)
    h=np.tanh(features@weights["first.weight"].T+weights["first.bias"])
    h=np.tanh(h@weights["second.weight"].T+weights["second.bias"])
    return h@weights["last.weight"].T+weights["last.bias"]


def main(output=OUT,modes=("pinn","supervised"),seeds=(0,1,2)):
    config=Config();count=0;field_count=0
    max_r_error,max_error_metric,max_field_error=0.,0.,0.
    for mode in modes:
        for seed in seeds:
            prefix=f"{mode}_seed-{seed}"
            payload=json.loads((output/f"{prefix}_weights.json").read_text())
            with (output/f"{prefix}_states.csv").open(newline="") as f:rows=list(csv.DictReader(f))
            d=np.array([float(r["d"]) for r in rows]);a=np.array([float(r["a"]) for r in rows])
            state=np.array([float(r["state"]) for r in rows])
            value=forward(payload,np.zeros_like(d),d,state)
            current=value[:,2]+1j*value[:,3]
            r_pred=np.exp(-2*config.gamma*a)*(1-current)
            for j,row in enumerate(rows):
                recorded=complex(float(row["predicted_real"]),float(row["predicted_imag"]))
                wave_r=wave_reference(float(row["length"]),float(row["switch_fraction"]),int(row["state"]))[0]
                max_r_error=max(max_r_error,abs(r_pred[j]-recorded))
                max_error_metric=max(max_error_metric,abs(abs(r_pred[j]-wave_r)-float(row["complex_R_error"])))
                count+=1
            with (output/f"{prefix}_fields.csv").open(newline="") as f:fields=list(csv.DictReader(f))
            for row in fields:
                d,a=float(row["d"]),float(row["a"])
                x=float(row["x"]);state=int(row["state"])
                b,c,e=wave_reference(a+d,a/(a+d),state)
                if int(row["segment"])==0:
                    fwd=np.exp(-config.gamma*x);back=b*np.exp(config.gamma*x)
                else:
                    y=x-a;fwd=c*np.exp(-config.gamma*y);back=e*np.exp(config.gamma*y)
                v,i=fwd+back,fwd-back
                recorded_v=complex(float(row["reference_v_real"]),float(row["reference_v_imag"]))
                recorded_i=complex(float(row["reference_i_real"]),float(row["reference_i_imag"]))
                max_field_error=max(max_field_error,abs(v-recorded_v),abs(i-recorded_i))
                field_count+=1
    result=dict(state_response_metrics_checked=count,selected_field_reference_rows_checked=field_count,
                max_numpy_vs_torch_predicted_R_disagreement=max_r_error,
                max_independent_complex_R_error_metric_disagreement=max_error_metric,
                max_independent_wave_field_reference_disagreement=max_field_error,
                passed=bool(max(max_r_error,max_error_metric,max_field_error)<1e-10))
    assert result["passed"],result
    (output/"independent-verification.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
    print(json.dumps(result,indent=2))


if __name__=="__main__":
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",type=Path,default=OUT)
    parser.add_argument("--pinn-only",action="store_true")
    parser.add_argument("--seed",type=int)
    args=parser.parse_args()
    main(args.output,("pinn",) if args.pinn_only else ("pinn","supervised"),(args.seed,) if args.seed is not None else (0,1,2))

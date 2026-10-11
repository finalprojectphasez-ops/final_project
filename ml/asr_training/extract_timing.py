import json, os, glob

for label, pattern in [
    ("ORIGINAL PILOT (50 steps, 100 train samples)",
     "asr_model/pilot_model/checkpoint-*/trainer_state.json"),
    ("CORRECTED PILOT (50 steps, 93 train samples)",
     "asr_model/pilot_model_corrected/checkpoint-*/trainer_state.json"),
]:
    files = sorted(glob.glob(pattern))
    if not files:
        print(f"{label}: no trainer_state.json found"); continue
    state  = json.load(open(files[-1]))
    h      = state["log_history"]
    t_rows = [e for e in h if "train_runtime" in e]
    e_rows = [e for e in h if "eval_loss" in e]
    steps  = state["global_step"]

    print(f"=== {label} ===")
    if t_rows:
        t = t_rows[0]
        rt = t["train_runtime"]
        sps = t["train_steps_per_second"]
        print(f"  Total steps              : {steps}")
        print(f"  Train runtime            : {rt:.2f} s  ({rt/60:.2f} min)")
        print(f"  Seconds per step         : {rt/steps:.3f} s/step")
        print(f"  Steps per second         : {sps:.4f}")
        print(f"  Train samples/s          : {t['train_samples_per_second']:.4f}")
        print(f"  Train loss (final)       : {t['train_loss']:.4f}")

    for e in e_rows:
        rt_e  = e.get("eval_runtime", 0)
        sp_e  = e.get("eval_samples_per_second", 0)
        ss_e  = e.get("eval_steps_per_second", 0)
        n_est = round(rt_e * sp_e) if sp_e else "?"
        print(f"  Eval @step {e['step']:>3}           : "
              f"wer={e['eval_wer']*100:.2f}%, "
              f"loss={e['eval_loss']:.4f}, "
              f"runtime={rt_e:.2f}s, "
              f"samples/s={sp_e:.3f}, "
              f"~{n_est} samples evaluated")
    print()

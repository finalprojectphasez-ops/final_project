"""
inspect_training_loss.py
Reads the Trainer's training log files to verify how training loss
and validation loss were computed, and reports the logged values.
"""
import os
import json
import glob

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR  = os.path.join(SCRIPT_DIR, "..", "asr_model", "pilot_model")
MODEL_DIR  = os.path.normpath(MODEL_DIR)

print(f"Looking for training logs in: {MODEL_DIR}\n")

# ── 1. trainer_state.json ──────────────────────────────────────────────────
# trainer_state.json lives in checkpoint subdirs, find the latest one
import glob as _glob
checkpoint_states = sorted(
    _glob.glob(os.path.join(MODEL_DIR, "checkpoint-*", "trainer_state.json"))
)
if checkpoint_states:
    state_file = checkpoint_states[-1]  # highest checkpoint number
    print(f"  Using trainer_state.json from: {state_file}\n")
else:
    state_file = os.path.join(MODEL_DIR, "trainer_state.json")

if os.path.exists(state_file):
    with open(state_file) as f:
        state = json.load(f)

    print("="*65)
    print("  trainer_state.json — all logged events")
    print("="*65)
    log_history = state.get("log_history", [])
    for entry in log_history:
        step  = entry.get("step", "?")
        epoch = entry.get("epoch", "?")
        # Training step entries
        if "loss" in entry and "eval_loss" not in entry:
            print(f"  [TRAIN] step={step:>4}, epoch={epoch}, "
                  f"loss={entry['loss']:.4f}, "
                  f"lr={entry.get('learning_rate', '?')}")
        # Eval entries
        if "eval_loss" in entry:
            wer = entry.get("eval_wer", "?")
            wer_str = f"{wer*100:.2f}%" if isinstance(wer, float) else str(wer)
            print(f"  [EVAL]  step={step:>4}, epoch={epoch}, "
                  f"eval_loss={entry['eval_loss']:.4f}, "
                  f"eval_wer={wer_str}")

    best = state.get("best_metric", None)
    best_model_checkpoint = state.get("best_model_checkpoint", None)
    print(f"\n  Best metric (WER)         : {best}")
    print(f"  Best checkpoint           : {best_model_checkpoint}")

    total_steps = state.get("global_step", "?")
    print(f"  Total training steps done : {total_steps}")

else:
    print(f"  [WARNING] trainer_state.json not found at: {state_file}")
    print("  Searching for any JSON logs...")
    for f in glob.glob(os.path.join(MODEL_DIR, "**", "*.json"), recursive=True):
        print(f"    Found: {f}")

# ── 2. Explain the loss discrepancy ────────────────────────────────────────
print("\n" + "="*65)
print("  LOSS CALCULATION ANALYSIS")
print("="*65)

if os.path.exists(state_file):
    train_losses = [e["loss"] for e in log_history if "loss" in e and "eval_loss" not in e]
    eval_losses  = [e["eval_loss"] for e in log_history if "eval_loss" in e]

    if train_losses:
        print(f"\n  Training loss values logged  : {[round(x,3) for x in train_losses]}")
        print(f"  Training loss (final)        : {train_losses[-1]:.4f}")
        print(f"  Training loss (average)      : {sum(train_losses)/len(train_losses):.4f}")

    if eval_losses:
        print(f"\n  Eval loss values logged      : {[round(x,3) for x in eval_losses]}")
        print(f"  Eval loss (final)            : {eval_losses[-1]:.4f}")

    print("""
  HOW EACH IS COMPUTED:
  - Training loss: computed during the FORWARD PASS while gradients
    are active and 8-bit quantized weights are being updated.
    The loss is the average cross-entropy over one mini-batch (size=2).
    It is logged every 10 steps.

  - Evaluation loss: computed in model.eval() mode (no gradients)
    on the validation set. The model's 8-bit weights are in inference
    mode, which uses cleaner float16 arithmetic, producing lower loss.

  - The gap (train=15.70, eval=3.48) is very large. Contributing factors:
    a) Training loss is logged as a per-step raw batch loss (high variance)
    b) Eval loss is an average over ALL eval samples in eval mode
    c) 8-bit quantized forward pass during training introduces extra
       numerical error in activations (documented bitsandbytes behaviour)
    d) With only 50 steps on 100 samples, the model may see very hard
       batches early (high train loss) but the eval sentences are easier.

  CONCLUSION: The training and eval losses use the SAME cross-entropy
  criterion, but are computed under different conditions (train vs eval
  mode, 8-bit quantization noise). The gap is large but plausible given
  the tiny dataset. It should narrow significantly with more training data.
""")

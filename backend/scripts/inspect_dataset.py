import csv
import json

with open("data/interview_dataset.csv", "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    samples = {}
    for row in reader:
        task = row["task"]
        if task not in samples:
            samples[task] = row
        if len(samples) == 3:
            break

for task, row in samples.items():
    print("=" * 60)
    print("TASK:", task)
    print("Job Role:", row.get("job_role"))
    print("Topic:", row.get("topic"))
    print("Difficulty:", row.get("difficulty"))
    print("Instruction:", row.get("instruction"))
    print("\nInput JSON (excerpt):")
    try:
        parsed_in = json.loads(row.get("input_json", "{}"))
        print(json.dumps(parsed_in, indent=2)[:600])
    except Exception as e:
        print(row.get("input_json")[:600])
    print("\nTarget JSON:")
    try:
        parsed_out = json.loads(row.get("target_json", "{}"))
        print(json.dumps(parsed_out, indent=2))
    except Exception as e:
        print(row.get("target_json"))

import csv
import json
import os
from typing import Dict, Any

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "interview_dataset.csv")
OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "finetuning")

def row_to_chat_format(row: Dict[str, Any]) -> Dict[str, Any]:
    task = row.get("task")
    instruction = row.get("instruction", "")
    input_str = row.get("input_json", "")
    target_str = row.get("target_json", "")
    job_role = row.get("job_role", "")
    difficulty = row.get("difficulty", "")

    system_prompt = (
        f"You are an expert technical interviewer and interview design system. "
        f"Task: {task}. Role: {job_role}. Difficulty: {difficulty}. "
        f"Always respond with a valid JSON object strictly matching the target schema."
    )

    user_content = f"Instruction: {instruction}\n\nInput:\n{input_str}"
    assistant_content = target_str

    return {
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
            {"role": "assistant", "content": assistant_content}
        ],
        "task": task,
        "job_role": job_role
    }

def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    
    questions_file = open(os.path.join(OUT_DIR, "train_questions.jsonl"), "w", encoding="utf-8")
    followup_file = open(os.path.join(OUT_DIR, "train_followups.jsonl"), "w", encoding="utf-8")
    all_file = open(os.path.join(OUT_DIR, "train_all.jsonl"), "w", encoding="utf-8")

    counts = {"role_question": 0, "followup": 0, "resume_extract": 0}

    with open(DATA_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            task = row.get("task")
            chat_example = row_to_chat_format(row)
            json_line = json.dumps({"messages": chat_example["messages"]}, ensure_ascii=False) + "\n"
            
            all_file.write(json_line)
            counts[task] = counts.get(task, 0) + 1

            if task == "role_question":
                questions_file.write(json_line)
            elif task == "followup":
                followup_file.write(json_line)

    questions_file.close()
    followup_file.close()
    all_file.close()

    print("Data preparation complete!")
    print(f"Exported to {OUT_DIR}:")
    print(f"- Total records: {sum(counts.values())}")
    print(f"- Counts: {counts}")

if __name__ == "__main__":
    main()

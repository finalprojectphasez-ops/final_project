from datasets import load_dataset
ds = load_dataset("ishands/commonvoice-indian_accent", split="train", trust_remote_code=True, streaming=True)
sample = next(iter(ds))
print(sample.keys())
print(sample.get('sentence', 'no sentence'))
print(sample.get('text', 'no text'))

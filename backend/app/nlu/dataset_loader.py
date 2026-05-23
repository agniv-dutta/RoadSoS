import json
from pathlib import Path
from typing import List, Optional

import torch
from torch.utils.data import Dataset
from transformers import AutoTokenizer


class EmergencyDataset(Dataset):
    def __init__(self, path: str, tokenizer_name: str = "xlm-roberta-base", max_length: int = 128, intent2id: Optional[dict] = None, slot2id: Optional[dict] = None):
        self.path = Path(path)
        self.data = json.load(open(self.path, encoding="utf8"))
        self.tokenizer = AutoTokenizer.from_pretrained(tokenizer_name, use_fast=True)
        self.max_length = max_length

        # build maps if not provided
        if intent2id is None:
            intents = sorted({ex["intent"] for ex in self.data})
            self.intent2id = {p: i for i, p in enumerate(intents)}
        else:
            self.intent2id = intent2id

        if slot2id is None:
            tags = []
            for ex in self.data:
                for t in ex["bio_tags"]:
                    if t not in tags:
                        tags.append(t)
            tags = sorted(tags)
            self.slot2id = {t: i for i, t in enumerate(tags)}
        else:
            self.slot2id = slot2id

    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx):
        ex = self.data[idx]
        words: List[str] = ex.get("tokens") or ex["text"].split()
        bio_tags: List[str] = ex["bio_tags"]

        encoding = self.tokenizer(words, is_split_into_words=True, truncation=True, padding="max_length", max_length=self.max_length)

        word_ids = encoding.word_ids()

        # align labels to subword tokens: first subword gets tag id, others -100
        slot_labels = []
        for i, wid in enumerate(word_ids):
            if wid is None:
                slot_labels.append(-100)
            else:
                if i == 0 or wid != word_ids[i - 1]:
                    tag = bio_tags[wid]
                    slot_labels.append(self.slot2id[tag])
                else:
                    slot_labels.append(-100)

        intent_label = self.intent2id[ex["intent"]]

        item = {
            "input_ids": torch.tensor(encoding["input_ids"], dtype=torch.long),
            "attention_mask": torch.tensor(encoding["attention_mask"], dtype=torch.long),
            "intent_label": torch.tensor(intent_label, dtype=torch.long),
            "slot_labels": torch.tensor(slot_labels, dtype=torch.long),
            "word_ids": word_ids,
            "id": ex.get("id"),
        }

        return item

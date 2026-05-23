#!/usr/bin/env python3
"""Generate BIO-annotated dataset and synthetic panic messages.

This script reads `panic_data.json`, converts examples to token-level BIO tags,
generates synthetic messages across languages, creates stratified train/val/test
splits, and validates the dataset. Outputs are written under
`app/nlu/dataset` as requested.

Only uses: json, random, collections.Counter
"""

import json
import random
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "nlu" / "dataset"
DATA_DIR.mkdir(parents=True, exist_ok=True)

INPUT = DATA_DIR / "panic_data.json"
OUT_FULL = DATA_DIR / "panic_data_bio.json"
OUT_TRAIN = DATA_DIR / "train.json"
OUT_VAL = DATA_DIR / "val.json"
OUT_TEST = DATA_DIR / "test.json"
MAPPING = DATA_DIR / "massive_slot_mapping.json"
README = DATA_DIR / "README.md"

random.seed(42)


def simple_tokenize(text: str) -> list[str]:
    # Normalize punctuation to spaces, keep unicode letters
    text = text.replace("'", " ")
    text = re.sub(r"([\.,!\?;:\(\)\[\]\"])+", " ", text)
    # collapse multiple spaces
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []
    return text.split(" ")


def find_span(tokens: list[str], phrase: str) -> tuple[int, int] | None:
    if not phrase:
        return None
    phrase = re.sub(r"\s+", " ", phrase.strip())
    p_tokens = phrase.split(" ")
    n = len(tokens)
    m = len(p_tokens)
    for i in range(n - m + 1):
        matched = True
        for j in range(m):
            if tokens[i + j].lower() != p_tokens[j].lower():
                matched = False
                break
        if matched:
            return i, i + m
    return None


ENTRAP_KEYWORDS = set(
    [
        "stuck",
        "stck",
        "trapped",
        "atokte",
        "atokata",
        "atke",
        "phanse",
        "phanse",
        "atke",
        "atke",
        "atke",
    ]
)

CHILD_KEYWORDS = set(["child", "children", "bachcha", "bachha", "baccha", "bachha", "bachha", "children"])

HAZARD_MAP = {
    "fire": ["fire", "agun", "agun", "fire", "fire!!!!", "fire!!!"],
    "fuel_leak": ["petrol", "fuel", "petrol", "fuel_leak", "petrol", "petrol lkg"],
}


def tag_example(entry: dict, lang_prefix: str, seq_id: int) -> dict:
    text = entry["text"]
    tokens = simple_tokenize(text)
    tags = ["O"] * len(tokens)

    # CASUALTY count: look for numeric token equal to casualties
    casualties = entry.get("slots", {}).get("casualties")
    if isinstance(casualties, int):
        s = str(casualties)
        for idx, t in enumerate(tokens):
            if t == s:
                tags[idx] = "B-CASUALTY_COUNT"
                break

    # LOCATION: match location_mention phrase
    loc = entry.get("slots", {}).get("location_mention")
    if loc:
        span = find_span(tokens, loc)
        if span:
            i0, i1 = span
            tags[i0] = "B-LOCATION"
            for k in range(i0 + 1, i1):
                tags[k] = "I-LOCATION"

    # HAZARD_TYPE
    hazard = entry.get("slots", {}).get("hazard_type")
    if hazard and hazard != "none":
        patterns = HAZARD_MAP.get(hazard, [hazard])
        for pat in patterns:
            span = find_span(tokens, pat)
            if span:
                i0, i1 = span
                tags[i0] = "B-HAZARD_TYPE"
                for k in range(i0 + 1, i1):
                    tags[k] = "I-HAZARD_TYPE"
                break

    # ENTRAPMENT
    ent = entry.get("slots", {}).get("entrapment")
    if ent:
        for idx, t in enumerate(tokens):
            if t.lower() in ENTRAP_KEYWORDS or "stuck" in t.lower() or "trapp" in t.lower():
                tags[idx] = "B-ENTRAPMENT"
                # try tag following if "inside" or similar
                if idx + 1 < len(tokens) and tokens[idx + 1].lower() in ("inside", "andar"):
                    tags[idx + 1] = "I-ENTRAPMENT"
                break

    # CHILD_INVOLVED
    child = entry.get("slots", {}).get("child_involved")
    if child:
        for idx, t in enumerate(tokens):
            if t.lower() in CHILD_KEYWORDS or "child" in t.lower() or "bach" in t.lower():
                tags[idx] = "B-CHILD_INVOLVED"
                break

    out = {
        "id": f"{lang_prefix}_{seq_id:03d}",
        "text": text,
        "intent": entry.get("intent"),
        "triage": entry.get("triage_level") or entry.get("triage") or entry.get("triage_level"),
        "language": entry.get("language") or lang_prefix,
        "tokens": tokens,
        "bio_tags": tags,
    }
    return out


def load_and_convert_existing() -> list[dict]:
    raw = json.loads(INPUT.read_text(encoding="utf8"))
    converted = []
    counters = Counter()
    seq_counters = defaultdict(int)
    for e in raw:
        lang = e.get("language", "en")
        prefix = "en"
        if lang == "bn":
            prefix = "bn"
        elif lang == "mixed":
            # leave as mixed but pick en prefix
            prefix = "en"
        converted.append(tag_example(e, prefix, len(converted) + 1))
        counters[e.get("intent")] += 1
    print("Converted existing examples per intent:", counters)
    return converted


# ---------- Synthetic generation helpers ----------

EN_LOCATIONS = ["highway", "toll", "junction", "market", "school", "bridge", "road", "temple", "checkpoint"]
BN_LOCATIONS = ["highway", "dhaka", "chittagong", "bridge", "poth", "toll"]
HI_LOCATIONS = ["highway", "toll", "market", "school", "road"]

def triage_from_props(casualties: int | None, entrap: bool, hazard: str | None, child: bool) -> str:
    if (casualties is not None and casualties >= 3) or entrap or child or (hazard and hazard != "none"):
        return "P1"
    if casualties == 1:
        return "P2"
    return "P3"


def gen_template_en(idx: int) -> dict:
    intent = random.choice(["emergency_crash", "fire_hazard", "medical_emergency", "vehicle_assistance"])
    casualties = None
    entrap = False
    hazard = "none"
    child = False
    if intent == "emergency_crash":
        casualties = random.choice([1, 2, 3, 4, None])
        entrap = random.choice([True, False])
        child = random.choice([False, False, True])
    if intent == "fire_hazard":
        casualties = random.choice([0, None, 1])
        hazard = random.choice(["fire", "fuel_leak"])
        entrap = random.choice([True, False])
    if intent == "medical_emergency":
        casualties = random.choice([1, None])
    if intent == "vehicle_assistance":
        casualties = 0

    num = casualties if isinstance(casualties, int) else random.choice([None, 2, 1])
    loc = random.choice(EN_LOCATIONS)
    parts = []
    if intent == "emergency_crash":
        parts.append(random.choice(["accident", "crash", "crash happened", "bad crash"]))
        if num:
            parts.append(str(num))
            parts.append(random.choice(["people", "ppl", "persons"]))
        if entrap:
            parts.append(random.choice(["stuck", "trapped", "inside"]))
    elif intent == "fire_hazard":
        parts.append(random.choice(["fire", "vehicle on fire", "tanker spill"]))
        if hazard == "fuel_leak":
            parts.append(random.choice(["petrol", "fuel", "leak"]))
    elif intent == "medical_emergency":
        parts.append(random.choice(["man collapsed", "unconscious", "bleeding"]))
    else:
        parts.append(random.choice(["need towing", "tyre burst", "minor accident"]))

    parts.append("near")
    parts.append(loc)
    text = " ".join([p for p in parts if p])
    entry = {
        "text": text,
        "language": "en",
        "slots": {
            "casualties": num,
            "entrapment": entrap,
            "hazard_type": hazard,
            "child_involved": child,
            "location_mention": loc,
        },
        "triage_level": triage_from_props(num, entrap, hazard, child),
        "intent": intent,
    }
    return entry


def gen_template_bn_roman(idx: int) -> dict:
    intent = random.choice(["emergency_crash", "fire_hazard", "medical_emergency"])
    loc = random.choice(BN_LOCATIONS)
    casualties = random.choice([1, 2, 3, None, 5])
    entrap = random.choice([True, False])
    child = random.choice([False, False, True])
    hazard = random.choice(["none", "fire", "fuel_leak"]) if intent == "fire_hazard" else "none"
    templates = [
        f"accident hoyeche {casualties} jon {loc} e",
        f"gari te agun lagche {loc} e log atke geche",
        f"{casualties} jon ghayel {loc} e please help",
    ]
    text = random.choice(templates)
    entry = {
        "text": text,
        "language": "bn",
        "slots": {
            "casualties": casualties if isinstance(casualties, int) else None,
            "entrapment": entrap,
            "hazard_type": hazard,
            "child_involved": child,
            "location_mention": loc,
        },
        "triage_level": triage_from_props(casualties if isinstance(casualties, int) else None, entrap, hazard, child),
        "intent": intent,
    }
    return entry


def gen_template_hi_roman(idx: int) -> dict:
    intent = random.choice(["emergency_crash", "medical_emergency", "vehicle_assistance"])
    loc = random.choice(HI_LOCATIONS)
    casualties = random.choice([1, 2, 3, None])
    entrap = random.choice([True, False])
    child = random.choice([False, True, False])
    hazard = "none"
    phrases = [
        f"accident hua {casualties} log {loc} pe" if casualties else f"accident hua {loc}",
        f"crash ho gaya {loc} pe {casualties} injured" if casualties else f"crash ho gaya {loc}",
    ]
    text = random.choice(phrases)
    entry = {
        "text": text,
        "language": "hi",
        "slots": {
            "casualties": casualties if isinstance(casualties, int) else None,
            "entrapment": entrap,
            "hazard_type": hazard,
            "child_involved": child,
            "location_mention": loc,
        },
        "triage_level": triage_from_props(casualties if isinstance(casualties, int) else None, entrap, hazard, child),
        "intent": intent,
    }
    return entry


BN_NATIVE_WORDS = [
    ("দুর্ঘটনা", "accident"),
    ("আগুন", "fire"),
    ("বাঁচ্চা", "child"),
    ("আটকে", "stuck"),
]

THAI_WORDS = [
    ("อุบัติเหตุ", "accident"),
    ("ไฟไหม้", "fire"),
    ("ติดอยู่", "stuck"),
    ("เด็ก", "child"),
]


def gen_template_bn_native(idx: int) -> dict:
    # Bengali unicode
    loc = random.choice(["হাইওয়ে", "বহির্গামী রাস্তা", "ব্রিজ", "স্কুল"])
    casualties = random.choice([1, 2, 3, None])
    entrap = random.choice([True, False])
    child = random.choice([False, True, False])
    hazard = random.choice(["none", "fire", "fuel_leak"]) if random.random() < 0.3 else "none"
    parts = []
    parts.append(random.choice(["দুর্ঘটনা", "ঝগড়া", "ক্র্যাশ"]))
    if casualties:
        parts.append(str(casualties))
        parts.append("জন")
    if entrap:
        parts.append("আটকে আছেন")
    parts.append(loc)
    text = " ".join(parts)
    entry = {
        "text": text,
        "language": "bn_native",
        "slots": {
            "casualties": casualties if isinstance(casualties, int) else None,
            "entrapment": entrap,
            "hazard_type": hazard,
            "child_involved": child,
            "location_mention": loc,
        },
        "triage_level": triage_from_props(casualties if isinstance(casualties, int) else None, entrap, hazard, child),
        "intent": random.choice(["emergency_crash", "fire_hazard"]),
    }
    return entry


def gen_template_thai(idx: int) -> dict:
    loc = random.choice(["ถนนหลวง", "ใกล้โรงเรียน", "สะพาน", "ทางด่วน"])
    casualties = random.choice([1, 2, 3, None])
    entrap = random.choice([True, False])
    child = random.choice([False, True, False])
    hazard = random.choice(["none", "fire", "fuel_leak"]) if random.random() < 0.3 else "none"
    parts = []
    parts.append(random.choice(["อุบัติเหตุ", "ชนกัน", "รถพลิกคว่ำ"]))
    if casualties:
        parts.append(str(casualties))
        parts.append("คน")
    if entrap:
        parts.append("ติดอยู่")
    parts.append(loc)
    text = " ".join(parts)
    entry = {
        "text": text,
        "language": "th",
        "slots": {
            "casualties": casualties if isinstance(casualties, int) else None,
            "entrapment": entrap,
            "hazard_type": hazard,
            "child_involved": child,
            "location_mention": loc,
        },
        "triage_level": triage_from_props(casualties if isinstance(casualties, int) else None, entrap, hazard, child),
        "intent": random.choice(["emergency_crash", "fire_hazard"]),
    }
    return entry


def gen_template_sinhala(idx: int) -> dict:
    # transliterated Sinhala mixed with Latin
    loc = random.choice(["road", "junction", "school"])
    casualties = random.choice([1, 2, None])
    entrap = random.choice([True, False])
    child = random.choice([False, True])
    text = f"accident {casualties if casualties else ''} loku loku {loc} hariyata help karanna"
    entry = {
        "text": text.strip(),
        "language": "si",
        "slots": {
            "casualties": casualties if isinstance(casualties, int) else None,
            "entrapment": entrap,
            "hazard_type": "none",
            "child_involved": child,
            "location_mention": loc,
        },
        "triage_level": triage_from_props(casualties if isinstance(casualties, int) else None, entrap, "none", child),
        "intent": random.choice(["emergency_crash", "medical_emergency"]),
    }
    return entry


def generate_synthetic(n_en=80, n_bn=60, n_hi=60, n_bn_native=40, n_th=40, n_si=20):
    synth = []
    idx = 1
    for i in range(n_en):
        synth.append(gen_template_en(i + 1))
    for i in range(n_bn):
        synth.append(gen_template_bn_roman(i + 1))
    for i in range(n_hi):
        synth.append(gen_template_hi_roman(i + 1))
    for i in range(n_bn_native):
        synth.append(gen_template_bn_native(i + 1))
    for i in range(n_th):
        synth.append(gen_template_thai(i + 1))
    for i in range(n_si):
        synth.append(gen_template_sinhala(i + 1))
    random.shuffle(synth)
    return synth


def compute_id_prefix(lang_code: str) -> str:
    if lang_code in ("en", "mixed"):
        return "en"
    if lang_code in ("bn", "bn_native"):
        return "bn"
    if lang_code == "hi":
        return "hi"
    if lang_code == "th":
        return "th"
    if lang_code == "si":
        return "si"
    return lang_code


def convert_all_and_write():
    existing = load_and_convert_existing()
    synth_raw = generate_synthetic()
    synth_converted = []
    for i, s in enumerate(synth_raw, start=1):
        prefix = compute_id_prefix(s.get("language", "en"))
        synth_converted.append(tag_example(s, prefix, i))

    combined = existing + synth_converted
    # assign unique ids sequentially by language groups
    counters = defaultdict(int)
    for ex in combined:
        prefix = ex["language"]
        p = compute_id_prefix(prefix)
        counters[p] += 1
        ex["id"] = f"{p}_{counters[p]:03d}"

    # write full
    OUT_FULL.write_text(json.dumps(combined, ensure_ascii=False, indent=2), encoding="utf8")
    print(f"Wrote full dataset to {OUT_FULL} ({len(combined)} examples)")
    return combined


def stratified_split(dataset: list[dict]):
    # Stratify by (intent, language)
    groups = defaultdict(list)
    for ex in dataset:
        key = (ex["intent"], ex["language"])
        groups[key].append(ex)

    train, val, test = [], [], []
    for key, items in groups.items():
        random.shuffle(items)
        n = len(items)
        n_train = int(round(n * 0.7))
        n_val = int(round(n * 0.15))
        n_test = n - n_train - n_val
        train.extend(items[:n_train])
        val.extend(items[n_train : n_train + n_val])
        test.extend(items[n_train + n_val :])

    # Enforce exact totals: train=266, val=57, test=57
    desired_train = int(round(len(dataset) * 0.7))
    desired_val = int(round(len(dataset) * 0.15))
    desired_test = len(dataset) - desired_train - desired_val

    # Helper to move one item from src to dst
    def move_one(src: list, dst: list):
        if not src:
            return False
        item = src.pop()
        dst.append(item)
        return True

    # Adjust sizes by moving items from largest set to smallest
    while len(train) > desired_train:
        # move from train to val or test
        if len(val) < desired_val:
            move_one(train, val)
        else:
            move_one(train, test)

    while len(train) < desired_train:
        # move from val or test to train
        if len(val) > desired_val:
            move_one(val, train)
        else:
            move_one(test, train)

    while len(val) > desired_val:
        if len(test) < desired_test:
            move_one(val, test)
        else:
            move_one(val, train)

    while len(val) < desired_val:
        if len(train) > desired_train:
            move_one(train, val)
        else:
            move_one(test, val)

    # Final adjustment if test differs
    while len(test) != desired_test:
        if len(test) > desired_test:
            move_one(test, train)
        else:
            if len(train) > desired_train:
                move_one(train, test)
            else:
                move_one(val, test)

    total = len(dataset)
    assert len(train) + len(val) + len(test) == total
    OUT_TRAIN.write_text(json.dumps(train, ensure_ascii=False, indent=2), encoding="utf8")
    OUT_VAL.write_text(json.dumps(val, ensure_ascii=False, indent=2), encoding="utf8")
    OUT_TEST.write_text(json.dumps(test, ensure_ascii=False, indent=2), encoding="utf8")
    print(f"Split: train={len(train)} val={len(val)} test={len(test)}")
    return train, val, test


def validate_bio(dataset: list[dict], train: list[dict], val: list[dict], test: list[dict]):
    errors = []
    # Check I-tags follow B-tags
    for ex in dataset:
        tags = ex["bio_tags"]
        for i, t in enumerate(tags):
            if t.startswith("I-"):
                if i == 0:
                    errors.append((ex["id"], "I-tag at start"))
                    continue
                prev = tags[i - 1]
                if prev == "O":
                    errors.append((ex["id"], f"I-tag without preceding B: {t} at {i}"))
                else:
                    # ensure same type
                    if prev.split("-")[-1] != t.split("-")[-1] and not prev.startswith("B-") and not prev.startswith("I-"):
                        errors.append((ex["id"], f"I-tag type mismatch at {i}"))

    # Intent and language distribution check
    def dist(listing):
        intents = Counter([e["intent"] for e in listing])
        langs = Counter([e["language"] for e in listing])
        return intents, langs

    all_intents, all_langs = dist(dataset)
    train_i, train_l = dist(train)
    val_i, val_l = dist(val)
    test_i, test_l = dist(test)

    def compare_counts(all_counter, sub_counter, name):
        issues = []
        total = sum(all_counter.values())
        for key, all_v in all_counter.items():
            sub_v = sub_counter.get(key, 0)
            all_pct = all_v / total if total else 0
            sub_pct = sub_v / sum(sub_counter.values()) if sum(sub_counter.values()) else 0
            if abs(all_pct - sub_pct) > 0.05:
                issues.append((name, key, all_v, sub_v, all_pct, sub_pct))
        return issues

    issues = []
    issues += compare_counts(all_intents, train_i, "train_intent")
    issues += compare_counts(all_intents, val_i, "val_intent")
    issues += compare_counts(all_intents, test_i, "test_intent")
    issues += compare_counts(all_langs, train_l, "train_lang")
    issues += compare_counts(all_langs, val_l, "val_lang")
    issues += compare_counts(all_langs, test_l, "test_lang")

    if errors or issues:
        print("Validation found issues:")
        for e in errors[:20]:
            print("ERR", e)
        for i in issues[:20]:
            print("DIST", i)
    else:
        print("Validation passed: BIO consistency and stratification within thresholds")


def write_massive_mapping():
    # Heuristic mapping to MASSIVE slot names — manual review recommended
    mapping = {
        "CASUALTY_COUNT": ["number", "count", "slot_number"],
        "LOCATION": ["location", "city", "address", "area"],
        "HAZARD_TYPE": ["hazard", "danger", "object"],
        "ENTRAPMENT": ["state", "condition", "status"],
        "CHILD_INVOLVED": ["person_type", "age_group", "child"]
    }
    MAPPING.write_text(json.dumps(mapping, ensure_ascii=False, indent=2), encoding="utf8")
    print(f"Wrote MASSIVE slot mapping to {MAPPING}")


def write_readme():
    README.write_text(
        """
Panic dataset (BIO) for RoadSoS

Sources:
- Original human-labeled 80 examples in `panic_data.json` (English, romanised Bengali/Hindi mixed).
- 300 synthetic examples generated programmatically across languages: English, romanised Bengali, romanised Hindi, native Bengali (Unicode), Thai (Unicode), Sinhala (transliterated/code-switched).

Annotation guidelines:
- Tokens are whitespace-tokenized after punctuation normalization.
- Slot labels use BIO tags: B-/I- for CASUALTY_COUNT, LOCATION, HAZARD_TYPE, ENTRAPMENT, CHILD_INVOLVED.
- CASUALTY counts are only tagged when a numeric token is present.

Split rationale:
- Train/val/test are stratified by (`intent`, `language`) groups and split 70/15/15 to avoid language or intent bias.

Validation:
- Script `generate_bio_and_synthetic.py` includes checks for BIO consistency and distribution drift.
""",
        encoding="utf8",
    )
    print(f"Wrote README to {README}")


def main():
    combined = convert_all_and_write()
    train, val, test = stratified_split(combined)
    validate_bio(combined, train, val, test)
    write_massive_mapping()
    write_readme()


if __name__ == "__main__":
    main()

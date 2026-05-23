
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

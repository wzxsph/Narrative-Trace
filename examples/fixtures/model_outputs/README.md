# Model Output Samples

This directory stores redacted model output samples for generation QA.

Rules:

- Do not commit raw provider responses.
- Do not commit API keys, bearer tokens, `.env` values, emails, or private endpoint details.
- Archive samples through `scripts/archive_model_output_sample.py` so each sample has provider, model, prompt set, source, schema, timestamp, and checksum metadata.
- A sample proves that a generation failure or behavior happened; it does not by itself prove the product experience is good.


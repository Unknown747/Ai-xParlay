---
name: Local football data handling
description: User-selected handling rules for the large historical football CSV.
---

The user chose local CSV import as the first data route and supplied a combined CSV covering many leagues and seasons. Preserve all observed seasons and leagues until coverage is inspected; do not automatically narrow it to the 11 leagues and five seasons suggested in `READ.md`. Keep the large source and generated CSV outside Git. Do not add automated scraping or send this dataset to external AI until source terms permit the intended use.

**Why:** the user already has a large dataset and wants the project built in stages; the original source's public terms restrict automated/AI-oriented use.

**How to apply:** keep future ingestion and modeling steps local-first, stream large files, report actual coverage, and revisit AI/source permissions before connecting external services.

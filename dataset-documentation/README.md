# Dataset Documentation

This folder contains dataset documentation for the **GradeAI Pro** project, following the [BU Spark! dataset documentation format](https://github.com/BU-Spark/dataset-documentation/tree/main/dataset-documentation).

## Files

| File | Semester | Description |
|---|---|---|
| `DATASETDOC-sp26.md` | Spring 2026 | Initial dataset documentation — lecture corpus, student submissions, rubric library, ChromaDB index |

## Naming Convention

Semester-specific documentation files follow the pattern:

```
DATASETDOC-[season][2-digit year].md
```

| Season Code | Meaning |
|---|---|
| `sp` | Spring |
| `fa` | Fall |
| `sum` | Summer |

**Examples:** `DATASETDOC-fa26.md`, `DATASETDOC-sp27.md`

## How to Update for Your Semester

1. Copy the latest `DATASETDOC-sp26.md` as your starting point
2. Rename it to match your semester (e.g., `DATASETDOC-fa26.md`)
3. Update all sections — especially chunk counts, model versions, and any new data sources
4. Commit the file to the `dev` branch before your final project submission

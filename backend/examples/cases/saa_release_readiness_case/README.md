# SAA Release Readiness Case

This example simulates a scenario close to reality for preparing an evidence pack for the release readiness section of the statement of work.

## Input data

- `input/knowledge_layers.json`

The file contains summary/detail knowledge layers and source metadata.

## How to launch

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\backend\scripts\demo_saa_release_readiness_case.ps1
```

The script will raise the API, perform a retrieval task on the case and display a short report on the evidence.

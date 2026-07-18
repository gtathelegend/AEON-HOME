# Shared — Cross-layer contracts

This directory contains definitions shared across all three layers
(Arduino firmware, Snapdragon backend, PWA frontend).

## Contents

```
shared/
  schemas/      JSON Schema definitions for all data structures
  protocol/     AEON serial binary protocol specification
  types/        TypeScript types mirroring backend Python dataclasses
  README.md     This file
```

## Schemas

| File                          | Description                              |
|-------------------------------|------------------------------------------|
| `feature_frame.schema.json`   | FeatureFrame — 7-float AI input vector   |
| `capability_token.schema.json`| JWT capability token payload             |

When adding a new data structure:
1. Define the JSON Schema in `schemas/`
2. Add a Python dataclass or Pydantic model in the relevant backend module
3. Add the TypeScript type in `types/index.ts`
4. Keep all three in sync

## Protocol

`protocol/aeon_protocol_v1.md` is the canonical specification for the
binary serial framing used between Arduino and the Snapdragon backend.

The Arduino C++ implementation is in `arduino/libraries/aeon_protocol/`.
The Python implementation is in `backend/aeon/serial/parser.py`.
Both must implement identical frame parsing — the spec is the source of truth.

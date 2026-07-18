# Tests

All tests are in this directory. Each subsystem has its own subdirectory.

## Structure

```
tests/
  backend/      Python pytest tests for the Snapdragon backend
  frontend/     Vitest tests for the React frontend
  arduino/      Unity framework tests for Arduino firmware (host-side)
  integration/  End-to-end tests (requires full hardware stack or simulator)
```

## Running backend tests

```bash
cd backend
pip install -r requirements.txt
pytest ../tests/backend -v
```

## Running frontend tests

```bash
npm run test --run    # single-pass (no watch mode)
```

## Running Arduino tests

Arduino unit tests use the [Unity](https://github.com/ThrowTheSwitch/Unity) framework
compiled for the host machine (no hardware needed):

```bash
cd arduino
# TODO: configure CMake + Unity host build
```

## CI

GitHub Actions workflow runs backend + frontend tests on every push.
See `.github/workflows/ci.yml`.

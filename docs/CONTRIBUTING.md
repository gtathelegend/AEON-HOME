# Contributing to ÆON Home

Thank you for contributing to the ÆON Home project. We welcome your contributions to firmware, backend services, frontend dashboard, or testing infrastructure.

---

## 1. Branch Strategy

- **`main`**: Production-ready branch. Always stable.
- **`develop`**: Integration branch for new features and tests.
- **Feature branches**: Named `feature/<name>` or `bugfix/<name>`, branched off `develop`.

---

## 2. Commit Message Conventions

We follow Conventional Commits format:
- **`feat: ...`**: A new feature (e.g. `feat: add context reasoning`).
- **`fix: ...`**: A bug fix.
- **`docs: ...`**: Documentation updates.
- **`refactor: ...`**: Code changes that neither fix bugs nor add features.
- **`test: ...`**: Adding or correcting tests.

---

## 3. Pull Request Guidelines

Before submitting a Pull Request:
1. Rebase on current `develop` branch.
2. Verify all pytest system integration tests pass locally:
   ```bash
   pytest
   ```
3. Verify that the frontend builds successfully without compiler/linter warnings:
   ```bash
   npm run build
   ```
4. Update the appropriate documentation files in the `docs/` folder.

# Changelog

## 0.10.1 — 2026-10-27

- Added SHA-256 identification and a shared catalog for special TAP/TZX files.
- Added Castle Escape, Forest Escape and Pyramid Escape compatibility patches
  replacing the floating-bus wait with a fixed delay. Exact hashes and original
  code signatures are checked before patching a captured snapshot.
- Added generated Russian and English help tables with hashes, fixes and limits.
- Added patch validation and regression coverage for unavailable floating bus.
- Prepared the first GitHub source import, Windows build automation, portable
  ZIP packaging and reviewed releases with SHA-256 checksums.
- Added a concise bilingual repository overview, detailed usage guide and issue templates.
- Centralized the application version for Python, the GUI and release packaging.

Hardware status: Escape patches still need verification on Delta 128K + AY.
Successful emulation does not establish compatibility with that machine.

## 0.10

- Added loading strategies for verified Dizzy 7 NEW, Fearzone 2018, Yazzie 128,
  New View and MILKY2 dumps.
- Explicitly reject the unsupported Castlevania EN/RU and Dizzy 8 dumps.

Earlier changes are described in README.md and VALIDATION.md.

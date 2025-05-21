# CHANGELOG.md

## SECTIONS (if applicable)
Added: New features or enhancements.
Changed: Backward-compatible changes (e.g., refactoring, config updates).
Deprecated: Features marked for future removal.
Removed: Backward-incompatible removals.
Fixed: Bug fixes.
Security: Security patches (critical to highlight). 

## Roadmap
- Implement additional / all prompt attributes and parameters
- Add ability to use OpenAI
- Update Chat to use json schema for first call and then ignore subsequently instead of warn and skip

## [0.1.2] - TBD
### Added
- Migrated from WrapAIVenice to WrapAI
- threading support in dialog_prompt_runner.py
- Updated dialog_prompt_runner.py
  - to use WSGridLayoutHandler
  - Added ability to change AI model from the default model and if Chat, to maintain memory in new model
- Updated for newest version of WrapAI model dropdown streamlining
- Updated so application, data version and file type changes in settings updates the prompt.json file 

## [0.1.1] - 2025-04-09
### Added
- CHANGELOG.py

### Changed
- main.py
- dialog_prompt_runner.py

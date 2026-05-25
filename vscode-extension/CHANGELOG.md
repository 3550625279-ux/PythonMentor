# Changelog

## [0.1.2] - 2026-05-25

### Fixed
- Backend startup timeout: increased install timeout to 20 min, health check to 120s
- Auto-retry backend startup once on health check failure
- Backend crash now shows "Show Output / Retry" notification instead of silent failure

### Changed
- Removed sentence-transformers / torch dependency (~2GB) — embedding now requires API key
- Added OpenAI-compatible embedding provider
- Added VS Code settings for embedding API key, model, and URL
- Changed pip install from editable mode (-e) to regular install

## [0.1.1] - 2026-05-25

### Fixed
- Student ID configuration now properly passed to backend
- Configure API Keys command now opens correct settings filter

### Changed
- Command titles unified to English
- Description field translated to English for marketplace
- Added MIT license field to package manifest

## [0.1.0] - 2026-05-25

### Added
- Socratic-method AI chat panel in sidebar
- Automatic Python error detection and diagnosis
- RAG knowledge retrieval from built-in knowledge base
- Multi-LLM support (Claude, OpenAI, Ollama)
- One-click backend auto-start on extension activation
- Session management with progress tracking
- Editor context awareness (file, language, selection)

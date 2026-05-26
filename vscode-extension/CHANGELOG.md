# Changelog

## [0.1.6] - 2026-05-26

### Added
- User-configurable LLM parameters in VS Code settings: maxTokens, temperature, topP, contextWindow
- ErrorWatcher debounce (2s) — no more popup spam on every keystroke
- autoStart failure notification — shows error message when backend fails to start
- Port conflict detection — health check exits early if backend process dies
- Session message limit — auto-truncates at 500 messages to prevent file growth

### Fixed
- Shell ENOENT error on Windows — explicit shell path for spawn/exec
- HistoryIndexer TypeError — removed invalid `fallback_model` parameter
- end_session() crash when LLM not configured — now returns clear error
- chatStream retries only on network errors, not HTTP 4xx
- Traceback parser now correctly identifies the innermost error frame
- Mutable default argument in ChatRequest (`context: dict = {}` → `dict | None = None`)
- Emotion detector keyword expansion and case-insensitive matching
- Reduced max_tokens for internal eval/critique/summary calls (was 2048, now 256–512)
- Removed unused `embedding_model` config field (was causing confusion)

## [0.1.5] - 2026-05-26

### Added
- Custom base URL for both Claude (`claudeBaseUrl`) and OpenAI (`openaiBaseUrl`) compatible APIs
- Configurable model names for Claude (`claudeModel`) and OpenAI (`openaiModel`)
- Clear error messages via SSE when LLM or Embedding API key is missing
- Connection error hints with specific troubleshooting per backend type

### Fixed
- Backend returns actionable error instead of generic "Internal Server Error" when API keys missing

## [0.1.4] - 2026-05-26

### Added
- Auto-check both LLM and Embedding API keys on startup — warns if either is missing
- Dual collection RAG (knowledge + history) with distance threshold filtering
- Four-layer dynamic prompt assembly (identity/state/knowledge/strategy)
- Self-critique system with violation logging
- Session end with LLM summary extraction and student profile update

### Changed
- Version bump for marketplace upload

## [0.1.3] - 2026-05-26

### Added
- Auto-check LLM and Embedding API configuration on backend startup — prompts user if either is missing

### Changed
- Added author field and fixed package/publish scripts for marketplace compatibility

### Fixed
- Improved error message when LLM is unavailable (500 errors now show helpful guidance instead of generic "Internal Server Error")

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

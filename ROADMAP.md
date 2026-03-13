# PyRIT MCP Server — Roadmap

This document tracks planned features, enhancements, and known gaps between
the PyRIT MCP Server and the full [PyRIT framework](https://github.com/Azure/PyRIT).

---

## v0.1.0 — Current Release (`main`)

**Status:** Released

- 42 MCP tools across 7 domains
- stdio transport (local, single-user)
- 6 attack orchestrators (Prompt Sending, Crescendo, PAIR, TAP, Skeleton Key, FLIP)
- 3 scorer types (Substring, LLM, Classifier)
- 12 text-to-text converters
- DuckDB in-memory session persistence
- Sandbox mode for safe testing
- Docker and Docker Compose deployment
- VS Code support (Claude Code & GitHub Copilot)
- Claude Desktop support
- 253 tests, 82%+ coverage

---

## v0.2.0 — In Development (`dev` branch)

**Branch:** [`dev`](https://github.com/ncasfl/Pyrit-MCP/tree/dev)
**Status:** Planning / early development

### Transport

- **SSE/HTTP transport** — Enable remote and shared server access beyond stdio.
  This unlocks:
  - Team setups where multiple users connect to a single PyRIT MCP server instance
  - CI/CD pipeline integration for automated red-team testing
  - Deployment on remote infrastructure without requiring local installation
  - Load-balanced server clusters for high-throughput testing

### New Attack Strategies

| Attack | Description | PyRIT Source |
|--------|-------------|-------------|
| Context Compliance | Establishes a permissive context before sending the payload | `context_compliance_attack` |
| Role Play | Instructs the target to adopt a character that would respond harmfully | `role_play_attack` |
| Multi-Prompt Sending | Sends prompts to multiple targets simultaneously | `multi_prompt_sending_attack` |

### New Scorers

| Scorer | Description |
|--------|-------------|
| Azure Content Safety | Uses Azure AI Content Safety API for harm detection |
| Refusal Scorer | Specifically detects when a target refuses to answer |
| Likert Scale Scorer | Scores on a 1-5 scale instead of binary pass/fail |
| Persuasion Scorer | Evaluates persuasion effectiveness across full conversations |
| Insecure Code Scorer | Detects insecure code patterns in responses |

### Authentication

- **Azure Entra (Azure AD)** — Token-based authentication for Azure-hosted models,
  eliminating the need for API key management
- **`.env.local` override support** — Local environment file that overrides `.env`
  without being committed to git

### Other

- Multimodal converter support (audio, image, video, file)
- XPIA (cross-domain prompt injection) workflow tools
- Azure SQL memory backend option for team/multi-session persistence

---

## Future Considerations (unscheduled)

These features exist in PyRIT but are not yet scheduled for a specific release:

### Attack Strategies

| Attack | Description | Notes |
|--------|-------------|-------|
| Chunked Request | Splits a harmful prompt across multiple turns so each message appears benign | Requires complex multi-message state management |
| Many-Shot Jailbreak | Packs many Q&A examples into a single long prompt to prime the model | Requires very large context windows |
| Violent Durian | A specific multi-turn persuasion technique | Experimental in PyRIT |
| Red Teaming (generic) | Generic multi-turn red teaming with custom objectives | Partially covered by Crescendo/PAIR |

### Scorers

| Scorer | Notes |
|--------|-------|
| Human-in-the-Loop | Pauses for manual review — not well-suited to MCP automation flow |
| Prompt Shield | Uses Azure Prompt Shield for injection detection — requires Azure subscription |

### Multimodal Converters

PyRIT supports converters beyond text-to-text that require multimodal target support:

- **Audio converters** — Text-to-speech for audio-based prompt injection
- **Image converters** — Text overlay on images, steganography, visual prompt injection
- **Video converters** — Video-based adversarial content generation
- **File converters** — Convert prompts to PDF, DOCX, or other document formats

### Advanced Memory

- **Azure SQL backend** — Enterprise-grade persistent storage for team environments
- **Memory labels** — Tag and filter conversation entries with custom metadata
- **Embedding search** — Semantic similarity search across stored interactions

### XPIA Workflows

- **Website XPIA** — Inject prompts via web content that a target AI system processes
- **AI Recruiter XPIA** — Test AI-powered recruitment tools for prompt injection vulnerabilities

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for how to get involved.

The `dev` branch is the integration branch for v0.2.0 work. Feature branches
should be created from `dev` and merged back via pull request.

If you'd like to work on a roadmap item, open an issue first to discuss the
approach and avoid duplicate effort.

---

## Workarounds

For PyRIT features not yet exposed as MCP tools, you can:

1. **Use PyRIT directly** via Python scripts for unsupported attack strategies
2. **Import results** into the MCP server using `pyrit_import_dataset_from_file`
   for scoring and reporting
3. **Combine approaches** — use PyRIT for execution and the MCP server for
   Claude-powered analysis and report generation

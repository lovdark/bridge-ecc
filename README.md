# BridgeECC

BridgeECC (BRECC) is an independent, ECC-compatible bridge for cross-harness workflows, command safety, and desktop tooling. It is designed to connect selected ECC capabilities with Hermes, PowerShell, macOS, Windows, Linux, and desktop browser-cockpit environments without requiring a full ECC checkout.

## Project status

Early public scaffold. The first implementation target is a portable PowerShell command-safety bridge with Hermes and desktop adapters.

## Design goals

- Keep the core small and space-conscious.
- Reuse selected ECC ideas and MIT-licensed components with attribution.
- Keep command analysis separate from command execution.
- Fail closed when analysis exceeds a time or work budget.
- Support Hermes, Linux, macOS, Windows, and desktop integrations.
- Use chunked tests so verification remains observable and bounded.
- Never include credentials, private workspace state, or raw sensitive command logs.

## Planned layout

- `core/` — policy schemas, decisions, and portable safety logic
- `adapters/` — Hermes, PowerShell, macOS, Windows, and desktop browser-cockpit bridges
- `skills/` — curated, adapted workflow skills
- `tests/` — core, platform, and compatibility tests
- `scripts/` — bounded test runners and upstream sync helpers
- `upstream/` — pinned source metadata, not a vendored full checkout

## ECC relationship

BridgeECC is independent and is not affiliated with or endorsed by the ECC maintainers unless explicitly stated. ECC is available at https://github.com/affaan-m/ECC. Selected reused material will retain its original license and attribution.

## Development

```text
npm test
```

The test command will remain divided into bounded stages as the project grows.

## License

MIT. See `LICENSE`.

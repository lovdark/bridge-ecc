# BridgeECC

BridgeECC (BRECC) is an independent, ECC-compatible bridge for cross-harness workflows, command safety, and desktop tooling. It is designed to connect selected ECC capabilities with Hermes, PowerShell, macOS, Windows, Linux, and desktop browser-cockpit environments without requiring a full ECC checkout.

## Project status

Runnable Python MVP: `brecc analyze` performs bounded, fail-closed command analysis and returns an allow, review, or deny decision. The analyzer is advisory only; it never executes a command. The runtime uses only the Python standard library and does not require Node.js.

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
python3 -m unittest discover -s tests -p 'test_*.py'
```

Analyze a command locally:

```text
python3 bin/brecc.py analyze "Get-ChildItem ./src"
python3 bin/brecc.py analyze --json "Remove-Item ./build -Recurse -Force"
python3 bin/brecc.py analyze --file ./command.txt
```

Exit status is `0` for allow/review, `1` for deny, and `2` for invalid CLI input. Review findings cover network, privilege, process-control, and dynamic-evaluation operations. Destructive operations and analysis-budget violations deny by default.

The JavaScript files are retained temporarily as historical scaffold material; Python is the canonical implementation and test path.

## License

MIT. See `LICENSE`.

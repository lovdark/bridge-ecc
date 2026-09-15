# BridgeECC

BridgeECC (BRECC) is an independent, ECC-compatible bridge for cross-harness workflows, command safety, and desktop tooling. It is designed to connect selected ECC capabilities with Hermes, PowerShell, macOS, Windows, Linux, and desktop browser-cockpit environments without requiring a full ECC checkout.

## Project status

Runnable Python-first compatibility MVP: `brecc analyze`, `brecc catalog`, `brecc validate`, `brecc doctor`, and `brecc adapters` provide policy, discovery, validation, diagnostics, and adapter capability contracts. The analyzer is advisory only; it never executes a command. The runtime uses only the Python standard library and does not require Node.js.

## Design goals

- Keep the core small and space-conscious.
- Reuse selected ECC ideas and MIT-licensed components with attribution.
- Keep command analysis separate from command execution.
- Fail closed when analysis exceeds a time or work budget.
- Support Hermes, Linux, macOS, Windows, and desktop integrations.
- Use chunked tests so verification remains observable and bounded.
- Never include credentials, private workspace state, or raw sensitive command logs.

## Planned layout

- `core/` — policy, catalog, diagnostics, and portable safety logic
- `adapters/` — Hermes, optional Node.js, PowerShell, and POSIX bridges
- `skills/` — curated, adapted workflow skills
- `tests/` — core, platform, and compatibility tests
- `scripts/` — bounded test runners and upstream sync helpers
- `upstream/` — pinned source metadata, not a vendored full checkout

## ECC relationship

BridgeECC is independent and is not affiliated with or endorsed by the ECC maintainers unless explicitly stated. ECC is available at https://github.com/affaan-m/ECC. Selected reused material will retain its original license and attribution.

## Development

```text
python3 -m unittest discover -s tests -p 'test_*.py'
# Optional editable install; exposes the `brecc` command
python3 -m pip install -e .
```

Analyze a command locally:

```text
python3 bin/brecc.py analyze "Get-ChildItem ./src"
python3 bin/brecc.py analyze --json "Remove-Item ./build -Recurse -Force"
python3 bin/brecc.py analyze --file ./command.txt
python3 bin/brecc.py doctor . --json
python3 bin/brecc.py adapters --json
python3 bin/brecc.py catalog /path/to/ecc --json
python3 bin/brecc.py validate /path/to/ecc --json
```

Exit status is `0` for allow/review, `1` for deny, and `2` for invalid CLI input. Review findings cover network, privilege, process-control, and dynamic-evaluation operations. Destructive operations and analysis-budget violations deny by default.

Node.js is an optional compatibility adapter for ECC scripts that have not yet been ported. It uses argument arrays, never shell interpolation, and reports a clear unavailable result when Node is absent. Python is the canonical implementation and test path.

## License

MIT. See `LICENSE`.

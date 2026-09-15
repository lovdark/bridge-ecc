# BridgeECC

BridgeECC (BRECC) is an independent, ECC-compatible bridge for cross-harness workflows, command safety, and desktop tooling. It is designed to connect selected ECC capabilities with Hermes, PowerShell, macOS, Windows, Linux, and desktop browser-cockpit environments without requiring a full ECC checkout.

## Project status

Runnable Python-first compatibility MVP: `brecc analyze`, `brecc catalog`, `brecc validate`, `brecc plan`, `brecc profiles`, `brecc ecc-plan`, `brecc doctor`, and `brecc adapters` provide policy, discovery, validation, read-only installation planning, ECC profile resolution, diagnostics, and adapter capability contracts. The analyzer is advisory only; it never executes a command. Golden policy fixtures cover safe, review, chained, dynamic, Git, container, infrastructure, PowerShell, and shell cases. The runtime uses only the Python standard library and does not require Node.js.

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
- `adapters/` — Hermes, hooks, optional Node.js, PowerShell, Windows, and POSIX bridges
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
python3 bin/brecc.py plan /path/to/ecc /target/path --component skill --json
python3 bin/brecc.py profiles /path/to/ecc --json
python3 bin/brecc.py ecc-plan /path/to/ecc developer --target hermes --home-dir "$HOME" --json
```

Exit status is `0` for allow/review, `1` for deny, and `2` for invalid CLI input. Review findings cover network, privilege, process-control, and dynamic-evaluation operations. Destructive operations and analysis-budget violations deny by default.

Node.js is an optional compatibility adapter for ECC scripts that have not yet been ported. It uses argument arrays, never shell interpolation, and reports a clear unavailable result when Node is absent. Python is the canonical implementation and test path. The policy layer denies destructive Git, container, infrastructure, disk, deletion, and shutdown operations; it reviews network, privilege, process-control, and dynamic-evaluation operations.

`plan` and hook adapters are read-only. They describe proposed copy actions or return approval contracts; they do not modify the filesystem or execute commands.

The validator has been smoke-tested against the inspected ECC checkout: 1,163 component files checked with zero validation errors.

The ECC profile resolver has been compared with ECC’s own `developer`/`hermes` plan: selected modules and target-skipped modules match, including transitive dependency ordering.

Supported target roots currently mirror ECC’s registry: Claude, Cursor, Antigravity, Codex, Gemini, Hermes, OpenCode, OpenClaw, CodeBuddy, JoyCode, Kimi, Qwen, and Zed. Target resolution is read-only and distinguishes home-scoped targets from project-scoped targets.

## License

MIT. See `LICENSE`.

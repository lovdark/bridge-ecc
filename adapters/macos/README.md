# macOS adapter

On macOS, use the POSIX adapter in `adapters/posix.py`. It reports the available `sh` executable and builds argv-only invocations. No macOS-specific runtime is required by the Python core. Swift/AppKit clients can consume the same JSON contracts.

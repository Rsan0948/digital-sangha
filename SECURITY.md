# Security Policy

## Reporting a vulnerability

Digital Sangha runs locally (loopback bind, optional Electron shell), so many
classes of vulnerability are out of scope by construction. The categories that
*are* in scope:

- Bugs that allow a non-loopback origin to reach a backend HTTP endpoint or
  WebSocket.
- Bugs that expose `data/encryption.key`, `config.yaml`, Spotify tokens stored
  in `data/sangha.db`, or LLM API keys held in environment variables /
  `config.yaml`.
- CSRF, prompt-injection, or origin-confusion bugs that bypass the Spotify
  OAuth state check or the WebSocket origin allowlist.
- Supply-chain risks introduced by pinned dependencies.

To report a vulnerability in the categories above:

1. **Do not open a public issue.**
2. Open a private security advisory at
   https://github.com/Rsan0948/digital-sangha/security/advisories/new with a
   description, reproduction steps, and any logs or artifacts that demonstrate
   the issue.

## Response time

A maintainer will acknowledge the report within 7 days and provide an initial
assessment (in scope / out of scope, severity, expected fix horizon) within
14 days. Fixes for in-scope issues land via a private branch and are disclosed
in the matching `## [X.Y.Z]` section of [CHANGELOG.md](CHANGELOG.md) under
"Security" when a release tag is cut.

## What is not in scope

- Issues that require physical access to the user's machine.
- Bugs in third-party cloud LLM providers (OpenAI, Anthropic, Google, DeepSeek)
  themselves — report those upstream.
- Issues that depend on a user installing a malicious browser extension or
  running the backend on a non-loopback interface against the documented
  configuration.

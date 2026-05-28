# OSS License Rationale

Update date: 2026-04-30

## Recommended license

`Apache License 2.0`.

## Why Apache-2.0

1. Permissive license, convenient for integration into enterprise circuits.
2. Explicit grant for patents, which reduces legal uncertainty for users of the framework.
3. Compatible with the "internal-first -> external contributors" model.
4. Well suited for mixed-stack infrastructure projects with API/MCP/contracts.

## Alternatives considered

- MIT:
- simpler text, but there is no explicit patent grant.
- BSD-3-Clause:
- also permissive, but often less familiar to enterprise AI/platform tooling than Apache-2.0.

## Conclusion

For the current project profile (`framework + integrations + OSS extension path`), Apache-2.0 provides the best balance of openness and legal predictability.

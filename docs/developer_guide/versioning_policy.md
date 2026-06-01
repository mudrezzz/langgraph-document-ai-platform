# Versioning & Deprecation Policy

Update date: 2026-04-30
Status: Active (P1 policy)

The policy defines how the project versions documentation and public API/MCP contracts.

## 1. Contract surface authority

Source of stability limits:

- `docs/developer_guide/public_contract_surface.md`
- `docs/developer_guide/api_reference.md`
- `docs/developer_guide/mcp_reference.md`

If a change is not reflected in these documents, it is not considered an official update to the public contract.

## 2. Stability levels

- `Stable`: supported contracts; breaking changes are prohibited without window deprecation.
- `Experimental`: breaking changes between increments are allowed.
- `Internal`: no external compatibility guarantees.

## 3. Versioning units

The project uses two independent versioning layers:

1. Documentation increment (`README`, architecture status, backlog notes).
2. Contract surface version (`public_contract_surface vN`).

Recommended principle:

- additive change in stable contract -> `vN` (minor description update);
- breaking change in stable contract -> `vN+1` + deprecation window and migration notes.

## 4. Deprecation policy

For stable API/MCP contracts:

1. Declare deprecation in docs (`public_contract_surface`, reference docs, changelog note).
2. Save the old contract for at least one documentation increment, if technically possible.
3. Add migration path (what should the client change).
4. After removal, update:
   - `public_contract_surface`
   - `api_reference`/`mcp_reference`
   - `docs/DOCS_BACKLOG.md`

For experimental contracts deprecation, the window can be shortened, but a migration note is required.

## 5. Breaking change checklist

Before making a breaking change to the stable surface:

1. Confirm the need and scope.
2. Update policy docs and references.
3. Add/update smoke/tests confirming the new contract.
4. Update release docs with triage and rollback note.

## 6. Version tags in docs

It is recommended to mark key documents:

- `Update date`
- `Status`
- if necessary `Contract Surface: vN`

This reduces desynchronization between code and documentation during fast increments.

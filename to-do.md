# To Do — F5.5 Read-through data blocks (opt-in)

F5.1 to F5.6 landed; their records are in the git history. F5.5 is the open feature in Epic 5.
The provider facts are verified (see `backlog.md`, Epic 5 decisions), so the feature is not blocked;
`acceptance.md` must be overwritten with the F5.5 criteria before the code.

## Decisions taken

1. Plain strings stay the default. A `data` block is emitted only for a name outside the run, and only
   for a scope the run declares, so a run that declares nothing writes the same bytes as before.
2. `DATA_SOURCE_SCHEMA` is data in `resource_mapping.py`, one row per type, written from the provider
   `data_source_schemas` and pinned by a test that reads the live schema, the way `LOCATION_SCHEMA` is.
   No attribute name comes from memory.
3. A read-through run must be labelled in the generated `README.md`, because a `data` block resolves at
   plan time and fails at plan, not at validate.
4. The gate must read a `data` block. `sanity_checks.py` reads only `resource` blocks today, so a run
   without `--validate` checks no `data` block. The new rule reads `location` and the sub-block shape,
   and `name` where the type declares one. `validate` enforces the required pair for the 106 types that
   have both, so the gate rule is the offline check, not a replacement for validate.

## Pieces

- [ ] `resource_mapping.py`: `DATA_SOURCE_SCHEMA`, verified against the provider `data_source_schemas`
      through the `provider_schema` fixture, which runs offline when the terraform binary and the
      provider cache are present.
- [ ] `sanity_checks.py`: read `data` blocks as blocks of their own (the gate reads `resource` blocks
      only). The rule: `location` present, every `location` sub-block one that `DATA_SOURCE_SCHEMA` or
      `LOCATION_SCHEMA` declares for the type, and `name` where the type declares one.
- [ ] The emit path: which name becomes a `data` block, and what the block holds (the type, the name,
      the location, and nothing else). A reference that resolves inside the run stays a plain string.
- [ ] A rule for the reports: a read-through name is not an entry the parse read, so the entry report,
      the property scan, and the shadow scan must not count it. State which section, if any, names it.
- [ ] The generated `README.md`: label a read-through run, so a reader knows the plan will call the API.
- [ ] Tests: the table against the live schema, the new gate rule (each violation detected, no false
      positive on the corpus), the opt-in path (a run that declares no read-through scope writes the
      golden bytes), and the label.
- [ ] Docs: `docs/ARCHITECTURE.md` §4 (the data block shape) and §4.6 (the gate rule),
      `docs/USAGE_GUIDE.md` and `README.md`.

## Open items for this feature

- The 22 data sources with no `name` attribute need the gate rule stated per shape, because a rule that
  requires `name` would refuse a settings or policy data block that is correct.
- A data source that returns a collection (`panos_addresses`) has no entry name to key, so it cannot
  feed a per-entry fact. Decide whether it is in scope at all.
- The coverage matrix has no row for a `data` block, so a property finding cannot name one. The gate
  rule is the only check that reads a `data` block.

## Related planning (not this feature)

Epic 6 planning landed on 2026-10-27 in `docs/CODEBASE_ASSEMBLY.md`: the unit, ownership, the order
between units, the import path, the site data layer, and the commit action. F5.5 is the first half of
the reference mechanism, so the codebase rule in `docs/CODEBASE_ASSEMBLY.md` §5 depends on this feature.
F5.5 stays the current feature; the Epic 6 pieces are not started.

# Acceptance Criteria: F3.1 Keyed data model

## Goal

Replace name-keyed storage and name deduplication in the parser with a keyed
data model. Each parsed object and rule is identified by
(device group, vsys, type, name). Objects that share a name but differ in
device group or vsys are distinct objects and all survive parsing.

## Context

- Epic 2 is complete. F3.1 is the first Epic 3 feature.
- Today the parser visits many elements twice (a broad XPath plus narrower
  XPaths in the same method) and hides the double visits behind two dedup
  patterns: first-wins `seen_names` sets and name-keyed dicts (last-wins).
- The pinned xfail `tests/test_edge_cases.py::test_dup_names_across_dgs_both_survive`
  states the desired behavior: same-named objects in different device groups
  must both survive.
- The F2.7 naming contract (sanitized name + 8-hex digest of source identity,
  order-independent, collision-safe, per-type domains) must stay intact.
  Same-named objects in different device groups already get distinct local
  names because the digest includes the defining device group.

## Done criteria

1. Every parse method visits each XML element exactly once (single broad path
   per element kind, document order). No `seen_names` first-wins sets and no
   name-keyed last-wins dicts remain in the parser.
2. Every parsed object and rule carries its identity fields: `device_group`
   (defining device group, or `Shared` for shared/template-scope) and `vsys`
   (nearest `<vsys><entry>` ancestor, or `vsys1` when the export omits the
   vsys wrapper). The key is (device group, vsys, type, name).
3. Same name across device groups: both objects parse (pinned xfail now
   passes; the old last-wins test is replaced).
4. Same name across vsys: both objects parse (new fixture + test).
5. Entry references (an entry with only `<id>`) are still skipped: they are
   pointers to a shared definition and carry no content.
6. References resolve to the defining object: `name_ref` accepts the
   referrer's context and resolves in the order (referrer context, Shared,
   template scope), with a flat fallback so context-less call sites and
   brown-field references keep working. Undeclared names stay plain strings.
7. The F2.7 naming contract tests pass unchanged: sanitized name + digest,
   order-independence, collision safety, per-type domains, no dangling refs.
8. Golden files for `sample` and `kitchen_sink` stay byte-identical or are
   regenerated deliberately with a reviewed diff (no accidental churn).
9. The full test suite passes (pytest -q), including the now-passing
   both-survive test with the xfail marker removed.
10. `terraform init` + `terraform validate` still pass for the wired fixture
    (dependency_wiring) when the terraform binary is present.

## Out of scope (Epic 3 follow-ups)

- vsys in `location` blocks (F3.5).
- Template-stack association and template-name contexts (F3.6).
- Splitting large rule resources (F3.3); template-variables (F3.4).
- The `split_device_groups.py` splitter (separate tool, unchanged).

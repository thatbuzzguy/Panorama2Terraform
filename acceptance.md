# Acceptance Criteria: F3.2 Preserve device-group association

## Goal

Carry the full source identity — (device group, vsys, type, name) — from
parse to emit. Same-named objects in different device groups or virtual
systems both survive, get distinct order-independent local names, and
every reference resolves by the referrer's own identity.

## Context

- F3.1 landed the keyed data model: the parser visits each entry once
  and records `device_group` + `vsys` on every object and rule.
- The device-group axis already carries to emit (verified this
  session): same-named objects in two device groups emit as distinct
  resources, references wire to each group's own objects, and
  `terraform validate` is green.
- Verified gap (reproduced with the committed fixtures):
  - same-named objects in two vsys share one digest
    (`web_6cc15ec0` vs `web_6cc15ec0_2`); the taken-name counter
    decides which one gets the base name, so the assignment flips when
    the XML order flips (violates the F2.7 order-independence
    contract);
  - a rule in vsys1 that references the shared name resolves to the
    vsys2 object when vsys2 is declared first (the reference chain
    ignores the referrer's vsys).
- F3.5 will add vsys to `location` blocks; F3.2 covers the naming
  digest and reference resolution only.

## Done criteria

1. `declare_resource_name` computes the digest from (scope, context,
   vsys, name) — the F3.1 identity key — and registers the local name
   under (scope, context, vsys, name); the flat (scope, name) index and
   the taken-name guard stay as before.
2. Every declare site (all 30) passes the object's `vsys`.
3. `name_ref` resolves in the order (referrer context, referrer vsys),
   then (Shared, referrer vsys), then (contextless, referrer vsys),
   then the flat first-declaration fallback. Undeclared names stay
   plain brown-field strings.
4. Every reference site passes the referrer's `vsys`.
5. Same name across vsys: both objects emit as distinct resources with
   distinct digests (no `_2` counter), and the identity-to-name
   assignment is unchanged when the XML entry order flips (two-order
   test).
6. A rule in one vsys that references a name defined in two vsys
   resolves to the same-vsys object regardless of declaration order
   (extended fixture + test).
7. Policy chains key on (device group, vsys): one vsys's rules never
   pivot on another vsys's rule (chain-boundary test).
8. The F2.7 naming contract tests pass unchanged: sanitized base +
   8-hex digest, order-independence, collision safety, per-type
   domains, no dangling references.
9. The F3.1 context tests pass: the referrer's device group wins, then
   Shared, then the contextless bucket, then the flat fallback.
10. Goldens for `sample` and `kitchen_sink` regenerate with a reviewed
    diff limited to local names (resource addresses, references,
    depends_on) — no attribute or value changes.
11. Gates: ruff clean; pytest -q green; `terraform init` +
    `terraform validate` green on the golden and fixture outputs.
12. Docs: the README "Resource naming" section states the digest input
    (scope, context, vsys, name); agent-status records the session.

## Out of scope

- vsys in `location` blocks (F3.5).
- Template-name contexts (F3.6).
- Per-device-group report keying (F3.9).
- Rulebase (pre/post/shared) tracking (backlog; lands after F3.1).

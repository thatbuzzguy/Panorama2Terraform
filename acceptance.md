# Acceptance Criteria — F2.7: Collision-safe naming

## Goal
Local Terraform resource names must be deterministic (independent of
emission order) and collision-safe. Today the first declaration of a
sanitized base name keeps it and later colliding declarations get
order-dependent counters (`a_b`, `a_b_2`, `a_b_3`): the same input in a
different order produces different names, and a reference site cannot
recompute the name. F2.7 builds every local name from the sanitized
name plus a short hash of the object's source identity.

## Design

`TerraformGenerator.declare_resource_name(name, scope, context)`:

- `base = sanitize_name(name)` or `unnamed` for an empty name.
- `digest = sha256(f'{scope}|{context}|{name}').hexdigest()[:8]`.
  The digest is a short hash of the object's source identity — its path
  in the export: the resource type, the device group or template that
  defines it, and the PAN-OS name (case-sensitive; it must be the raw
  name, not the sanitized one, so `a-b` and `a_b` differ).
- Local name = `base_digest`; if that address is already taken in the
  scope (a true duplicate declaration or a digest collision), append
  `_2`, `_3`, ... so the output is always valid HCL.
- `name_ref` is unchanged: `(scope, name)` registry, first declaration
  wins, plain string for undeclared names. Context-aware resolution is
  F3.1.

## Definition of Done

1. **Deterministic names.**
   The local name of an object depends only on its identity, not on
   emission order or run count: declaring the same objects in different
   orders assigns each the same name. A duplicate declaration of the same
   identity gets the counter suffix, so the output stays valid HCL.
2. **Colliding names.**
   `a-b`, `a_b`, `A-B` in one scope yield three distinct names, each
   matching `^a_b_[0-9a-f]{8}$`. The same PAN-OS name in two contexts
   (for example two device groups) yields two distinct names of the
   same shape.
3. **Empty names.**
   An empty name yields `unnamed_<digest>` — a valid, stable resource
   name; the counter guard still applies.
4. **References unchanged.**
   `name_ref` still returns an `HclRef` for declared names, a plain
   string for undeclared ones, object scope before group scope, and
   never a reference to an undeclared resource.
5. **Tests.**
   - `tests/test_robustness.py`: collision and same-context tests
     rewritten to the hashed shape; new tests for order-independence,
     empty-name stability, and per-raw-name reference resolution.
   - `tests/test_dependency_wiring.py`: hardcoded local names replaced
     by lookups on the PAN-OS `name` attribute so the suite does not
     depend on the naming scheme; the no-dangling-reference invariant
     and the terraform gate stay.
6. **Goldens.**
   `sample` and `kitchen_sink` regenerate; `terraform validate` passes
   on both.
7. **Docs.**
   README gains a short "Resource naming" note; backlog and
   to-do/PLAN/agent-status entries updated; commit.

## Gate

- `ruff check .` clean
- `pytest` green (terraform validate gates run when terraform exists)
- `terraform validate` green on the sample and kitchen-sink outputs

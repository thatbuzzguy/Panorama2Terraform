# Acceptance — F1.7: Security and robustness tests

## Purpose
Prove the converter and splitter behave safely on hostile or degenerate
input, and fix the gaps the tests expose.

## Hostile input (must fail cleanly: non-zero exit, no traceback, no data leak)
1. Entity expansion ("billion laughs" internal DTD).
2. External entity reference (XXE, `SYSTEM "file://..."`).
3. Not well-formed XML (illegal control character in text).

## Degenerate input (must produce valid output or skip safely)
4. Object names containing tab and carriage return: the generated .tf
   must contain no raw control characters (HCL strings only allow
   escaped forms). FIX `escape_string` accordingly.
5. Entries without a `name` attribute: skipped, no crash.
6. Sanitization collisions: PAN-OS names `a-b`, `a_b`, and `A-B` all
   sanitize to `a_b` today, producing duplicate Terraform resource
   addresses (invalid HCL). FIX with a per-type name registry that
   suffixes duplicates; references recompute the same input string and
   therefore resolve to the same name.

## Non-goals
- No deep-nesting memory DoS hardening (record in backlog; would need a
  size limit on input, a product decision).
- No Epic 2/3 behavior changes.

## Done when
- tests/test_robustness.py passes (green tests pin the fixes; hostile
  cases assert clean failure).
- Golden files byte-identical (no collisions in sample/kitchen sink).
- ruff clean; full suite green.
- Committed with an ASD-STE100 message.

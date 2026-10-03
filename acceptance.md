# Acceptance — F2.1: Provider baseline

## Purpose
Pin the generated `provider.tf` to a v2 range that is actually verified,
and record that range in the docs.

## Facts established
- The registry's latest 2.x release is **2.0.14** (the audit's reference
  version, 128 resource types).
- The generator currently pins `~> 2.0.7`, which predates six 2.0.x
  releases and is not the version any test has verified.

## Changes
1. `generate_provider_config` emits `version = "~> 2.0.14"` with a
   comment recording that 2.0.14 is the verified v2 baseline.
2. Goldens (sample + kitchen-sink) regenerated; only `provider.tf` may
   change in each set.
3. README provider-version lines updated from 2.0.7 to 2.0.14
   (recording the supported range; claim verification is F2.11).

## Verification (auto-retarget)
- F1.4 conformance test reads the pin from the golden `provider.tf`, so it
  re-runs against 2.0.14 with the same expected split: 43 xfailed,
  13 xpassed (13 missing types, missing `location` — Epic 2 work).
- F1.5 `terraform init` gate stays green.
- Full gate: ruff clean; pytest 106 passed, 46 xfailed, 13 xpassed.

## Non-goals
- No emitter changes (F2.2–F2.4).
- No README coverage-claim rewrite (F2.11).

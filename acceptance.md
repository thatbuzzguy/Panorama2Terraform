# Acceptance — F1.6: Fixture corpus for edge cases

## Purpose
Build the shared edge-case fixture set (the test asset all three epics
build on) and pin current behavior with tests. Red→green markers point at
the epic that must change behavior.

## Edge cases (per PLAN.md F1.6)
1. **Quoted device-group names** — DG names containing single and double
   quotes. The splitter builds XPath with an f-string, which breaks on
   single-quote names. FIX the splitter to match attributes in Python
   (no string interpolation), then pin with a test.
2. **Duplicate names across device groups** — same object name in two DGs.
   Current: last-wins (one entry). Pin current behavior (green) and add
   an xfail asserting both entries survive (Epic 3 F3.1 keyed model).
3. **Multi-vsys** — objects under vsys1 and vsys2. Pin: both are parsed.
   (vsys scoping in output is Epic 2 F2.3 / Epic 3.)
4. **Mixed virtual and logical routers** — VR in a template plus LR in a
   vsys, static routes with next-vip and next-vr nexthops. Pin: both
   routers and all routes parse with correct attribution.
5. **IPv6** — an IPv6 address object. Pin: IPv4 parses. xfail: IPv6 keeps
   its value (currently dropped to an empty entry; Epic 2 F2.4).
6. **Multi-port services** — a tcp service with a port list and a dual
   tcp/udp service. Pin current behavior: port list passes through; dual
   protocol keeps tcp only (udp loss recorded in backlog).

## Non-goals
- No Epic 2/3 behavior changes. Red→green cases are xfail.
- No golden regeneration (edge fixtures are parser-level; the kitchen sink
  remains the generator's golden source).

## Done when
- Six `edge_*.xml` fixtures under tests/fixtures/.
- tests/test_edge_cases.py passes with the intended xfail set.
- Splitter no longer breaks on single-quote DG names.
- ruff clean; full suite green.
- Committed with an ASD-STE100 message.

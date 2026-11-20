# Acceptance — the golden set and the printed rule output re-measured (Epic 9, Piece 21, Phase 9D)

Criteria set 2026-11-19 for Piece 21, the piece that closes Epic 9: re-measure the whole golden set and the
pins that name the printed rule output as they now read with the rule data pair, the iterated block, and the
retargeted F2.5 key-order rule. No generator change is expected; a number that a pin states as a measurement
must be the number the current tree answers.

## Criteria

1. **The golden set.** Each golden case is the output of one run on the source the case names, so the pin reads
   the set through the four cases `tests/test_golden_files.py` holds. Every golden `.tf` file must equal the
   bytes a real run wrote for that case. A golden that already agrees with the run stays unchanged; a golden
   that disagrees moves only by copying the run's output, never by editing a file.
2. **The pins that name a printed set** state the number as a derivation read from the same door the pin reads,
   and the measurement is re-taken on the current tree:
   - the resource-line patterns in `tests/conftest.py`: the `.tf` file counts, the match count the three shapes
     answer, the count of resource lines without the block brace, and the two capture-group counts;
   - the report counts for the sample run and the kitchen-sink run: the `.tf` set, the data-file set, and the
     resource count;
   - the rule data pair's file set inside the unit directories its rows name;
   - the round-trip cross-check's corpus table, the fixture count and the category split;
   - the printed rule blocks, the rows behind them, and the map entries, across the corpus and the goldens.
   A measurement that no longer holds is restated as the number the tree answers, with the date it was read.
3. **F2.5, the definition of done.** A pin must show the apply order equals the XML order through the key order.
   Inside one iterated block the apply order is the order the printed map holds its entries, which is the sorted
   key order, and the key is the chain ordinal joined to the unit digest, so the two orders are the same order
   whenever one unit holds one chain per rule type. The corpus must be read, not one fixture and two golden
   parts: where the corpus fact is not pinned, add the pin.
4. **Pin honesty.** No pin is weakened and no pin measures nothing. A pin that measures content must still
   measure content through a run, not a hand-built row.

## Pins this piece moves

- `tests/test_policy_order.py`: one new pin for the key order read across the accepted corpus, and the module's
  header names the corpus as the material the pin reads.
- `tests/conftest.py`: the resource-line pattern comment's measurement, restated as the numbers the current tree
  answers.
- `tests/test_golden_files.py`: the header names the golden set as the four cases the module holds, which is the
  set the pins read.
- `README.md` §Testing names `tests/test_policy_order.py`, so its entry names the corpus half the new pin reads.

## Gate

`ruff check .`, `ruff format --check .`, `python3 tools/check_documents.py`, `python3 -m pytest`, in that
order, single process, conservative threads.

Before, measured 2026-11-19 on the committed tree at `4a5868c`: `ruff check .` clean at `py310`,
`ruff format --check .` clean on the 103 Python files, 1,718 pins in 53 test modules — 1,714 pass, with the same
4 skip for the missing `tflint` binary — and `python3 tools/check_documents.py` reports no finding.

After, measured 2026-11-19 on the final tree: `ruff check .` clean at `py310`, `ruff format --check .` clean on
the 103 Python files, `python3 tools/check_documents.py` reports no finding, and `python3 -m pytest` passes 1,715
pins with the same 4 skip for the missing `tflint` binary. 1,719 pins in 53 test modules, against 1,718 before,
and the one module that moved is `tests/test_policy_order.py`, 8 -> 9, which is the corpus pin. No pin was
removed and no pin was weakened, so the count can only have gone up.

## Measurement, read 2026-11-19

- Golden set, read through the four cases `tests/test_golden_files.py` holds: 87 `.tf` files, 14 in `sample`, 61
  in `kitchen_sink`, 3 in `single_unit`, 9 in `filter_containers`. All 87 equal the bytes the run wrote, so no
  golden moves in this piece.
- Corpus run on the 66 accepted fixtures: 584 `.tf` files. The three shapes the test set held before answer the
  same 387 matches on the goldens plus the corpus run (87 + 584 files), 0 resource lines lack the trailing brace,
  and the capture groups answer 42 distinct types and 238 distinct addresses. The numbers recorded on 2026-11-13
  (414 matches, 262 addresses) no longer hold, because the iterated block prints one block per rule type per unit
  instead of one block per rule.
- Printed rule output, corpus: 18 blocks over 9 fixtures, 37 rows, 37 map entries, 0 units holding more than one
  chain, and the printed entry order is the XML order for all 18 blocks.
- Printed rule output, goldens: 6 blocks, 12 rows, 12 map entries, and the printed entry order is the XML order
  for all 6.
- Report counts: sample run 14 `.tf` files, 4 data files, 17 resources; kitchen-sink run 61 `.tf` files, 8 data
  files, 64 resources.
- Round-trip cross-check across the corpus: 19 facts on 8 fixtures, 3 + 15 + 1 by category, and no fact names a
  rule row. `check_data_files` and `check_rule_blocks` report 0 findings across the corpus.

## Result

The golden set is unchanged: every golden already agreed with the run. The measurement that moved is the
resource-line pattern comment in `tests/conftest.py`. One pin is added in `tests/test_policy_order.py` for the
key order read across the corpus, which is the F2.5 definition of done, so no pin is weakened and no pin measures
nothing. Two documents named the emitted rule shape as one block per rule with a per-instance pivot and
`depends_on`, which is the shape the iterated block replaced: `docs/ARCHITECTURE.md` §4.4 and the README resource
table, and both now state the key order as the apply order. `tests/test_golden_files.py`'s header named the golden
set as two pipeline runs, which is not the set the pins read, so it names the four cases.

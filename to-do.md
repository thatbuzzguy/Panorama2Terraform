# To Do

No feature is in progress. Epic 5 is complete; F5.5 (read-through data blocks) landed on
2026-10-28 and its record is in the git history.

## Next feature (not started)

Epic 6 (codebase assembly), `PLAN.md`. The design record is `docs/CODEBASE_ASSEMBLY.md`. F6.1
(unit boundary as data) is the first piece, because F6.2, F6.3 and F6.4 all need the unit.

The decisions F6.1 needs before code:

1. The directory naming rule: one directory name per declared scope.
2. The manifest data shape: the four scope facts, the directory, the entry count, and the names the
   unit references from outside itself.
3. Whether the manifest is one file per codebase or one file per unit.

Write `acceptance.md` with the F6.1 criteria before the code.

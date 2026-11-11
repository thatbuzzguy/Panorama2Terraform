# Acceptance criteria — the phase 2 history rewrite

## Scope

The rewrite moves the 46 phase 2 commits from `dev` into the main line, so `git log` shows the
per-commit detail instead of the two squashed Feature Drop commits, and it sets the author on those
commits to `rdavidbrown@live.com`. It changes no file content and no commit message. The 9 commits
from the original upstream keep their hashes and their author
`devnullNZ <gordon@gswsystems.com>`.

The rewrite lives on the branch `history-rewrite` in the worktree
`/home/ryan/.local/share/opencode/worktree/1670f9/history-rewrite`. No branch pointer is moved, and
nothing is pushed, until the landing is confirmed.

## The criteria

1. **The 9 upstream commits keep their hashes.** The rebase starts at `74cf4c0`, the last commit of
   the original upstream, so those commits are not replayed and cannot change.
2. **The two squashed commits are replaced by the commits that produced them.** Feature Drop 1
   (`28e6e10`) has the same tree as the dev commit `3e60c44`, which is the first 20 phase 2 commits;
   Feature Drop 2 (`bf9b577`) has the same tree as the dev tip, which is the last 26. So the squashes
   lost nothing, and the detail did not need to be written again.
3. **Each rewritten commit keeps its message, its tree and its author date.** Only the author and the
   committer change. The committer comes from the git config, so a replayed commit names
   `rdavidbrown@live.com` for both.
4. **The replay of the 122 later commits changes nothing.** Each commit after Feature Drop 2 has the
   same tree, the same message and the same author date as the original. The replay ran with no
   conflict.
5. **The final state matches the current `development` tip tree.** The landing point is the commit
   whose tree equals `development`'s tip; the tracking commit that records this page sits after it.
6. **The main line has no merge commits.** The two PR merge commits on `origin/main` (`708f546`,
   `3ae014f`) are dropped, and `main` fast-forwards to the rewritten line.
7. **The chronology stays in date order.** The phase 2 commits (October 2 to 20) sit before the later
   work (October 26 onward), because the replay keeps each author date.

## Measured

Run `bash /tmp/opencode/verify_history_rewrite.sh` from the worktree or the main checkout. The script
compares each commit with its original by commit hash for the upstream set, and by tree hash, message
and author date for the rewritten sets.

- Segment 1 (upstream, 9 commits): 0 mismatches.
- Segment 2 (phase 2, 46 commits): 0 mismatches, and every author reads `rdavidbrown@live.com`.
- Segment 3 (later work, 124 commits including the two F8.9 commits): 0 mismatches.
- Final tree: `history-rewrite` = `1522c0d3c88310fb44bfd8725f16cc527e167bf5` = `development` tip.
- Commit count: 177 = 9 + 46 + 122 + 2, with 0 merge commits.
- Authorship: 168 `Ryan Brown <rdavidbrown@live.com>`, 9 `devnullNZ <gordon@gswsystems.com>`.
- Test run: unchanged, because no tool module and no test file changes in the rewrite. The suite reads
  1650 pins, and `ruff check .` is clean.

## The pieces that stay open

- The landing: point `development`, `dev` and `main` at the rewritten line, which needs a force-push,
  and drop the two PR merge commits.
- The `licensing` branch, 4 commits on top of `development`, needs the same rebase.
- Commit hashes written inside historical files are stale for the rewritten commits, because a commit
  cannot name its own new hash. The tracked markdown names no commit hash, so the final state needs no
  change for this.

# Agent memory — synced through the repo

This directory is the persistent memory of the Claude Code sessions working on this
repo (one fact per file, indexed in `MEMORY.md`). It is checked into git so it travels
to every machine; on each machine it is **symlinked into the session's native memory
location**, so memory reads/writes keep working transparently and every new memory
lands in version control.

## Bootstrap on a new machine (once per machine)

Paste this into a new Claude Code conversation in the repo:

> My persistent agent memory is checked into this repo at `docs/agent-memory/`
> (see its README). Your session's memory directory (the path in your system prompt
> under "Memory") is machine-local and empty/stale here. Set up the sync: back up
> whatever is at your memory directory path, then replace it with a symlink to this
> repo's `docs/agent-memory/` (absolute path). Verify `MEMORY.md` resolves through
> the symlink, then load it and confirm what you know about this project.

After that one-time step, memory works natively and `git diff docs/agent-memory/`
shows what the sessions learned — commit it like any other change.

## Notes

- The files are mostly `type: project` knowledge (measured recipes, failure
  mechanisms, category DNA). The heavier operational history lives in
  `INCIDENTS.md` at the repo root; the per-category detail in
  `<category>/*-embroidery-knowledge.md`. This directory is the working index that
  sessions load first.
- If two machines commit memory concurrently, resolve like any text conflict —
  entries are one-fact-per-file precisely so merges stay trivial.

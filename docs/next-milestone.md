# Next iteration: portable comparison evidence

Status: planned handoff, 2026-11-04. EF-006 completes the
[previous five tasks](governance/handoff-2026-10-31.md).

1. **Canonical comparison export.** Define deterministic normalized JSON for a
   validated comparison, including version and byte-limit rules. Preserve source
   report digests and reject mutated SDK objects before output.
2. **Retained evidence identity.** Publish a digest of the canonical comparison
   encoding for external retention. Distinguish original-file bytes and source
   report digests; make no signature or attestation claim.
3. **Exclusive canonical export CLI.** Validate retained evidence and export
   canonical bytes without overwrite, with a fixed identity summary. Test
   equivalent formatting, invalid versions, collisions and byte limits.
4. **Expected-identity verification.** Check a retained comparison against an
   explicit expected digest before review/export. Keep internal and source
   consistency checks separate; never retrieve embedded paths or URLs.
5. **Portable retention acceptance.** Extend the synthetic workflow through
   canonical export, expected-digest checks and source verification, including
   consistent replacement, reversed direction and changed failed agreement.
   Preserve descriptive-only performance interpretation.

Priority: independent comparison checking now works; canonical retention makes
it portable without signing or remote infrastructure. PR #3 is merged into
feat/runtime-benchmarks; #2 and #1 remain open. Recheck the stack before branching
and use its merged base. These tasks are planned only; no merge/release/deployment.

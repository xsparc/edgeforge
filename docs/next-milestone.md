# Next iteration: retained identity contracts

Status: planned handoff, 2026-11-05. EF-007 completes the
[previous five tasks](governance/handoff-2026-11-04.md).

1. **EF-008: strict identity record.** Define a closed versioned model and discoverable JSON schema for the identity summary; reject invalid profile, digest and byte count.
2. **EF-008: retained identity intake.** Add bounded duplicate-safe reading of independently retained identity JSON with semantic checks and sanitized errors.
3. **EF-008: identity-file verification.** Verify canonical comparison digest and byte count against an explicit identity file, leaving both files unchanged.
4. **EF-008: review gate integration.** Support the validated identity file before HTML/canonical export, define mutual exclusion with a digest argument and preserve exclusive output.
5. **EF-008: portable acceptance example.** Demonstrate native synthetic source reports, identity retention, consistent replacement rejection, failed agreement, and canonical round trip without timing gates or extra inference during review.

Check the remaining stacked PRs before choosing a base. No merge, release or
physical-device performance claim is authorized. These tasks are planned only.

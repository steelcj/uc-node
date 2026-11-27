---
title: Handoff for uc-node, Phase Two Prompt
description: The Claude Code prompt for phase two of the handoff work, three fixes from the phase one review, then an end-to-end run with the client example-org on Incus, from intake through admission and one rejection, testing the guides as it goes.
version: 0.1.0
status: provisional
date: 2026-11-27
language: en-CA
---

# Handoff for uc-node, Phase Two Prompt

## Where this comes from

Phase one is on the branch `handoff` at `220d64f`, with its report, `2026-11-27--14-48-38-uc-node-handoff-phase-one-report.md`. Reviewing the branch confirmed the report and found one more gap, the third fix below. The design points the report raised are drafted for Christopher in uc-contracts, on the branch `design-after-uc-node-phase-one`: raw node handoff 0.1.2, client inventory layout 0.1.1 and node lifecycle overview 0.1.6. uc-controller's items are drafted in its ROADMAP, on a branch of the same name.

## Fixes before the run

| Fix | Why |
| :-- | :-- |
| `sudo` measured with `sudo -l -U <initial_username>` | The contract's field is whether the user can use sudo. Group membership misses a sudoers rule naming the user directly |
| Guide 4 says a rejection deletes a committed candidate from the working tree | `git status` then shows a deletion, which needs a commit too |
| The check play refuses a node definition field it does not know | A node definition is passed with `-e`, which overrides every variable, not only the hashes and connection variables the check play refuses today. A stray `users`, `foomuuri_*` or `ssh_client_options` in an old or hand-edited node definition would change the build without a word. A list of the allowed fields, from the README's field table, makes every override deliberate |

## Before running the prompt

Christopher does these first, which tests guide 0 and guide 1:

1. Set up `example-org` by following guide 0: the folder, the inventory with uc-controller's `scripts/new-inventory`, its `CHANGE-ME` values, `logs/rejected/`, `intake/defaults.yml`, and the batch for the day, such as `raw-2026-11-27-01`, with `scripts/new-batch` and uc-controller's batch-secrets recipe.
2. Make the key `~/.ssh/example-org-raw-initial-id_ed25519`.
3. Write the node definition for `dev.example.org` with `scripts/new-node ~/.private/uc/example-org/uc-inventory`.
4. Note in a few lines, for the session, anything in guides 0 and 1 that was wrong, unclear or missing.
5. Make sure no Incus instance named `dev-example-org` or `stage-example-org` exists.

## Prompt

```text
This is phase two of the handoff work. Read, in this order: en/docs/sessions/2026-11-27--13-22-47-uc-node-handoff-plan-and-kickoff.md, en/docs/sessions/2026-11-27--14-48-38-uc-node-handoff-phase-one-report.md, and this file, en/docs/sessions/2026-11-27--15-01-56-uc-node-handoff-phase-two-prompt.md. Read the latest version of each design document in uc-contracts' en/docs/design/, and the branch design-after-uc-node-phase-one there if it is not merged yet, which drafts the changes phase one suggested.

Work on the branch handoff, and commit after each step. Stop after step 6 and write the phase two report.

Ground rules for the whole phase:
- The design documents in uc-contracts are evolving designs, not rules. Where one does not fit what you find, stop and ask, saying what does not fit and the options you see. Never edit a uc-contracts document yourself.
- Never read anything under ~/.secrets/, and never print a secret or a hash. The build and admission read the batch through uc_secret, which is allowed. Search every build's and admission's output for $6$ and $y$, as in phase one.
- Under ~/.private/, read and write only ~/.private/uc/example-org/. Never touch another client's folder.
- In example-org's client inventory, commit only as guide 4 says to, with a message saying it is a test of guide 4, so every commit there is part of the test.
- Follow CLAUDE.md's known issues.
- Run yamllint, ansible-lint, both syntax checks and tests/run_tests.py with UC_CONTROLLER set before each commit in uc-node.
- Never push, never merge, never cut a release, and change nothing in uc-controller or uc-contracts.

1. Measure sudo with sudo -l -U.
   - In tasks/confirmation.yml, measure sudo with sudo -l -U <initial_username>, run as root: true when it lists at least one rule the user may run, false when it says the user may not run sudo, and a failed build for any other result. Keep sudo_nopasswd as it is.
   - Add fixtures for a user allowed by group, a user allowed by a rule naming the user, and a user with no rule, and test the parsing against them.

2. Refuse a node definition field the build does not know.
   - Add node_optional_fields to inventory/group_vars/all/platforms.yml, from the README's field table, and the platform fields per platform. The check play refuses a node definition that sets a field outside node_required_fields, node_optional_fields and the platform's fields, naming the fields. The node definition's fields are the keys of <uc_client_inventory>/intake/<node_fqdn>.yml, which the check play already reads. Extra variables given on the command line beside the node definition, such as -e uc_raw_node_adopt=true, are not node definition fields and stay allowed.
   - scripts/new-node writes only those fields, and refuses a defaults file holding another, naming it.
   - Tests for a node definition with an unknown field, one with only known fields, and a command-line extra variable that is not in the file.

3. Guide 4: say that a rejection removes the candidate from the working tree even when it was committed, so git status shows a deletion, and that committing the deletion keeps the client inventory saying what the fleet wants.

4. The run, as guide 4 says, with UC_CONTROLLER set to the uc-controller checkout.
   - Before building, check the setup the operator made with guide 0: modes of ~/.private/uc/example-org/ and its directories, check_inventory.py and yamllint on the client inventory, and the batch through the guide's own check. Do not read the batch file.
   - Build dev.example.org with scripts/build. Check the confirmation, the candidate, check_inventory.py and the client yamllint. Compare the fingerprint at the console as guide 4 says, with incus exec.
   - Review and commit the candidate as guide 4 says.
   - Admit the node with uc-controller's 05_admit.yml, by turning the candidate into admit_candidates as guide 4 says, and running admission with scripts/inventory-args. Report admission's result, what it wrote in the client inventory, and whether its identity and host key checks agreed with the candidate.
   - Do not onboard the node.

5. A rejection.
   - Write a node definition for stage.example.org with scripts/new-node, with the same batch, build it with UC_CONTROLLER pointing at a temporary copy of uc-controller whose check_raw_confirmation.py fails RN-ACC-07, as in phase one, and follow guide 4's When a node is rejected section: the entry in logs/rejected/, the candidate removed, and what the guide says to do with it.
   - Remove the stage-example-org instance and stage.example.org's node definition afterwards, and say so in the report. Leave the rejection in the log.

6. Fix the guides.
   - Fix every point where guides 0, 1, 2 or 4, or the README, did not match what the run did, including the operator's notes on guides 0 and 1, which Christopher gives at the start of the session. One commit per guide.
   - Write the phase two report, en/docs/sessions/<timestamp>-uc-node-handoff-phase-two-report.md, by the sessions README: the fixes, the run step by step with what each guide said and what happened, admission's result, the rejection, every guide change, anything in the design documents that did not fit, what is left in example-org (the dev-example-org instance, its admitted entry, the commits, the batch), and what remains before release 0.3.0.
```

## Changelog

| Version | Date | Change |
| :-- | :-- | :-- |
| 0.1.0 | 2026-11-27 | First version |

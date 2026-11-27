---
title: Handoff for uc-node, Phase Two Report
description: What phase two of the handoff work changed, the end-to-end run with the client example-org on Incus from intake through admission and one rejection, what each guide said and what happened, every guide change, what did not fit the design documents, what is left in example-org, and what remains before release 0.3.0.
version: 0.1.0
status: provisional
date: 2026-11-27
language: en-CA
---

# Handoff for uc-node, Phase Two Report

## Summary

Phase two is done, on the branch `handoff`, none of it pushed. The three fixes from the phase one review are in. The end-to-end run worked. `dev.example.org` was built on Incus from example-org's client inventory, its confirmation passed uc-controller's checker, its candidate was reviewed and committed, and uc-controller's `05_admit.yml` admitted it, with every host key agreeing across the confirmation, admission's scan and the console. `stage.example.org`, built against a checker that fails RN-ACC-07, was rejected as guide 4 describes, and then removed.

The run turned up one bug in uc-node, which is fixed: the defaults setting for the initial user had a different name from the node definition field. It also turned up a dozen points in the guides, which are fixed, one commit per guide. Nothing in the design documents stopped a step. One point is worth deciding before release: admission names an admitted node by its hostname, `dev`, while the candidate and the handoff design name it by its fully qualified domain name.

Before phase two, nine commits from `b30fadb` to `9a1b190` dealt with the operator's notes on guides 0 and 1. They are not repeated here.

## Before starting

| Item | Found |
| :-- | :-- |
| uc-node | `handoff` at `9a1b190`, the operator's notes done, the working tree clean |
| uc-contracts | `main` at `80c6e16`. The branch `design-after-uc-node-phase-one`, at `0a84260`, not merged, drafts raw node handoff 0.1.2, client inventory layout 0.1.1 and node lifecycle overview 0.1.6. I read those drafts as the latest versions |
| uc-controller | `main` at `8799481`. Used as it is, and copied once for the rejection. Nothing changed in it |
| example-org | Its client inventory's first commit, `b5f3421` on `main`, made by the operator, with `intake/defaults.yml` and `intake/dev.example.org.yml` |
| Incus | No instance named `dev-example-org` or `stage-example-org` |

Under `~/.private/` I read and wrote only `~/.private/uc/example-org/`. Under `~/.secrets/` I opened no file. I listed the modes of the batch files and their directories, as guide 0's check does, and asked `uc_secret` whether the value is a crypt hash, which prints only `true`. Every build's and admission's output was searched for `$6$` and `$y$`, and none held either.

## The fixes

| Fix | Commit | What |
| :-- | :-- | :-- |
| 1. `sudo` measured with `sudo -l -U` | `70fe411` | `tasks/confirmation.yml` asks `sudo -l -U <initial_username>`, as root, with `LC_ALL=C`. A new filter, `plugins/filter/uc_sudo.py`, enabled with `filter_plugins` in `ansible.cfg`, reads the answer: `yes` when sudo lists at least one rule, `no` when it says the user may not run sudo, and `unknown` for anything else, such as a non-zero exit, which fails the build. The fixtures are real output from sudo 1.9.16p2 on Debian 13, captured in a throwaway container that was then deleted: a user allowed by group, a user allowed by a rule naming the user, and a user with no rule. The first two print the same, which is the point: the old measure, the user's groups, said false for the second. `sudo_nopasswd` is unchanged. A throwaway Incus build reported `sudo: true` and passed the checker |
| 2. A node definition field the build does not know | `495c6c7` | `platforms.yml` gains `node_optional_fields`, from the README's field table: `node_label`, `platform`, `ssh_port`, `ssh_sources`. The check play refuses a node definition whose file in `intake/` sets a field outside `node_required_fields`, `node_optional_fields` and the platform's `required_fields`, naming the fields. Extra variables on the command line, such as `-e uc_raw_node_adopt=true`, stay allowed. `scripts/new-node` writes only those fields, and refuses a defaults file with a setting it does not offer. Tests: one unknown field, several, another platform's field, only known fields, a command-line extra variable, and the defaults refusal |
| 3. Guide 4, a rejection and a committed candidate | `e60f938` | A rejection removes the candidate from the working tree even when it was committed, so `git status` shows ` D candidates/<fqdn>.yml`. Committing the deletion keeps the client inventory saying what the fleet wants |

### A bug the run found

| Commit | What |
| :-- | :-- |
| `aada8e3` | The defaults file named the initial user `initial_user`, and a node definition names it `initial_username`. The operator's hand-written `intake/defaults.yml` used `initial_username`. Until fix 2, `scripts/new-node` silently ignored it and fell back to `initial`, which happened to be right. After fix 2 it refused the file. The setting is now `initial_username`, the node definition's name, and a test checks it is used |

## Checks

Before each commit I ran `yamllint .`, `ansible-lint` (production profile), `ansible-playbook build.yml --syntax-check` for an Incus and an ssh node definition in a temporary client inventory, and `tests/run_tests.py` with `UC_CONTROLLER` set. There were three exceptions, all documentation only. For fix 3 and guide 0's commit, I ran the checks straight after the commit, on the same tree, and they passed. The last commit, the CHANGELOG line, had yamllint only. On the final tree every check passes:

| Check | Result |
| :-- | :-- |
| `yamllint .` | Clean |
| `ansible-lint` | Passes, production profile |
| Syntax checks, Incus and ssh | Both pass |
| `tests/run_tests.py` with `UC_CONTROLLER` | 97 tests, all pass |
| `tests/run_tests.py` without `UC_CONTROLLER` | 97 tests, all pass, 3 skipped: the checker tests |
| Links and anchors in the README, CHANGELOG, ROADMAP, guides and known issues | None broken, after `5c62b13` fixed two that the operator-notes commit `98fa0d4` had broken |

## The run

### Checking the setup made with guide 0

| Guide 0 says | What I found |
| :-- | :-- |
| `~/.private`, `uc/`, `example-org/`, `logs/` and `logs/rejected/` at `0700` | All `0700`. `uc-inventory/` and `intake/` are `0775`, which guide 0 does not set. They are inside the `0700` client folder, so nothing is exposed |
| The client inventory passes its pre-commit checks | `check_inventory.py` passes. yamllint passes with three line-length warnings: the key lines in `intake/defaults.yml` and `intake/dev.example.org.yml`, 131 characters, and one in `onboard/stage/group_vars/all.yml`, 121. The operator made line-length a warning in `.yamllint` for them |
| `CHANGE-ME` values replaced, `onboard_ssh_private_key_file` naming the client's key | None left. Both onboard stages name `~/.ssh/example-org-raw-initial-id_ed25519` |
| The batch check: modes, then `uc_secret` | At first, `~/.secrets/uc/build/batches/raw-2026-11-27-01.yml` did not exist, and `uc_secret`'s refusal said so and pointed at guide 0. I stopped and asked. The operator put it in place, with a timestamp of 15:38, so probably renamed, and the fleet file at 17:06. Then all four directories were `drwx------`, both files `-rw-------`, and the check printed `true` |
| `scripts/new-node` accepts the defaults | It refused them, because of the `initial_user` and `initial_username` bug above. After `aada8e3` it accepts them |

### Build dev.example.org

`UC_CONTROLLER=<uc-controller> scripts/build ~/.private/uc/example-org/uc-inventory dev.example.org`, as guide 2 describes.

| Guide 2 says | What happened |
| :-- | :-- |
| `scripts/build` prints the command it runs | It did |
| The bootstrap shows a red error, counted as `rescued=1` | One `fatal: ... timed out waiting for ping module test`, and `rescued=1` in the recap |
| It ends with the address, the fingerprint and the console command | `10.119.134.118`, `SHA256:OWSNbuUyW4BHGxi4l1gF+yLf/0KrMK8fagKhi8rhkZM`, and "The confirmation passed check_raw_confirmation.py." Exit 0, `failed=0`, no rejection written |
| The node checks: marker, hostnames, running, Python and sudo, sshd, Foomuuri with `10-base.conf` alone, two boots, the confirmation `root root 0644` | Every one as expected |

| Check | Result |
| :-- | :-- |
| The confirmation, through `incus exec`, with `check_raw_confirmation.py` | `pass`, no findings. `sudo: true`, `sudo_nopasswd: false`. `baseline: "0.2.0"`, since `VERSION` is not cut yet |
| The candidate | Every field of the handoff design, quoted, `producer_version: "0.2.0"` |
| `check_inventory.py`, the client inventory's yamllint | Both pass, with the two line-length warnings above |
| The fingerprint at the console, as guide 4 says | `incus exec dev-example-org -- ssh-keygen -lf ...` gave the same ED25519 fingerprint as the build and the candidate |

### Review and commit the candidate

Following guide 4. `git status --short` showed `?? candidates/`. Guide 4's `git diff candidates/` printed nothing, since the candidate was a new, untracked file, so the review step reviewed nothing. `git add candidates/dev.example.org.yml intake/dev.example.org.yml` staged the candidate alone, since the node definition had been in the first commit. The commit's hook passed it, showing yamllint's warnings. Commit `c7d6aa2`, "Candidate dev.example.org, batch raw-2026-11-27-01 (test of uc-node's guide 4, review and commit the candidate)".

### Admission

Guide 4's conversion gave one `admit_candidates` entry, the address and the fingerprint. The client's key was already in the agent with eleven others. Before running admission I checked that both its SSH command and the admitted group use `IdentitiesOnly=yes` with `onboard_ssh_private_key_file`, so only the client's key was offered, as CLAUDE.md's PerSourcePenalties note asks. I skipped `ssh-add`, which would have asked for a passphrase to load a key already loaded.

`ansible-playbook $(scripts/inventory-args <client inventory> raw onboard/dev) ingress/playbooks/05_admit.yml -e admit_batch_id="$batch" -e @"$candidates"`, from the uc-controller checkout.

| | Result |
| :-- | :-- |
| Exit | 0 |
| Report | `10.119.134.118: admitted dev - dev is new on every count` |
| Confirmation check | Passed |
| Host keys | The scanned keys equal the confirmation's: RSA `22wCdk...`, ECDSA `VGMq1Q...`, ED25519 `OWSNbu...`. The ED25519 key is the candidate's and the console's |
| Identity | New on every count. The machine ID written equals the confirmation's |
| Become with the batch password | Confirmed. The batch password admission holds matches the hash uc-node built with |
| `raw/admitted.yml` | A host `dev`, with `ansible_host`, `ansible_port`, `raw_node_contract: 0.3.1`, `raw_node_baseline: 0.2.0`, `raw_node_machine_id`, `raw_node_macs`, `raw_node_batch` and `raw_node_admitted` |
| `ssh/known_hosts` | The three host keys under `dev`, between `BEGIN` and `END` comment lines |

Guide 4 said to commit those "as uc-controller's guides describe", without the commands. I committed them as `77a1296`, "Admit dev.example.org, batch raw-2026-11-27-01 (test of uc-node's guide 4, run admission)". The node was not onboarded.

### The rejection

`scripts/new-node` wrote `intake/stage.example.org.yml` from the defaults with four answers, folding the key line before its comment. I built it with `UC_CONTROLLER` pointing at a copy of uc-controller, made with `rsync` and without `.git`, whose `check_raw_confirmation.py` expected `sudo_nopasswd: true`, so a correct node fails RN-ACC-07 alone.

| Guide 4 says | What happened |
| :-- | :-- |
| The build says it wrote a rejection | Exit 2, at "Stop if the confirmation does not meet the contract", then `[WARNING]: uc_reject: stage.example.org could not be secured. Rejection written to .../logs/rejected/2026-11-27--17-17-28-rejected-uc-node-cannot-be-secured.yml` |
| One entry, with the fields in the table | `node`, `rejected`, `controller: "uc-node"`, the play and task as `step`, `reason: "cannot-be-secured"`, `clauses: ["RN-ACC-07"]`, the node's real fingerprint (it matches the console) and the batch. The checker's message is not in it |
| The candidate removed | stage had none, so nothing was said or removed. dev's candidate was untouched |
| What to do: fix, rebuild or leave | I left it: `incus delete --force stage-example-org`, and removed `intake/stage.example.org.yml`, which was never committed, so `git status` stayed clean and there was nothing to commit |

I removed the `stage-example-org` instance, stage's node definition and the copy of uc-controller. The rejection stays in the log.

## Guide changes

| Commit | Guide | Change, and the point in the run behind it |
| :-- | :-- | :-- |
| `2a41f30` | 0 | The defaults example says `initial_username`, and new-node refuses a setting it does not offer. The key is given as a path, which keeps `defaults.yml` within the yamllint limit, and new-node's folded key line fits, so the limit can stay an error. The first commit holds the template and the defaults. A node definition is committed with its candidate, and committing one early does no harm |
| `331a197` | 1 | `initial_username` in the example and the table. The table lists `node_label` and `platform`, which the operator's file set. Only the table's settings are allowed. The key as a path, and leave new-node's fold alone |
| `c2b0217` | 2 | The test of an instance uc-node does not own used `dev-example-org`, and its cleanup deleted that instance and `intake/dev.example.org.yml`. In example-org those are now the admitted node. The test uses `prod`, after checking the client has no node with that label, and the cleanup says to `git rm` a committed candidate. Every node check in guide 2 held on `dev-example-org` |
| `fad89db`, `5c62b13` | 3 | The remaining `-p 2222` examples removed, since SSH stays on 22, with the note on a manual `ssh` to another port. The troubleshooting entry for a node definition that sets another `ssh_port` keeps the build's own message. The fix for a node stuck in `starting`, lost with the earlier-version section, is now in The node has not finished booting, and the known issue's link points there |
| `1d45d5b` | 4 | Review with `git add`, then `git diff --cached`, since plain `git diff` showed nothing. A node definition committed earlier is no change. `UC_CONTROLLER` only on the commit. Check the agent before `ssh-add`. Admission's report, that it names the node `dev`, what it writes, and the commands to check and commit `raw/admitted.yml` and `ssh/known_hosts`. The commands to leave a rejected node on Incus |

The README matched the run and needed no change. The CHANGELOG records the sudo measure, the field refusal and the defaults rename.

## The two questions from the start of the session

### Should guide 0 say to make line-length a warning?

No. Every line over the limit came from writing the key line itself. In `intake/defaults.yml` the operator wrote the key line instead of the path guides 0 and 1 show. In `intake/dev.example.org.yml`, `scripts/new-node` had folded the key line before its comment, at 96 characters, and the file was later edited so that it ended up on one 131-character line. With the key given as a path in the defaults and new-node's fold left alone, every file uc-node writes stays within 120. Guides 0 and 1 now say so. A warning works, but it would also let through other long lines the limit is there to catch. The 121-character line in `onboard/stage/group_vars/all.yml` is uc-controller's, a quoted key line in a list, which cannot be folded the same way. It is worth raising with uc-controller, rather than relaxing the client inventory's limit for it.

### Does the node definition belong in the first commit, or with its candidate?

With its candidate, as guide 4 says, though either works. Committed with the candidate, the history records a node definition when its node was built and handed over, in the same commit as the record of the handover. A node definition that is written and never built, or whose build is rejected, never enters the history. Committed in the first commit, as the operator did, nothing breaks: guide 4's `git add` finds no change in it, and the candidate is committed alone, as the run showed. Guide 0 now says the first commit holds the template and the defaults, and that an early node definition does no harm.

## What did not fit

None of these stopped a step. I edited no uc-contracts document.

### Admission names the node by its hostname

The candidate is keyed by the fully qualified domain name, `dev.example.org`, as the handoff design defines it. Admission wrote `dev`, the confirmation's hostname, to `raw/admitted.yml` and `ssh/known_hosts`. The handoff design's example shows `dev.example.org` there, and says its keys are illustrative and admission's own win. Within one client inventory, two domains with the same label, such as `dev.example.org` and `dev.example.net`, would share the name `dev`. Admission's identity match would report a name collision rather than admit the second.

Suggested: decide which name the fleet uses after admission. If it is the hostname, the handoff design says so, and that a client inventory holds one node per label. If it is the fully qualified domain name, admission takes it from the candidate once it reads `candidates/`.

### `sudo` in the contract

Fix 1 measures `sudo` as `sudo -l -U` reports it. Suggested: the contract's field says it is measured that way, as the plan's decisions now do.

### The version the run's nodes report

`baseline` in the confirmation, `producer_version` in the candidate, and `raw_node_baseline` in `raw/admitted.yml` are all `0.2.0`, since `VERSION` is not cut. Phase one saw this coming. `dev.example.org` will report 0.2.0 until it is rebuilt after the release.

### The design's intake example and the yamllint limit

The handoff design's `intake/dev.example.org.yml` writes the key line, with the client's comment, on one quoted line of about 130 characters, past the client inventory's limit of 120. Suggested: the example shows the key folded before its comment, as `scripts/new-node` writes it, or the layout design states the limit.

### For uc-controller, not changed

- `05_admit.yml`'s usage comment still shows `~/uc-inventories/example.org` and `raw-1970-01-01-01`.
- The template's `onboard/stage/group_vars/all.yml`, once filled in, has a quoted key line of 121 characters.
- Phase one's items still stand: `intake/` and `candidates/` in the template, the batch secrets guide pointing at uc-node's guide 0, and admission reading `candidates/`.

## What is left in example-org

| What | Where |
| :-- | :-- |
| The instance `dev-example-org`, running, at `10.119.134.118` | Incus |
| Its candidate, committed | `candidates/dev.example.org.yml` |
| Its admitted entry, as `dev`, and its three host keys, committed | `raw/admitted.yml`, `ssh/known_hosts` |
| Its node definition and the defaults, from the operator's first commit | `intake/dev.example.org.yml`, `intake/defaults.yml` |
| Two commits of the guide 4 test, after the operator's `b5f3421` | `c7d6aa2` the candidate, `77a1296` the admission, on `main` |
| The rejection of `stage.example.org` | `logs/rejected/2026-11-27--17-17-28-rejected-uc-node-cannot-be-secured.yml`, mode `0644` in the `0700` log |
| The batch `raw-2026-11-27-01`, both files | `~/.secrets/uc/build/batches/` and `~/.secrets/uc/fleet/batches/` |

The client inventory's working tree is clean. `stage-example-org` and `intake/stage.example.org.yml` were removed, and no other instance was made. The plan retires the test batch after the run. `dev-example-org` was built with it, so retire it when that node goes, or keep both for a test of onboarding.

## What remains before 0.3.0

1. Review the branch `handoff`, from `70fe411` to the commit of this report, and the operator-notes commits before it. Nothing is pushed or merged.
2. Decide the name of an admitted node, above, and whether the contract states how `sudo` is measured.
3. Merge the uc-contracts branch `design-after-uc-node-phase-one`, with any changes from this report.
4. Cut 0.3.0, so nodes report it. Rebuilding `dev.example.org` afterwards would show that a rebuild of an admitted node changes only the reboot, the confirmation and the candidate's `built`, and that admission reports it as known. Phase two ran neither the rebuild nor guide 2's refusal test.
5. An ssh platform build, which neither phase has run.
6. Retire example-org's test batch and instance, or keep them for onboarding.

## Changelog

| Version | Date | Change |
| :-- | :-- | :-- |
| 0.1.0 | 2026-11-27 | First version |

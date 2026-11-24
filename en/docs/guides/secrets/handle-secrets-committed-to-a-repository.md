---
title: Handle Secrets Committed to a Repository
description: What to do when a password, key, token or other private information has been committed to a git repository, from containment to clean-up and prevention.
version: 0.1.0
status: provisional
date: 2026-11-23
language: en-CA
---

# Handle Secrets Committed to a Repository

A secret that reaches a git repository stays in its history after the file is deleted or edited, and once pushed it may already be in other clones, forks, caches and synced copies. This procedure puts the order of work right: make the secret useless first, then remove it from history, then make sure it cannot happen the same way again.

## What counts as a secret

- passwords, password hashes and passphrases
- private keys: SSH, GPG, TLS, release-signing keys
- API tokens, OAuth secrets, cloud credentials, webhook URLs that carry a token
- recovery codes and one-time backup codes
- private information about people: personal addresses, phone numbers, client details that were not meant to be published
- internal details that widen an attack: a server's address next to the account that logs in to it, for example

Password hashes count. A SHA-512 crypt hash can be cracked offline if the password is weak, so a leaked hash is handled like a leaked password.

## The order of work

| Step | Why it comes here |
| :-- | :-- |
| Stop and assess | Decide how far the secret has gone before changing anything |
| Rotate | Once the secret no longer works, the leak is harmless, whatever else happens |
| Remove from history | Stops new copies being made from the repository |
| Remove from GitHub's side | Clears cached views and pull request refs that a force-push does not reach |
| Clean every other copy | Clones, forks, synced copies, release artifacts |
| Verify | Confirm the secret is gone from every place that matters |
| Record and prevent | Learn from it without writing the secret down again |

Rotation always comes before the history rewrite. A rewrite takes time, can go wrong, and never reaches copies that were already made. Rotation works immediately and everywhere.

## Stop and assess

Do not push anything else to the repository until this step is done.

### Find every occurrence

Search all of history, not only the current files. Replace `THE-SECRET` with a distinctive part of the value, typed at the prompt rather than saved in a file:

```sh
read -rs SECRET
git log --all --oneline -S "$SECRET"
git grep -F "$SECRET" $(git rev-list --all) -- | cut -d: -f1-2 | sort -u
unset SECRET
```

`read -rs` keeps the value out of your shell history and off the screen. The first command lists the commits that added or removed it, the second the commit and file pairs that contain it.

Also scan for secrets you have not noticed yet:

```sh
gitleaks git -v
```

### Decide how far it has gone

| Question | How to answer it |
| :-- | :-- |
| Was it pushed? | `git branch -r --contains <commit>`. If no remote branch contains it, see the next section |
| Is the repository public? | The repository's settings, or try cloning it while signed out |
| How long was it exposed? | The commit's push time, from the remote's activity log |
| Are there forks? | The repository's Forks list |
| Was it in a release or tag? | `git tag --contains <commit>`, and the release assets |
| Is it synced elsewhere? | Mirrors, CI caches, claude.ai Projects or other tools that sync the repository |

Assume a secret in a public repository has been seen. Automated scanners watch public pushes and can find credentials within minutes.

### If it was never pushed

The fix is local and no rotation is needed, unless the secret left the machine some other way:

```sh
# The secret is in the last commit only
git rm --cached path/to/file      # or edit the file to remove it
git commit --amend

# The secret is in an earlier unpushed commit
git rebase -i <commit>^           # mark the commit as edit, fix it, continue
```

Then run the search above again to confirm it is gone, and go to the prevention section.

## Rotate

Change every exposed secret at its source, before touching the repository:

| Secret | Rotation |
| :-- | :-- |
| A server or account password | Change it on the server or service, and in your password manager |
| A provider panel password | Change it in the panel, and turn on two-factor authentication if it is off |
| An SSH key | Generate a new key, install it, remove the old public key from every `authorized_keys` |
| An API token | Revoke it at the provider and issue a new one |
| A password hash | Change the password it was made from, and make a new hash |
| A signing key | Revoke it, publish the revocation, make a new key, and re-sign what needs it |

Then check for use of the old secret while it was exposed: login history (`journalctl -u ssh`, the provider's access log), unexpected changes, and new keys or users on the server. If there are signs it was used, treat the system as compromised: rotate everything on it, and consider rebuilding it.

Rotation alone can be the end of it. If the secret is a credential that is now useless, rewriting history is optional. It is still worth doing for a public repository, for anything personal that cannot be rotated, and for anything that reveals more than the credential itself.

## Remove it from history

Rewriting history changes the hash of every commit from the first affected one onward, removes commit and tag signatures, and requires a force-push. Merge or close open pull requests first.

### Install git-filter-repo

Version 2.47 or later is needed for `--sensitive-data-removal`:

```sh
pip install --user --upgrade git-filter-repo
git filter-repo --version
```

### Work in a fresh clone

```sh
git clone https://github.com/OWNER/REPOSITORY.git REPOSITORY-clean
cd REPOSITORY-clean
```

`git filter-repo` refuses to run in a clone that is not fresh, which protects your working copy.

### Choose what to remove

To remove whole files from every commit, give their full paths from the repository root, and add every old path if a file was moved or renamed:

```sh
git filter-repo --sensitive-data-removal --invert-paths \
  --path 'docs/notes/server-access.md' \
  --path 'docs/notes/old name with spaces.md'
```

To keep the files but replace the secret wherever it appears, write the replacements to a file outside the repository, one per line:

```sh
install -m 0600 /dev/null ~/replacements.txt
(umask 077 && "${EDITOR:-nano}" ~/replacements.txt)
```

```text
the-old-password==>REDACTED
regex:ghp_[A-Za-z0-9]{36}==>REDACTED-TOKEN
```

```sh
git filter-repo --sensitive-data-removal --replace-text ~/replacements.txt
shred -u ~/replacements.txt
```

The replacements file holds the secrets themselves, so it is created private and shredded after use.

### Check before pushing

`git filter-repo` removes the `origin` remote. Search again before adding it back:

```sh
read -rs SECRET
git grep -F "$SECRET" $(git rev-list --all) -- || echo "not found"
unset SECRET
grep -c '^refs/pull/.*/head$' .git/filter-repo/changed-refs || true
```

Note the "First Changed Commit(s)" line in the filter-repo output, and the number of pull request refs. If either looks wrong, delete this clone and start again. After the push there is no going back.

### Force-push

```sh
git remote add origin https://github.com/OWNER/REPOSITORY.git
git push --force --mirror origin
```

Pushes to `refs/pull/*` fail, because GitHub keeps them read-only. That is expected. If branch protection blocks other refs, turn it off for the push and back on straight after.

## Remove it from GitHub's side

A force-push leaves the old commits reachable through pull request refs and cached views. For sensitive data that rotation cannot make harmless, contact GitHub Support with:

- the owner and repository name
- the number of affected pull requests
- the first changed commits from the filter-repo output

Support can dereference or delete affected pull requests, run garbage collection and remove cached views. They only do this for sensitive data.

Also delete and re-create any release whose assets, such as source archives or `dist/` builds, contain the secret, and move tags that were rewritten.

## Clean every other copy

| Copy | What to do |
| :-- | :-- |
| Your other clones, on every machine | Delete them and clone again. Do not pull into them: a pull followed by a push puts the secret back |
| Collaborators' clones | Ask them to re-clone, or to rebase, never merge, branches made from the old history |
| Forks | Ask each fork owner to delete the fork or remove the data. GitHub cannot do this for you |
| Synced copies | Re-sync or remove: claude.ai Project sources, mirrors, backup tools, CI caches |
| Working copies elsewhere | Scratch clones, AI session workspaces, archives made from the repository |
| Notes and session records | Anything that quoted the secret, including records of the session that found it |

## Verify

- The search in [Find every occurrence](#find-every-occurrence) finds nothing in a fresh clone.
- `gitleaks git -v` in a fresh clone reports nothing new.
- The old secret no longer works where it was used.
- On GitHub, an old commit URL that held the secret returns 404 once Support has finished.

## Record and prevent

### Write an incident note, without the secret

Record what leaked (by kind, never by value), where, for how long, how it was found, what was rotated, and what changed to stop it happening again. Keep it with your other process documents.

### Keep secrets out of working trees

- Keep secrets in a password manager, and in files under a private directory outside every repository, such as `~/.secrets/`, with mode `0600` in a directory of mode `0700`.
- Scratch notes that may hold credentials go outside the repository too. A directory inside the repository and listed in `.gitignore` is the second-best choice, since one `git add -f` publishes it.
- Write examples with documentation addresses and domains: `192.0.2.0/24`, `198.51.100.0/24`, `203.0.113.0/24`, `2001:db8::/32`, `example.org`.

### Catch them before they are committed

Add gitleaks as a pre-commit hook with the pre-commit framework:

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.24.2  # example, pin the current release
    hooks:
      - id: gitleaks
```

```sh
pip install --user pre-commit
pre-commit install
pre-commit run --all-files
```

Pin `rev` to the current gitleaks release. Every clone needs `pre-commit install`, so add it to the repository's setup instructions.

### Catch them before they are pushed

Turn on secret scanning and push protection in each GitHub repository's security settings. Push protection blocks a push that contains a recognised credential format. It does not recognise plain passwords, so it is a second line, not a replacement for the pre-commit hook.

### Commit deliberately

- Stage files by name, and read `git diff --cached` before every commit.
- Avoid `git add .`, `git add -A` and `git commit -a` in repositories that sit next to secrets or scratch notes.

## Worked example: uc-node, 2026-11-23

### What happened

Commit `f54a45b` added working notes to a public repository. Two of them held plaintext passwords next to the address of a VPS and the account that logs in to it:

- `en/docs/guides/ex2/cloud-flair.md`
- `en/docs/guides/blacklists/x imata.md`

Earlier commits were not affected, so tag `v0.1.1` is unaffected.

### What to do

1. Change both passwords, at the VPS and in the provider panel, and check the VPS's SSH log for logins from unknown addresses since the commit was pushed.
2. Decide which notes to keep. They hold useful findings, so either move them out of the repository to a private place, or keep them with the passwords replaced.
3. In a fresh clone, remove the two files, using quotes for the path with a space, or use `--replace-text` to keep them without the passwords.
4. Search again, force-push, and contact GitHub Support if the passwords cannot be rotated.
5. Re-sync the claude.ai Project's GitHub source, delete other clones and clone again, and remove scratch copies, including the one made in the Claude session that found it.
6. Add the gitleaks pre-commit hook and turn on push protection.
7. Record the incident in uc-processes, without the passwords.

## Changelog

| Version | Date | Change |
| :-- | :-- | :-- |
| 0.1.0 | 2026-11-23 | First draft, provisional |

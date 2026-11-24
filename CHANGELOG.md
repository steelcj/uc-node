# CHANGELOG.md

# Changelog

All notable changes to the uc-radar repository are recorded here. This is the repository-level changelog: it records what each tagged release contained and why. Each document additionally carries its own changelog, in its frontmatter and in a Changelog table, for changes internal to that document.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versions track the `VERSION` file and the git tags. Dates are ISO 8601.

## [Unreleased]

## [0.1.0] - 2026-11-23

### Recreated Repository

Copied remaining requirements from old repo

	modified:   CHANGELOG.md
	modified:   README.md
	modified:   ROADMAP.md
	new file:   ansible.cfg
	new file:   build.yml
	new file:   en/docs/guides/1-setup-the-defaults-for-new-nodes.md
	new file:   en/docs/guides/2-build-and-check-a-raw-node.md
	new file:   en/docs/guides/add-a-new-platform-to-the-node-creation-controller.md
	new file:   en/docs/guides/add-a-new-platform.md
	new file:   en/docs/guides/setup-ex2-vps-node.md
	modified:   scripts/bump-version.py
	modified:   scripts/cut-release.py
	modified:   scripts/publish-release.py


### Additions to support VPS and related issues


	modified:   .gitignore
	modified:   CHANGELOG.md
	renamed:    en/guides/1-setup-the-defaults-for-new-nodes.md -> en/docs/guides/1-setup-the-defaults-for-new-nodes.md
	renamed:    en/guides/2-build-and-check-a-raw-node.md -> en/docs/guides/2-build-and-check-a-raw-node.md
	new file:   en/docs/guides/add-a-new-platform-to-the-node-creation-controller.md
	new file:   en/docs/guides/add-a-new-platform.md
	new file:   en/docs/guides/blacklists/misc.md
	new file:   en/docs/guides/blacklists/uc-node-ovh-reseller-vps-issues-and-fixes.md
	new file:   en/docs/guides/blacklists/x imata.md
	new file:   en/docs/guides/ex2/cloud-flair.md
	new file:   en/docs/guides/releases/artifacts/cut-and-publish-a-release-v0.1.2.md
	new file:   en/docs/guides/releases/artifacts/cut-and-publish-a-release-v0.1.3.md
	new file:   en/docs/guides/releases/artifacts/cut-and-publish-a-release-v0.1.4.md
	new file:   en/docs/guides/releases/artifacts/cut-and-publish-a-release.md
	new file:   en/docs/guides/releases/cut-and-publish-a-release.md
	new file:   en/docs/guides/setup-ex2-vps-node.md
	modified:   group_vars/all/incus.yml
	new file:   group_vars/all/names.yml
	modified:   group_vars/all/node.yml
	new file:   scripts/bump-version.py

### File System Organization

Reorganized files and used cleaned up repos cut and pub release resources to create uc-repo repo template

	modified:   .gitignore Added dist/
	renamed:    en/guides/1-setup-the-defaults-for-new-nodes.md -> en/docs/guides/1-setup-the-defaults-for-new-nodes.md
	renamed:    en/guides/2-build-and-check-a-raw-node.md -> en/docs/guides/2-build-and-check-a-raw-node.md
	new file:   en/docs/guides/releases/artifacts/cut-and-publish-a-release-v0.1.2.md
	new file:   en/docs/guides/releases/artifacts/cut-and-publish-a-release-v0.1.3.md
	new file:   en/docs/guides/releases/artifacts/cut-and-publish-a-release-v0.1.4.md
	new file:   en/docs/guides/releases/artifacts/cut-and-publish-a-release.md
	new file:   en/docs/guides/releases/cut-and-publish-a-release.md
	new file:   scripts/bump-version.py

## [0.1.1] - 2026-11-23

### Commented out robertdebock.software

Left in place in case it is needed in the future. `steelcj.foomuuri` installs Foomuuri and `robertdebock.openssh` installs the SSH server, so `robertdebock.software` has nothing left to install. It has been commented out in  `build.yml` as well as  `group_vars/all/software.yml`. It is not currently required so it is commented out in  `requirements.yml` as well.

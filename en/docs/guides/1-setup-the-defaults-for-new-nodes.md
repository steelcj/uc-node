# Set Up the Defaults for New Nodes

## Create the defaults for scripts/new-node

`scripts/new-node` reads its defaults from `~/.secrets/uc-raw/defaults.yml`. That file holds password hashes, so it and its directories must be readable by you alone.

The defaults are the values most of your nodes share. The node's label, its platform and, on the `ssh` platform, its address differ from node to node, so `scripts/new-node` always asks for them.

### Create the directories

```sh
install -d -m 0700 ~/.secrets ~/.secrets/uc-raw
```

`install -d -m 0700` creates each directory with mode `0700` from the start, so there's no moment where another user can list it. If `~/.secrets` already exists, tighten it anyway:

```sh
chmod 0700 ~/.secrets ~/.secrets/uc-raw
```

### Create the file

```sh
install -m 0600 /dev/null ~/.secrets/uc-raw/defaults.yml
```

This creates an empty file with mode `0600` before anything is written to it.

### Make the password hashes

Run this once for root's password and once for the initial user's:

```sh
openssl passwd -6
```

It asks for the password twice and prints a hash that starts with `$6$`. It reads the password from the terminal, so the password never appears in your shell history or the process list. The initial user's password must be at least 15 characters (RN-ACC-08). Keep both passwords in your password manager: the file only holds the hashes, and the orchestration controller needs the initial user's password for `sudo`.

### Fill in the file

Open it with a private file-creation mask, so your editor's swap and backup files are private too:

```sh
(umask 077 && "${EDITOR:-nano}" ~/.secrets/uc-raw/defaults.yml)
```

Then paste:

```yaml
---
# ~/.secrets/uc-raw/defaults.yml
#
# Defaults for scripts/new-node. Holds password hashes, so keep it at mode
# 0600, in a directory of mode 0700.

# The client's domain. A node is named <node label>.<client domain>,
# for example raw.example.org.
client_domain: example.org

# The initial user of a raw node.
initial_user: initial

# The public key the initial user logs in with: the key line itself, or the
# path to a .pub file.
ssh_public_key: ssh-ed25519 AAAA... you@laptop

# The port SSH listens on.
ssh_port: 22

# Addresses or networks allowed to reach SSH. Empty means any. On the ssh
# platform, the list must include the controller's own public address.
ssh_sources: []

# The default passwords, as SHA-512 crypt hashes only. Make each with:
#   openssl passwd -6
# The initial user's password must be at least 15 characters (RN-ACC-08).
root_password_hash: "<hash of the root password>"
initial_password_hash: "<hash of the initial user's password>"
```

To get your public key line:

```sh
cat ~/.ssh/id_ed25519.pub
```

Keep the hashes in double quotes. They contain `$`, which is safe inside quotes in YAML.

### Check the permissions

```sh
stat -c '%a %n' ~/.secrets ~/.secrets/uc-raw ~/.secrets/uc-raw/defaults.yml
```

Expected:

```
700 /home/<you>/.secrets
700 /home/<you>/.secrets/uc-raw
600 /home/<you>/.secrets/uc-raw/defaults.yml
```

`scripts/new-node` refuses to run if the file or the `uc-raw` directory allows anyone else in, and says which one to fix.

### Check that the script accepts it

```sh
scripts/new-node
```

Answer `y` to "Use defaults?", press Enter for the node label and the platform, then answer `n` to the write question. If a value doesn't meet its rule, the script names the setting and says why.

Next: [Build and Check a Raw Node](2-build-and-check-a-raw-node.md) on the local Incus host, or [Build a Node on an SSH Host](3-build-a-node-on-an-ssh-host.md).

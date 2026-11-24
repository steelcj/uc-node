I'll check the uc-node repo to see what it expects from a target host.

There's no setting for this yet. uc-node 0.1.1 only builds local Incus containers: the first play in `build.yml` launches the instance, and every later step connects with `community.general.incus`, not SSH. Nothing in `group_vars` or the node definition points it at a remote host.

You can still run it against the VPS today without changing the code, because the configuration plays only target the group `raw_node`.

**1. Put your key on the VPS while root still has password login**

```sh
ssh-copy-id -i ~/.ssh/id_ed25519.pub root@<vps-ip>
```

After this you don't need `sshpass` or `--ask-pass`. The build changes root's password to the hash in your node definition anyway.

**2. Add an inventory file that lives outside the repo, next to your other secrets**

```bash
nano ~/.secrets/uc-raw/hosts.yml
```

content

```sh
---
raw_node:
  hosts:
    vps-vishpala:
      ansible_host: 203.0.113.10
      ansible_user: root
      ansible_port: 22
```

```bash
install -m 0600 /dev/null ~/.secrets/uc-raw/hosts.yml
```

**3. Run the build, skipping the Incus play**

```sh
ansible-playbook build.yml \
  -i inventory -i ~/.secrets/uc-raw/hosts.yml \
  --limit raw_node \
  -e @$HOME/.secrets/uc-raw/vishpala.com.yml
```

Output:

```bash
ansible-playbook build.yml   -i inventory -i ~/.secrets/uc-raw/hosts.yml   --limit raw_node   -e @$HOME/.secrets/uc-raw/vishpala.com.yml
[WARNING]: Could not match supplied host pattern, ignoring: raw_node
[ERROR]: Specified inventory, host pattern and/or --limit leaves us with no hosts to target.
```

`--limit raw_node` leaves `localhost` out, so the "Create the node" play matches no hosts and is skipped. Bootstrap, hostname, users, Foomuuri, OpenSSH and the reboot then run over SSH.

**Things that will catch you on the first run**

- **The reboot step fails the first time.** The OpenSSH role sets `PermitRootLogin no`. The run continues over the SSH connection that's already open, but after the reboot Ansible can't log back in as root, so the wait times out. The node reboots anyway. Before you run it again, switch the inventory to the initial user:

  ```yaml
  ansible_user: initial
  ansible_become: true
  ```

  Then add 

  ```
  --ask-become-pass
  ```

   and run it again. Later runs should finish cleanly.

- **Leave `ssh_port: 22` for the first run.** If you change the port in the same run, Foomuuri and sshd move to the new port while Ansible is still connected on 22. Change it once the node is working.

- **`ssh_sources` locks you out if it's wrong.** If you fill it in, make sure it includes your current public IP. An empty list allows any address, and key-only login still applies.

- **Check the OS first.** The local builds use `images:debian/13`, and that's the only target uc-node has been tested on. Run `cat /etc/os-release` on the VPS to confirm it's Debian 13. Also check whether the provider runs cloud-init, because it can reset the hostname on reboot.

If you want this supported properly rather than worked around, I'd add a `target: incus | ssh` field to the node definition and a ROADMAP entry for it. That would also be the natural place to fix the reboot problem, by having the run switch to the initial user after the OpenSSH step.
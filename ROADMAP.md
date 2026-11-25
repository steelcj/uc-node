# Roadmap

## Next

### Tag steelcj.foomuuri

`requirements.yml` pins `steelcj.foomuuri` to a commit, because the role has no release yet. Tag the repository, for example `0.1.2`, and pin the tag instead.

### Raise the cloud-init and Foomuuri ordering cycle upstream

On Debian 13, cloud-init 25 and Foomuuri form a systemd ordering cycle:

```text
cloud-init-network.service
  after systemd-networkd-wait-online.service
  after systemd-networkd.service
  after network-pre.target
  after foomuuri.service
  after foomuuri-boot.service
  after sysinit.target
  after cloud-init-network.service, which is ordered before sysinit.target
```

`foomuuri.service` and `foomuuri-boot.service` keep systemd's default dependencies, so they are ordered after `sysinit.target`, while `cloud-init-network.service` is ordered before it. systemd breaks the cycle at boot by deleting one job. On the Debian 13 cloud image it deleted `cloud-init-network.service`, so cloud-init waited forever and the node stayed in `starting`. systemd may choose either side of a cycle, so another boot could drop a Foomuuri unit and leave the node without its firewall.

The ssh platform now disables cloud-init after the first boot, and every build fails if `journalctl -b` holds an ordering cycle after the reboot. Raise the cycle with Foomuuri upstream, and in steelcj.foomuuri, for example so `foomuuri-boot.service` does not take the default dependencies, or with cloud-init if its ordering is the cause.

### Check Ubuntu Server installs from uc-ventoy for the same cycle

Ubuntu Server installs made with uc-ventoy keep cloud-init. Check whether their cloud-init and Foomuuri versions form the same cycle, and whether disabling cloud-init after the first boot is right for them too.

### Change the SSH port after first contact

The ssh platform refuses a first build whose `ssh_port` is not the first-contact port, because `steelcj.foomuuri` runs before `robertdebock.openssh` and allows only `foomuuri_ssh_port`. A port change on a later build is not supported either: the contract probe tries the new port, sshd still listens on the old one, and root can no longer log in. The smallest safe approach found so far, without changing the role, is to open the port in use as an extra `foomuuri_services` entry for the build that moves the port, so the firewall accepts both until sshd has moved, and to probe the old port when the new one does not answer.

### Raise AuthorizedKeysCommand none with robertdebock.openssh

The role's templates always write `AuthorizedKeysCommand {{ openssh_authorized_keys_command }}`, with `none` as the default. sshd 10 does not read `none` as unset for this option, and logs "AuthorizedKeysCommand path is not absolute" whenever no key in `authorized_keys` matches. uc-node sets it to `/usr/bin/true`. Ask the role to leave the line out when the value is `none`.

## Later

### Write confirmation.yml

The orchestration controller needs to know that a node meets the contract, and how to reach it. uc-node does not write `confirmation.yml` yet. Decide what it holds, for example the fully qualified domain name, the addresses, `ssh_port` and the build's time, and where it is written: on the node, on the controller, or both.

### Decide which provider agents may stay on a raw node

The ssh platform disables cloud-init after the first boot. Other provider agents, such as `qemu-guest-agent`, are left as they are. Write a contract clause that says which agents may remain, and what the build does with the others.

### Decide who owns DNS

Decide whether the A and AAAA records for a node's fully qualified domain name are part of the raw node contract or a step for the orchestration controller.

### Check the firewall zones on hosts with more than one interface

An Incus container has one interface. A VPS may have a public interface, a private network and IPv6. Check that Foomuuri's zones match the interfaces such a host really has, and that its rules cover IPv6.

### Order hosts through a provider's API

The ssh platform adopts a host ordered by hand. A provider whose API passes the Universal Cake metrics could have a platform of its own that orders the host, for example with the `hetzner.hcloud` collection, and then reuses the ssh platform's plays.

### Bring the design documents in line

The uc-create-raw-node design brief and the simple split describe an earlier design: five playbooks, `raw_node_firewall`, a platform registry, attempt records and a validator. Update them to the controller as it is now, with its platforms in `inventory/group_vars/all/platforms.yml` and `platforms/`, or retire what no longer applies.

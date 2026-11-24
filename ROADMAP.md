# Roadmap

## Next

### Set the hostname and fully qualified domain name on the node

The node is still named after the client domain inside. Calculate the two names agreed for a raw node from the client domain, and hand them to `robertdebock.hostname`:

| Name | Rule | For `vishpala.com` |
| :-- | :-- | :-- |
| Hostname | the first label of the fully qualified domain name | `raw` |
| Fully qualified domain name | `raw.<client domain>` | `raw.vishpala.com` |

The fully qualified domain name becomes its own variable, and `incus_instance` in `group_vars/all/incus.yml` is calculated from it instead of repeating the rule.

### Check the node definition before anything is created

A missing field is only found after the instance has been created and bootstrapped, when `robertdebock.users` reads it. Add a check at the start of the Create the node play, so the run stops before anything is created:

- every required field is present
- the client domain is DNS labels separated by dots
- the naming rules hold, once they are settled

`scripts/new-node` already checks its answers, so the check in `build.yml` covers node definitions written by hand.

### Tag steelcj.foomuuri

`requirements.yml` pins `steelcj.foomuuri` to a commit, because the role has no release yet. Tag the repository, for example `0.1.2`, and pin the tag instead.

### Bring the design documents in line

The uc-create-raw-node design brief and the simple split describe an earlier design: five playbooks, `raw_node_firewall`, a platform registry, attempt records and a validator. Update them to the controller as it is now, or retire what no longer applies.


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

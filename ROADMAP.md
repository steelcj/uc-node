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


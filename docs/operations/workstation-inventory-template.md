# Workstation Inventory Template

Create one external record per managed workstation class. Do not put completed inventories, machine/user identity, network values, or approval evidence in Git.

| Field | Required external value |
|---|---|
| Windows edition, build, and patch policy | Exact supported class |
| Access version and update channel | Exact Microsoft 365/Access version and channel |
| Access bitness | 32-bit or 64-bit |
| Word version and bitness | Exact supported version/bitness |
| CPU architecture | x64 or separately approved architecture |
| Display scale and resolution | Tested scale/resolution classes |
| Trust Center and macro policy | Approved policy outcome |
| Trusted-location capability | Narrow path and ACL outcome |
| Proxy, firewall, and TLS inspection | Compatibility outcome only |
| LocalAppData permission | Required application/update access outcome |
| Endpoint protection result | `.accde` and updater acceptance outcome |
| Supported or excluded decision | Supported, remediate, or exclude |

If both Access bitnesses appear in inventory, each requires a separate artifact and complete test evidence.

Agents record only whether the inventory was reviewed, never its contents.

Store completed records in the agency-approved system of record.

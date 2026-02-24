# Attack Path Finder (Dijkstra)

A tiny, **self-contained** Python demo that models a toy “attack graph” and uses **Dijkstra’s shortest path** algorithm to find the cheapest path from a chosen START node to a TARGET node.

It’s meant to be readable and easy to tweak for coursework, demos, and security documentation.

## What it does

- Builds a directed graph of nodes (attacker, hosts, users, services, databases, a vault, logs, etc.)
- Each edge has:
  - `Result` (think: *event / technique / action*, e.g., `phishing_success`, `vault_access`)
  - `weight` (think: *cost / difficulty / friction*)
- Runs Dijkstra from your START node
- Prints:
  - The shortest path START → TARGET (with total cost + hop count)
  - A ranking of how “reachable” the 6 main assets are from your START node

## Quick start

### Requirements
- Python **3.9+** (no external libraries)

### Run
```bash
python attack_path_dijkstra.py
```

You’ll be prompted for:
- START node (press Enter for `attacker`)
- TARGET node

## Sample run

Example inputs:
- START: `Finance_Database`
- TARGET: `vault:secrets`

Example output (shortened):
```text
=== Assets (6 places) ===
1. Finance_Database
2. HR_Database
3. Customer_Database
4. Orders_Database
5. vault:secrets
6. Logs

Enter the 2 nodes you have in mind.
START node (press Enter for 'attacker'): Finance_Database
TARGET node (one of the assets or any node): vault:secrets

=== Shortest Path Result (Dijkstra) ===
[+] Path found: Finance_Database -> vault:secrets
    Total cost: 55.00
    Hops      : 11

Steps:
  01. Finance_Database -> srv:fileserver | Result =service_account_reuse | w=2
  02. srv:fileserver -> net:core | Result =route_to_core | w=30
  03. net:core -> attacker | Result =route_from_core | w=10
  ...
```

## Customizing the graph

Open `attack_path_dijkstra.py` and edit `build_demo_graph()`:

- Add/remove nodes by adding edges with:
  ```python
  g.add_edge("src", "dst", "Result_name", weight)
  ```
- Change “default routing” costs through `net:core` inside `add_core_connectivity(...)`
- Use `overrides` to make specific nodes harder/easier to route to/from

## Notes

- **Lower weight = easier** (cheaper attack step)
- The `net:core` node is a convenience trick to keep the directed graph strongly connected, so paths exist between any two nodes.
- This is a **toy** demo graph (not a real threat model). For real use, edge weights should be derived from your risk model (e.g., privilege level required, exposure, controls, detection likelihood, etc.).

## Repo contents

- `attack_path_dijkstra.py` — main script
- `LICENSE` — MIT
- `SECURITY.md` — security policy
- `CONTRIBUTING.md` — contribution notes

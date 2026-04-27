# Demo Scenario — Two-Reagent Mix + Rinse

A typical microfluidic control sequence packaged as Flow Designer JSON and
Flow Graph JSON. Use it to verify the GUI end-to-end on your hardware, and as
a starting template for your own protocols.

## The scenario

Eight-step two-reagent mixing experiment:

| Step | Action | Why |
|------|--------|-----|
| 1 | Switch valves → `(1, 0, 0, 0)` | Open the inlet channel on V1 |
| 2 | Move syringe (pump A) → 100 µL/min, 50 µL | Push reagent A into the mixing chamber |
| 3 | Wait 3 s | Let the slug reach the chamber |
| 4 | Move syringe (pump B) → 100 µL/min, 50 µL | Push reagent B |
| 5 | Wait 30 s | React |
| 6 | Switch valves → `(0, 1, 0, 0)` | Re-route to the rinse channel on V2 |
| 7 | Move syringe (pump A) → 200 µL/min, 200 µL | Rinse at higher flow rate |
| 8 | Stop board | Park all pumps + close valves |

Total time: ~45 s plus pump-response latency. Total volume: 300 µL.

## Files

- `demo_scenario_flow.json` — loads into **Flow Designer** tab
- `demo_scenario_graph.json` — loads into **Flow Graph** tab (same scenario,
  8-node linear chain)

## Running on the demo (macOS, no hardware)

1. `cd labsmith-repo/Python`
2. `python3 dev_tools/demo_launcher.py`
3. GUI comes up and auto-connects to a stub board with three fake devices:
   `SPS01_1`, `SPS01_2`, `C4VM_10`.
4. **Flow Designer tab** → `Load flow` → pick
   `test_data/demo_scenario_flow.json` → `Run flow`. Each row highlights cyan
   while executing, green on success.
5. **Flow Graph tab** → `Load graph` → pick
   `test_data/demo_scenario_graph.json` → `Run graph`. Each node's border
   turns cyan → green as it runs.

Stub "hardware" completes every command instantly with success. This only
verifies the GUI / control path, NOT the real LabSmith behaviour.

## Running on real hardware (Windows)

After connecting the board, the Flow Designer and Flow Graph parameter panels
show editable dropdowns populated from the currently connected devices. Prefer
choosing `Pump1`, `Manifold (Addr 32)`, or the equivalent names reported by
your hardware from those dropdowns, then save the flow/graph again.

Old demo files that still contain `SPS01_1`, `SPS01_2`, or `C4VM_10` are kept
compatible: the app maps those legacy placeholders to connected devices and
shows a warning recommending that you reselect from the dropdown. This lets old
JSON run without forcing an immediate file migration.

If you want to edit JSON manually, use the names your LabSmith board actually
returned on connect. Two ways to find them:

1. **Bus modules tab** → look at the device table. The "Name" column shows the
   `GetName()` value for every connected SPS01 / C4VM / C4AM / C4PM / CEP01.
2. **Manual Control tab** → the syringe / manifold dropdowns list the same
   names.

Then edit the JSON file(s) and substitute:

| Placeholder (in demo files) | What to replace it with |
|-----------------------------|-------------------------|
| `SPS01_1` | The real pump that dispenses reagent A |
| `SPS01_2` | The real pump that dispenses reagent B |
| `C4VM_10` | The real valve manifold that routes inlet vs rinse |

You probably also want to tune:

- **Flow rates** (`flowrate`, µL/min): match your tubing and back-pressure
- **Volumes** (`volume`, µL): match your mixing chamber size
- **Wait times** (`seconds`): match your reaction kinetics
- **Valve positions** (`v1`..`v4`): must correspond to your physical plumbing.
  The demo uses position `1` = "open / route on this channel" and `0` = "no
  change / closed", which is the GUI's binary mode. The underlying driver
  also supports positions 2 (closed) and 3 (position B); expose those through
  the GUI only if you need them.

Once substituted, load and `Run` exactly as in the demo.

## Things to look for during the demo

- **Stop button stays responsive** while a move is in flight (click it mid-run
  — execution should halt within ~200 ms and the current row turns orange).
- **Device offline / stalled** during a move raises a clear error dialog and
  the failed row turns red. No silent "green = success" when nothing
  happened.
- **Multi-node Graph** follows the edges in topological order (single chain
  here). If you edit the graph to create a branch, cycle, or multiple
  starts/ends, the pre-run validator refuses with a specific message instead
  of running garbage.
- **Save flow / Save graph** produces a file with `version: 1` that loads
  back unchanged (round-trip safe). Loading a future `version: 2` file is
  rejected with a clear message, not silently misinterpreted.

## Troubleshooting

- **"Syringe X is offline"** — check the COM cable and `CmdGetStatus` on the
  Bus modules tab. The new code refuses to send move commands to an offline
  pump rather than issue no-ops.
- **"Syringe X stalled during move"** — hardware stalled mid-run. The new
  code raises immediately instead of waiting for the hardware to magically
  recover.
- **GUI freezes during connect** — the default path uses a worker thread.
  If the Windows COM driver crashes on cross-thread use, set the env var
  `LABSMITH_SYNC_CONNECT=1` and relaunch; connect will run on the GUI thread
  (briefly freezes the window but avoids the thread-affinity risk).
- **MoveWaitScript.py says "not enough pumps on board"** — the script
  invokes a 4-pump `MoveWait` but only fewer pumps are connected. Either
  connect more pumps or reduce the `MoveWait` call to match the pump count.

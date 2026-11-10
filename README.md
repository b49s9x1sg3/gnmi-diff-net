# gnmi-diff-net

Read-only gNMI state differ for network change windows and CI.

You render intended state from the source of truth, collect the running state
from the device, and get a leaf-level patch review **before** anything is
pushed. No session, no credentials, no write path: the tool only compares two
JSON snapshots, so it is safe to run from a laptop, a jump host or a pipeline.

## Why

Reviewing a rendered config diff is not enough when the device has drifted:
a push can revert an out-of-band change nobody remembers, or miss a change the
renderer does not own. Comparing running vs intended makes both visible and
tags each path with a blast-radius tier:

| severity | sample paths |
| --- | --- |
| high | `/system/...`, `/network-instances/...`, `.../config/enabled`, `mtu`, `address` |
| medium | routing policy, BGP, prefix lists |
| low | descriptions, aliases, other leaves |

Changed paths are sorted high impact first. Removals are reported too: intended
state is authoritative, so anything absent from it is a candidate revert.

## Install

Python 3.9+, standard library only.

```sh
git clone https://github.com/b49s9x1sg3/gnmi-diff-net
cd gnmi-diff-net
python -m unittest discover -s tests      # optional check
```

Run it in place with `python -m gnmi_diff.cli`, or install the `gnmi-diff`
entry point with `pip install .` into a throwaway virtualenv.

## Usage

```sh
python -m gnmi_diff.cli --running examples/running.json --intended examples/intended.json
```

```
intended.json: 6 change(s)
marker  severity  path
-       high      /interfaces/ethernet-1/2/config/enabled  True
+       high      /interfaces/ethernet-1/3/config/enabled  True
+       high      /interfaces/ethernet-1/3/config/mtu  9214
~       high      /system/config/hostname  'leaf-01' -> 'leaf-02'
-       low       /interfaces/ethernet-1/2/config/description  'old-lab-uplink'
+       low       /interfaces/ethernet-1/3/config/description  'new-member'
drift detected: 6 change(s) (4 high, 2 low)
```

`--json` emits the same change set as objects (`path`, `kind`, `before`,
`after`, `severity`) for a chatop or ticket. `--check` exits `1` on any drift
and `0` when the device matches, which is the CI mode: pin the snapshot you
last reviewed as `--intended`.

Exit codes: `0` reviewed/clean, `1` drift under `--check`, `2` unreadable or
malformed snapshot.

## Change window and rollback

1. Snapshot running state to `pre.json`, render intended state to `desired.json`.
2. Run the differ; post the high tier first for a second pair of eyes.
3. Push only the reviewed paths, then re-collect and diff again until clean.
4. Rollback: keep `pre.json` in the ticket; run `--intended pre.json` against a
   fresh snapshot to get the revert set.

A snapshot is only as fresh as its collection. Re-collect immediately before
apply, never reuse yesterday's file, and hold the window if the diff contains
unexplained removals.

## Layout

```
gnmi_diff/model.py   snapshot loading, flattening, severity tiers
gnmi_diff/diff.py    pure add/remove/modify diff and text report
gnmi_diff/cli.py     argument parsing, exit codes, JSON output
examples/            running and intended snapshots for a two-leaf lab
tests/               diff, severity, sequencing and CLI exit-code tests
```

Paths are slash-joined snapshot keys; sequences are indexed
(`/ntp/server/1`). Apply is intentionally out of scope: pipe the JSON to your
existing gNMI Set wrapper after review.

## License

MIT, see [LICENSE](LICENSE).

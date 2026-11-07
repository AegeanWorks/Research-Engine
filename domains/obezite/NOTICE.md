# Ported obezite claim-ledger notice

- Source: `projects/obezite-mekanizma-projesi`, committed HEAD
  `18b5d4d8e2196384f4e960f01b3031beb0a6315a`.
- License: Aegean Source License 1.1 (`LicenseRef-ASL-1.1`), same as the host.
- Ported: `08_ARACLAR/sentez_uret.py` (as `domains.obezite.sentez`) and `08_ARACLAR/atif.py`.
  The 6.1 GB corpus, the canonical ledger and every generated synthesis file stay external.
- Modifications: package path changed; the default root is the sibling checkout; generated
  projections go to the pack, never to the source tree; the file inventory is opt-in.
- The source repository is read-only and is never modified.

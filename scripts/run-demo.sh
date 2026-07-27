#!/usr/bin/env sh
set -eu

python3 -m opensignal.cli demo \
  --evidence-set evidence_sets/fda-demo-v1.json

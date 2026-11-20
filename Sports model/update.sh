#!/bin/zsh
# One refresh: new scores, box scores, DraftKings lines, injuries, then fresh
# predictions in PREDICTIONS.md. Meant to run every 30 minutes.
cd "$(dirname "$0")"
mkdir -p logs
echo "=== $(date '+%Y-%m-%d %H:%M:%S')" >> logs/update.log
/opt/homebrew/bin/python3.14 predict.py --quiet >> logs/update.log 2>&1
tail -n 2000 logs/update.log > logs/update.tmp && mv logs/update.tmp logs/update.log

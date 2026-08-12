#!/usr/bin/env bash
cd /c/Users/noori/reelforge
for i in $(seq 1 80); do
  done_ct=$(grep -l '"status": "done"' static/generated/*/job.json 2>/dev/null | wc -l)
  echo "[$i] total_done=$done_ct"
  hit=0
  for j in ea27978e57ef 43f08a7183cd 7f1b1dcf5ba9; do
    if grep -q '"status": "done"' static/generated/$j/job.json 2>/dev/null; then hit=$((hit+1)); fi
  done
  echo "  target jobs done so far: $hit/3"
  if [ "$hit" -eq 3 ]; then echo "ALL 3 TARGET JOBS DONE"; break; fi
  sleep 12
done
echo "=== final target job states ==="
for j in ea27978e57ef 43f08a7183cd 7f1b1dcf5ba9; do
  echo "$j: $(grep -o '"status": "[^"]*"' static/generated/$j/job.json | head -1)"
done

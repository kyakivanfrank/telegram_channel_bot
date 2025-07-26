#!/bin/bash

LOG_DIR="logs"
MAX_LINES=1000  # Keep only the last 1000 lines

rotate_file() {
  local file="$1"
  if [ -f "$file" ]; then
    local line_count
    line_count=$(wc -l < "$file")
    if [ "$line_count" -gt "$MAX_LINES" ]; then
      tail -n "$MAX_LINES" "$file" > "$file.tmp" && mv "$file.tmp" "$file"
      echo "$(basename "$file") rotated at $(date)"
    fi
  fi
}

rotate_file "$LOG_DIR/bot_log.txt"
rotate_file "$LOG_DIR/start_log.txt"

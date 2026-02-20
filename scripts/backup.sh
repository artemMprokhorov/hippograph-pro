#!/bin/bash
# Backup script for Neural Memory Graph
# Creates timestamped backup of the database

BACKUP_DIR="${BACKUP_DIR:-./backups}"
DB_PATH="${DB_PATH:-./data/memory.db}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/memory_backup_$TIMESTAMP.db"

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

# Check if database exists
if [ ! -f "$DB_PATH" ]; then
    echo "❌ Database not found: $DB_PATH"
    exit 1
fi

# Create backup
cp "$DB_PATH" "$BACKUP_FILE"

if [ $? -eq 0 ]; then
    echo "✅ Backup created: $BACKUP_FILE"
    
    # Show backup size
    SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    echo "   Size: $SIZE"
    
    # Keep only last 10 backups
    cd "$BACKUP_DIR"
    ls -t memory_backup_*.db | tail -n +11 | xargs -r rm
    echo "   Cleaned old backups (keeping last 10)"
else
    echo "❌ Backup failed"
    exit 1
fi

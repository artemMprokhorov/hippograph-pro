#!/bin/bash
# Restore script for Neural Memory Graph
# Restores database from backup

BACKUP_DIR="${BACKUP_DIR:-./backups}"
DB_PATH="${DB_PATH:-./data/memory.db}"

# List available backups
echo "Available backups:"
ls -la "$BACKUP_DIR"/memory_backup_*.db 2>/dev/null

if [ $? -ne 0 ]; then
    echo "❌ No backups found in $BACKUP_DIR"
    exit 1
fi

# Get latest backup if no argument provided
if [ -z "$1" ]; then
    BACKUP_FILE=$(ls -t "$BACKUP_DIR"/memory_backup_*.db | head -1)
    echo ""
    echo "Using latest backup: $BACKUP_FILE"
else
    BACKUP_FILE="$1"
fi

# Confirm restore
echo ""
read -p "⚠️  This will overwrite current database. Continue? (y/N) " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    exit 0
fi

# Stop container if running
docker-compose stop 2>/dev/null

# Restore
cp "$BACKUP_FILE" "$DB_PATH"

if [ $? -eq 0 ]; then
    echo "✅ Database restored from: $BACKUP_FILE"
    
    # Restart container
    docker-compose up -d 2>/dev/null
    echo "✅ Container restarted"
else
    echo "❌ Restore failed"
    exit 1
fi

# Import/Export

Backup your Neural Memory Graph database.

## Export

```bash
python3 scripts/export_memory.py data/memory.db backups/export.json
```

## What Gets Exported

- All notes with metadata  
- All connections (edges)
- All entities and relationships
- **Note:** Embeddings NOT exported (recomputed on import)

## File Sizes

- 300 notes: ~5-6 MB
- 1000 notes: ~15-20 MB

## Backup Strategy

- Before major changes
- Weekly automated backups
- Store securely (plain text!)

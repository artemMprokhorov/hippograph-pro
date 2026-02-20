# Troubleshooting

Common issues and solutions for Neural Memory Graph.

## Container Issues

### Container won't start

**Check logs:**
```bash
docker-compose logs
```

**Common causes:**
- Port 5001 already in use → Change in docker-compose.yml
- Not enough RAM → Need 4GB minimum
- Disk full → Clean Docker cache: `docker system prune`

### Container starts but exits immediately

Check for Python errors:
```bash
docker-compose logs | grep -i error
```

Usually missing dependencies or database path issues.

---

## Connection Issues

### "Unauthorized" error

- Verify API key matches between `.env` and your client
- Check URL encoding if key contains special characters
- Try Bearer token instead of URL parameter

### Connection refused

1. Check container is running: `docker-compose ps`
2. Verify port mapping: should show `5001->5000`
3. Test locally: `curl http://localhost:5001/health`

### ngrok tunnel not working

- Ensure ngrok is pointing to correct port (5001, not 5000)
- Check ngrok dashboard for errors
- Free tier has session limits - restart if expired

---

## Search Issues

### Search returns no results

- Verify notes exist: use `neural_stats` tool
- Check if query is too specific
- Similarity threshold may be too high (default 0.5)

### Search returns wrong results

Possible embedding drift after rebuild:
```bash
# Recompute all embeddings
docker-compose exec neural-memory python /app/scripts/recompute_embeddings.py
```

---

## Performance Issues

### Slow search

- Normal for first query (model loading)
- Subsequent queries should be <1s
- If consistently slow, check available RAM

### High memory usage

- Embedding model uses ~2GB, this is normal
- With many notes (1000+), consider increasing RAM
- SQLite can be swapped for PostgreSQL for large scale

---

## Database Issues

### Database corruption

Restore from backup:
```bash
./scripts/restore.sh
```

### Lost data after container restart

- Check volume mount in docker-compose.yml
- Data should persist in `./data/memory.db`
- If using Docker volume (not bind mount), data is inside Docker

### Migrate to new server

1. Stop container: `docker-compose down`
2. Copy entire project folder including `./data/`
3. Start on new server: `docker-compose up -d`

---

## Getting Help

If none of these solutions work:

1. Check GitHub Issues for similar problems
2. Open new issue with:
   - Docker logs
   - Your OS and Docker version
   - Steps to reproduce

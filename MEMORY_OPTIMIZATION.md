# Memory Optimization Guide for Production

## Current Memory Issues (1.58 GB)

### Root Causes:
1. **Too many worker processes** - Each worker loads entire app into memory
2. **Duplicate schedulers** - Scheduler running in every worker instead of master only
3. **No HTTP connection pooling** - New connections created for each AI request
4. **Infrequent worker recycling** - Workers accumulate memory over time

## Changes Made:

### 1. Reduced Worker Count (`gunicorn.conf.py`)
**Before:** `workers = cpu_count * 2 + 1` (e.g., 5-9 workers)
**After:** `workers = cpu_count + 1` (e.g., 3-5 workers)
**Memory Saved:** ~40-60% reduction in base memory

### 2. Aggressive Worker Recycling
**Before:** 
- `max_requests = 1000`
- `max_worker_lifetime = 3600` (1 hour)

**After:**
- `max_requests = 500` (restart after 500 requests)
- `max_worker_lifetime = 1800` (restart after 30 minutes)

**Benefit:** Prevents memory leaks from accumulating

### 3. Fixed Scheduler Duplication (`main.py`)
**Before:** Scheduler started in every worker process
**After:** Scheduler only runs in master process
**Memory Saved:** ~100-200 MB (5-9 duplicate schedulers eliminated)

### 4. HTTP Connection Pooling (`app/utils/ai.py`)
**Before:** New `httpx.AsyncClient` created for each AI request
**After:** Persistent client with connection pooling
**Memory Saved:** ~20-50 MB per concurrent request
**Performance:** Faster AI requests through connection reuse

## Environment Variables

You can override worker count in production:

```bash
# Set custom worker count (default: cpu_count + 1)
export GUNICORN_WORKERS=3

# Set bind address (default: 0.0.0.0:8000)
export GUNICORN_BIND="0.0.0.0:8000"
```

## Expected Results:

### Before Optimization:
- **Memory:** ~1.58 GB
- **Workers:** 5-9 (depending on CPU cores)
- **Schedulers:** 5-9 duplicate instances

### After Optimization:
- **Memory:** ~600-800 MB (60% reduction)
- **Workers:** 3-5 (depending on CPU cores)
- **Schedulers:** 1 instance (master only)

## Monitoring Commands:

```bash
# Check memory usage
docker stats

# Check worker count
ps aux | grep gunicorn | wc -l

# View logs for scheduler messages
docker logs <container-id> | grep scheduler
```

## Additional Recommendations:

### 1. Database Connection Pooling
Add to your database configuration:
```python
# In app/core/database.py
engine = create_engine(
    DATABASE_URL,
    pool_size=5,          # Max connections per worker
    max_overflow=10,      # Additional connections if needed
    pool_recycle=3600,    # Recycle connections after 1 hour
    pool_pre_ping=True    # Verify connections before use
)
```

### 2. Enable Garbage Collection Logging
Add to `main.py` startup:
```python
import gc
gc.set_debug(gc.DEBUG_STATS)
```

### 3. Monitor Memory Per Worker
Add to `gunicorn.conf.py`:
```python
def worker_exit(server, worker):
    import resource
    usage = resource.getrusage(resource.RUSAGE_SELF)
    server.log.info(f"Worker {worker.pid} exited. Memory used: {usage.ru_maxrss / 1024:.2f} MB")
```

### 4. Consider Using Preload
Add to `gunicorn.conf.py`:
```python
preload_app = True  # Load app before forking workers
```
**Benefit:** Shares read-only memory between workers
**Caution:** Requires careful handling of database connections

## Deployment Steps:

1. **Deploy changes** to production
2. **Restart application** to apply new configuration
3. **Monitor memory** for 1-2 hours
4. **Adjust workers** if needed using `GUNICORN_WORKERS` env var
5. **Check logs** for scheduler messages (should only see 1 instance)

## Troubleshooting:

### If memory is still high:
1. Check for memory leaks in custom code
2. Review database query efficiency
3. Monitor AI request frequency
4. Consider reducing `max_tokens` in AI requests

### If performance degrades:
1. Increase worker count: `export GUNICORN_WORKERS=4`
2. Check database connection pool size
3. Monitor request queue length

### If scheduler doesn't run:
1. Check logs for "Starting usage tracking scheduler (master process)"
2. Verify no "Skipping scheduler in worker process" messages
3. Ensure at least one worker is running

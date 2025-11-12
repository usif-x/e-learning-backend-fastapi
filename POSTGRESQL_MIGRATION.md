# PostgreSQL Migration Guide

## Overview

Your FastAPI e-learning backend has been successfully converted from MySQL to PostgreSQL. Here's what was changed and next steps.

## Changes Made

### 1. Database Configuration

✅ **Already configured for PostgreSQL**

- `app/core/database.py` - Uses `postgresql+psycopg2://` connection string
- `requirements.txt` - Contains `psycopg2-binary==2.9.10`

### 2. Model Updates

✅ **Updated model definitions for PostgreSQL compatibility:**

- **courses.py**: Changed `server_default="0"` to `server_default='false'` for boolean fields
- **admin.py**: Removed `autoincrement=True` (default behavior in PostgreSQL)

### 3. Alembic Configuration

✅ **Updated migration configuration:**

- **alembic.ini**: Updated connection string reference to PostgreSQL
- **migrations/env.py**: Changed from `mysql+pymysql://` to `postgresql+psycopg2://`

### 4. Migration Files

✅ **Fixed existing migrations for PostgreSQL:**

- **101ddea63624_add_is_free_column_to_courses_table.py**: Changed boolean default from '0' to 'false'
- **a5a114ab47a8_add_wallet_column.py**: Added server_default='0' for wallet_balance

## PostgreSQL-Specific Improvements

### 1. Boolean Handling

- PostgreSQL uses `true`/`false` instead of `1`/`0` for boolean values
- Updated server defaults accordingly

### 2. Auto-increment

- PostgreSQL automatically handles serial/identity columns
- Removed explicit `autoincrement=True` declarations

### 3. String Length Constraints

- Your current String(length) definitions are already PostgreSQL compatible
- No changes needed for varchar constraints

## Database Setup Steps

### 1. Install PostgreSQL

```bash
# macOS with Homebrew
brew install postgresql
brew services start postgresql

# Create database
createdb elearning
```

### 2. Environment Variables

Update your `.env` file with PostgreSQL credentials:

```env
DB_HOST=localhost
DB_PORT=5432
DB_USERNAME=your_username
DB_PASSWORD=your_password
DB_DATABASE=elearning
```

### 3. Run Migrations

```bash
# Install Alembic if not already installed
pip install alembic

# Generate initial migration (if starting fresh)
alembic revision --autogenerate -m "Initial PostgreSQL schema"

# Or run existing migrations
alembic upgrade head
```

## Verification Steps

### 1. Test Database Connection

```python
# Test connection
python -c "
from app.core.database import engine
with engine.connect() as conn:
    print('✅ PostgreSQL connection successful')
"
```

### 2. Check Table Creation

```sql
-- Connect to PostgreSQL and verify tables
\c elearning
\dt
```

### 3. Test Application

```bash
# Start the FastAPI application
uvicorn main:app --reload
```

## Key Differences from MySQL

| Feature           | MySQL             | PostgreSQL             |
| ----------------- | ----------------- | ---------------------- |
| Boolean defaults  | `'0'`, `'1'`      | `'false'`, `'true'`    |
| Auto-increment    | `AUTO_INCREMENT`  | `SERIAL` or `IDENTITY` |
| String types      | `VARCHAR`, `TEXT` | `VARCHAR`, `TEXT`      |
| Numeric precision | Similar           | Similar                |
| Case sensitivity  | Case insensitive  | Case sensitive         |

## Performance Benefits

PostgreSQL offers several advantages over MySQL:

1. **Better JSON Support**: Native JSONB type for flexible data
2. **Advanced Indexing**: GIN, GiST, and partial indexes
3. **Full-Text Search**: Built-in text search capabilities
4. **Concurrent Performance**: Better handling of concurrent reads/writes
5. **Data Integrity**: Stronger ACID compliance
6. **Extensions**: Rich ecosystem of extensions

## Next Steps

1. **Backup MySQL Data** (if migrating existing data):

   ```bash
   mysqldump -u root -p elearning > mysql_backup.sql
   ```

2. **Data Migration** (if needed):

   - Export data from MySQL
   - Transform and import to PostgreSQL
   - Consider using tools like `pgloader` for automated migration

3. **Test Thoroughly**:

   - Test all API endpoints
   - Verify data integrity
   - Check performance
   - Test Telegram bot integration

4. **Monitor Performance**:
   - Enable PostgreSQL logging
   - Monitor query performance
   - Optimize indexes as needed

## Troubleshooting

### Common Issues:

1. **Connection Refused**:

   - Ensure PostgreSQL is running: `brew services restart postgresql`
   - Check port 5432 is available

2. **Authentication Failed**:

   - Verify credentials in `.env`
   - Check PostgreSQL user permissions

3. **Migration Errors**:
   - Drop and recreate database if starting fresh
   - Check migration file syntax

Your models are now fully PostgreSQL-compatible! 🎉

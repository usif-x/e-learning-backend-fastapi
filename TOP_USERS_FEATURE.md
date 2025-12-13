# Top Users Platform Usage Feature

## Overview
Added functionality to track and display the top 20 users who spend the most time on the platform for three different time periods:
- **Today**: Top users for the current day
- **This Week**: Top users for the current week (Monday to Sunday)
- **This Month**: Top users for the current month

## Implementation Details

### 1. Database Schema
Uses the existing `UserDailyUsage` model which tracks:
- `user_id`: User identifier
- `date`: Date of activity
- `minutes_spent`: Total minutes spent on the platform
- `last_ping`: Last activity timestamp

### 2. New API Endpoints

#### GET `/usage/top/today`
Returns the top 20 users by minutes spent today.

**Response:**
```json
{
  "period": "today",
  "start_date": "2025-12-13",
  "end_date": "2025-12-13",
  "users": [
    {
      "user_id": 123,
      "display_name": "John Doe",
      "total_minutes": 180,
      "rank": 1
    },
    ...
  ]
}
```

#### GET `/usage/top/week`
Returns the top 20 users by minutes spent this week (Monday to Sunday).

**Response:**
```json
{
  "period": "week",
  "start_date": "2025-12-09",
  "end_date": "2025-12-15",
  "users": [
    {
      "user_id": 456,
      "display_name": "Jane Smith",
      "total_minutes": 1200,
      "rank": 1
    },
    ...
  ]
}
```

#### GET `/usage/top/month`
Returns the top 20 users by minutes spent this month.

**Response:**
```json
{
  "period": "month",
  "start_date": "2025-12-01",
  "end_date": "2025-12-31",
  "users": [
    {
      "user_id": 789,
      "display_name": "Bob Johnson",
      "total_minutes": 5400,
      "rank": 1
    },
    ...
  ]
}
```

### 3. Files Modified

#### `/app/schemas/user_daily_usage.py`
- Added `TopUserItem` schema for individual user data
- Added `TopUsersResponse` schema for the leaderboard response

#### `/app/services/user_daily_usage.py`
- Added `get_top_users_today()` method
- Added `get_top_users_week()` method
- Added `get_top_users_month()` method

Each method:
- Joins `UserDailyUsage` with `User` table to get user information
- Aggregates total minutes spent per user
- Orders by total minutes descending
- Limits to top 20 users
- Returns formatted data with rank

#### `/app/routers/user_daily_usage.py`
- Added three new GET endpoints:
  - `/top/today`
  - `/top/week`
  - `/top/month`
- All endpoints are public (no authentication required)

## Usage Examples

### Using cURL

```bash
# Get top users today
curl http://localhost:8000/usage/top/today

# Get top users this week
curl http://localhost:8000/usage/top/week

# Get top users this month
curl http://localhost:8000/usage/top/month
```

### Using Python requests

```python
import requests

# Get top users today
response = requests.get("http://localhost:8000/usage/top/today")
data = response.json()

for user in data["users"]:
    print(f"Rank {user['rank']}: {user['display_name']} - {user['total_minutes']} minutes")
```

## Key Features

1. **Automatic Ranking**: Users are automatically ranked from 1 to 20 based on their total minutes
2. **User Display Names**: Shows user's full name (first name + last name) or just first name if last name is not available
3. **Time Period Context**: Each response includes the start and end dates for the period
4. **Efficient Queries**: Uses SQL aggregation and joins for optimal performance
5. **Consistent Data**: All time periods use the same data source and calculation method

## Notes

- The endpoints are **public** and don't require authentication
- Week calculation follows Monday-Sunday convention
- Month calculation uses the current calendar month
- Display names are constructed from `telegram_first_name` and `telegram_last_name` fields
- If a user has no activity in the specified period, they won't appear in the results
- The limit is hardcoded to 20 users but can be easily modified in the service methods

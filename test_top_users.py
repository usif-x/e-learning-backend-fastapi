#!/usr/bin/env python3
"""
Test script for the Top Users Platform Usage endpoints.
This script tests the three new endpoints:
- GET /usage/top/today
- GET /usage/top/week
- GET /usage/top/month
"""

import requests
import json
from datetime import date

# Configuration
BASE_URL = "http://localhost:8000"
ENDPOINTS = [
    "/usage/top/today",
    "/usage/top/week",
    "/usage/top/month",
]


def test_endpoint(endpoint: str):
    """Test a single endpoint and display results."""
    url = f"{BASE_URL}{endpoint}"
    
    print(f"\n{'='*80}")
    print(f"Testing: {endpoint}")
    print(f"{'='*80}")
    
    try:
        response = requests.get(url, timeout=10)
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            print(f"\nPeriod: {data['period']}")
            print(f"Start Date: {data['start_date']}")
            print(f"End Date: {data['end_date']}")
            print(f"Total Users: {len(data['users'])}")
            
            print(f"\n{'Rank':<6} {'User ID':<10} {'Display Name':<30} {'Minutes':<10}")
            print("-" * 80)
            
            for user in data['users'][:10]:  # Show top 10
                print(
                    f"{user['rank']:<6} "
                    f"{user['user_id']:<10} "
                    f"{user['display_name']:<30} "
                    f"{user['total_minutes']:<10}"
                )
            
            if len(data['users']) > 10:
                print(f"... and {len(data['users']) - 10} more users")
            
            print(f"\n✓ Test passed for {endpoint}")
            return True
            
        else:
            print(f"\n✗ Test failed with status code: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print(f"\n✗ Connection error: Could not connect to {BASE_URL}")
        print("Make sure the server is running!")
        return False
        
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        return False


def main():
    """Run all endpoint tests."""
    print("=" * 80)
    print("Top Users Platform Usage - Endpoint Tests")
    print("=" * 80)
    print(f"Base URL: {BASE_URL}")
    print(f"Date: {date.today()}")
    
    results = []
    
    for endpoint in ENDPOINTS:
        result = test_endpoint(endpoint)
        results.append((endpoint, result))
    
    # Summary
    print(f"\n{'='*80}")
    print("Test Summary")
    print(f"{'='*80}")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for endpoint, result in results:
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"{status:<12} {endpoint}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    exit(main())

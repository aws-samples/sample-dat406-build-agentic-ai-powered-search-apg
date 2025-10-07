#!/usr/bin/env python3
"""Quick test of search endpoint"""
import requests
import json

response = requests.post(
    "http://localhost:8000/api/search",
    json={"query": "wireless headphones", "limit": 3}
)

print(f"Status: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print(f"Found {data['total_results']} results")
    print(f"Search time: {data.get('search_time_ms', 0):.2f}ms")
    for result in data['results'][:2]:
        product = result['product']
        print(f"  - {product['product_description'][:60]}... ${product['price']}")
else:
    print(f"Error: {response.text}")

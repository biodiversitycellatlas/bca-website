import http.client
import os
import sys

headers = (
    {"X-Forwarded-Proto": "https"}
    if os.environ.get("ENVIRONMENT") == "prod"
    else {}
)
conn = http.client.HTTPConnection("localhost", 8000, timeout=2)
conn.request("GET", "/health/", headers=headers)
sys.exit(0 if conn.getresponse().status == 200 else 1)

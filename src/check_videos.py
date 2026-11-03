import os
import re
import requests
from dotenv import load_dotenv

load_dotenv()
KEY = os.getenv("YOUTUBE_API_KEY")

RAW = [
    "v=x_RV3xZWb5w",
    "v=7oOxFhNXrBk",
    "v=s3Lgesida1Q",
    "v=95P1o2HpAdw",
    "v=5yhDSXfYZAQ",
    "v=oKqSJ54-KSo",
]

def to_id(x):
    m = re.search(r"(?:v=|youtu\.be/|shorts/)([A-Za-z0-9_-]{11})", x)
    return m.group(1) if m else x.strip()

IDS = [to_id(x) for x in RAW]
print("asking for:", IDS)

r = requests.get(
    "https://www.googleapis.com/youtube/v3/videos",
    params={"part": "snippet,statistics", "id": ",".join(IDS), "key": KEY},
    timeout=30,
)
print("status:", r.status_code)
data = r.json()
if r.status_code != 200:
    print(data.get("error", {}).get("message"))
    raise SystemExit

items = data.get("items", [])
print("videos found:", len(items), "of", len(IDS))

for v in items:
    s, st = v["snippet"], v["statistics"]
    print(v["id"], "|", s["channelTitle"], "|", s["title"][:50],
          "| posted:", s["publishedAt"][:10],
          "| comments:", st.get("commentCount", "off"),
          "| views:", st.get("viewCount"))

missing = set(IDS) - {v["id"] for v in items}
if missing:
    print("not found (wrong ID, private or removed):", missing)
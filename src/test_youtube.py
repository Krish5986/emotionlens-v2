import os
import requests
from dotenv import load_dotenv

load_dotenv()
KEY = os.getenv("YOUTUBE_API_KEY")
VIDEO_ID = "x_RV3xZWb5w"

url = "https://www.googleapis.com/youtube/v3/commentThreads"
params = {
    "part": "snippet",
    "videoId": VIDEO_ID,
    "maxResults": 5,
    "order": "time",
    "textFormat": "plainText",
    "key": KEY,
}

r = requests.get(url, params=params, timeout=30)
print("status:", r.status_code)
data = r.json()

if r.status_code != 200:
    print(data.get("error", {}).get("message"))
    raise SystemExit

for item in data["items"]:
    c = item["snippet"]["topLevelComment"]["snippet"]
    print(c["publishedAt"], "| likes:", c["likeCount"], "|", c["textDisplay"][:100])
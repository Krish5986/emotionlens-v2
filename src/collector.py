import os
import time
import sqlite3
import argparse
import datetime as dt
import requests
from dotenv import load_dotenv

load_dotenv()
KEY = os.getenv("YOUTUBE_API_KEY")
DB_PATH = os.path.join("data", "comments.db")
API = "https://www.googleapis.com/youtube/v3/commentThreads"
DAILY_LIMIT = 8000        # safe margin under YouTube's default 10,000 units a day
MAX_PAGES_FIRST_RUN = 30  # up to 3,000 comments per video on the first run

VIDEOS = {
    "x_RV3xZWb5w": "A",
    "7oOxFhNXrBk": "A",
    "oKqSJ54-KSo": "A",
    "s3Lgesida1Q": "B",
    "95P1o2HpAdw": "B",
    "5yhDSXfYZAQ": "B",
}


def connect():
    os.makedirs("data", exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.execute("""CREATE TABLE IF NOT EXISTS comments (
        comment_id TEXT PRIMARY KEY, video_id TEXT, theme TEXT,
        published_at TEXT, like_count INTEGER, reply_count INTEGER,
        text TEXT, fetched_at TEXT)""")
    con.execute("CREATE TABLE IF NOT EXISTS video_state (video_id TEXT PRIMARY KEY, backfilled INTEGER)")
    con.execute("CREATE TABLE IF NOT EXISTS quota_log (day TEXT PRIMARY KEY, calls INTEGER)")
    con.commit()
    return con


def today():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")


def calls_today(con):
    row = con.execute("SELECT calls FROM quota_log WHERE day=?", (today(),)).fetchone()
    return row[0] if row else 0


def add_call(con):
    con.execute("INSERT OR REPLACE INTO quota_log VALUES (?, ?)", (today(), calls_today(con) + 1))
    con.commit()


def fetch_page(con, video_id, page_token=None):
    if calls_today(con) >= DAILY_LIMIT:
        raise RuntimeError("daily call limit reached")
    params = {"part": "snippet", "videoId": video_id, "maxResults": 100,
              "order": "time", "textFormat": "plainText", "key": KEY}
    if page_token:
        params["pageToken"] = page_token
    r = requests.get(API, params=params, timeout=30)
    add_call(con)
    return r.status_code, r.json()


def poll_video(con, video_id, theme):
    row = con.execute("SELECT backfilled FROM video_state WHERE video_id=?", (video_id,)).fetchone()
    backfilled = bool(row and row[0])
    token, pages, new_total = None, 0, 0
    while True:
        status, data = fetch_page(con, video_id, token)
        if status != 200:
            print(f"  {video_id}: error {status}: {data.get('error', {}).get('message')}")
            return new_total
        now = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
        new_here = 0
        for item in data.get("items", []):
            top = item["snippet"]["topLevelComment"]
            c = top["snippet"]
            cur = con.execute(
                "INSERT OR IGNORE INTO comments VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (top["id"], video_id, theme, c["publishedAt"], c["likeCount"],
                 item["snippet"]["totalReplyCount"], c["textDisplay"], now))
            new_here += cur.rowcount
        con.commit()
        new_total += new_here
        pages += 1
        token = data.get("nextPageToken")
        if not token or (not backfilled and pages >= MAX_PAGES_FIRST_RUN):
            con.execute("INSERT OR REPLACE INTO video_state VALUES (?, 1)", (video_id,))
            con.commit()
            break
        if backfilled and new_here == 0:
            break
    return new_total


def run_once(con):
    print(dt.datetime.now().strftime("%H:%M:%S"), "polling", len(VIDEOS), "videos")
    for video_id, theme in VIDEOS.items():
        try:
            n = poll_video(con, video_id, theme)
            print(f"  {video_id} (theme {theme}): {n} new")
        except RuntimeError as e:
            print("stopping:", e)
            return False
        except requests.RequestException as e:
            print(f"  {video_id}: network problem ({e.__class__.__name__}), will retry next round")
    total = con.execute("SELECT COUNT(*) FROM comments").fetchone()[0]
    print(f"  total comments stored: {total} | API calls today (UTC): {calls_today(con)}")
    return True


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--loop", action="store_true", help="keep polling")
    ap.add_argument("--every", type=int, default=10, help="minutes between polls")
    args = ap.parse_args()
    if not KEY:
        raise SystemExit("No API key found. Check your .env file.")
    con = connect()
    if not args.loop:
        run_once(con)
    else:
        while run_once(con):
            time.sleep(args.every * 60)
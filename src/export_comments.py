import sqlite3
import pandas as pd

con = sqlite3.connect("data/comments.db")
df = pd.read_sql(
    "SELECT comment_id, video_id, theme, published_at, like_count, reply_count, text FROM comments",
    con,
)
df.to_csv("data/comments_export.csv", index=False, encoding="utf-8-sig")
print(len(df), "comments exported")
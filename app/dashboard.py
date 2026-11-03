import pandas as pd
import streamlit as st

st.set_page_config(page_title="EmotionLens", layout="wide")
st.title("EmotionLens: comment sentiment monitor")

REQUIRED = ["theme", "published_at", "label", "confidence", "margin",
            "reverse_tag", "lang_guess", "text"]

uploaded = st.sidebar.file_uploader("Upload a scored CSV (optional)", type="csv")
df = pd.read_csv(uploaded) if uploaded else pd.read_csv("data/comments_scored.csv")

missing = [c for c in REQUIRED if c not in df.columns]
if missing:
    st.error(f"The file is missing these columns: {missing}")
    st.stop()

df["published_at"] = pd.to_datetime(df["published_at"], utc=True)

themes = sorted(df["theme"].unique())
chosen = st.sidebar.multiselect("Theme", themes, default=themes)
df = df[df["theme"].isin(chosen)]

step = st.sidebar.radio("Time step", ["hour", "day"], index=0)
margin_cut = st.sidebar.slider("Review if model margin is below", 0.0, 1.0, 0.2, 0.05)

order = ["negative", "neutral", "positive"]
review = df["reverse_tag"] | (df["margin"] < margin_cut) | (df["lang_guess"] != "english/other")

c1, c2, c3 = st.columns(3)
c1.metric("Comments", len(df))
c2.metric("Negative share", f"{(df['label'] == 'negative').mean():.0%}")
c3.metric("Flagged for review", int(review.sum()))

st.subheader("Sentiment by theme")
by_theme = pd.crosstab(df["theme"], df["label"], normalize="index").reindex(columns=order, fill_value=0)
st.bar_chart(by_theme)

st.subheader("Comments over time by sentiment")
freq = "h" if step == "hour" else "D"
df["bucket"] = df["published_at"].dt.floor(freq)
over_time = df.groupby(["bucket", "label"]).size().unstack(fill_value=0).reindex(columns=order, fill_value=0)
st.line_chart(over_time)

st.subheader("Needs human review")
st.caption("Flagged: reversing hashtags, model unsure (small margin), or Hindi/Hinglish text.")
flagged = df[review][["theme", "label", "confidence", "margin", "lang_guess", "text"]]
st.dataframe(flagged.sort_values("margin").head(200))
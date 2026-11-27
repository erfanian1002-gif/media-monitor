import streamlit as st
import urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from datetime import datetime, timedelta, timezone
from html import unescape
import re

st.set_page_config(
    page_title="سامانه پایش رسانه",
    page_icon="🔎",
    layout="wide"
)

st.title("سامانه پایش و جست‌وجوی رسانه")
st.caption("آزمایشی ــ دریافت خبر از خوراک RSS مستقیم BBC فارسی")

FEED_URL = "https://feeds.bbci.co.uk/persian/rss.xml"


def clean_text(value):
    value = unescape(value or "")
    value = re.sub(r"<[^>]+>", " ", value)
    return " ".join(value.split())


def fetch_feed():
    request = urllib.request.Request(
        FEED_URL,
        headers={"User-Agent": "Mozilla/5.0"}
    )

    with urllib.request.urlopen(request, timeout=25) as response:
        xml_data = response.read()

    root = ET.fromstring(xml_data)
    items = []

    for item in root.findall(".//item"):
        title = clean_text(item.findtext("title", default=""))
        description = clean_text(item.findtext("description", default=""))
        link = item.findtext("link", default="")
        pub_date = item.findtext("pubDate", default="")

        try:
            date = parsedate_to_datetime(pub_date)
            if date.tzinfo is None:
                date = date.replace(tzinfo=timezone.utc)
            date_text = date.astimezone().strftime("%Y-%m-%d %H:%M")
        except Exception:
            date = None
            date_text = pub_date or "تاریخ نامشخص"

        items.append({
            "title": title,
            "description": description,
            "link": link,
            "date": date,
            "date_text": date_text,
        })

    return items


topic = st.text_input(
    "موضوع جست‌وجو",
    placeholder="مثلاً: مهاجرین افغانستانی"
)

if st.button("جست‌وجوی خبرها", type="primary"):
    if not topic.strip():
        st.warning("موضوع جست‌وجو را وارد کن.")
    else:
        try:
            with st.spinner("در حال دریافت خوراک خبری..."):
                items = fetch_feed()

            st.success(f"اتصال برقرار شد؛ {len(items)} خبر از خوراک دریافت شد.")

            cutoff = datetime.now(timezone.utc) - timedelta(days=30)
            topic_words = topic.strip().lower().split()

            matches = []
            for item in items:
                searchable = (
                    item["title"] + " " + item["description"]
                ).lower()

                is_recent = (
                    item["date"] is None
                    or item["date"].astimezone(timezone.utc) >= cutoff
                )

                if is_recent and all(word in searchable for word in topic_words):
                    matches.append(item)

            if matches:
                st.subheader(f"{len(matches)} خبر مرتبط")
                for item in matches:
                    with st.container(border=True):
                        st.caption(f"BBC فارسی · {item['date_text']}")
                        st.markdown(f"**{item['title']}**")
                        if item["description"]:
                            st.write(item["description"])
                        if item["link"]:
                            st.markdown(f"[مشاهده خبر اصلی]({item['link']})")
            else:
                st.info(
                    "اتصال برقرار شد، اما در خبرهای موجود در این خوراک "
                    "مطابق با عبارت واردشده نتیجه‌ای پیدا نشد."
                )

                with st.expander("نمایش چند خبر دریافت‌شده برای بررسی اتصال"):
                    for item in items[:5]:
                        st.markdown(f"**{item['title']}**")
                        st.caption(item["date_text"])
                        if item["link"]:
                            st.markdown(f"[مشاهده خبر]({item['link']})")

        except Exception as error:
            st.error(
                f"دریافت خوراک خبری ناموفق بود: "
                f"{type(error).__name__}: {error}"
            )

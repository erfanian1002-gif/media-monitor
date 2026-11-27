import streamlit as st
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from datetime import datetime, timedelta, timezone
from html import unescape
from concurrent.futures import ThreadPoolExecutor, as_completed
import re

st.set_page_config(
    page_title="سامانه پایش رسانه",
    page_icon="🔎",
    layout="wide"
)

st.title("سامانه پایش و جست‌وجوی رسانه")
st.caption("نسخه آزمایشی ــ جست‌وجوی خبرهای عمومی از طریق RSS جست‌وجوی Google News")

# ۳۰ رسانه فارسی‌زبان یا مرتبط با ایران و افغانستان
# جست‌وجو به دامنه هر رسانه محدود می‌شود.
SOURCES = [
    ("BBC فارسی", "bbc.com/persian"),
    ("رادیو فردا", "radiofarda.com"),
    ("ایران اینترنشنال", "iranintl.com"),
    ("صدای آمریکا فارسی", "ir.voanews.com"),
    ("دویچه‌وله فارسی", "dw.com/fa-ir"),
    ("یورونیوز فارسی", "parsi.euronews.com"),
    ("بی‌بی‌سی دری", "bbc.com/dari"),
    ("آریانانیوز", "ariananews.af"),
    ("طلوع‌نیوز", "tolonews.com"),
    ("پژواک", "pajhwok.com"),
    ("خامه پرس", "khaama.com"),
    ("افغانستان اینترنشنال", "afintl.com"),
    ("خبرگزاری جمهوری اسلامی", "irna.ir"),
    ("ایسنا", "isna.ir"),
    ("ایرنا", "irna.ir"),
    ("مهر", "mehrnews.com"),
    ("تسنیم", "tasnimnews.ir"),
    ("فارس", "farsnews.ir"),
    ("ایسنا", "isna.ir"),
    ("خبرآنلاین", "khabaronline.ir"),
    ("تابناک", "tabnak.ir"),
    ("انتخاب", "entekhab.ir"),
    ("ایسکانیوز", "iscanews.ir"),
    ("ایلنا", "ilna.ir"),
    ("خبرگزاری دانشجو", "snn.ir"),
    ("جماران", "jamaran.news"),
    ("شرق", "sharghdaily.com"),
    ("اعتماد", "etemadonline.com"),
    ("رادیو زمانه", "radiozamaneh.com"),
    ("العربیه فارسی", "persian.alarabiya.net"),
]

def clean_text(value):
    value = unescape(value or "")
    value = re.sub(r"<[^>]+>", " ", value)
    return " ".join(value.split())

def make_feed_url(topic, domain):
    query = f'{topic} site:{domain} when:30d'
    params = {
        "q": query,
        "hl": "fa",
        "gl": "IR",
        "ceid": "IR:fa",
    }
    return "https://news.google.com/rss/search?" + urllib.parse.urlencode(params)

def fetch_source(source, topic):
    name, domain = source
    url = make_feed_url(topic, domain)

    request = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0"}
    )

    with urllib.request.urlopen(request, timeout=15) as response:
        xml_data = response.read()

    root = ET.fromstring(xml_data)
    results = []

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

        results.append({
            "source": name,
            "title": title,
            "description": description,
            "link": link,
            "date": date,
            "date_text": date_text,
        })

    return results

topic = st.text_input(
    "موضوع جست‌وجو",
    placeholder="مثلاً: مهاجرین افغانستانی"
)

if st.button("جست‌وجوی خبرها", type="primary"):
    if not topic.strip():
        st.warning("موضوع جست‌وجو را وارد کن.")
    else:
        all_results = []
        errors = []

        with st.spinner("در حال بررسی ۳۰ رسانه؛ ممکن است کمی زمان ببرد..."):
            with ThreadPoolExecutor(max_workers=8) as executor:
                futures = {
                    executor.submit(fetch_source, source, topic.strip()): source
                    for source in SOURCES
                }

                for future in as_completed(futures):
                    source = futures[future]
                    try:
                        all_results.extend(future.result())
                    except Exception as error:
                        errors.append(f"{source[0]}: {type(error).__name__}")

        # حذف موارد تکراری بر اساس لینک
        unique_results = {}
        for item in all_results:
            key = item["link"] or item["title"]
            unique_results[key] = item

        results = list(unique_results.values())

        # مرتب‌سازی بر اساس تاریخ انتشار
        results.sort(
            key=lambda item: item["date"] or datetime.min.replace(tzinfo=timezone.utc),
            reverse=True
        )

        st.success(
            f"بررسی {len(SOURCES)} رسانه تمام شد؛ "
            f"{len(results)} خبر دریافت شد."
        )

        if results:
            for item in results:
                with st.container(border=True):
                    st.caption(f"{item['source']} · {item['date_text']}")
                    st.markdown(f"**{item['title']}**")

                    if item["description"]:
                        st.write(item["description"])

                    if item["link"]:
                        st.markdown(f"[مشاهده خبر اصلی]({item['link']})")
        else:
            st.info(
                "خبری دریافت نشد. ممکن است موضوع نتیجه‌ای نداشته باشد "
                "یا دسترسی به Google News برقرار نشده باشد."
            )

        if errors:
            with st.expander(f"نمایش خطاهای {len(errors)} رسانه"):
                for error in errors:
                    st.write(error)

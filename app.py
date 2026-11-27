import streamlit as st
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

st.set_page_config(page_title="سامانه پایش رسانه", page_icon="🔎", layout="wide")
st.title("سامانه پایش و جست‌وجوی رسانه")
st.caption("آزمایشی ــ جست‌وجوی خبرهای عمومی از طریق Google News RSS")

topic = st.text_input("موضوع جست‌وجو", placeholder="مثلاً: مهاجرین افغانستانی")
regions = st.multiselect(
    "محدوده جست‌وجو",
    ["ایران", "افغانستان"],
    default=["ایران", "افغانستان"]
)

def fetch_news(topic, region):
    region_settings = {
        "ایران": ("IR", "IR:fa"),
        "افغانستان": ("AF", "AF:fa"),
    }
    gl, ceid = region_settings[region]
    query = f"{topic} when:30d"
    url = (
        "https://news.google.com/rss/search?q="
        + urllib.parse.quote_plus(query)
        + f"&hl=fa&gl={gl}&ceid={ceid}"
    )

    request = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0"}
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        xml_data = response.read()

    root = ET.fromstring(xml_data)
    results = []

    for item in root.findall(".//item"):
        title = item.findtext("title", default="بدون عنوان")
        link = item.findtext("link", default="")
        pub_date = item.findtext("pubDate", default="")
        source = item.findtext("source", default="منبع نامشخص")

        try:
            date_text = parsedate_to_datetime(pub_date).strftime("%Y-%m-%d %H:%M")
        except Exception:
            date_text = pub_date or "تاریخ نامشخص"

        results.append({
            "title": title,
            "link": link,
            "date": date_text,
            "source": source,
            "region": region,
        })

    return results

if st.button("جست‌وجوی خبرها", type="primary"):
    if not topic.strip():
        st.warning("موضوع جست‌وجو را وارد کن.")
    elif not regions:
        st.warning("حداقل یک محدوده را انتخاب کن.")
    else:
        all_results = []
        errors = []

        with st.spinner("در حال دریافت خبرها..."):
            for region in regions:
                try:
                    all_results.extend(fetch_news(topic.strip(), region))
                except Exception as error:
                    errors.append(f"{region}: {error}")

        if all_results:
            st.success(f"{len(all_results)} نتیجه دریافت شد.")
            for item in all_results:
                with st.container(border=True):
                    st.caption(f"{item['region']} · {item['source']} · {item['date']}")
                    st.markdown(f"**{item['title']}**")
                    if item["link"]:
                        st.markdown(f"[مشاهده خبر اصلی]({item['link']})")
        else:
            st.info("نتیجه‌ای دریافت نشد؛ ممکن است موضوع نتیجه‌ای نداشته باشد یا دسترسی به منبع برقرار نشده باشد.")

        for error in errors:
            st.warning(error)

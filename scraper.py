import requests
from bs4 import BeautifulSoup
import pandas as pd
import logging
import psycopg2


logging.basicConfig(
    level = logging.INFO,
    format = "%(asctime)s -%(levelname)s -%(message)s",
    filename = "app.log",
    filemode = "a"
)
def analyze_sentiment(title):
    title = title.lower()

    positive_words = ['growth' , 'success' ,'rise', 'gain', 'launch', 'expansion']
    negative_words = ['loss' ,'fall', 'down' , 'closed' , 'fraud' , 'unsuccessful' ,'drop' ,'decline' ,'scam', 'fall', 'lawsuit','crash']

    if any(word in title for word in positive_words):
        return "Positive / Good News"
    elif any(word in title for word in negative_words):
        return "Negative / Bad News"
    else:
        return "Neutral"
    
def start_research(company):

    try:
        logging.info(f"Research started for {company} .......")

        url = f"https://news.google.com/rss/search?q={company}"
        headers = {'User-Agent': 'Mozilla/5.0'}

        response = requests.get(url,headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.content , "xml")

    except Exception as e:

        logging.error(f"Exception occurred: {e}")
        return

    news_data = []


    for item in soup.find_all("item")[:10]:
        title = item.title.text
        pub_date = item.pubDate.text
        link = item.link.text
        sentiment = analyze_sentiment(title)

        news_data.append({
        "Company" : company,
        "Title": title,
        "Sentiment" : sentiment,
        "Link" : link,
        "Date" : pub_date
        })
        
    logging.info("Data found")
    logging.info("Starting sentiment analysis")

    if not news_data:
        logging.warning("Data not found")
        return
    
    df = pd.DataFrame(news_data)
    df["Date"]=pd.to_datetime(df['Date'])
    filename = f"{company}.xlsx"
    logging.info("Saved as data frame")

    df.to_excel(filename ,index=False)
    logging.info("Saved to excel")

    return filename
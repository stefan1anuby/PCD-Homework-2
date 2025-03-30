from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from google.cloud import bigquery
from google.oauth2 import service_account
import re
from collections import Counter

app = FastAPI()
templates = Jinja2Templates(directory="templates")

#Load credentials from a JSON key file
credentials = service_account.Credentials.from_service_account_file(
    "service-account-key.json"
)

# Create BigQuery client using credentials
client = bigquery.Client(credentials=credentials, project=credentials.project_id)

BQ_CONNECTION_ID = "project-id"

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    
    # 1. Top 5 users with most labeled messages
    top_users_query = f"""SELECT * FROM EXTERNAL_QUERY('{BQ_CONNECTION_ID}',"SELECT author, COUNT(*) AS message_count FROM messages WHERE label = true GROUP BY author ORDER BY message_count DESC LIMIT 5")"""
    top_users_result = client.query(top_users_query).result()
    top_users = [{"author": row["author"], "count": row["message_count"]} for row in top_users_result]

    # 2. Number of messages over time (per day)
    timeline_query = f""" SELECT * FROM EXTERNAL_QUERY('{BQ_CONNECTION_ID}', "SELECT DATE(created_at) as date, COUNT(*) as count FROM messages GROUP BY date ORDER BY date")"""

    timeline_result = client.query(timeline_query).result()
    timeline_data = [{"date": row["date"].strftime("%Y-%m-%d"), "count": row["count"]} for row in timeline_result]

    # 3. Most frequent words in all messages
    messages_query = f""" SELECT * FROM EXTERNAL_QUERY('{BQ_CONNECTION_ID}', "SELECT message FROM messages" ) """

    messages_result = client.query(messages_query).result()
    all_text = " ".join([row["message"] for row in messages_result])
    words = re.findall(r"\b\w+\b", all_text.lower())
    common_words = Counter(words).most_common(10)

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "top_users": top_users,
        "timeline": timeline_data,
        "common_words": common_words
    })

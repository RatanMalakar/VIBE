from flask import Flask , jsonify ,render_template
import pandas as pd
import subprocess
from scraper import start_research
from flask import request
import webbrowser

app=Flask(__name__)

@app.route("/")
def home():
    return open("index.html").read()

@app.route("/articles")
def get_articles():
    company=request.args.get("company")

    if not company:
        return{"error":"Please provide company name "}
    
    df=pd.read_excel(f"{company}.xlsx")
    return jsonify(df.to_dict(orient="records"))


@app.route("/refresh")
def refresh():
    company = request.args.get("company")

    if not company :
        return{"error":"Please provide company name"}
    
    file = start_research(company)

    if not file:
        return{"error":"FAiled to fetch data"}
    
    return {"Messege":f"Data updated for {company}"}


if __name__ == "__main__" :
    webbrowser.open("http://127.0.0.1:5000/")
    app.run(debug=True)
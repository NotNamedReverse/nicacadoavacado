from flask import Flask, redirect, render_template, url_for, request
from flask_sqlalchemy import SQLAlchemy
from threading import Thread
from openai import OpenAI
from thefuzz import process
import re

client = OpenAI(
    api_key="sk-qDTHAWc-lY8o7MTSJ5_PKdcXW1bk6b4k11xBt6mrbDT3BlbkFJ7cwrJia5FPA_kxHH2qCElq349lmCqNYKe4LYm2Yt4A"
)

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///data.db"  # Corrected URI
db = SQLAlchemy(app=app)

class Page(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(255), unique=True, nullable=False)
    content = db.Column(db.String(5000), unique=True, nullable=False)

    views = db.Column(db.Integer, default=0)

@app.route('/',  methods=['GET', 'POST'])
def home():
    if request.method == "POST":
        query = request.form.get("search")

        print("post")

        return redirect(url_for("searchPage", query=query))

    return render_template("home.html")

@app.route("/page/<pagename>")
def page(pagename):
    page = Page.query.filter_by(name=pagename).first()

    if page is not None:

        return render_template("page.html", name = page.name, content = page.content)

def createNewPage(name):
    print("Building page: " + name)

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role":"system", "content":"You make wikipedia/textbook pages. You have a maximum character count of 5000. You write based of online sources and write at around a middle/high school level. make sure you write your sources (with links) at the bottom. You can not use wikipedia. Only respond with the content of the page. Do not write a title. Make sure this all fits within the character limit."},
            {"role": "user", "content": f"Create a page about: {name}"},
        ]
    )

    content = response.choices[0].message.content

    if content is not None:
        newPage = Page(name=name.lower(), content=content,views=0)

        with app.app_context():
            db.session.add(newPage)
            db.session.commit()

            print("successfully built page: " + name)

@app.route('/search/<query>', methods=['GET', 'POST'])
def searchPage(query):
    if request.method == "GET":
        query = query.lower()

        print("Searching for: " + query)

        # Get all page names from the database
        all_pages = Page.query.all()
        all_page_names = [page.name for page in all_pages]

        # If no pages exist, return a "404"
        if not all_page_names:
            return render_template("searchResult.html", query=query, page="404")

        # Use fuzzy search to find the best match
        best_match, score = process.extractOne(query, all_page_names)

        print(f"Best match: {best_match} (Score: {score})")

        # Skip if no match is above the minimum threshold (e.g., 50)
        if score < 50:
            return render_template("searchResult.html", query=query, page="404")

        # Redirect if the match is good enough (e.g., score > 70)
        if score > 70:
            return redirect(url_for("page", pagename=best_match))

        # Render "page not found" or list the best match if it’s above a lower threshold (50-70 range)
        return render_template("searchResult.html", query=query, page=best_match)

    elif request.method == "POST":
        query = query.lower()

        print("Creating page: " + query)

        # Start thread to create a new page
        Thread(target=createNewPage, args=[query]).start()

        return render_template("loadingpage.html", pageName=query)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()

    app.run(port=25565)

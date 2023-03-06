# -*- coding: utf-8 -*-

import time
from flask import Flask, render_template, session, redirect, url_for, request
import hashlib

from data import VALID_VALGFAG, data, DEFAULT_SESSION, VALID_STUDY_FIELDS
import glob
from structures import User

app = Flask(__name__)
app.secret_key = b'_5#y2L"2\n\xec]/'
all_reviews = data["reviews_for_studieretninger"] + data["reviews_for_valgfag"]


@app.before_request
def pre_request():
    if not "session" in session:
        session["session"] = DEFAULT_SESSION


@app.context_processor
def app_context():
    return session["session"]


@app.route("/")
def home():
    glob.last_visited_page = "home"

    # the reviews on the homepage will always be filtered by the newest ones.
    all_reviews.sort(key=lambda x: x["posted"], reverse=True)

    return render_template(
        "homepage.html",
        reviews=all_reviews,
    )


@app.route("/register", methods=["POST", "GET"])
def register():
    if request.method == "POST":
        pwhash = hashlib.md5(request.form["password"].encode())

        # lowers all username and replaces spaces with _ for more "safe" usernames
        username = request.form["username"].lower().replace(" ", "_")
        display = request.form["display"]
        field_of_study = int(request.form["field_of_study"])
        optional_subject = int(request.form["subject"])
        grade = request.form["grade"].upper()

        u = User(
            password=pwhash.hexdigest(),
            username=username,
            display=display,
            id=len(data["users"]),
            grade=grade,
            field_of_study=VALID_STUDY_FIELDS[field_of_study],
            optional_subject=VALID_VALGFAG[optional_subject],
        )

        data["users"].append(u)
        session["session"] = u.__dict__ | {"logged_in": True}
        return redirect(url_for("home"))

    glob.last_visited_page = "register"
    return render_template("register.html")


@app.route("/login", methods=["POST", "GET"])
def login():
    if request.method == "POST":
        hash = hashlib.md5(request.form["password"].encode())
        uname = request.form["username"]

        # sees if the typed username is in user data
        for u in data["users"]:
            if u.username == uname:
                user = u
                break
        else:
            error = "Dit brugernavn og kodeord passer ikke."
            return render_template("login.html", error=error)

        # sees if the typed username matches the password hash
        if user.get_password() != hash.hexdigest():
            error = "Dit brugernavn og kodeord passer ikke."
            return render_template("login.html", error=error)

        # combines user dictionary with the logged_in key
        # which is being used to determine whether or not
        # if a session is logged in.
        session["session"] = u.__dict__ | {"logged_in": True}
        return redirect(url_for("home"))

    glob.last_visited_page = "login"
    return render_template("login.html")


@app.post("/logout")
def logout():
    session["session"] = DEFAULT_SESSION

    return redirect(url_for("home"))


@app.get("/studieretninger")
def review_listing():
    glob.last_visited_page = "review_listing"

    # `reviews` is a list of all reviews which has a field_of_study key in it.
    return render_template(
        "studieretninger.html", reviews=[x for x in all_reviews if "field_of_study" in x]
    )


@app.get("/valgfag")
def review_valgfag_listing():
    glob.last_visited_page = "review_valgfag_listing"
    
    # `reviews` is a list of all reviews which has a subject key in it.
    return render_template("valgfag.html", reviews=[x for x in all_reviews if "subject" in x])


@app.get("/review/<id>")
def review(id: int):
    glob.last_visited_page = "review"

    # finds review based on review id
    for review in all_reviews:
        if review["id"] == int(id):
            return render_template("review.html", review=review)

    return redirect(url_for("home"))


@app.post("/delete/<id>")
def delete_review(id: int):
    if not session["session"]["logged_in"]:
        return redirect(url_for("reviews"))

    # loops through all reviews and if a review matches
    # the requested review but also matches the reviews
    # author id and the user session id, it's a match
    # and then removes it from all reviews
    for review in all_reviews:
        if review["id"] == int(id) and review["user"]["id"] == session["session"]["id"]:
            all_reviews.remove(r)
            break
    else:
        return redirect(url_for("reviews"))

    return redirect(url_for("reviews"))


@app.route("/edit/<id>", methods=["POST", "GET"])
def edit_review(id):
    if request.method == "POST":
        for review in all_reviews:
            if review["id"] == int(id):
                review["title"] = request.form["title"]
                review["content"] = request.form["content"]
                review["rating"] = float(request.form["rating"])
                break
            else:
                return redirect(url_for("reviews"))
    
        return redirect(url_for("reviews"))
    
    if not session["session"]["logged_in"]:
        return redirect(url_for("reviews"))

    glob.last_visited_page = "edit_review"

    # finds the requested review by review id
    for review in all_reviews:
        if review["id"] == int(id):
            return render_template("edit.html", review=review)
        
    return render_template(url_for("home"))


@app.get("/reviews")
def reviews():
    if not session["session"]["logged_in"]:
        return redirect(url_for("login"))
    
    glob.last_visited_page = "reviews"
    r = []

    # finds all of the session users reviews
    # based on all reviews user id and session user id.
    for review in all_reviews:
        if review["user"]["id"] == session["session"]["id"]:
            r.append(review)

    return render_template("reviews.html", reviews=r)


@app.route("/opret", methods=["POST", "GET"])
def create_review():
    if not session["session"]["logged_in"]:
        exit(1)

    if request.method == "POST":
        category = int(request.form["category"])
        path = ["reviews_for_studieretninger", VALID_STUDY_FIELDS]

        # if the category exceeds the length of valid field of studies
        # the category is something inside of valgfag, as the value of
        # request.form category on valgfag is plus'd with the length of
        # valid study fields for easy distinction.
        if category > len(VALID_STUDY_FIELDS):
            path = ["reviews_for_valgfag", VALID_VALGFAG]
            category -= len(VALID_STUDY_FIELDS)
        # otherwise if it exceeds that, the category doesn't exist.
        elif category > len(VALID_VALGFAG):
            print("category doesn't exist")
            return render_template("oprettelse.html")

        input = {
            "posted": int(time.time()),
            "user": session["session"],
            "id": (new_id := len(all_reviews) + 1), # counts all the reviews and adds it with 1 to get a new unique id.
            "title": request.form["title"],
            "content": request.form["content"],
            "hearts": [],
            "rating": float(request.form["rating"]),
            "comments": [],
        }

        if path[0] == "reviews_for_studieretninger":
            input |= {"field_of_study": path[1][category]}
        else:
            input |= {"subject": path[1][category]}

        all_reviews.append(input)
        all_reviews.sort(key=lambda x: x["posted"], reverse=True)

        return redirect(url_for("review", id=new_id))
    
    glob.last_visited_page = "opret"
    return render_template("oprettelse.html")


@app.post("/create_comment/<review_id>")
def create_comment(review_id: int):
    if not session["session"]["logged_in"]:
        exit(1)

    pos = 0
    # finds the review based no the requests argument `id`
    # and all of the reviews
    for review in all_reviews:
        if review["id"] == int(review_id):
            break
        pos += 1

    # if the review exceeds the length of all reviews
    # the review doesn't exist.
    if len(all_reviews) - 1 < pos:
        print("whoopsies")
        return redirect(url_for("review", id=review_id))

    input = {
        "user": session["session"],
        "content": request.form["content"],
        "hearts": 0,
    }

    all_reviews[pos]["comments"].append(input)
    return redirect(url_for("review", id=review_id))


@app.post("/like/<id>")
def like_review(id: int):
    if not session["session"]["logged_in"]:
        return redirect(url_for(glob.last_visited_page, id=id))
                        
    for r in all_reviews:
        if r["id"] == int(id):
            # if user sessions id is already found in the
            # list of hearts of the review. then remove
            # the like from the review.
            if session["session"]["id"] in r["hearts"]:
                r["hearts"].remove(session["session"]["id"])
            else:
                r["hearts"].append(session["session"]["id"])

    return redirect(url_for(glob.last_visited_page, id=id))


if __name__ == "__main__":
    app.run(debug=True)

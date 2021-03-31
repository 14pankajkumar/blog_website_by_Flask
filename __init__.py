from flask import Flask, render_template, request, session, redirect
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail
from werkzeug.utils import secure_filename
import pymysql
import math
import json
import os


# -- OPEN JSON FILE ---
with open("config.json", "r") as f:
    params = json.load(f)["params"]


# --- APP CONFIG & DB CONNECTION ---
local_server = True
app = Flask(__name__)
app.secret_key = 'the-random-string'
app.config['UPLOAD_FOLDER'] = params['upload_location']

if (local_server):
    app.config['SQLALCHEMY_DATABASE_URI'] = params['local_uri']
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = params['prod_uri']

db = SQLAlchemy(app)


# ---- DB TABLE CONFIG ------
class Contacts(db.Model):
    sno = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(20), nullable=False)
    phone_num = db.Column(db.String(12), nullable=False)
    msg = db.Column(db.String(120), nullable=False)
    date = db.Column(db.String(12), nullable=False)

class Posts(db.Model):
    sno = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(80), nullable=False)
    tagline = db.Column(db.String(50), nullable=False)
    slug = db.Column(db.String(20), nullable=False)
    content = db.Column(db.String(120), nullable=False)
    date = db.Column(db.String(12), nullable=False)
    img_file = db.Column(db.String(12), nullable=False)


# ---EMAIL CONFIG---
app.config.update(
    MAIL_SERVER = 'smtp.gmail.com',
    MAIL_PORT = '465',
    MAIL_USE_SSL = True,
    MAIL_USERNAME = params['gmail_user'],
    MAIL_PASSWORD = params['gmail_password']
)
mail = Mail(app)


# ---- HOME PAGE -----
@app.route("/")
def home():
    """ PAGINATION """
    posts = Posts.query.filter_by().all()
    last = math.ceil(len(posts)/int(params['no_of_posts']))
    page = request.args.get('page')
    if (not str(page).isnumeric()):
        page = 1
    page = int(page)
    posts = posts[(page-1)*int(params['no_of_posts']):(page-1)*int(params['no_of_posts'])+int(params['no_of_posts'])]

    if (page==1):
        prev_page  = "#"
        next_page = "/?page=" + str(page + 1)
    elif (page==last):
        prev_page  = "/?page=" + str(page - 1)
        next_page = "#"
    else :
        prev_page  = "/?page=" + str(page - 1)
        next_page = "/?page=" + str(page + 1)


    return render_template("index.html", params=params, posts=posts, prev_page=prev_page, next_page=next_page)


# ----- ABOUT PAGE -------
@app.route("/about")
def about():
    return render_template("about.html", params=params)


# ----- CONTACT PAGE ---------
@app.route("/contact", methods=['GET', 'POST'])
def contact():
    if (request.method=='POST'):
        """
        Add entry to database
        """
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        message = request.form.get('msg')

        entry = Contacts(name=name, phone_num=phone, msg=message, email=email, date=datetime.now())
        db.session.add(entry)
        db.session.commit()

        # ---- SENDING EMAILS -----
        mail.send_message(
            'New message from '+name,
            sender = email,
            body = phone +"\n" + email + "\n" + message ,
            recipients = [params['gmail_user']]
        )

    return render_template("contact.html", params=params)


# ------- POST PAGE / FETCHING POST FROM DB ---------
@app.route("/post/<string:post_slug>",methods=['GET'])
def post_route(post_slug):
    post = Posts.query.filter_by(slug=post_slug).first()

    return render_template("post.html", params=params, post=post)


# ------ LOGIN & DASHBORD PAGE -------------
@app.route("/dashboard", methods=['GET', 'POST'])
def login():
    if ('user' in session and session['user'] == params['admin_user']):
        posts = Posts.query.all()
        return render_template("dashboard.html", params=params, posts=posts)

    elif request.method == 'POST':
        # ---- REDIRECT TO ADMIN PANEL -----
        username = request.form.get('uname')
        userpass = request.form.get('pass')
        if (username == params['admin_user'] and userpass == params['admin_password'] ):
            # ----- SET THE SESSION VARIABLE ----
            session['user'] = username
            posts = Posts.query.all()
            return render_template("dashboard.html", params=params, posts=posts)
        else:
            return "Wrong username or password"

    return render_template("login.html", params=params)


# ----- LOGOUT -----------
@app.route("/logout")
def logout():
    session.pop('user')
    return redirect("/dashboard")


# ------ EDIT PAGE -----------
@app.route("/edit/<string:sno>", methods=['GET', 'POST'])
def edit(sno):
    if ('user' in session and session['user'] == params['admin_user']):

        if request.method == 'POST':
            title = request.form.get('title')
            tagline = request.form.get('tline')
            slug = request.form.get('slug')
            img_file = request.form.get('img_file')
            content = request.form.get('content')

            if sno == "0":
                post = Posts(title=title, tagline=tagline, slug=slug, img_file=img_file, content=content, date= datetime.now())
                db.session.add(post)
                db.session.commit()
            else:
                post = Posts.query.filter_by(sno=sno).first()
                post.title = title
                post.tagline = tagline
                post.slug = slug
                post.img_file = img_file
                post.content = content
                db.session.commit()
                return redirect("/edit/" + sno)
    else:
        return redirect("/dashboard")

    post = Posts.query.filter_by(sno=sno).first()            
    return render_template("edit.html", params=params, post=post, sno=sno)



# ----- DELETE POSTS ------------
@app.route("/delete/<string:sno>", methods=['GET', 'POST'])
def delete(sno):
    if ('user' in session and session['user'] == params['admin_user']):
        post = Posts.query.filter_by(sno=sno).first()
        db.session.delete(post)
        db.session.commit()
        return redirect("/dashboard")
    
    else:
        return redirect("/dashboard")


# ------- UPLOAD A FILE ----------------
@app.route("/uploader", methods=['GET', 'POST'])
def uploader():
    if ('user' in session and session['user'] == params['admin_user']):

        if request.method == 'POST':
            f = request.files['file1']
            f.save(os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(f.filename)))
            return "Uploaded Successfully"
    else:
        return redirect("/dashboard")

if __name__ == "__main__":
    app.run(debug=True)
import re
from time import time
from datetime import datetime

import sqlalchemy
from flask import Flask, render_template, abort, url_for, redirect, flash, request
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from flask_bcrypt import Bcrypt
from flask_fontawesome import FontAwesome
from flask_login import LoginManager
from flask_login import UserMixin
from flask_login import login_user, logout_user, current_user
from flask_migrate import Migrate, MigrateCommand
from flask_script import Manager
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import scoped_session
from wtforms.validators import InputRequired, Length
from forms import RegistrationForm, LoginForm

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = "mysql://root@localhost/flaskblog"
app.config['SECRET_KEY'] = "qwertyuuioashdkfnvnhkdjfhfjk"
#SQLALCHEMY_TRACK_MODIFICATIONS = False
fa = FontAwesome(app)
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

migrate = Migrate(app, db)
manager = Manager(app)

manager.add_command('db', MigrateCommand)

login_manager = LoginManager(app)
admin = Admin(app)


@login_manager.user_loader
def load_user(id):
    return Users.query.get(int(id))


posts_tags = db.Table('posts_tags',
                      db.Column('post_id', db.Integer,
                                db.ForeignKey('post.id')),
                      db.Column('tag_id', db.Integer,
                                db.ForeignKey('tag.id')))


def slugify(s):
    pattern = r'[^\w+]'
    return re.sub(pattern, '-', S)


class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255))
    subtitle = db.Column(db.String(255))
    content = db.Column(db.Text)
    author = db.Column(db.String(255))
    date_posted = db.Column(db.DateTime)
    slug = db.Column(db.String(255), unique=True)
    comments = db.relationship('Comments', backref=db.backref('comments.id'), lazy=True)
    tags = db.relationship('Tag', secondary=posts_tags, backref=db.backref('posts.id'), lazy='dynamic')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.generate_slug()

    def generate_slug(self):
        if self.title:
            self.slug = slugify(self.title)
        else:
            self.slug = str(int(time()))

    def __repr__(self):
        return f'<Post id: {self.id}, title: {self.title}>'


class Tag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(140))
    slug = db.Column(db.String(140), unique=True)
    user_id = db.Column(db.Integer, unique=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.slug = self.title

    def __repr__(self):
        return f'<Tag id: {self.id}, title: {self.title}>'


class Comments(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    firstname = db.Column(db.String(50), unique=False)
    email = db.Column(db.String(50), unique=False)
    comment = db.Column(db.Text, nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    pub_date = db.Column(db.DateTime)

    def __repr__(self):
        return f"Comment('{self.id}', '{self.pub_date}')"


class Users(db.Model, UserMixin):
    id = db.Column(db.Integer , primary_key=True)
    firstname = db.Column(db.String(255))
    lastname = db.Column(db.String(255))
    email = db.Column(db.String(255), nullable=False)
    password = db.Column(db.String(255))
    author = db.relationship('Comments', backref=db.backref('author', lazy=True))


admin.add_view(ModelView(Post, db.session))


@app.route("/", methods=['POST', 'GET'])
def homepage():
    page = request.args.get('page', 1, type =int)
    if request.method == 'POST' and 'tag' in request.form:
       tag = request.form["tag"]
       search = "%{}%".format(tag)
       posts = Post.query.filter(Post.title.like(search)).paginate(per_page=page, error_out=False)
       return render_template('index.html', posts=posts, tag=tag)
    posts = Post.query.paginate(page=page, per_page=4)
    return render_template("index.html", posts=posts)


@app.route("/login", methods=['POST', 'GET'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = Users.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user)
            return redirect(url_for('homepage'))
        flash('Wrong credentials', 'danger')
    return render_template('login.html', form=form)


@app.route("/register", methods=['POST', 'GET'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_token = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        users = Users(firstname=form.firstname.data, lastname=form.lastname.data, email=form.email.data,
                      password=hashed_token)
        db.session.add(users)
        db.session.commit()
        flash(f' Account {form.email.data} Created !', 'success')
        return redirect(url_for('homepage'))
    return render_template('register.html', form=form)


@app.route("/post/comments", methods=['POST', 'GET'])
def comment():
    try: 
        com = Comments.query.all()
        return render_template('comments.html', com=com)
    except sqlalchemy.orm.exc.NoResultFound:
        abort(404)


@app.route("/post/<string:slug>", methods=['POST', 'GET'])
def post(slug):
    try:
        post = Post.query.filter_by(slug=slug).one()

        if request.method == 'POST':
            firstname = request.form.get('firstname')
            email = request.form.get('email')
            comment = request.form.get('comment')
            comments = Comments(firstname=firstname, email=email, comment=comment, post_id=post.id, user_id=current_user.id, pub_date=datetime.now())
            db.session.add(comments)
            db.session.commit()
            flash('Comment has been submitted', 'success')

            return redirect(url_for('posts'))

        return render_template("individual_post.html", post=post)
    except sqlalchemy.orm.exc.NoResultFound:
        abort(404)


@app.route('/logout')
def logout():
    logout_user()
    flash("You have been logged out Successifuly!", "info")
    return redirect(url_for('homepage'))


if __name__ == "__main__":
    app.run(debug=True)

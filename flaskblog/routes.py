import os
import secrets
from PIL import Image
from flask import render_template, url_for, flash, redirect, request, abort
from flaskblog import app, db, bcrypt
from flaskblog.forms import RegistrationForm, LoginForm, UpdateAccountForm, PostForm
from flaskblog.models import User, Post
from flask_login import login_user, current_user, logout_user, login_required
import time
from apscheduler.triggers.cron import CronTrigger

from flask import session
import random
from apscheduler.schedulers.background import BackgroundScheduler
from flaskblog import app, db  # Import the app and db objects



@app.route("/")
@app.route("/home")
def home():
    # Get all users who have submitted the quiz
    submitted_users = [user for user in User.query.all() if user.quiz_submitted]

    # Sort the submitted users based on score and time_taken
    sorted_users = sorted(submitted_users, key=lambda user: (-user.score, user.time_taken))

    # Get the top 10 users
    top_10_users = sorted_users[:10]

    users = User.query.all()

    # Sort users by total_score and time_taken
    sorted_users = sorted(users, key=lambda user: (-user.total_score, user.time_taken))
    # Render the template, passing the top 10 users to the template
    return render_template('home.html', top_10_users=top_10_users,sorted_users=sorted_users[:10])




@app.route("/about")
def about():
    return render_template('about.html', title='About')


@app.route("/register", methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(username=form.username.data, email=form.email.data, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash('Your account has been created! You are now able to log in', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)


@app.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('home'))
        else:
            flash('Login Unsuccessful. Please check email and password', 'danger')
    return render_template('login.html', title='Login', form=form)


@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('home'))


def save_picture(form_picture):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(app.root_path, 'static/profile_pics', picture_fn)

    output_size = (125, 125)
    i = Image.open(form_picture)
    i.thumbnail(output_size)
    i.save(picture_path)

    return picture_fn


@app.route("/account", methods=['GET', 'POST'])
@login_required
def account():
    form = UpdateAccountForm()
    if form.validate_on_submit():
        if form.picture.data:
            picture_file = save_picture(form.picture.data)
            current_user.image_file = picture_file
        current_user.username = form.username.data
        current_user.email = form.email.data
        db.session.commit()
        flash('Your account has been updated!', 'success')
        return redirect(url_for('account'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
    image_file = url_for('static', filename='profile_pics/' + current_user.image_file)

    # Get all users who have submitted the quiz
    submitted_users = [user for user in User.query.all() if user.quiz_submitted]

    # Sort the submitted users based on score and time_taken
    sorted_users = sorted(submitted_users, key=lambda user: (-user.score, user.time_taken))

    # Find the current user's rank
    current_user_rank = None
    for i, user in enumerate(sorted_users):
        if user == current_user:
            current_user_rank = i + 1
            break

    return render_template('account.html', title='Account',
                           image_file=image_file, form=form,
                           sorted_users=sorted_users,
                           current_user=current_user,
                           current_user_rank=current_user_rank)

@app.route("/post/new", methods=['GET', 'POST'])
@login_required
def new_post():
    form = PostForm()
    if form.validate_on_submit():
        post = Post(title=form.title.data, content=form.content.data, author=current_user)
        db.session.add(post)
        db.session.commit()
        flash('Your post has been created!', 'success')
        return redirect(url_for('home'))
    return render_template('create_post.html', title='New Post',
                           form=form, legend='New Post')


@app.route("/post/<int:post_id>")
def post(post_id):
    post = Post.query.get_or_404(post_id)
    return render_template('post.html', title=post.title, post=post)


@app.route("/post/<int:post_id>/update", methods=['GET', 'POST'])
@login_required
def update_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.author != current_user:
        abort(403)
    form = PostForm()
    if form.validate_on_submit():
        post.title = form.title.data
        post.content = form.content.data
        db.session.commit()
        flash('Your post has been updated!', 'success')
        return redirect(url_for('post', post_id=post.id))
    elif request.method == 'GET':
        form.title.data = post.title
        form.content.data = post.content
    return render_template('create_post.html', title='Update Post',
                           form=form, legend='Update Post')


@app.route("/post/<int:post_id>/delete", methods=['POST'])
@login_required
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.author != current_user:
        abort(403)
    db.session.delete(post)
    db.session.commit()
    flash('Your post has been deleted!', 'success')
    return redirect(url_for('home'))

questions_answers = [
    {'question': 'The capital of India is New Delhi.', 'answer': 'True'},
    {'question': 'The official language of Karnataka is Kannada.', 'answer': 'True'},
    {'question': 'Taj Mahal is located in Mumbai.', 'answer': 'False'},
    {'question': 'The national animal of India is the Tiger.', 'answer': 'True'},
    {'question': 'Karnataka is known as the Garden City of India.', 'answer': 'False'},
    {'question': 'The Indian Ocean lies to the east of India.', 'answer': 'False'},
    {'question': 'Bangalore is the capital city of Karnataka.', 'answer': 'True'},
    {'question': 'The national flower of India is the Lotus.', 'answer': 'True'},
    {'question': 'Karnataka shares its border with Maharashtra.', 'answer': 'True'},
    {'question': 'The Red Fort is located in Mumbai.', 'answer': 'False'},
    {'question': 'The national bird of India is the Peacock.', 'answer': 'True'},
    {'question': 'Karnataka is the largest state in India by area.', 'answer': 'False'},
    {'question': 'The Ganges River originates in Karnataka.', 'answer': 'False'},
    {'question': 'The Indian flag has three horizontal stripes.', 'answer': 'True'},
    {'question': 'Karnataka has a coastline along the Arabian Sea.', 'answer': 'False'},
    {'question': 'The Qutub Minar is located in Bangalore.', 'answer': 'False'},
    {'question': 'Hindi is the most widely spoken language in Karnataka.', 'answer': 'False'},
    {'question': 'The national emblem of India is the Ashoka Chakra.', 'answer': 'False'},
    {'question': 'Mysore Palace is located in Mysore, Karnataka.', 'answer': 'True'},
    {'question': 'The Indian rupee is the currency of India.', 'answer': 'True'},
    {'question': 'The Western Ghats run through Karnataka.', 'answer': 'True'},
    {'question': 'The Indian national anthem is "Jana Gana Mana".', 'answer': 'True'},
    {'question': 'The Vidhana Soudha is the legislative assembly building of Karnataka.', 'answer': 'True'},
    {'question': 'The Indian flag has a blue wheel in the center.', 'answer': 'True'},
    {'question': 'Karnataka is known for its silk production.', 'answer': 'True'},
    {'question': 'Mahatma Gandhi was born in Karnataka.', 'answer': 'False'},
    {'question': 'The India Gate is located in Bangalore.', 'answer': 'False'},
    {'question': 'Karnataka is home to the Bandipur National Park.', 'answer': 'True'},
    {'question': 'The official sport of India is cricket.', 'answer': 'False'},
    {'question': 'Karnataka is known for its IT industry, particularly in Bangalore.', 'answer': 'True'},
    {'question': 'The Indian parliament is called the Lok Sabha.', 'answer': 'False'},
    {'question': 'The Mysore Dasara festival is celebrated in Karnataka.', 'answer': 'True'},
    {'question': 'The highest mountain peak in Karnataka is Tadiandamol.', 'answer': 'True'},
    {'question': 'The national tree of India is the Banyan tree.', 'answer': 'True'},
    {'question': 'Karnataka has the highest literacy rate among Indian states.', 'answer': 'False'},
    {'question': 'The India-Pakistan border is called the Radcliffe Line.', 'answer': 'False'},
    {'question': 'The Karnataka High Court is located in Mysore.', 'answer': 'False'},
    {'question': 'The Lotus Temple is located in Bangalore.', 'answer': 'False'},
    {'question': 'Karnataka is known for its coffee production.', 'answer': 'True'},
    {'question': 'The Indian national motto is "Satyameva Jayate".', 'answer': 'True'},
    {'question': 'Karnataka was formed on November 1st, 1956.', 'answer': 'True'},
    {'question': 'The Rashtrapati Bhavan is the official residence of the Prime Minister of India.', 'answer': 'False'},
    {'question': 'Karnataka has the highest number of tiger reserves in India.', 'answer': 'True'},
    {'question': 'The Indian national song is "Vande Mataram".', 'answer': 'True'},
    {'question': 'The state bird of Karnataka is the Indian Roller.', 'answer': 'True'},
    {'question': 'The Indian national currency symbol is ₹.', 'answer': 'True'},
    {'question': 'Karnataka has the highest number of UNESCO World Heritage Sites in India.', 'answer': 'True'},
    {'question': 'The national aquatic animal of India is the Ganges River Dolphin.', 'answer': 'True'}
]

scheduler = BackgroundScheduler()
scheduler.start()

def update_questions():
    global questions_answers  # Ensure questions_answers is defined and available here
    random.shuffle(questions_answers)
    with app.app_context():
        print("its wroking")
        users = User.query.all()
        for user in users:
            user.score = 0
            user.quiz_submitted = False
            user.time_taken = '00:00'
            db.session.commit()

# Schedule the update_questions function to run every 5 minutes
scheduler.add_job(update_questions, CronTrigger(hour=0, minute=0))

@app.route("/quiz", methods=['GET', 'POST'])
@login_required
def quiz():
    if current_user.quiz_submitted:
        flash('You have already submitted the quiz.', 'info')
        return redirect(url_for('account'))

    # Select 10 random questions for the quiz
    selected_questions=questions_answers[:10]
    if request.method == 'POST':
        # Only execute this block if the quiz hasn't been submitted yet
        score = 0
        for i, qa in enumerate(selected_questions, start=1):
            user_answer = request.form.get('question-' + str(i))
            if user_answer == qa['answer']:
                score += 1
        end_time = time.time()
        start_time = session.pop('quiz_start_time', None)  # Retrieve start time from session
        if start_time is None:
            flash('Error: Start time not found.', 'danger')
            return redirect(url_for('account'))
        elapsed_time_seconds = end_time - start_time
        elapsed_minutes = int(elapsed_time_seconds // 60)
        elapsed_seconds = int(elapsed_time_seconds % 60)
        elapsed_time_formatted = f"{elapsed_minutes}:{elapsed_seconds:02d}"

        current_user.time_taken = elapsed_time_formatted
        current_user.elapsed_time = elapsed_time_formatted
        current_user.score = score
        current_user.total_score=current_user.total_score+score

        elapsed_minutes, elapsed_seconds = map(int, elapsed_time_formatted.split(':'))

        # Split the current_user_total_time into hours, minutes, and seconds
        total_hours, total_minutes, total_seconds = map(int, current_user.total_time.split(':'))

        # Add the elapsed time to the total time
        total_seconds += elapsed_seconds
        total_minutes += elapsed_minutes

        # Adjust the hours and minutes if seconds exceed 59
        total_minutes += total_seconds // 60
        total_seconds %= 60
        total_hours += total_minutes // 60
        total_minutes %= 60

        # Format the result
        new_total_time_str = f"{total_hours:02d}:{total_minutes:02d}:{total_seconds:02d}"
        current_user.total_time = new_total_time_str

        current_user.quiz_submitted = True
        db.session.commit()
        flash('Quiz submitted successfully!', 'success')
        return redirect(url_for('account'))
    elif request.method == 'GET':
        # Set start time in session when quiz page is loaded
        session['quiz_start_time'] = time.time()
        return render_template('quiz.html', questions_answers=selected_questions)

@app.route("/blog")
def blog():
    posts = Post.query.all()
    return render_template('blog.html', posts=posts)
from flask import Flask, request, redirect, url_for, render_template, send_from_directory, session, flash
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import os
import cv2 as cv

app = Flask(__name__)
app.secret_key = 'supersecretkey'

# Configure database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

UPLOAD_FOLDER = 'static/uploads/'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'mp4', 'avi'}
MAX_IMAGE_SIZE = (800, 800)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def resize_image(image, max_size):
    h, w = image.shape[:2]
    if h > max_size[0] or w > max_size[1]:
        scaling_factor = min(max_size[0] / h, max_size[1] / w)
        new_size = (int(w * scaling_factor), int(h * scaling_factor))
        resized_image = cv.resize(image, new_size, interpolation=cv.INTER_AREA)
        return resized_image
    return image

def process_video(input_path, output_path, process_function):
    cap = cv.VideoCapture(input_path)
    fourcc = cv.VideoWriter_fourcc(*'mp4v')
    out = None

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        processed_frame = process_function(frame)
        if out is None:
            out = cv.VideoWriter(output_path, fourcc, 20.0, (processed_frame.shape[1], processed_frame.shape[0]))
        out.write(processed_frame)

    cap.release()
    out.release()

def convert_frame_to_grayscale(frame):
    return cv.cvtColor(frame, cv.COLOR_BGR2GRAY)

def blur_faces_in_frame(frame):
    face_cascade = cv.CascadeClassifier(cv.data.haarcascades + 'haarcascade_frontalface_default.xml')
    gray = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, 1.1, 4)
    for (x, y, w, h) in faces:
        face = frame[y:y+h, x:x+w]
        face = cv.GaussianBlur(face, (99, 99), 30)
        frame[y:y+h, x:x+w] = face
    return frame


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user:
            flash('Username already exists. Please choose a different one.', 'danger')
        else:
            hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
            new_user = User(username=username, password=hashed_password)
            db.session.add(new_user)
            db.session.commit()
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('upload_file'))
        else:
            flash('Login Unsuccessful. Please check username and password, or register first.', 'danger')
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/', methods=['GET', 'POST'])
@login_required
def upload_file():
    if request.method == 'POST':
        if 'file' not in request.files:
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            session['original_file'] = filename
            session['upload_success'] = True
            return redirect(url_for('edit_file', filename=filename))
    else:
        session.pop('upload_success', None)
    return render_template('index.html')

@app.route('/edit/<filename>', methods=['GET', 'POST'])
@login_required
def edit_file(filename):
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    edited_filename = None

    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'exit':
            return redirect(url_for('upload_file'))
        elif action == 'undo':
            original_filename = session.get('original_file')
            if original_filename:
                return redirect(url_for('edit_file', filename=original_filename))
        elif action == 'convert':
            if filename.endswith(('.jpg', '.jpeg', '.png')):
                image = cv.imread(file_path)
                resized_image = resize_image(image, MAX_IMAGE_SIZE)
                edited_image = cv.cvtColor(resized_image, cv.COLOR_BGR2GRAY)
                edited_filename = 'edited_' + filename
                cv.imwrite(os.path.join(app.config['UPLOAD_FOLDER'], edited_filename), edited_image)
            elif filename.endswith(('.mp4', '.avi')):
                edited_filename = 'edited_' + filename
                process_video(file_path, os.path.join(app.config['UPLOAD_FOLDER'], edited_filename), convert_frame_to_grayscale)
        elif action == 'blur_faces':
            if filename.endswith(('.jpg', '.jpeg', '.png')):
                image = cv.imread(file_path)
                resized_image = resize_image(image, MAX_IMAGE_SIZE)
                edited_image = blur_faces_in_frame(resized_image)
                edited_filename = 'blurred_' + filename
                cv.imwrite(os.path.join(app.config['UPLOAD_FOLDER'], edited_filename), edited_image)
            elif filename.endswith(('.mp4', '.avi')):
                edited_filename = 'blurred_' + filename
                process_video(file_path, os.path.join(app.config['UPLOAD_FOLDER'], edited_filename), blur_faces_in_frame)

        if edited_filename:
            return redirect(url_for('edit_file', filename=edited_filename))

    return render_template('edit.html', filename=filename)

@app.route('/uploads/<filename>')
@login_required
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)

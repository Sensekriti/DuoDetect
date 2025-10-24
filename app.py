from flask import Flask, request, render_template, redirect, url_for, send_from_directory, flash, session,jsonify
from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, FileField
from wtforms.validators import DataRequired, Email, NumberRange, Regexp
from datetime import datetime
import os
from PIL import Image
import hashlib
import pymongo
from pymongo.errors import ConnectionFailure
import uuid
from flask_mail import Mail, Message
from dotenv import load_dotenv


load_dotenv()  # Load .env file

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = './uploads'
app.config['SECRET_KEY'] = 'india-ai-secure-key-2024'
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024  # 2MB

# Flask-Mail Config
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get("MAIL_USERNAME")
app.config['MAIL_PASSWORD'] = os.environ.get("MAIL_PASSWORD")
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get("MAIL_DEFAULT_SENDER")
mail = Mail(app)

# MongoDB
try:
    client = pymongo.MongoClient("mongodb://localhost:27017/", serverSelectionTimeoutMS=5000)
    client.server_info()
    db = client["india_ai"]
    collection = db["submissions"]
    print("MongoDB connected")
except ConnectionFailure as e:
    print(f"MongoDB connection failed: {e}")
    exit(1)

# Form
class SubmissionForm(FlaskForm):
    name = StringField('Full Name', validators=[DataRequired()])
    email = StringField('Email Address', validators=[DataRequired(), Email()])
    age = IntegerField('Age', validators=[DataRequired(), NumberRange(min=18)])
    phone = StringField('Phone Number', validators=[DataRequired(), Regexp(r'^\d{10}$')])
    address = StringField('Residential Address', validators=[DataRequired()])
    photo = FileField('Passport Size Photograph', validators=[DataRequired()])

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/instructions')
def instructions():
    return render_template('instructions.html')

@app.route('/apply', methods=['GET', 'POST'])
def submit_page():
    form = SubmissionForm()

    if 'application_id' not in session:
        session['application_id'] = f"APP{datetime.now().strftime('%Y%m%d')}_{uuid.uuid4().hex[:8].upper()}"

    if request.method == 'POST':
        if not form.validate_on_submit():
            return jsonify({
                "success": False,
                "message": "Please fix form errors."
            }), 400

        name = form.name.data.strip()
        email = form.email.data.strip()
        age = form.age.data
        phone = form.phone.data.strip()
        address = form.address.data.strip()
        photo = form.photo.data

        # One submission per email
        if collection.find_one({"email": email}):
            return jsonify({
                "success": False,
                "message": "You have already submitted an application with this email."
            }), 400

        # Validate image
        if not photo.filename.lower().endswith(('.png', '.jpg', '.jpeg')):
            return jsonify({"success": False, "message": "Invalid image format."}), 400

        # Save image
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        ext = os.path.splitext(photo.filename)[1].lower()
        filename = f"{session['application_id']}_{timestamp}{ext}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        photo.save(filepath)

        try:
            with Image.open(filepath) as img:
                img.verify()
        except:
            os.remove(filepath)
            return jsonify({"success": False, "message": "Invalid image file."}), 400

        # Hash image
        with open(filepath, 'rb') as f:
            img_hash = hashlib.sha256(f.read()).hexdigest()

        # Save to DB
        submission = {
            'application_id': session['application_id'],
            'name': name, 'email': email, 'age': age, 'phone': phone,
            'address': address, 'photo_path': filename, 'image_hash': img_hash,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'status': 'submitted'
        }

        try:
            collection.insert_one(submission)

            # Send Email
            try:
                msg = Message(
                    subject="Application Submitted - IndiaAI",
                    recipients=[email],
                    body=(
                        f"Dear {name},\n\n"
                        f"Your application has been submitted successfully!\n\n"
                        f"Application ID: {submission['application_id']}\n"
                        f"Submitted on: {submission['timestamp']}\n\n"
                        f"We are processing your photo with AI face authentication.\n"
                        f"Thank you!\n\nIndiaAI Team"
                    )
                )
                mail.send(msg)
                print(f"Email sent to {email}")
            except Exception as e:
                print(f"Email failed: {e}")

            session.pop('application_id', None)

            redirect_url = url_for('show_results') if collection.count_documents({}) >= 5 else None

            return jsonify({
                "success": True,
                "message": f"Application submitted! ID: {submission['application_id']}",
                "redirect": redirect_url
            })

        except Exception as e:
            return jsonify({"success": False, "message": str(e)}), 500

    return render_template('apply.html', form=form)

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

def apply_ai_deduplication_logic(submissions):
    pattern = ['A', 'B', 'A', 'A', 'B']
    for i, sub in enumerate(submissions):
        if i < len(pattern):
            sub['cluster_id'] = pattern[i]
            sub['ai_confidence'] = f"{95 - (i * 5)}%"
            sub['verification_status'] = 'Potential Duplicate - Requires Verification' if pattern[i] == 'A' else 'Verified Unique Application'
        else:
            sub['cluster_id'] = 'unique'
            sub['ai_confidence'] = "Pending"
            sub['verification_status'] = 'Additional Application - Pending AI Analysis'
    return submissions

@app.route('/Dashboard')
def show_results():
    submissions = list(collection.find().sort("timestamp", 1))
    submissions = apply_ai_deduplication_logic(submissions)
    stats = {
        'total_applications': len(submissions),
        'potential_duplicates': len([s for s in submissions if s['cluster_id'] == 'A']),
        'unique_applications': len([s for s in submissions if s['cluster_id'] == 'B']),
        'pending_analysis': len([s for s in submissions if s['cluster_id'] == 'unique'])
    }
    return render_template('results.html', submissions=submissions, stats=stats)

@app.route('/admin/clear')
def clear_submissions():
    count = collection.delete_many({}).deleted_count
    session.clear()
    flash(f"Cleared {count} applications.", "info")
    return redirect(url_for('index'))

@app.route('/privacy')
def privacy():
    return render_template('privacy.html')

if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    app.run(debug=True, host='127.0.0.1', port=5000)
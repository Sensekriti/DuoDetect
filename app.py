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
import time
from flask_mail import Mail, Message
from dotenv import load_dotenv
from deepface import DeepFace
from deepface.modules import modeling


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

        print("Running AI face matching...")
        start = time.time()
        status, best_match_id, best_confidence, top_matches = run_face_matching(
        filepath, app.config['UPLOAD_FOLDER'], filename
        )
        ai_time = round(time.time() - start, 2)

        # Save to DB
        submission = {
            'application_id': session['application_id'],
            'name': name, 'email': email, 'age': age, 'phone': phone,
            'address': address, 'photo_path': filename, 'image_hash': img_hash,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'status': 'processed',
            'ai_result': {
                'status': status,
                'best_match_id': best_match_id,
                'best_confidence': best_confidence,
                'ai_time_seconds': ai_time,
                'top_matches': top_matches
            }
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

# --- REAL FACE MATCHING WITH TOP 5 ---
def run_face_matching(probe_path: str, gallery_folder: str, exclude_filename: str):
    try:
        results = DeepFace.find(
            img_path=probe_path,
            db_path=gallery_folder,
            model_name="ArcFace",
            distance_metric="cosine",
            enforce_detection=False,
            detector_backend="opencv",
            silent=True
        )

        if not results or (isinstance(results, list) and len(results) == 0):
            return "Unique", None, None, []

        df = results[0] if isinstance(results, list) else results
        if df.empty:
            return "Unique", None, None, []

        # EXCLUDE SELF
        df = df[df['identity'].apply(lambda x: os.path.basename(x) != exclude_filename)]
        if df.empty:
            return "Unique", None, None, []

        df_sorted = df.sort_values("distance").head(5)
        threshold = df_sorted.iloc[0].get("threshold", 0.40)
        best_distance = df_sorted.iloc[0]["distance"]
        is_duplicate = best_distance < threshold
        status = "Duplicate" if is_duplicate else "Unique"

        top_matches = []
        for _, row in df_sorted.iterrows():
            match_filename = os.path.basename(row["identity"])
            match_id = match_filename.split('_')[0]
            confidence = round((1 - row["distance"]) * 100, 2)
            top_matches.append({
                "application_id": match_id,
                "photo_path": match_filename,
                "distance": round(row["distance"], 4),
                "confidence": confidence
            })

        best_match_id = top_matches[0]["application_id"] if top_matches else None
        best_confidence = top_matches[0]["confidence"] if top_matches else None

        return status, best_match_id, best_confidence, top_matches

    except Exception as e:
        print(f"DeepFace error: {e}")
        return "Error", None, None, []

    except Exception as e:
        print(f"DeepFace error: {e}")
        # Clean up on error
        if os.path.exists(temp_gallery):
            for f in os.listdir(temp_gallery):
                os.remove(os.path.join(temp_gallery, f))
            os.rmdir(temp_gallery)
        return "Error", None, None, [f"AI error: {str(e)}"]

@app.route('/Dashboard')
def show_results():
    submissions = list(collection.find().sort("timestamp", 1))
    stats = {
        'total': len(submissions),
        'duplicates': len([s for s in submissions if s.get('ai_result', {}).get('status') == 'Duplicate']),
        'unique': len([s for s in submissions if s.get('ai_result', {}).get('status') == 'Unique']),
        'pending': len([s for s in submissions if s.get('status') != 'processed'])
    }
    print(submissions)
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
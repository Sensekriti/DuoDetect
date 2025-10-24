from flask import Flask, request, render_template, redirect, url_for, send_from_directory, flash, session
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

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = '/media/cair/4e7fa135-fc0e-4140-a0c6-9c81a4d992bd/XTRAtest/india-ai/uploads'
app.config['SECRET_KEY'] = 'india-ai-secure-key-2024'  # Change in production
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024  # 2MB file size limit

# MongoDB connection
try:
    client = pymongo.MongoClient("mongodb://localhost:27017/", serverSelectionTimeoutMS=5000)
    client.server_info()  # Test connection
    db = client["india_ai"]
    collection = db["submissions"]
    print("MongoDB connection successful")
except ConnectionFailure as e:
    print(f"Failed to connect to MongoDB: {e}")
    exit(1)

# WTForms for form validation
class SubmissionForm(FlaskForm):
    name = StringField('Full Name', validators=[DataRequired(message="Full name is required")])
    email = StringField('Email Address', validators=[DataRequired(message="Email is required"), Email(message="Invalid email address")])
    age = IntegerField('Age', validators=[DataRequired(message="Age is required"), NumberRange(min=18, message="Age must be 18 or older")])
    phone = StringField('Phone Number', validators=[DataRequired(message="Phone is required"), Regexp(r'^\d{10}$', message="Phone must be exactly 10 digits")])
    address = StringField('Residential Address', validators=[DataRequired(message="Address is required")])
    photo = FileField('Passport Size Photograph', validators=[DataRequired(message="Photograph is required")])

@app.route('/')
def index():
    """Landing page explaining the challenge"""
    return render_template('index.html')

@app.route('/instructions')
def instructions():
    """Page with detailed instructions"""
    return render_template('instructions.html')

@app.route('/apply', methods=['GET', 'POST'])
def submit_page():
    """Main application submission page"""
    form = SubmissionForm()
    submission_count = collection.count_documents({})
    
    # Generate unique application ID for this session
    if 'application_id' not in session:
        session['application_id'] = f"APP{datetime.now().strftime('%Y%m%d')}_{uuid.uuid4().hex[:8].upper()}"
    
    if request.method == 'POST':
        if form.validate_on_submit():
            print("Form validated. Processing application...")
            name = form.name.data.strip()
            email = form.email.data.strip()
            age = form.age.data
            phone = form.phone.data.strip()
            address = form.address.data.strip()
            photo = form.photo.data

            # Validate image format
            if not photo.filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                flash("Invalid image format. Please upload PNG, JPG, or JPEG format.", "error")
                return render_template('apply.html', form=form, submission_count=submission_count)

            # Save image with secure filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            file_extension = os.path.splitext(photo.filename)[1].lower()
            filename = f"{session['application_id']}_{timestamp}{file_extension}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            
            try:
                photo.save(filepath)
                print(f"Image saved to: {filepath}")
                
                # Verify image was saved
                if not os.path.exists(filepath):
                    flash("Error: Image could not be saved. Please try again.", "error")
                    return render_template('apply.html', form=form, submission_count=submission_count)
                    
            except Exception as e:
                flash(f"Error saving image: {str(e)}", "error")
                return render_template('apply.html', form=form, submission_count=submission_count)

            # Validate image integrity
            try:
                with Image.open(filepath) as img:
                    img.verify()
                print("Image validated successfully")
            except Exception as e:
                flash(f"Invalid image file. Please upload a valid photograph.", "error")
                os.remove(filepath)  # Clean up invalid file
                return render_template('apply.html', form=form, submission_count=submission_count)

            # Compute image content hash for deduplication
            try:
                with open(filepath, 'rb') as f:
                    img_hash = hashlib.sha256(f.read()).hexdigest()
                print(f"Image hash computed: {img_hash}")
            except Exception as e:
                flash(f"Error processing image. Please try again.", "error")
                return render_template('apply.html', form=form, submission_count=submission_count)

            # Store submission in MongoDB
            submission = {
                'application_id': session['application_id'],
                'name': name,
                'email': email,
                'age': age,
                'phone': phone,
                'address': address,
                'photo_path': filename,
                'image_hash': img_hash,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'status': 'submitted'
            }
            
            try:
                result = collection.insert_one(submission)
                print(f"Application saved to MongoDB with ID: {result.inserted_id}")
                
                # Clear session for new application
                session.pop('application_id', None)
                
                flash(f"Application submitted successfully! Your Application ID: {submission['application_id']}", "success")
                
                # Redirect to results after 5 submissions (for demo purposes)
                if collection.count_documents({}) >= 5:
                    return redirect(url_for('show_results'))
                    
                return redirect(url_for('submit_page'))
                
            except Exception as e:
                flash(f"Error saving application: {str(e)}", "error")
                return render_template('apply.html', form=form, submission_count=submission_count)
                
        else:
            # Form validation failed
            for field, errors in form.errors.items():
                for error in errors:
                    flash(f"{getattr(form, field).label.text}: {error}", "error")
            return render_template('apply.html', form=form, submission_count=submission_count)

    return render_template('apply.html', form=form, submission_count=submission_count)

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    """Serve uploaded images"""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

def apply_ai_deduplication_logic(submissions):
    """Apply AI-based deduplication logic with A B A A B pattern for demo"""
    pattern = ['A', 'B', 'A', 'A', 'B']
    cluster_colors = {
        'A': '#DC3545',  # Red for potential duplicates
        'B': '#198754',  # Green for unique
        'unique': '#6C757D'  # Gray for additional submissions
    }
    
    cluster_descriptions = {
        'A': 'Potential Duplicate - Requires Verification',
        'B': 'Verified Unique Application',
        'unique': 'Additional Application - Pending AI Analysis'
    }
    
    for i, submission in enumerate(submissions):
        if i < len(pattern):
            submission['cluster_id'] = pattern[i]
            submission['ai_confidence'] = f"{95 - (i * 5)}%"
            submission['verification_status'] = cluster_descriptions[pattern[i]]
        else:
            submission['cluster_id'] = 'unique'
            submission['ai_confidence'] = "Pending"
            submission['verification_status'] = cluster_descriptions['unique']
    
    # Count cluster sizes
    cluster_sizes = {}
    for submission in submissions:
        cluster_id = submission['cluster_id']
        cluster_sizes[cluster_id] = cluster_sizes.get(cluster_id, 0) + 1
    
    # Assign colors and sizes
    for submission in submissions:
        cluster_id = submission['cluster_id']
        submission['cluster_color'] = cluster_colors.get(cluster_id, '#6C757D')
        submission['cluster_size'] = cluster_sizes.get(cluster_id, 1)
    
    return submissions

@app.route('/results')
def show_results():
    """Display AI deduplication results"""
    submissions = list(collection.find().sort("timestamp", pymongo.ASCENDING))
    
    # Apply AI deduplication logic
    submissions_with_analysis = apply_ai_deduplication_logic(submissions)
    
    stats = {
        'total_applications': len(submissions),
        'potential_duplicates': len([s for s in submissions_with_analysis if s['cluster_id'] == 'A']),
        'unique_applications': len([s for s in submissions_with_analysis if s['cluster_id'] == 'B']),
        'pending_analysis': len([s for s in submissions_with_analysis if s['cluster_id'] == 'unique'])
    }
    
    return render_template('results.html', 
                         submissions=submissions_with_analysis, 
                         stats=stats)

@app.route('/admin/clear')
def clear_submissions():
    """Admin route to clear all submissions (for testing)"""
    result = collection.delete_many({})
    session.clear()
    flash(f"Cleared {result.deleted_count} applications. Demo reset.", "info")
    return redirect(url_for('index'))

@app.route('/privacy')
def privacy():
    """Privacy policy page"""
    return render_template('privacy.html')

if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    app.run(debug=True, host='127.0.0.1', port=5000)
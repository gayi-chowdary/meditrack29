from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.utils import secure_filename
import boto3
import os
import uuid

# App setup
app = Flask(_name_)
app.secret_key = 'secret_key_here'
app.config['UPLOAD_FOLDER'] = 'uploads'

# AWS Config
REGION = 'us-east-1'
dynamodb = boto3.resource('dynamodb', region_name=REGION)
sns = boto3.client('sns', region_name=REGION)

SNS_TOPIC_ARN = 'arn:aws:sns:ap-south-1:YOUR_ACCOUNT_ID:YourTopicName'  # 🔁 Replace this

# DynamoDB Tables
users_table = dynamodb.Table('Users')
appointments_table = dynamodb.Table('Appointments')
reports_table = dynamodb.Table('Reports')

# ---------------- ROUTES ---------------- #

@app.route('/')
def index():
    print("✅ MedTrack is running!")
    return render_template('index.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        users_table.put_item(
            Item={
                'email': request.form['email'],
                'name': request.form['name'],
                'password': request.form['password'],
                'role': request.form['role']
            }
        )
        return redirect(url_for('login'))
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        role = request.form['role']
        user = users_table.get_item(Key={'email': email}).get('Item')
        if user and user['role'] == role and user['password'] == request.form['password']:
            session['user'] = email
            session['role'] = role
            return redirect(url_for('dashboard'))
        return "Invalid login credentials"
    return render_template('login.html')


@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html')


@app.route('/book-appointment', methods=['GET', 'POST'])
def book_appointment():
    if 'user' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        appointment_data = {
            'appointment_id': str(uuid.uuid4()),
            'patient_email': session['user'],
            'doctor': request.form['doctor'],
            'date': request.form['date'],
            'time': request.form['time']
        }
        appointments_table.put_item(Item=appointment_data)

        # ✅ Send SNS Notification
        try:
            sns.publish(
                TopicArn=SNS_TOPIC_ARN,
                Subject='New Appointment Booked',
                Message=f"""
                Patient: {appointment_data['patient_email']}
                Doctor: {appointment_data['doctor']}
                Date: {appointment_data['date']}
                Time: {appointment_data['time']}
                """
            )
        except Exception as e:
            print("❌ SNS Error:", e)

        return redirect(url_for('dashboard'))

    return render_template('book-appointment.html')


@app.route('/submit-diagnosis', methods=['GET', 'POST'])
def submit_diagnosis():
    if 'user' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        file = request.files['report_file']
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        reports_table.put_item(
            Item={
                'report_id': str(uuid.uuid4()),
                'patient_email': request.form['patient_name'],
                'doctor_name': request.form['doctor_name'],
                'summary': request.form['summary'],
                'filename': filename
            }
        )
        return redirect(url_for('dashboard'))

    return render_template('submit-diagnosis.html')


@app.route('/medical-history')
def medical_history():
    if 'user' not in session:
        return redirect(url_for('login'))

    user_email = session['user']
    reports = reports_table.scan().get('Items', [])
    user_reports = [r for r in reports if r['patient_email'] == user_email]
    return render_template('medical-history.html', reports=user_reports)


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


# ---------------- RUN SERVER ---------------- #
if _name_ == '_main_':
    if not os.path.exists('uploads'):
        os.makedirs('uploads')
    app.run(host="0.0.0.0", port=5000, debug=True)

from flask import Flask, render_template, request, redirect, url_for, session
import boto3
import uuid

app = Flask(__name__)
app.secret_key = 'secret_key_here'

# AWS Setup
dynamodb = boto3.resource('dynamodb', region_name='ap-south-1')
s3 = boto3.client('s3', region_name='ap-south-1')
S3_BUCKET = 'your-s3-bucket-name'

users_table = dynamodb.Table('Users')
appointments_table = dynamodb.Table('Appointments')
reports_table = dynamodb.Table('Reports')


@app.route('/')
def index():
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
        if user and user['role'] == role:
            session['user'] = email
            session['role'] = role
            return redirect(url_for('dashboard'))
        return "Invalid login"
    return render_template('login.html')


@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html')


@app.route('/book-appointment', methods=['GET', 'POST'])
def book_appointment():
    if request.method == 'POST':
        appointments_table.put_item(
            Item={
                'appointment_id': str(uuid.uuid4()),
                'patient_email': session['user'],
                'doctor': request.form['doctor'],
                'date': request.form['date'],
                'time': request.form['time']
            }
        )
        return redirect(url_for('dashboard'))
    return render_template('book-appointment.html')


@app.route('/submit-diagnosis', methods=['GET', 'POST'])
def submit_diagnosis():
    if request.method == 'POST':
        file = request.files['report_file']
        filename = file.filename
        s3.upload_fileobj(file, S3_BUCKET, filename)

        reports_table.put_item(
            Item={
                'report_id': str(uuid.uuid4()),
                'patient_email': request.form['patient_name'],
                'doctor_name': request.form['doctor_name'],
                'summary': request.form['summary'],
                'filename': filename,
                's3_url': f"https://{S3_BUCKET}.s3.amazonaws.com/{filename}"
            }
        )
        return redirect(url_for('dashboard'))
    return render_template('submit-diagnosis.html')


@app.route('/medical-history')
def medical_history():
    reports = reports_table.scan().get('Items', [])
    return render_template('medical-history.html', reports=reports)


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0',port=5000)


from flask import Flask, render_template, request, redirect, url_for, session
import os
import uuid

# App setup
app = Flask(__name__)
app.secret_key = 'secret_key_here'
app.config['UPLOAD_FOLDER'] = 'uploads'



# In-memory storage for local mode
users_table = []
appointments_table = []
reports_table = []

# View a report for an appointment
@app.route('/view-report/<appointment_id>')
def view_report(appointment_id):
    # Find the appointment
    report = next((r for r in reports_table if r['report_id'] == appointment_id), None)
    if report:
        # Try to find a matching appointment for context
        appt = next((a for a in appointments_table if a['patient_email'] == report['patient_email'] and a['doctor'] == report['doctor_name']), None)
        # If no appointment, create a minimal context
        if not appt:
            appt = {
                'doctor': report['doctor_name'],
                'patient_email': report['patient_email'],
                'date': report.get('date', 'N/A'),
                'time': 'N/A'
            }
        return render_template('view_report.html', appointment=appt, report=report)
    # Fallback: try to find by appointment_id (legacy)
    appt = next((a for a in appointments_table if a['appointment_id'] == appointment_id), None)
    if not appt:
        return "Report not found."
    report = next((r for r in reports_table if r['patient_email'] == appt['patient_email'] and r['doctor_name'] == appt['doctor']), None)
    return render_template('view_report.html', appointment=appt, report=report)
    # Try to find a report for this appointment (by patient, doctor, and date)
    report = next((r for r in reports_table if r['patient_email'] == appt['patient_email'] and r['doctor_name'] == appt['doctor']), None)
    return render_template('view_report.html', appointment=appt, report=report)

# ---------------- ROUTES ---------------- #

@app.route('/')
def index():
    print("✅ MedTrack is running!")  # add this line
    return render_template('index.html')




@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        role = request.form['role']
        # Prevent duplicate registration
        existing = next((u for u in users_table if u['email'] == email and u['role'] == role), None)
        if existing:
            print(f"[DEBUG] Registration failed: user already exists for {email} ({role})")
            return "User already exists for this email and role. Please login."
        user = {
            'email': email,
            'name': request.form['name'],
            'password': request.form['password'],
            'role': role
        }
        users_table.append(user)
        print(f"[DEBUG] Registered user: {user}")
        return redirect(url_for('login'))
    return render_template('register.html')




@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        role = request.form['role']
        password = request.form['password']
        print(f"[DEBUG] Login attempt: {email}, {role}, {password}")
        print(f"[DEBUG] Current users: {users_table}")
        user = next((u for u in users_table if u['email'] == email and u['role'] == role and u['password'] == password), None)
        if user:
            session['user'] = email
            session['role'] = role
            print(f"[DEBUG] Login success: {user}")
            if role == 'doctor':
                return redirect(url_for('doctor_dashboard'))
            return redirect(url_for('dashboard'))
        print("[DEBUG] Invalid login")
        return "Invalid login"
    return render_template('login.html')
# Doctor dashboard route
@app.route('/doctor-dashboard')
def doctor_dashboard():
    if 'user' not in session or session.get('role') != 'doctor':
        return redirect(url_for('login'))
    doctor_email = session.get('user')
    doctor = next((u for u in users_table if u['email'] == doctor_email), None)
    doctor_name = doctor['name'] if doctor else 'Doctor'
    # Show all appointments for this doctor
    doctor_appointments = [a for a in appointments_table if a['doctor'] == doctor_email or a['doctor'] == 'dr_john' or a['doctor'] == 'dr_susan' or a['doctor'] == 'dr_kumar']
    # (For demo: show all appointments. In real, match doctor name/email)
    return render_template('doctor_dashboard.html', appointments=doctor_appointments, doctor_name=doctor_name)

# Doctor view appointment details
@app.route('/doctor-appointment/<appointment_id>')
def doctor_appointment_detail(appointment_id):
    if 'user' not in session or session.get('role') != 'doctor':
        return redirect(url_for('login'))
    appt = next((a for a in appointments_table if a['appointment_id'] == appointment_id), None)
    if not appt:
        return "Appointment not found."
    return render_template('doctor_appointment_detail.html', appointment=appt)




@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))
    user_email = session.get('user')
    user_role = session.get('role')
    if user_role == 'doctor':
        return redirect(url_for('doctor_dashboard'))
    user = next((u for u in users_table if u['email'] == user_email), None)
    user_name = user['name'] if user else 'User'
    # Only show this user's appointments
    user_appointments = [a for a in appointments_table if a['patient_email'] == user_email]
    # Mark completed if a report exists for this appointment
    for a in user_appointments:
        a['completed'] = any(r['patient_email'] == a['patient_email'] and r['doctor_name'] == a['doctor'] for r in reports_table)
    pending_count = sum(1 for a in user_appointments if not a['completed'])
    completed_count = sum(1 for a in user_appointments if a['completed'])
    total_count = len(user_appointments)
    return render_template('dashboard.html', user_name=user_name, user_role=user_role,
                           appointments=user_appointments, pending_count=pending_count,
                           completed_count=completed_count, total_count=total_count)


# View Appointments route
@app.route('/appointments')
def view_appointments():
    if 'user' not in session:
        return redirect(url_for('login'))
    user_email = session.get('user')
    user_role = session.get('role')
    if user_role == 'patient':
        user_appointments = [a for a in appointments_table if a['patient_email'] == user_email]
    else:
        user_appointments = appointments_table
    return render_template('appointments.html', appointments=user_appointments)


@app.route('/book-appointment', methods=['GET', 'POST'])
def book_appointment():
    if request.method == 'POST':
        appointment = {
            'appointment_id': str(uuid.uuid4()),
            'patient_email': session.get('user'),
            'doctor': request.form['doctor'],
            'date': request.form['date'],
            'time': request.form['time']
        }
        appointments_table.append(appointment)
        return redirect(url_for('dashboard'))
    return render_template('book-appointment.html')


@app.route('/submit-diagnosis', methods=['GET', 'POST'])
def submit_diagnosis():
    if request.method == 'POST':
        file = request.files['report_file']
        filename = file.filename
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        report = {
            'report_id': str(uuid.uuid4()),
            'patient_email': request.form['patient_name'],
            'doctor_name': request.form['doctor_name'],
            'summary': request.form['summary'],
            'filename': filename
        }
        reports_table.append(report)
        return redirect(url_for('dashboard'))
    return render_template('submit-diagnosis.html')


@app.route('/medical-history')
def medical_history():
    return render_template('medical-history.html', reports=reports_table)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ---------------- RUN SERVER ---------------- #
if __name__ == '__main__':
    if not os.path.exists('uploads'):
        os.makedirs('uploads')
    # Add a sample report if none exist
    if not reports_table:
        reports_table.append({
            'report_id': 'sample-1',
            'patient_email': 'sample@example.com',
            'doctor_name': 'Dr. Susan Lee',
            'summary': 'Diagnosis: Viral Infection. Rest, hydration, and Paracetamol advised.',
            'filename': 'sample_report.pdf'
        })
    app.run(debug=True)

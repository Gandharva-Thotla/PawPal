from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_file
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from database import get_db, init_db, seed_sample_data
from datetime import datetime
import os
import random
import json

app = Flask(__name__)
app.secret_key = 'pawpal_pet_adoption_portal_secret_key_2026'

# Configure upload directory
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB max

# Initialize and seed database on startup
init_db()
try:
    seed_sample_data()
except Exception as e:
    print(f"Seed note: {e}")


# ============== CONTEXT PROCESSOR ==============
@app.context_processor
def inject_global_vars():
    """Inject current year and session user details to all templates"""
    return {
        'current_year': datetime.now().year,
        'current_user': session.get('user_name'),
        'current_role': session.get('role')
    }


# ============== DECORATORS ==============
def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please sign in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def shelter_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in with your shelter staff account.', 'warning')
            return redirect(url_for('login'))
        if session.get('role') != 'shelter':
            flash('Access restricted. Shelter staff privileges required.', 'danger')
            return redirect(url_for('adopter_dashboard'))
        return f(*args, **kwargs)
    return decorated_function


# ============== PUBLIC ROUTES ==============
@app.route('/')
def index():
    db = get_db()
    species = request.args.get('species')
    status = request.args.get('status')
    shelter_id = request.args.get('shelter_id')
    search = request.args.get('search', '').strip().lower()

    # Query metrics
    stats = {
        'available_pets': db.execute("SELECT COUNT(*) as c FROM pets WHERE status = 'Available'").fetchone()['c'],
        'adopted_pets': db.execute("SELECT COUNT(*) as c FROM pets WHERE status = 'Adopted'").fetchone()['c'],
        'total_applications': db.execute("SELECT COUNT(*) as c FROM adoption_applications").fetchone()['c'],
        'total_shelters': db.execute("SELECT COUNT(*) as c FROM shelters").fetchone()['c']
    }

    # Build dynamic query for pets
    query = '''
        SELECT p.*, s.name as shelter_name, s.city as shelter_city, s.state as shelter_state
        FROM pets p
        JOIN shelters s ON p.shelter_id = s.id
        WHERE 1=1
    '''
    params = []

    if species and species != 'all':
        query += ' AND LOWER(p.species) = LOWER(?)'
        params.append(species)
    if status and status != 'all':
        query += ' AND LOWER(p.status) = LOWER(?)'
        params.append(status)
    if shelter_id and shelter_id != 'all':
        query += ' AND p.shelter_id = ?'
        params.append(shelter_id)
    if search:
        query += ''' AND (
            LOWER(p.name) LIKE ? OR
            LOWER(p.breed) LIKE ? OR
            LOWER(p.personality) LIKE ? OR
            LOWER(p.bio) LIKE ?
        )'''
        search_param = f"%{search}%"
        params.extend([search_param, search_param, search_param, search_param])

    query += ' ORDER BY p.id DESC'
    pets = db.execute(query, params).fetchall()
    db.close()

    return render_template(
        'index.html',
        pets=pets,
        stats=stats,
        selected_species=species,
        selected_status=status,
        search_query=search
    )


@app.route('/pets/<int:pet_id>')
def pet_detail(pet_id):
    db = get_db()
    pet = db.execute('''
        SELECT p.*, s.name as shelter_name, s.email as shelter_email, s.phone as shelter_phone,
               s.address as shelter_address, s.city as shelter_city, s.state as shelter_state,
               s.director as shelter_director, s.license_no as shelter_license
        FROM pets p
        JOIN shelters s ON p.shelter_id = s.id
        WHERE p.id = ?
    ''', (pet_id,)).fetchone()

    if not pet:
        db.close()
        flash('Pet not found.', 'danger')
        return redirect(url_for('index'))

    photos = db.execute('SELECT * FROM pet_photos WHERE pet_id = ? ORDER BY is_primary DESC', (pet_id,)).fetchall()
    db.close()

    return render_template('pet_detail.html', pet=pet, photos=photos)


@app.route('/shelters')
def shelters_list():
    db = get_db()
    shelters = db.execute('''
        SELECT s.*, COUNT(p.id) as pet_count
        FROM shelters s
        LEFT JOIN pets p ON s.id = p.shelter_id AND p.status = 'Available'
        GROUP BY s.id
    ''').fetchall()
    db.close()
    return render_template('shelters.html', shelters=shelters)


@app.route('/track')
def track_public():
    code = request.args.get('code', '').strip().upper()
    app_record = None
    timeline = []

    if code:
        db = get_db()
        app_record = db.execute('''
            SELECT a.*, p.name as pet_name, p.species, p.breed, p.primary_photo,
                   s.name as shelter_name, s.phone as shelter_phone, s.email as shelter_email
            FROM adoption_applications a
            JOIN pets p ON a.pet_id = p.id
            JOIN shelters s ON p.shelter_id = s.id
            WHERE UPPER(a.tracking_code) = ? OR LOWER(a.applicant_email) = LOWER(?)
        ''', (code, code)).fetchone()

        if app_record:
            timeline = db.execute('''
                SELECT * FROM application_timeline
                WHERE application_id = ?
                ORDER BY created_at ASC
            ''', (app_record['id'],)).fetchall()
        db.close()

    return render_template('track.html', code=code, app_record=app_record, timeline=timeline)


# ============== AUTHENTICATION ==============
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        db = get_db()
        user = db.execute('SELECT * FROM users WHERE LOWER(email) = LOWER(?)', (email,)).fetchone()
        db.close()

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            session['user_email'] = user['email']
            session['role'] = user['role']
            session['shelter_id'] = user['shelter_id']

            flash(f"Welcome back, {user['name']}!", 'success')
            if user['role'] == 'shelter':
                return redirect(url_for('shelter_dashboard'))
            return redirect(url_for('adopter_dashboard'))
        else:
            flash('Invalid email or password. Please try again.', 'danger')

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    db = get_db()
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        phone = request.form.get('phone', '').strip()
        role = request.form.get('role', 'adopter')
        shelter_id = request.form.get('shelter_id') if role == 'shelter' else None

        # Check existing
        existing = db.execute('SELECT id FROM users WHERE LOWER(email) = LOWER(?)', (email,)).fetchone()
        if existing:
            db.close()
            flash('An account with this email address already exists.', 'warning')
            return redirect(url_for('register'))

        hashed_pw = generate_password_hash(password)
        cursor = db.cursor()
        cursor.execute('''
            INSERT INTO users (name, email, password, phone, role, shelter_id)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (name, email, hashed_pw, phone, role, shelter_id))
        user_id = cursor.lastrowid
        db.commit()
        db.close()

        session['user_id'] = user_id
        session['user_name'] = name
        session['user_email'] = email
        session['role'] = role
        session['shelter_id'] = shelter_id

        flash('Registration successful! Welcome to PawPal.', 'success')
        if role == 'shelter':
            return redirect(url_for('shelter_dashboard'))
        return redirect(url_for('adopter_dashboard'))

    shelters = db.execute('SELECT id, name, city, state FROM shelters ORDER BY name').fetchall()
    db.close()
    return render_template('register.html', shelters=shelters)


@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('index'))


# ============== ADOPTER APPLICATION FLOW ==============
@app.route('/apply/<int:pet_id>', methods=['GET', 'POST'])
def apply_pet(pet_id):
    db = get_db()
    pet = db.execute('''
        SELECT p.*, s.name as shelter_name
        FROM pets p
        JOIN shelters s ON p.shelter_id = s.id
        WHERE p.id = ?
    ''', (pet_id,)).fetchone()

    if not pet:
        db.close()
        flash('Pet not found.', 'danger')
        return redirect(url_for('index'))

    if request.method == 'POST':
        applicant_name = request.form.get('applicant_name', '').strip()
        applicant_email = request.form.get('applicant_email', '').strip()
        applicant_phone = request.form.get('applicant_phone', '').strip()
        address = request.form.get('address', '').strip()
        housing_type = request.form.get('housing_type', 'Single Family Home')
        ownership = request.form.get('ownership', 'Own')
        landlord_approval = request.form.get('landlord_approval', 'N/A')
        has_fenced_yard = 1 if request.form.get('has_fenced_yard') else 0
        fence_height = request.form.get('fence_height', 'Standard')
        adults_in_home = int(request.form.get('adults_in_home', 2))
        children_in_home = int(request.form.get('children_in_home', 0))
        current_pets = request.form.get('current_pets', 'None')
        hours_alone = request.form.get('hours_alone', '2-4 hours')
        activity_level = request.form.get('activity_level', 'Moderate')
        vet_reference = request.form.get('vet_reference', '')
        motivation = request.form.get('motivation', '').strip()

        tracking_code = f"PAW-{random.randint(10000, 99999)}"
        user_id = session.get('user_id')

        cursor = db.cursor()
        cursor.execute('''
            INSERT INTO adoption_applications (
                tracking_code, pet_id, user_id, applicant_name, applicant_email, applicant_phone,
                address, housing_type, ownership, landlord_approval, has_fenced_yard, fence_height,
                adults_in_home, children_in_home, current_pets, hours_alone, activity_level,
                vet_reference, motivation, status, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Submitted', ?)
        ''', (
            tracking_code, pet_id, user_id, applicant_name, applicant_email, applicant_phone,
            address, housing_type, ownership, landlord_approval, has_fenced_yard, fence_height,
            adults_in_home, children_in_home, current_pets, hours_alone, activity_level,
            vet_reference, motivation, 'Application submitted via PawPal portal. Awaiting staff review.'
        ))
        app_id = cursor.lastrowid

        # Insert initial timeline log
        cursor.execute('''
            INSERT INTO application_timeline (application_id, status, note)
            VALUES (?, 'Submitted', 'Application received and logged into shelter queue.')
        ''', (app_id,))

        # Update pet status to Pending if Available
        if pet['status'] == 'Available':
            cursor.execute("UPDATE pets SET status = 'Pending' WHERE id = ?", (pet_id,))

        db.commit()
        db.close()

        flash(f"🎉 Adoption application submitted! Reference Code: {tracking_code}", 'success')
        return redirect(url_for('track_public', code=tracking_code))

    db.close()
    return render_template('adopter/apply.html', pet=pet)


@app.route('/adopter/dashboard')
@login_required
def adopter_dashboard():
    db = get_db()
    user_id = session['user_id']
    user_email = session['user_email']

    applications = db.execute('''
        SELECT a.*, p.name as pet_name, p.species, p.breed, p.primary_photo,
               s.name as shelter_name
        FROM adoption_applications a
        JOIN pets p ON a.pet_id = p.id
        JOIN shelters s ON p.shelter_id = s.id
        WHERE a.user_id = ? OR LOWER(a.applicant_email) = LOWER(?)
        ORDER BY a.id DESC
    ''', (user_id, user_email)).fetchall()
    db.close()

    return render_template('adopter/dashboard.html', applications=applications)


# ============== SHELTER MANAGEMENT PORTAL ==============
@app.route('/shelter/dashboard')
@shelter_required
def shelter_dashboard():
    db = get_db()
    shelter_id = session.get('shelter_id', 1)

    shelter = db.execute('SELECT * FROM shelters WHERE id = ?', (shelter_id,)).fetchone()
    if not shelter:
        shelter = db.execute('SELECT * FROM shelters ORDER BY id ASC LIMIT 1').fetchone()

    stats = {
        'available': db.execute("SELECT COUNT(*) as c FROM pets WHERE shelter_id = ? AND status = 'Available'", (shelter['id'],)).fetchone()['c'],
        'pending_pets': db.execute("SELECT COUNT(*) as c FROM pets WHERE shelter_id = ? AND status = 'Pending'", (shelter['id'],)).fetchone()['c'],
        'adopted': db.execute("SELECT COUNT(*) as c FROM pets WHERE shelter_id = ? AND status = 'Adopted'", (shelter['id'],)).fetchone()['c'],
        'pending_apps': db.execute('''
            SELECT COUNT(*) as c FROM adoption_applications a
            JOIN pets p ON a.pet_id = p.id
            WHERE p.shelter_id = ? AND a.status NOT IN ('Completed', 'Declined')
        ''', (shelter['id'],)).fetchone()['c']
    }

    recent_apps = db.execute('''
        SELECT a.*, p.name as pet_name, p.primary_photo
        FROM adoption_applications a
        JOIN pets p ON a.pet_id = p.id
        WHERE p.shelter_id = ?
        ORDER BY a.id DESC
        LIMIT 10
    ''', (shelter['id'],)).fetchall()

    db.close()
    return render_template('shelter/dashboard.html', shelter=shelter, stats=stats, applications=recent_apps)


@app.route('/shelter/register-pet', methods=['GET', 'POST'])
@shelter_required
def register_pet():
    db = get_db()
    shelter_id = session.get('shelter_id', 1)

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        species = request.form.get('species', 'Dog')
        breed = request.form.get('breed', '').strip()
        age = request.form.get('age', '').strip()
        gender = request.form.get('gender', 'Unknown')
        size = request.form.get('size', 'Medium')
        color = request.form.get('color', '').strip()
        adoption_fee = float(request.form.get('adoption_fee', 120))
        microchip = request.form.get('microchip', '').strip() or f"985-{random.randint(1000, 9999)}-{random.randint(1000, 9999)}"
        vaccinated = 1 if request.form.get('vaccinated') else 0
        neutered = 1 if request.form.get('neutered') else 0
        house_trained = 1 if request.form.get('house_trained') else 0
        good_with_kids = 1 if request.form.get('good_with_kids') else 0
        good_with_dogs = 1 if request.form.get('good_with_dogs') else 0
        good_with_cats = 1 if request.form.get('good_with_cats') else 0
        special_needs = request.form.get('special_needs', 'None')
        personality = request.form.get('personality', 'Playful, Friendly')
        bio = request.form.get('bio', '').strip()

        # Handle file upload or image URL
        photo_url = request.form.get('pet_photo_url', '').strip()
        file = request.files.get('pet_photo_file')
        if file and file.filename != '':
            filename = secure_filename(f"pet_{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}")
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            photo_url = f"/static/uploads/{filename}"

        if not photo_url:
            photo_url = "https://images.unsplash.com/photo-1543466835-00a7907e9de1?auto=format&fit=crop&w=800&q=80"

        cursor = db.cursor()
        cursor.execute('''
            INSERT INTO pets (
                name, species, breed, age, gender, size, color, status, shelter_id, adoption_fee,
                microchip, vaccinated, neutered, house_trained, good_with_kids, good_with_dogs,
                good_with_cats, special_needs, personality, bio, primary_photo
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 'Available', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            name, species, breed, age, gender, size, color, shelter_id, adoption_fee,
            microchip, vaccinated, neutered, house_trained, good_with_kids, good_with_dogs,
            good_with_cats, special_needs, personality, bio, photo_url
        ))
        pet_id = cursor.lastrowid

        cursor.execute('''
            INSERT INTO pet_photos (pet_id, photo_url, is_primary) VALUES (?, ?, 1)
        ''', (pet_id, photo_url))

        db.commit()
        db.close()

        flash(f"🐾 {name} has been registered and is now listed for adoption!", 'success')
        return redirect(url_for('manage_pets'))

    db.close()
    return render_template('shelter/register_pet.html')


@app.route('/shelter/manage-pets')
@shelter_required
def manage_pets():
    db = get_db()
    shelter_id = session.get('shelter_id', 1)
    pets = db.execute('''
        SELECT * FROM pets WHERE shelter_id = ? ORDER BY id DESC
    ''', (shelter_id,)).fetchall()
    db.close()
    return render_template('shelter/manage_pets.html', pets=pets)


@app.route('/shelter/pets/<int:pet_id>/status', methods=['POST'])
@shelter_required
def update_pet_status(pet_id):
    new_status = request.form.get('status')
    if new_status in ['Available', 'Pending', 'Adopted']:
        db = get_db()
        db.execute('UPDATE pets SET status = ? WHERE id = ?', (new_status, pet_id))
        db.commit()
        db.close()
        flash(f'Pet status updated to {new_status}.', 'success')
    return redirect(url_for('manage_pets'))


@app.route('/shelter/applications')
@shelter_required
def shelter_applications():
    db = get_db()
    shelter_id = session.get('shelter_id', 1)
    app_id = request.args.get('app_id', type=int)

    applications = db.execute('''
        SELECT a.*, p.name as pet_name, p.primary_photo, p.species, p.breed
        FROM adoption_applications a
        JOIN pets p ON a.pet_id = p.id
        WHERE p.shelter_id = ?
        ORDER BY a.id DESC
    ''', (shelter_id,)).fetchall()

    selected_app = None
    if app_id:
        selected_app = db.execute('''
            SELECT a.*, p.name as pet_name, p.primary_photo, p.breed, p.species, p.adoption_fee, p.microchip
            FROM adoption_applications a
            JOIN pets p ON a.pet_id = p.id
            WHERE a.id = ?
        ''', (app_id,)).fetchone()

    db.close()
    return render_template('shelter/view_applications.html', applications=applications, selected_app=selected_app)


@app.route('/shelter/applications/<int:app_id>/status', methods=['POST'])
@shelter_required
def update_application_status(app_id):
    new_status = request.form.get('status')
    timeline_note = request.form.get('timeline_note', '').strip() or f"Status updated to {new_status}"

    db = get_db()
    app_row = db.execute('SELECT * FROM adoption_applications WHERE id = ?', (app_id,)).fetchone()
    if not app_row:
        db.close()
        flash('Application not found.', 'danger')
        return redirect(url_for('shelter_applications'))

    cursor = db.cursor()
    cursor.execute('''
        UPDATE adoption_applications
        SET status = ?, notes = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    ''', (new_status, timeline_note, app_id))

    cursor.execute('''
        INSERT INTO application_timeline (application_id, status, note)
        VALUES (?, ?, ?)
    ''', (app_id, new_status, timeline_note))

    # If completed, automatically generate official Adoption Record and set pet to Adopted
    if new_status == 'Completed':
        pet = db.execute('SELECT * FROM pets WHERE id = ?', (app_row['pet_id'],)).fetchone()
        shelter = db.execute('SELECT * FROM shelters WHERE id = ?', (pet['shelter_id'],)).fetchone()

        record_count = db.execute('SELECT COUNT(*) as c FROM adoption_records').fetchone()['c']
        rec_number = f"REC-2026-{(record_count + 95):04d}"
        cert_code = f"CERT-PAW-{random.randint(100000, 999900)}"
        today = datetime.now().strftime("%Y-%m-%d")

        cursor.execute('''
            INSERT INTO adoption_records (
                record_number, application_id, pet_id, adopter_name, adopter_email, adopter_phone,
                adopter_address, shelter_id, shelter_director, microchip_number, rabies_tag_number,
                adoption_fee, fee_status, adoption_date, handover_date, certificate_code
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Paid in Full', ?, ?, ?)
        ''', (
            rec_number, app_id, pet['id'], app_row['applicant_name'], app_row['applicant_email'],
            app_row['applicant_phone'], app_row['address'], shelter['id'], shelter['director'],
            pet['microchip'], f"RAB-{random.randint(1000, 9999)}", pet['adoption_fee'],
            today, today, cert_code
        ))
        new_rec_id = cursor.lastrowid

        # Insert standard follow-ups
        cursor.execute('''
            INSERT INTO follow_ups (record_id, milestone, due_date, status, notes)
            VALUES (?, 'Day 7 Check-in', date('now', '+7 days'), 'Scheduled', 'Verify initial home transition.')
        ''', (new_rec_id,))
        cursor.execute('''
            INSERT INTO follow_ups (record_id, milestone, due_date, status, notes)
            VALUES (?, 'Month 1 Check-in', date('now', '+30 days'), 'Scheduled', 'First month veterinary wellness check.')
        ''', (new_rec_id,))

        cursor.execute("UPDATE pets SET status = 'Adopted' WHERE id = ?", (pet['id'],))
        db.commit()
        db.close()

        flash(f"🏆 Adoption Finalized! Official Record #{rec_number} created with Certificate.", 'success')
        return redirect(url_for('view_certificate', record_id=new_rec_id))

    db.commit()
    db.close()
    flash(f"Application status updated to {new_status}.", 'success')
    return redirect(url_for('shelter_applications', app_id=app_id))


@app.route('/shelter/records')
@shelter_required
def shelter_records():
    db = get_db()
    shelter_id = session.get('shelter_id', 1)

    records = db.execute('''
        SELECT r.*, p.name as pet_name, p.breed as pet_breed, p.primary_photo
        FROM adoption_records r
        JOIN pets p ON r.pet_id = p.id
        WHERE r.shelter_id = ?
        ORDER BY r.id DESC
    ''', (shelter_id,)).fetchall()

    # Attach follow-ups to each record
    records_list = []
    for r in records:
        fups = db.execute('SELECT * FROM follow_ups WHERE record_id = ? ORDER BY id ASC', (r['id'],)).fetchall()
        r_dict = dict(r)
        r_dict['follow_ups'] = fups
        records_list.append(r_dict)

    db.close()
    return render_template('shelter/adoption_records.html', records=records_list)


@app.route('/shelter/records/<int:record_id>/certificate')
def view_certificate(record_id):
    db = get_db()
    record = db.execute('''
        SELECT r.*, p.name as pet_name, p.breed as pet_breed, p.species as pet_species,
               p.gender as pet_gender, p.primary_photo, s.name as shelter_name,
               s.license_no as shelter_license
        FROM adoption_records r
        JOIN pets p ON r.pet_id = p.id
        JOIN shelters s ON r.shelter_id = s.id
        WHERE r.id = ?
    ''', (record_id,)).fetchone()
    db.close()

    if not record:
        flash('Adoption record not found.', 'danger')
        return redirect(url_for('index'))

    return render_template('shelter/certificate.html', record=record)


@app.route('/shelter/followups/<int:followup_id>/complete', methods=['POST'])
@shelter_required
def complete_followup(followup_id):
    db = get_db()
    db.execute('''
        UPDATE follow_ups
        SET status = 'Completed', notes = 'Follow-up successfully completed with adopter.', completed_at = CURRENT_TIMESTAMP
        WHERE id = ?
    ''', (followup_id,))
    db.commit()
    db.close()
    flash('Post-adoption follow-up check-in marked as Completed.', 'success')
    return redirect(url_for('shelter_records'))


@app.route('/shelter/records/<int:record_id>/add-followup', methods=['POST'])
@shelter_required
def add_followup(record_id):
    milestone = request.form.get('milestone', '').strip()
    due_date = request.form.get('due_date')
    if milestone and due_date:
        db = get_db()
        db.execute('''
            INSERT INTO follow_ups (record_id, milestone, due_date, status, notes)
            VALUES (?, ?, ?, 'Scheduled', '')
        ''', (record_id, milestone, due_date))
        db.commit()
        db.close()
        flash(f'New follow-up milestone "{milestone}" scheduled.', 'success')
    return redirect(url_for('shelter_records'))


@app.route('/shelter/records/export-json')
@shelter_required
def export_records_json():
    db = get_db()
    records = db.execute('SELECT * FROM adoption_records ORDER BY id DESC').fetchall()
    db.close()
    records_data = [dict(r) for r in records]
    return jsonify(records_data)


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"🐾 PawPal Flask Application running on http://localhost:{port}")
    app.run(host='0.0.0.0', port=port, debug=True)

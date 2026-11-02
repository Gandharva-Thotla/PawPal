import sqlite3
import os
from werkzeug.security import generate_password_hash

DATABASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pawpal.db')

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.executescript('''
        CREATE TABLE IF NOT EXISTS shelters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            phone TEXT NOT NULL,
            address TEXT NOT NULL,
            city TEXT NOT NULL,
            state TEXT NOT NULL,
            director TEXT NOT NULL,
            license_no TEXT NOT NULL,
            established INTEGER DEFAULT 2014,
            rating REAL DEFAULT 4.9,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            phone TEXT,
            role TEXT NOT NULL DEFAULT 'adopter',
            shelter_id INTEGER,
            address TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (shelter_id) REFERENCES shelters(id)
        );

        CREATE TABLE IF NOT EXISTS pets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            species TEXT NOT NULL,
            breed TEXT NOT NULL,
            age TEXT NOT NULL,
            gender TEXT NOT NULL,
            size TEXT NOT NULL,
            color TEXT,
            status TEXT DEFAULT 'Available',
            shelter_id INTEGER NOT NULL,
            adoption_fee REAL DEFAULT 120.0,
            microchip TEXT,
            vaccinated INTEGER DEFAULT 1,
            neutered INTEGER DEFAULT 1,
            house_trained INTEGER DEFAULT 1,
            good_with_kids INTEGER DEFAULT 1,
            good_with_dogs INTEGER DEFAULT 1,
            good_with_cats INTEGER DEFAULT 0,
            special_needs TEXT DEFAULT 'None',
            personality TEXT,
            bio TEXT,
            primary_photo TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (shelter_id) REFERENCES shelters(id)
        );

        CREATE TABLE IF NOT EXISTS pet_photos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pet_id INTEGER NOT NULL,
            photo_url TEXT NOT NULL,
            is_primary INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (pet_id) REFERENCES pets(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS adoption_applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tracking_code TEXT UNIQUE NOT NULL,
            pet_id INTEGER NOT NULL,
            user_id INTEGER,
            applicant_name TEXT NOT NULL,
            applicant_email TEXT NOT NULL,
            applicant_phone TEXT NOT NULL,
            address TEXT NOT NULL,
            housing_type TEXT DEFAULT 'Single Family Home',
            ownership TEXT DEFAULT 'Own',
            landlord_approval TEXT,
            has_fenced_yard INTEGER DEFAULT 1,
            fence_height TEXT,
            adults_in_home INTEGER DEFAULT 2,
            children_in_home INTEGER DEFAULT 0,
            current_pets TEXT,
            hours_alone TEXT,
            activity_level TEXT,
            vet_reference TEXT,
            motivation TEXT NOT NULL,
            status TEXT DEFAULT 'Submitted',
            notes TEXT,
            submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (pet_id) REFERENCES pets(id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS application_timeline (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            application_id INTEGER NOT NULL,
            status TEXT NOT NULL,
            note TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (application_id) REFERENCES adoption_applications(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS adoption_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            record_number TEXT UNIQUE NOT NULL,
            application_id INTEGER,
            pet_id INTEGER NOT NULL,
            adopter_name TEXT NOT NULL,
            adopter_email TEXT NOT NULL,
            adopter_phone TEXT NOT NULL,
            adopter_address TEXT NOT NULL,
            shelter_id INTEGER NOT NULL,
            shelter_director TEXT NOT NULL,
            microchip_number TEXT NOT NULL,
            rabies_tag_number TEXT,
            adoption_fee REAL DEFAULT 120.0,
            fee_status TEXT DEFAULT 'Paid in Full',
            adoption_date TEXT NOT NULL,
            handover_date TEXT NOT NULL,
            certificate_code TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (pet_id) REFERENCES pets(id),
            FOREIGN KEY (shelter_id) REFERENCES shelters(id),
            FOREIGN KEY (application_id) REFERENCES adoption_applications(id)
        );

        CREATE TABLE IF NOT EXISTS follow_ups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            record_id INTEGER NOT NULL,
            milestone TEXT NOT NULL,
            due_date TEXT NOT NULL,
            status TEXT DEFAULT 'Scheduled',
            notes TEXT,
            completed_at TIMESTAMP,
            FOREIGN KEY (record_id) REFERENCES adoption_records(id) ON DELETE CASCADE
        );
    ''')
    
    conn.commit()
    conn.close()
    print('PawPal SQLite database initialized successfully!')

def seed_sample_data():
    conn = get_db()
    cursor = conn.cursor()
    
    # Check if shelters already seeded
    existing_shelters = cursor.execute('SELECT COUNT(*) FROM shelters').fetchone()[0]
    if existing_shelters > 0:
        conn.close()
        return

    print('Seeding realistic PawPal sample data...')
    
    # 1. Seed Shelters
    shelters_data = [
        ("Happy Paws Sanctuary", "contact@happypaws.org", "(415) 555-0192", "742 Evergreen Terrace", "San Francisco", "CA", "Dr. Sarah Jenkins, DVM", "CA-SHELTER-8821", 2014, 4.9, "Dedicated to rescuing, rehabilitating, and finding loving forever homes for companion animals across the Bay Area."),
        ("Safe Haven Animal Rescue", "adoptions@safehavenrescue.org", "(512) 555-0348", "1204 Willow Creek Way", "Austin", "TX", "Marcus Vance", "TX-RESCUE-4910", 2017, 4.8, "A no-kill rescue organization committed to healing wounded paws and matching great pets with great humans."),
        ("Furry Friends Rescue Network", "hello@furryfriendsnetwork.org", "(206) 555-0811", "389 Pine Crest Ave", "Seattle", "WA", "Elena Rostova", "WA-ANIMAL-6729", 2011, 5.0, "Community-driven animal advocacy offering medical treatment and transparent digital adoption pipelines.")
    ]
    cursor.executemany('''
        INSERT INTO shelters (name, email, phone, address, city, state, director, license_no, established, rating, description)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', shelters_data)

    # 2. Seed Users (Demo Adopter & Demo Shelter Staff)
    demo_adopter_pw = generate_password_hash("adopter123")
    demo_shelter_pw = generate_password_hash("shelter123")
    
    users_data = [
        ("Samantha Reed", "adopter@pawpal.org", demo_adopter_pw, "(512) 555-8291", "adopter", None, "452 Barton Springs Rd, Austin, TX"),
        ("Dr. Sarah Jenkins", "shelter@happypaws.org", demo_shelter_pw, "(415) 555-0192", "shelter", 1, "742 Evergreen Terrace, San Francisco, CA"),
        ("Marcus Vance", "marcus@safehavenrescue.org", demo_shelter_pw, "(512) 555-0348", "shelter", 2, "1204 Willow Creek Way, Austin, TX")
    ]
    cursor.executemany('''
        INSERT INTO users (name, email, password, phone, role, shelter_id, address)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', users_data)

    # 3. Seed Pets
    pets_data = [
        ("Barnaby", "Dog", "Golden Retriever & Lab Mix", "2 years", "Male", "Large (62 lbs)", "Honey Gold", "Available", 1, 150.0, "985-1410-0934-821", 1, 1, 1, 1, 1, 0, "None", "Playful, Gentle, Cuddle Bug, Fast Learner", "Barnaby is an energetic and joyful Golden mix who loves nothing more than playing fetch in the park and resting his head on your lap during movie night. Walks beautifully on leash.", "https://images.unsplash.com/photo-1552053831-71594a27632d?auto=format&fit=crop&w=800&q=80"),
        ("Luna & Cleo", "Cat", "Domestic Shorthair (Bonded Pair)", "1 year", "Female", "Medium (9 lbs)", "Silver Tabby & Calico", "Available", 1, 100.0, "985-1410-0934-822", 1, 1, 1, 1, 1, 1, "Must be adopted together", "Affectionate, Curious, Vocal, Purr Machine", "Luna and Cleo are inseparable sisters rescued from a greenhouse. They love chasing feather toys and grooming each other. Double the cuteness for your home!", "https://images.unsplash.com/photo-1514888286974-6c03e2ca1dba?auto=format&fit=crop&w=800&q=80"),
        ("Milo", "Dog", "Australian Shepherd", "3 years", "Male", "Medium (48 lbs)", "Blue Merle with Copper Points", "Pending", 2, 180.0, "985-1410-0934-823", 1, 1, 1, 1, 1, 1, "Needs active yard or running companion", "Athletic, Intelligent, Loyal, Agility Star", "Milo is a brilliant Aussie who loves trail running, agility courses, and solving puzzle feeders. An active application is in review.", "https://images.unsplash.com/photo-1503256207526-0d5d80fa2f47?auto=format&fit=crop&w=800&q=80"),
        ("Bella", "Dog", "French Bulldog", "4 years", "Female", "Small (22 lbs)", "Fawn with Black Mask", "Available", 2, 200.0, "985-1410-0934-824", 1, 1, 1, 1, 0, 1, "Prefers cool air-conditioned environment", "Couch Potato, Hilarious, Snuggle Queen, Quiet", "Bella is the ultimate companion for cozy apartment living. Her favorite activity is sleeping on fluffy blankets and snoring softly like a tiny motorboat.", "https://images.unsplash.com/photo-1583337130417-3346a1be7dee?auto=format&fit=crop&w=800&q=80"),
        ("Oliver", "Cat", "Maine Coon Mix", "1.5 years", "Male", "Large (16 lbs)", "Ginger Smoke", "Available", 3, 120.0, "985-1410-0934-825", 1, 1, 1, 1, 1, 1, "Requires weekly brushing", "Majestic, Friendly, Gentle Giant, Chatty", "Oliver has stunning tufted ears, a glorious bushy tail, and the sweetest temperament. He greets everyone at the front door with soft chirps.", "https://images.unsplash.com/photo-1573865526739-10659fec78a5?auto=format&fit=crop&w=800&q=80"),
        ("Pip & Clover", "Rabbit", "Holland Lop", "8 months", "Female", "Small (4 lbs)", "Caramel & White", "Available", 3, 60.0, "985-1410-0934-826", 1, 1, 1, 1, 0, 1, "Litterbox trained, indoor housing only", "Playful, Inquisitive, Binkying Champion, Gentle", "Pip is a friendly Holland lop rabbit who does joyful binkies (twists in midair!) when happy. Loves timothy hay and fresh organic greens.", "https://images.unsplash.com/photo-1585110396000-c9ffd4e4b308?auto=format&fit=crop&w=800&q=80"),
        ("Rocky", "Dog", "Beagle", "5 years", "Male", "Medium (26 lbs)", "Tri-Color", "Adopted", 1, 140.0, "985-1410-0934-827", 1, 1, 1, 1, 1, 0, "None", "Friendly, Scent Detective, Sweet", "Rocky was successfully adopted by the Miller family! He now enjoys a big backyard in Mill Valley.", "https://images.unsplash.com/photo-1505628346881-b72b27e84530?auto=format&fit=crop&w=800&q=80")
    ]
    cursor.executemany('''
        INSERT INTO pets (name, species, breed, age, gender, size, color, status, shelter_id, adoption_fee, microchip, vaccinated, neutered, house_trained, good_with_kids, good_with_dogs, good_with_cats, special_needs, personality, bio, primary_photo)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', pets_data)

    # 4. Seed Pet Gallery Photos
    photos_data = [
        (1, "https://images.unsplash.com/photo-1552053831-71594a27632d?auto=format&fit=crop&w=800&q=80", 1),
        (1, "https://images.unsplash.com/photo-1518717758536-85ae29035b6d?auto=format&fit=crop&w=800&q=80", 0),
        (2, "https://images.unsplash.com/photo-1514888286974-6c03e2ca1dba?auto=format&fit=crop&w=800&q=80", 1),
        (2, "https://images.unsplash.com/photo-1533738363-b7f9aef128ce?auto=format&fit=crop&w=800&q=80", 0),
        (3, "https://images.unsplash.com/photo-1503256207526-0d5d80fa2f47?auto=format&fit=crop&w=800&q=80", 1),
        (4, "https://images.unsplash.com/photo-1583337130417-3346a1be7dee?auto=format&fit=crop&w=800&q=80", 1),
        (5, "https://images.unsplash.com/photo-1573865526739-10659fec78a5?auto=format&fit=crop&w=800&q=80", 1),
        (6, "https://images.unsplash.com/photo-1585110396000-c9ffd4e4b308?auto=format&fit=crop&w=800&q=80", 1),
        (7, "https://images.unsplash.com/photo-1505628346881-b72b27e84530?auto=format&fit=crop&w=800&q=80", 1)
    ]
    cursor.executemany('''
        INSERT INTO pet_photos (pet_id, photo_url, is_primary) VALUES (?, ?, ?)
    ''', photos_data)

    # 5. Seed Applications
    cursor.execute('''
        INSERT INTO adoption_applications (
            tracking_code, pet_id, user_id, applicant_name, applicant_email, applicant_phone, address,
            housing_type, ownership, landlord_approval, has_fenced_yard, fence_height, adults_in_home,
            children_in_home, current_pets, hours_alone, activity_level, vet_reference, motivation, status, notes
        ) VALUES (
            'PAW-78210', 3, 1, 'Samantha Reed', 'adopter@pawpal.org', '(512) 555-8291', '452 Barton Springs Rd, Austin, TX',
            'House with Yard', 'Own', 'N/A', 1, '6-foot wood fence', 2, 0, 'None currently; raised Border Collie for 12 years',
            '3 hours (remote work)', 'Very Active (Trail Running, Hiking)', 'Dr. Davis at Austin City Vet Clinic - (512) 555-0922',
            'We have an active outdoor lifestyle and love herding breeds. Milo will have plenty of exercise and love.',
            'Home Visit Scheduled', 'Stellar vet references verified. Scheduled home walkthrough for Nov 4th.'
        )
    ''')
    app_id = cursor.lastrowid
    
    # Application timeline
    timeline_data = [
        (app_id, "Submitted", "Application received and assigned to coordinator Marcus Vance.", "2026-10-22 14:30:00"),
        (app_id, "Under Review", "Vet reference checked and verified with stellar history.", "2026-10-24 10:15:00"),
        (app_id, "Home Visit Scheduled", "Home visit & meet-and-greet arranged for Nov 4th at 2:00 PM.", "2026-10-27 11:00:00")
    ]
    cursor.executemany('''
        INSERT INTO application_timeline (application_id, status, note, created_at) VALUES (?, ?, ?, ?)
    ''', timeline_data)

    # 6. Seed Finalized Adoption Record & Certificate
    cursor.execute('''
        INSERT INTO adoption_records (
            record_number, application_id, pet_id, adopter_name, adopter_email, adopter_phone,
            adopter_address, shelter_id, shelter_director, microchip_number, rabies_tag_number,
            adoption_fee, fee_status, adoption_date, handover_date, certificate_code
        ) VALUES (
            'REC-2026-0089', NULL, 7, 'Robert & Sarah Miller', 'miller.family@example.com', '(415) 555-9012',
            '520 Cascade Dr, Mill Valley, CA 94941', 1, 'Dr. Sarah Jenkins, DVM', '985-1410-0934-827',
            'CA-SF-RABIES-9921', 140.0, 'Paid in Full', '2026-09-28', '2026-09-28', 'CERT-PAW-998821'
        )
    ''')
    record_id = cursor.lastrowid

    # Follow-ups
    followups_data = [
        (record_id, "Day 7 Check-in", "2026-10-05", "Completed", "Rocky settled into his new bed immediately. Eating well and loves walking in Mill Valley trails.", "2026-10-05 16:00:00"),
        (record_id, "Month 1 Check-in", "2026-10-28", "Completed", "Adopter sent photos. Rocky is deeply bonded with both kids and in excellent physical shape.", "2026-10-28 11:30:00"),
        (record_id, "Month 6 Check-in", "2027-03-28", "Scheduled", "Routine wellness checkup and license renewal confirmation.", None)
    ]
    cursor.executemany('''
        INSERT INTO follow_ups (record_id, milestone, due_date, status, notes, completed_at) VALUES (?, ?, ?, ?, ?, ?)
    ''', followups_data)

    conn.commit()
    conn.close()
    print('Sample PawPal data seeded successfully!')

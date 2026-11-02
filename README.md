# 🐾 PawPal - Digital Pet Adoption Portal

A comprehensive Flask & SQLite platform connecting animal shelters with individuals and families interested in adopting pets.

---

## 🌟 Key Features

1. **Register Pets for Adoption**:
   - Shelter intake form with species, breed, age, size, gender, adoption fee, health flags (vaccinated, spayed/neutered, house-trained), compatibility badges (good with kids, dogs, cats), personality tags, and rescue bio.
2. **Upload Pet Photographs**:
   - File upload supporting JPG/PNG/WEBP files securely saved to `static/uploads/`, plus preset sample image helpers.
3. **Submit Adoption Applications**:
   - Comprehensive 4-part application questionnaire: applicant contact, residence & fenced yard specifications, pet care history & vet contact, and commitment declaration.
   - Generates unique tracking code (e.g., `PAW-78210`).
4. **Track Application Status**:
   - Real-time lookup by Reference Code (`PAW-XXXXX`) or email with a 5-stage visual progress stepper (`Submitted` → `Under Review` → `Home Visit Scheduled` → `Approved` → `Completed`) and coordinator logs.
5. **Manage Adoption Records**:
   - Shelter operations dashboard with applications review queue.
   - Official legal adoption records archive.
   - **Printable Certificate of Adoption** featuring ornate border, verified seal, pet photograph, microchip ID, adopter name, and shelter director signature.
   - Post-adoption follow-up check-in tracker (Day 7, Month 1, Month 6).
   - One-click JSON export.

---

## 🚀 How to Run

### 1. Install Requirements
```bash
pip install -r requirements.txt
```

### 2. Start the Flask Application
```bash
python app.py
```

### 3. Open in Browser
Visit **http://localhost:5000**

You can register a new account as an **Adopter** or as a **Shelter Staff** coordinator directly via the **Join PawPal** page.

---

## 📁 Project Structure

```
pawpal/
├── app.py                     # Main Flask application & routes
├── database.py                # SQLite database helper & schema
├── pawpal.db                  # Pre-seeded SQLite database
├── requirements.txt           # Flask==3.0.0, Werkzeug==3.0.1
├── README.md                  # Project documentation
├── static/
│   ├── css/
│   │   └── style.css          # Design system stylesheet
│   └── uploads/               # Uploaded pet photos
└── templates/
    ├── base.html              # Base navigation, auth state, and footer
    ├── index.html             # Landing page, stats counter, pet directory & filters
    ├── pet_detail.html        # Pet profile with gallery & health checklist
    ├── shelters.html          # Partner shelters directory
    ├── track.html             # Public application status tracker
    ├── login.html             # User sign in page
    ├── register.html          # Register as Adopter or Shelter Staff
    ├── adopter/
    │   ├── dashboard.html     # Adopter portal with submitted applications
    │   └── apply.html         # 4-step adoption application form
    └── shelter/
        ├── dashboard.html     # Shelter director analytics & urgent queue
        ├── register_pet.html  # Pet intake form with photo upload
        ├── manage_pets.html   # Pet roster & status toggle
        ├── view_applications.html # Review applications & update evaluation
        ├── adoption_records.html  # Legal records archive & follow-ups
        └── certificate.html   # Printable Certificate of Adoption
```

---

## 📄 License
MIT License.

import base64
import os
import sys
from datetime import datetime
import pymongo
from cryptography.fernet import Fernet
from dotenv import load_dotenv

load_dotenv()

# --- 1. MONGODB DATABASE CONFIGURATION ---
CONNECTION_STRING = (
    "mongodb+srv://arshjain2004_db_user:5skZud1jkDPg0IUD@cluster0.lwf0rej.mongodb.net/"
    "?retryWrites=true&w=majority&tls=true&tlsAllowInvalidCertificates=true"
)

try:
    client = pymongo.MongoClient(CONNECTION_STRING, serverSelectionTimeoutMS=5000)
    client.admin.command('ping')
    
    db = client['healthcare_system']
    patients_col = db['patients']
    doctors_col = db['doctors']
    records_col = db['medical_records']
    insurance_col = db['insurance_ledgers']
    
    print("✔ Connected successfully to MongoDB Atlas over Hotspot!")
except Exception as e:
    print(f"❌ Database Connection Error: {e}")
    sys.exit(1)


# --- 2. SECURITY & CRYPTOGRAPHY MODULE ---
ENVIRONMENT_KEY = os.getenv("MONGO_CRYPTO_KEY")

if not ENVIRONMENT_KEY:
    print("❌ Critical System Error: Security Key 'MONGO_CRYPTO_KEY' not set in environment.")
    sys.exit(1)

try:
    cipher_suite = Fernet(ENVIRONMENT_KEY.encode())
except Exception as e:
    print(f"❌ Critical System Error: Invalid encryption key format ({e}).")
    sys.exit(1)

def mock_encrypt(text):
    return cipher_suite.encrypt(text.encode()).decode()

def mock_decrypt(enc_text):
    return cipher_suite.decrypt(enc_text.encode()).decode()


# --- 3. ONE-TIME DATABASE SEEDER ---
def seed_database_if_empty():
    """Seeds the database with baseline records without contact strings if empty."""
    if patients_col.count_documents({}) == 0:
        print("\n[System] Cloud database empty. Initializing baseline schemas...")
        
        mock_patients = [
            {"_id": "P101", "name": "Alice Sharma", "age": 29},
            {"_id": "P102", "name": "Bob Reddy", "age": 45},
            {"_id": "P103", "name": "Charlie Khan", "age": 34}
        ]
        mock_doctors = [
            {"_id": "D501", "name": "Dr. Smith", "specialty": "Cardiology"},
            {"_id": "D502", "name": "Dr. Varma", "specialty": "General Medicine"}
        ]
        mock_insurance = [
            {"_id": "P101", "total": 10000, "utilized": 0, "balance": 10000},
            {"_id": "P102", "total": 10000, "utilized": 0, "balance": 10000},
            {"_id": "P103", "total": 10000, "utilized": 0, "balance": 10000}
        ]
        
        patients_col.insert_many(mock_patients)
        doctors_col.insert_many(mock_doctors)
        insurance_col.insert_many(mock_insurance)
        print("✔ Cloud seeding configuration completed.")


def verify_user(user_id, user_type):
    if user_type == "PATIENT":
        return patients_col.find_one({"_id": user_id}) is not None
    elif user_type == "DOCTOR":
        return doctors_col.find_one({"_id": user_id}) is not None
    return False


# --- 4. CORE SYSTEM MODULES ---
def patient_module():
    print("\n--- PATIENT INTERFACE ---")
    print("1. Login (Existing User)")
    print("2. Register (New User)")
    choice = input("Select Option: ")

    if choice == '2':
        print("\n--- NEW PATIENT REGISTRATION ---")
        p_id = input("Create unique Patient ID (e.g., P104): ").strip()
        
        if verify_user(p_id, "PATIENT"):
            print("✖ Error: This Patient ID already exists.")
            return
            
        name = input("Enter Full Name: ").strip()
        try:
            age = int(input("Enter Age: "))
        except ValueError:
            print("✖ Error: Age must be a numerical value.")
            return

        patients_col.insert_one({"_id": p_id, "name": name, "age": age})
        insurance_col.insert_one({"_id": p_id, "total": 10000, "utilized": 0, "balance": 10000})
        print(f"✔ Account Activated! Welcome, {name}. ID: {p_id}")
        return

    elif choice == '1':
        print("\n--- PATIENT LOGIN ---")
        p_id = input("Enter Patient ID: ").strip()

        patient = patients_col.find_one({"_id": p_id})
        if not patient:
            print("✖ Access Denied: Patient ID not found.")
            return

        print(f"\nWelcome back, {patient['name']} (Age: {patient['age']})")
        notes = input("Enter Clinical Notes (Sensitive): ")
        allergies = input("Enter Allergies (comma separated): ").split(",")

        secure_notes = mock_encrypt(notes)

        record = {
            "recordId": f"MR-{datetime.now().strftime('%Y%m%d%H%M')}",
            "patientId": p_id,
            "encryptedNotes": secure_notes,
            "allergies": [a.strip() for a in allergies],
            "timestamp": datetime.now().isoformat()
        }
        records_col.insert_one(record)
        print(f"✔ Medical Record securely synced to Cloud Database.")
    else:
        print("Invalid Selection.")


def doctor_module():
    print("\n--- DOCTOR INTERFACE ---")
    print("1. Login (Existing Doctor)")
    print("2. Register (New Doctor)")
    choice = input("Select Option: ")

    if choice == '2':
        print("\n--- NEW DOCTOR REGISTRATION ---")
        d_id = input("Create unique Doctor ID (e.g., D503): ").strip()
        
        if verify_user(d_id, "DOCTOR"):
            print("✖ Error: This Doctor ID already exists.")
            return
            
        name = input("Enter Full Name (with Dr.): ").strip()
        specialty = input("Enter Medical Department Specialization: ").strip()

        doctors_col.insert_one({"_id": d_id, "name": name, "specialty": specialty})
        print(f"✔ Access Authorized! Added {name} to system registries.")
        return

    elif choice == '1':
        print("\n--- DOCTOR LOGIN ---")
        d_id = input("Enter Doctor ID: ").strip()

        doctor = doctors_col.find_one({"_id": d_id})
        if not doctor:
            print("✖ Access Denied: Unauthorized Doctor ID.")
            return

        print(f"\nAuthorized: {doctor['name']} ({doctor['specialty']})")
        p_id = input("Enter Patient ID to view history: ").strip()

        if not verify_user(p_id, "PATIENT"):
            print("✖ Error: Patient ID not found.")
            return

        results = list(records_col.find({"patientId": p_id}))
        if not results:
            print("No medical history found for this patient.")
            return

        for rec in results:
            decrypted_notes = mock_decrypt(rec['encryptedNotes'])
            print(f"\n[Record ID: {rec['recordId']}] | Date: {rec['timestamp']}")
            print(f"Allergies: {', '.join(rec['allergies'])}")
            print(f"Decrypted Notes: {decrypted_notes}")
    else:
        print("Invalid Selection.")


def insurer_module():
    print("\n--- INSURANCE PROCESSING ---")
    p_id = input("Enter Patient ID to process claim: ").strip()

    ledger = insurance_col.find_one({"_id": p_id})
    patient = patients_col.find_one({"_id": p_id})
    
    if not ledger or not patient:
        print("✖ Error: No insurance profile found for this ID.")
        return

    print(f"Patient: {patient['name']} | Available Balance: ${ledger['balance']}")

    try:
        claim_amount = float(input("Enter claim amount to utilize: "))
        if 0 < claim_amount <= ledger['balance']:
            insurance_col.update_one(
                {"_id": p_id},
                {"$inc": {"utilized": claim_amount, "balance": -claim_amount}}
            )
            updated_ledger = insurance_col.find_one({"_id": p_id})
            print(f"✔ Claim Approved. Remaining Balance: ${updated_ledger['balance']}")
        else:
            print("✖ Invalid Amount or Insufficient Funds.")
    except ValueError:
        print("✖ Error: Please enter a numeric value.")


def balance_check():
    print("\n--- INSURANCE BALANCE INQUIRY ---")
    p_id = input("Enter Patient ID: ").strip()
    
    ledger = insurance_col.find_one({"_id": p_id})
    patient = patients_col.find_one({"_id": p_id})
    
    if ledger and patient:
        print(f"\nSummary for {patient['name']}:")
        print(f"Age: {patient['age']}")
        print(f"Balance: ${ledger['balance']} / Utilized: ${ledger['utilized']}")
    else:
        print("✖ Patient profile or ledger map not found.")


# --- 5. MAIN APPLICATION INTERFACE ---
def main():
    seed_database_if_empty()
    
    while True:
        print("\n=============================================")
        print("--- SECURE CLOUD DIGITAL HEALTH SYSTEM ---")
        print("=============================================")
        print("1. Patient Portal (Login/Register/Log Notes)")
        print("2. Doctor Portal (Login/Register/View History)")
        print("3. Process Insurance Claim (Update Ledger)")
        print("4. Check Balance")
        print("5. Exit")
        choice = input("Select Option: ")

        if choice == '1': patient_module()
        elif choice == '2': doctor_module()
        elif choice == '3': insurer_module()
        elif choice == '4': balance_check()
        elif choice == '5': 
            print("Closing system database connection. Goodbye.")
            client.close()
            break
        else: 
            print("Invalid Choice.")

if __name__ == "__main__":
    main()
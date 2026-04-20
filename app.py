import os
import json
from flask import Flask, request, jsonify
from flask_cors import CORS
import firebase_admin
from firebase_admin import credentials, firestore, auth

# 1. Initialize the Flask App and allow cross-origin requests
app = Flask(__name__)
CORS(app)

# 2. Secure Firebase Initialization
# Look for the secret Environment Variable we will set in Render
firebase_creds = os.environ.get("FIREBASE_CREDENTIALS")

if firebase_creds:
    # We are in the cloud! Load the keys securely from the secret text
    cred_dict = json.loads(firebase_creds)
    cred = credentials.Certificate(cred_dict)
else:
    # We are testing locally. Use the physical file.
    cred = credentials.Certificate("serviceAccountKey.json")

firebase_admin.initialize_app(cred)

# 3. Connect to the Firestore Database
db = firestore.client()

# --- SECURITY MIDDLEWARE ---
# (Keep the rest of your app.py code exactly the same below here!)

# --- SECURITY MIDDLEWARE ---
def verify_token(req):
    """Extracts and verifies the Firebase ID token from the request headers."""
    auth_header = req.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return None
    
    token = auth_header.split('Bearer ')[1]
    try:
        # Firebase decodes the token and extracts the user's UID securely
        decoded_token = auth.verify_id_token(token)
        return decoded_token['uid']
    except Exception as e:
        print(f"Token verification failed: {e}")
        return None

# --- API ENDPOINTS ---

@app.route('/api/data', methods=['GET'])
def get_user_data():
    """Loads the planner data for the logged-in user."""
    uid = verify_token(request)
    if not uid:
        return jsonify({"error": "Unauthorized"}), 401

    try:
        # Look for a document matching the user's UID in the 'users' collection
        doc_ref = db.collection('users').document(uid)
        doc = doc_ref.get()
        
        if doc.exists:
            return jsonify(doc.to_dict()), 200
        else:
            # If the user is new, return a blank slate
            return jsonify({"types": [], "tasks": [], "events": [], "eventOnlyTypes": []}), 200
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/data', methods=['POST'])
def save_user_data():
    """Saves the planner data for the logged-in user."""
    uid = verify_token(request)
    if not uid:
        return jsonify({"error": "Unauthorized"}), 401

    try:
        # Grab the JSON data sent from the frontend
        planner_data = request.json
        
        # Save it directly to the user's document in Firestore
        db.collection('users').document(uid).set(planner_data)
        
        return jsonify({"message": "Data saved successfully"}), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- RUN THE SERVER ---
if __name__ == '__main__':
    # Runs the server on port 5000
    app.run(debug=True, port=5000)
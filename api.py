from flask import Flask, jsonify, request
from flask_cors import CORS
from database import Database
import os

app = Flask(__name__)
CORS(app)
db = Database()
API_KEY = os.getenv('DASHBOARD_API_KEY', 'hanoibox2026')

def auth():
    return (request.args.get('key') or request.headers.get('X-API-Key')) == API_KEY

@app.route('/api/dashboard')
def dashboard():
    if not auth(): return jsonify({'error':'Unauthorized'}), 401
    return jsonify(db.get_dashboard_data())

@app.route('/api/members')
def members():
    if not auth(): return jsonify({'error':'Unauthorized'}), 401
    return jsonify(db.get_active_members())

@app.route('/api/payments')
def payments():
    if not auth(): return jsonify({'error':'Unauthorized'}), 401
    return jsonify(db.get_recent_payments(20))

@app.route('/api/expiring')
def expiring():
    if not auth(): return jsonify({'error':'Unauthorized'}), 401
    days = int(request.args.get('days', 7))
    return jsonify({'expiring': db.get_expiring_members(days), 'expired': db.get_expired_members()})

@app.route('/health')
def health():
    return jsonify({'status': 'ok'})

def run_api():
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 8080)), debug=False)

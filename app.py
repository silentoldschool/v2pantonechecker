import os, uuid
from datetime import datetime
from flask import Flask, request, jsonify, abort
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
CORS(app)  # <--- wichtig für Frontend-Fetch
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL','sqlite:///pantone.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- Models ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    api_token = db.Column(db.String(64), unique=True, index=True)
    role = db.Column(db.String(50), default='user')

class ColorCheck(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    hex_color = db.Column(db.String(16), nullable=True)
    pantone = db.Column(db.String(64))
    notes = db.Column(db.Text)
    status = db.Column(db.String(32), default='pending')  # pending, approved, rejected
    points = db.Column(db.String(256))  # CSV der Punkte
    alternative_hex = db.Column(db.String(16), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref='checks')

# --- Auth Helper ---
def token_auth():
    token = request.headers.get('X-API-TOKEN') or request.headers.get('Authorization')
    if token and token.startswith('Token '):
        token = token.split(' ',1)[1]
    if not token:
        abort(401, 'token missing')
    user = User.query.filter_by(api_token=token).first()
    if not user:
        abort(401, 'invalid token')
    return user

# --- Login ---
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    username = data.get('username')
    password = data.get('password')
    if not username or not password:
        return jsonify({'error':'username and password required'}), 400
    user = User.query.filter_by(username=username).first()
    if not user or not check_password_hash(user.password_hash, password):
        return jsonify({'error':'invalid credentials'}), 401
    if not user.api_token:
        user.api_token = uuid.uuid4().hex
        db.session.commit()
    return jsonify({'token': user.api_token})

# --- ColorCheck Endpunkte ---
@app.route('/colorchecks', methods=['POST'])
def add_check():
    user = token_auth()
    data = request.get_json() or {}
    hex_color = data.get('hex_color')
    pantone = data.get('pantone')
    notes = data.get('notes')
    points = data.get('points', [])
    if not pantone:
        return jsonify({'error':'pantone required'}), 400
    cc = ColorCheck(
        hex_color=hex_color,
        pantone=pantone.upper().replace(' ', ''),
        notes=notes,
        user_id=user.id,
        points=','.join(points),
        status='approved' if user.role=='admin' else 'pending'
    )
    db.session.add(cc)
    db.session.commit()
    return jsonify({'id': cc.id, 'created_at': cc.created_at.isoformat()}), 201

@app.route('/colorchecks', methods=['GET'])
def list_checks():
    user = token_auth()
    q = ColorCheck.query
    if user.role != 'admin':
        q = q.filter_by(user_id=user.id)
    entries = q.order_by(ColorCheck.created_at.desc()).limit(200).all()
    result = []
    for e in entries:
        result.append({
            'id': e.id,
            'hex_color': e.hex_color,
            'pantone': e.pantone,
            'notes': e.notes,
            'status': e.status,
            'points': e.points.split(',') if e.points else [],
            'alternative_hex': e.alternative_hex,
            'created_at': e.created_at.isoformat(),
            'user': e.user.username
        })
    return jsonify(result)

# --- Farb-Anfrage Endpunkt ---
@app.route('/colorchecks/request', methods=['POST'])
def request_color():
    user = token_auth()
    data = request.get_json() or {}
    pantone = data.get('pantone')
    points = data.get('points', [])
    alternative_hex = data.get('alternative_hex')
    if not pantone:
        return jsonify({'error': 'Pantone required'}), 400

    cc = ColorCheck(
        hex_color='',  # wird automatisch generiert
        pantone=pantone.upper().replace(' ', ''),
        notes='',
        user_id=user.id,
        status='pending',
        points=','.join(points),
        alternative_hex=alternative_hex
    )
    try:
        db.session.add(cc)
        db.session.commit()
        return jsonify({'status': 'ok', 'message': 'Color request saved', 'id': cc.id})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# --- Userverwaltung ---
@app.route('/users', methods=['GET'])
def list_users():
    user = token_auth()
    if user.role != 'admin':
        abort(403)
    users = User.query.all()
    return jsonify([{'id':u.id,'username':u.username,'role':u.role,'api_token':u.api_token} for u in users])

@app.route('/users', methods=['POST'])
def add_user():
    user = token_auth()
    if user.role != 'admin':
        abort(403)
    data = request.get_json() or {}
    username = data.get('username')
    password = data.get('password')
    role = data.get('role', 'user')
    if not username or not password:
        return jsonify({'error':'username and password required'}), 400
    if User.query.filter_by(username=username).first():
        return jsonify({'error':'username exists'}), 400
    new_user = User(
        username=username,
        password_hash=generate_password_hash(password),
        api_token=uuid.uuid4().hex,
        role=role
    )
    db.session.add(new_user)
    db.session.commit()
    return jsonify({'status':'ok','username':new_user.username,'api_token':new_user.api_token})

# --- Beispiel Endpunkte ---
@app.route("/")
def index():
    return "PantoneChecker läuft erfolgreich 🚀"

@app.route("/colors")
def colors():
    return {"status": "ok", "message": "Hier kommen später die Farben."}

# --- DB initialisieren ---
with app.app_context():
    db.create_all()
    if not User.query.filter_by(username="admin").first():
        admin = User(
            username="admin",
            password_hash=generate_password_hash("admin123"),
            api_token=uuid.uuid4().hex,
            role="admin"
        )
        db.session.add(admin)
        db.session.commit()
        print("Admin-User erstellt:", admin.username, "Token:", admin.api_token)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080)

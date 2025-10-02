import os, uuid
from datetime import datetime
from flask import Flask, request, jsonify, abort, render_template
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_cors import CORS

app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app)  # erlaubt Frontend Zugriff auf API

app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL','sqlite:///pantone.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# ------------------ MODELS ------------------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    api_token = db.Column(db.String(64), unique=True, index=True)
    role = db.Column(db.String(50), default='user')

class ColorCheck(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    hex_color = db.Column(db.String(16))
    pantone = db.Column(db.String(16), nullable=False)
    points = db.Column(db.String(200))  # z.B. Testliner weiß, Kraftliner braun
    status = db.Column(db.String(50), default='requested')  # requested / approved / rejected
    alt_color = db.Column(db.String(16))  # falls Farbe nicht passt
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    user = db.relationship('User', backref='checks')

# ------------------ AUTH ------------------
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

# ------------------ ROUTES ------------------
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/login", methods=['POST'])
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
    return jsonify({'token': user.api_token, 'role': user.role})

@app.route('/colorchecks/request', methods=['POST'])
def request_color():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No JSON received'}), 400

    # Beispiel: erstelle eine neue Anfrage
    try:
        hex_color = data.get('hex_color')
        pantone = data.get('pantone')
        # ... weitere Logik hier

        return jsonify({'status': 'ok', 'message': 'Request saved'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route("/colorchecks", methods=['GET'])
def list_checks():
    user = token_auth()
    if user.role == 'admin':
        entries = ColorCheck.query.order_by(ColorCheck.created_at.desc()).all()
    else:
        entries = ColorCheck.query.filter_by(user_id=user.id).order_by(ColorCheck.created_at.desc()).all()
    result = []
    for e in entries:
        result.append({
            'id': e.id,
            'pantone': e.pantone,
            'hex_color': e.hex_color,
            'points': e.points.split(','),
            'status': e.status,
            'alt_color': e.alt_color,
            'user': e.user.username
        })
    return jsonify(result)

@app.route("/users", methods=['GET'])
def list_users():
    user = token_auth()
    if user.role != 'admin':
        abort(403)
    users = User.query.all()
    return jsonify([{'id':u.id,'username':u.username,'role':u.role} for u in users])

# ------------------ INIT DB ------------------
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

# ------------------ RUN ------------------
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080)


import os
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from pymongo import MongoClient
from datetime import datetime
from bson import ObjectId

app = Flask(__name__)
CORS(app)

# ✅ SQLite Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# ✅ MongoDB Connection Function (Fix for Fork Issues & SSL)
def get_mongo_collection():
    MONGO_URI = os.getenv("MONGO_URI")
    if not MONGO_URI:
        raise ValueError("MONGO_URI environment variable is not set!")
    client = MongoClient(MONGO_URI, tls=True)
    return client["API_TEST"]["items"], client["API_TEST"]["logs"]

# ✅ SQLite Model
class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255), nullable=False)

# Create database tables
with app.app_context():
    db.create_all()

def log_activity(action, details):
    """Logs API activity in MongoDB and prints it to the terminal."""
    mongo_collection, mongo_logs = get_mongo_collection()
    log_entry = {
        "action": action,
        "details": details,
        "timestamp": datetime.utcnow()
    }
    mongo_logs.insert_one(log_entry)
    print(f"[LOG] {log_entry['timestamp']} - {log_entry['action']}: {log_entry['details']}")

# ------------------- CRUD Operations for SQLite -------------------
@app.route('/sqlite/items', methods=['POST'])
def create_sqlite_item():
    data = request.json
    new_item = Item(name=data['name'], description=data['description'])
    db.session.add(new_item)
    db.session.commit()
    log_activity("CREATE_SQLITE", f"Item '{data['name']}' added to SQLite.")
    return jsonify({"message": "SQLite item created!"}), 201

@app.route('/sqlite/items', methods=['GET'])
def get_sqlite_items():
    items = Item.query.all()
    log_activity("READ_SQLITE", "Fetched all items from SQLite.")
    return jsonify([{ "id": item.id, "name": item.name, "description": item.description } for item in items])

# ------------------- CRUD Operations for MongoDB -------------------
@app.route('/mongo/items', methods=['POST'])
def create_mongo_item():
    data = request.json
    mongo_collection, _ = get_mongo_collection()
    new_item = {"name": data["name"], "description": data["description"]}
    mongo_collection.insert_one(new_item)
    log_activity("CREATE_MONGO", f"Item '{data['name']}' added to MongoDB.")
    return jsonify({"message": "MongoDB item created!"}), 201

@app.route('/mongo/items', methods=['GET'])
def get_mongo_items():
    mongo_collection, _ = get_mongo_collection()
    items = list(mongo_collection.find({}, {"_id": 0}))
    log_activity("READ_MONGO", "Fetched all items from MongoDB.")
    return jsonify(items), 200

@app.route('/mongo/items/<string:item_id>', methods=['GET'])
def get_mongo_item_by_id(item_id):
    """Fetch a specific MongoDB item by its ObjectId."""
    try:
        mongo_collection, _ = get_mongo_collection()
        item = mongo_collection.find_one({"_id": ObjectId(item_id)}, {"_id": 0})
        if item:
            log_activity("READ_MONGO", f"Fetched item with ID {item_id} from MongoDB.")
            return jsonify(item), 200
        else:
            return jsonify({"error": "Item not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ------------------- Activity Logs Endpoint -------------------
@app.route('/logs', methods=['GET'])
def get_logs():
    """Fetch all logs from MongoDB."""
    _, mongo_logs = get_mongo_collection()
    logs = list(mongo_logs.find({}, {"_id": 0}))
    return jsonify(logs), 200

# ✅ Run the API using Gunicorn for production
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000, debug=True)

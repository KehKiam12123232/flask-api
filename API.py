from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from pymongo import MongoClient
from datetime import datetime
from bson import ObjectId  # Import ObjectId to handle MongoDB IDs

app = Flask(__name__)
CORS(app)  # Allows API access from different networks

# ✅ SQLite Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# ✅ MongoDB Atlas Configuration
MONGO_URI = "mongodb+srv://marlou23:marlou456@cluster1.43wso.mongodb.net/API_TEST.items?retryWrites=true&w=majority"
mongo_client = MongoClient(MONGO_URI)
mongo_db = mongo_client["API_TEST"]
mongo_collection = mongo_db["items"]
mongo_logs = mongo_db["logs"]  # New collection for logging

# ✅ SQLite Model
class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255), nullable=False)

# Create the database tables
with app.app_context():
    db.create_all()

def log_activity(action, details):
    """Logs API activity in MongoDB and prints it to the terminal."""
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
    new_item = {"name": data["name"], "description": data["description"]}
    mongo_collection.insert_one(new_item)
    log_activity("CREATE_MONGO", f"Item '{data['name']}' added to MongoDB.")
    return jsonify({"message": "MongoDB item created!"}), 201

@app.route('/mongo/items', methods=['GET'])
def get_mongo_items():
    items = list(mongo_collection.find({}, {"_id": 0}))
    log_activity("READ_MONGO", "Fetched all items from MongoDB.")
    return jsonify(items), 200

@app.route('/mongo/items/<string:item_id>', methods=['GET'])
def get_mongo_item_by_id(item_id):
    """Fetch a specific MongoDB item by its ObjectId."""
    try:
        # Convert the string ID to ObjectId
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
    logs = list(mongo_logs.find({}, {"_id": 0}))
    return jsonify(logs), 200

# ✅ Run the API
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)  # Accessible over a network

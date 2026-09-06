from flask import Flask, jsonify, request, send_from_directory
import json
import os
import time

app = Flask(__name__, static_folder='static', static_url_path='/static')

DATA_FILE = 'data.json'


def load_data():
    if not os.path.exists(DATA_FILE):
        return {"profiles": [], "decks": [], "last_updated": 0}
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


@app.route('/')
def index():
    return send_from_directory('static', 'index.html')


@app.route('/manifest.json')
def manifest():
    return send_from_directory('static', 'manifest.json')


@app.route('/service-worker.js')
def service_worker():
    return send_from_directory('static', 'service-worker.js', mimetype='application/javascript')


@app.route('/api/data', methods=['GET'])
def get_data():
    return jsonify(load_data())


@app.route('/api/data', methods=['POST'])
def post_data():
    incoming = request.get_json()
    if incoming is None:
        return jsonify({"error": "invalid json"}), 400
    incoming['last_updated'] = int(time.time() * 1000)
    save_data(incoming)
    return jsonify({"status": "ok", "last_updated": incoming['last_updated']})


if __name__ == '__main__':
    if not os.path.exists(DATA_FILE):
        save_data({"profiles": [], "decks": [], "last_updated": 0})
    app.run(debug=True, host='0.0.0.0', port=5000)
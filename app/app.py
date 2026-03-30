from flask import Flask, request, jsonify
import psycopg2, os, redis, json, time, threading
from prometheus_client import Counter, Histogram, start_http_server

app = Flask(__name__)

# Connexion PostgreSQL
def get_db():
    return psycopg2.connect(
        host=os.environ['DB_HOST'],
        database=os.environ['DB_NAME'],
        user=os.environ['DB_USER'],
        password=os.environ['DB_PASSWORD']
    )

# Connexion Redis
cache = redis.Redis(
    host=os.environ.get('REDIS_HOST', 'redis'),
    port=6379,
    decode_responses=True
)

# Métriques Prometheus
REQUEST_COUNT = Counter(
    'flask_http_request_total',
    'Total des requêtes HTTP',
    ['method', 'endpoint', 'status']
)
REQUEST_LATENCY = Histogram(
    'flask_http_request_duration_seconds',
    'Latence des requêtes HTTP',
    ['method', 'endpoint']
)

# ============ ROUTES ============

@app.route('/tasks', methods=['GET'])
def get_tasks():
    start = time.time()
    cached = cache.get('tasks_list')
    if cached:
        REQUEST_COUNT.labels('GET', '/tasks', '200').inc()
        REQUEST_LATENCY.labels('GET', '/tasks').observe(time.time() - start)
        return jsonify(json.loads(cached))
    conn = get_db()
    cur = conn.cursor()
    cur.execute('SELECT id, title, done FROM tasks')
    tasks = [{'id': r[0], 'title': r[1], 'done': r[2]}
             for r in cur.fetchall()]
    cur.close()
    conn.close()
    cache.setex('tasks_list', 60, json.dumps(tasks))
    REQUEST_COUNT.labels('GET', '/tasks', '200').inc()
    REQUEST_LATENCY.labels('GET', '/tasks').observe(time.time() - start)
    return jsonify(tasks)

@app.route('/tasks', methods=['POST'])
def create_task():
    start = time.time()
    data = request.get_json(force=True)
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        'INSERT INTO tasks (title) VALUES (%s) RETURNING id',
        (data['title'],)
    )
    task_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    cache.delete('tasks_list')
    REQUEST_COUNT.labels('POST', '/tasks', '201').inc()
    REQUEST_LATENCY.labels('POST', '/tasks').observe(time.time() - start)
    return jsonify({'id': task_id}), 201

@app.route('/tasks/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    start = time.time()
    conn = get_db()
    cur = conn.cursor()
    cur.execute('DELETE FROM tasks WHERE id = %s', (task_id,))
    conn.commit()
    cur.close()
    conn.close()
    cache.delete('tasks_list')
    REQUEST_COUNT.labels('DELETE', '/tasks', '200').inc()
    REQUEST_LATENCY.labels('DELETE', '/tasks').observe(time.time() - start)
    return jsonify({'message': 'Task deleted'}), 200

@app.route('/health')
def health():
    return jsonify({'status': 'ok'}), 200

@app.route('/visits')
def visits():
    count = cache.incr('visit_counter')
    return jsonify({'visits': count})

if __name__ == '__main__':
    # Démarrer le serveur métriques sur port 8000 dans un thread séparé
    start_http_server(8000)
    print("Serveur métriques Prometheus démarré sur port 8000")
    app.run(host='0.0.0.0', port=5000, debug=False)
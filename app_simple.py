import os
from flask import Flask, jsonify

app = Flask(__name__)

# Configuração básica
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'pcp-secret')

@app.route('/')
def index():
    return jsonify({
        "status": "ok",
        "message": "PCP Web API - Servidor rodando com sucesso!",
        "database": "PostgreSQL" if os.environ.get('DATABASE_URL') else "SQLite"
    })

@app.route('/health')
def health():
    return jsonify({"status": "healthy"}), 200

@app.route('/api/dashboard')
def api_dashboard():
    return jsonify({
        "total_obras": 0,
        "total_ops": 0,
        "total_apontamentos": 0,
        "maquinas_producao": []
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

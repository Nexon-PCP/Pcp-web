"""
Script de teste para a rota /apresentacao
Execute este arquivo para testar se a rota está funcionando
"""

from flask import Flask, render_template, jsonify

app = Flask(__name__, template_folder='templates')

# Rota de apresentação
@app.route("/apresentacao")
def apresentacao():
    """Modo apresentação - tela cheia que muda a cada 10 segundos"""
    print("[TESTE] Acessando rota /apresentacao")
    return render_template("apresentacao.html")


# API de dados
@app.route("/api/apresentacao")
def api_apresentacao():
    """API que retorna dados para o modo apresentação"""
    print("[TESTE] Acessando API /api/apresentacao")
    
    return jsonify({
        'dashboard': {
            'total_obras': 5,
            'obras_ativas': 3,
            'total_ops': 12,
            'ops_em_producao': 8,
            'tarefas_concluidas': 45,
            'tarefas_em_execucao': 23,
            'tarefas_planejadas': 15,
            'progresso_medio': 65.5
        },
        'obras': [
            {'codigo': 'OB001', 'nome': 'Obra 1', 'cliente': 'Cliente A', 'status': 'ATIVA', 'total_ops': 3},
            {'codigo': 'OB002', 'nome': 'Obra 2', 'cliente': 'Cliente B', 'status': 'ATIVA', 'total_ops': 5},
        ],
        'ops': [
            {'id': 'OP001', 'produto': 'Produto A', 'cliente': 'Cliente A', 'quantidade': 100, 'percentual': 75.0, 'status': 'EM_EXECUCAO'},
            {'id': 'OP002', 'produto': 'Produto B', 'cliente': 'Cliente B', 'quantidade': 50, 'percentual': 50.0, 'status': 'EM_EXECUCAO'},
        ]
    })


if __name__ == '__main__':
    print("=" * 60)
    print("🧪 TESTE DE APRESENTAÇÃO")
    print("=" * 60)
    print("\n✅ Rotas disponíveis:")
    print("   - http://192.168.2.101:5000/apresentacao")
    print("   - http://192.168.2.101:5000/api/apresentacao")
    print("\n🔄 Pressione CTRL+C para parar\n")
    print("=" * 60 + "\n")
    
    app.run(host='0.0.0.0', port=5000, debug=True)

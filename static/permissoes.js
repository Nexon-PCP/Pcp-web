/**
 * Sistema de Permissões - JavaScript
 * Mostra mensagens amigáveis quando usuário tenta acessar recursos sem permissão
 */

// Função para mostrar mensagem de aviso
function mostrarMensagemPermissao(mensagem) {
    // Remover mensagem anterior se existir
    const msgAnterior = document.querySelector('.alerta-permissao');
    if (msgAnterior) {
        msgAnterior.remove();
    }
    
    // Criar elemento de alerta
    const alerta = document.createElement('div');
    alerta.className = 'alerta-permissao';
    alerta.innerHTML = `
        <div class="alerta-conteudo">
            <span class="alerta-icone">🔒</span>
            <span class="alerta-texto">${mensagem}</span>
            <button class="alerta-fechar" onclick="this.parentElement.parentElement.remove()">×</button>
        </div>
    `;
    
    // Inserir no topo da página
    document.body.insertBefore(alerta, document.body.firstChild);
    
    // Auto-remover após 5 segundos
    setTimeout(() => {
        if (alerta.parentElement) {
            alerta.remove();
        }
    }, 5000);
}

// Função para desabilitar botão sem permissão
function desabilitarBotaoSemPermissao(botaoId, mensagem) {
    const botao = document.getElementById(botaoId);
    if (botao) {
        botao.disabled = true;
        botao.style.opacity = '0.5';
        botao.style.cursor = 'not-allowed';
        botao.title = mensagem;
        
        // Adicionar evento de clique para mostrar mensagem
        botao.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            mostrarMensagemPermissao(mensagem);
        });
    }
}

// Função para verificar permissão e desabilitar botões
function verificarPermissoes(usuarioTipo) {
    const permissoes = {
        'ADMIN': ['criar-obra', 'deletar-obra', 'criar-op', 'deletar-op', 'criar-tarefa', 'editar-tarefa'],
        'GERENTE': ['criar-op', 'criar-tarefa', 'editar-tarefa'],
        'OPERADOR': ['editar-tarefa'],
        'VISUALIZADOR': []
    };
    
    const acoesPermitidas = permissoes[usuarioTipo] || [];
    
    // Desabilitar botões sem permissão
    const botoes = document.querySelectorAll('[data-acao]');
    botoes.forEach(botao => {
        const acao = botao.getAttribute('data-acao');
        if (!acoesPermitidas.includes(acao)) {
            const mensagem = botao.getAttribute('data-mensagem') || 'Você não tem permissão para esta ação';
            desabilitarBotaoSemPermissao(botao.id, mensagem);
        }
    });
}

// Executar quando página carregar
document.addEventListener('DOMContentLoaded', () => {
    // Obter tipo de usuário da sessão (armazenado em data-usuario-tipo no body)
    const usuarioTipo = document.body.getAttribute('data-usuario-tipo');
    if (usuarioTipo) {
        verificarPermissoes(usuarioTipo);
    }
});

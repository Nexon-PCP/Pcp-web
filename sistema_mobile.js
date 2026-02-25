/**
 * SISTEMA PCP/SAP - MOBILE RESPONSIVO
 * JavaScript para menu hambúrguer e interações mobile
 * VERSÃO CORRIGIDA - USA CLASSE .show
 */

(function() {
  'use strict';

  // Aguardar DOM carregar
  document.addEventListener('DOMContentLoaded', function() {
    
    // ===== CRIAR BOTÃO HAMBÚRGUER =====
    criarBotaoHamburguer();
    
    // ===== CONFIGURAR MENU MOBILE =====
    configurarMenuMobile();
    
    // ===== MELHORIAS DE UX MOBILE =====
    configurarScrollTabelas();
    configurarFechamentoAutomatico();
    
  });

  /**
   * Criar botão hambúrguer dinamicamente
   */
  function criarBotaoHamburguer() {
    // Verificar se já existe
    if (document.querySelector('.menu-toggle')) {
      return;
    }

    // Criar botão
    var btnHamburguer = document.createElement('button');
    btnHamburguer.className = 'menu-toggle';
    btnHamburguer.setAttribute('aria-label', 'Abrir menu');
    btnHamburguer.innerHTML = '☰';
    
    // Inserir no início do body
    document.body.insertBefore(btnHamburguer, document.body.firstChild);
    
    // Adicionar evento de clique
    btnHamburguer.addEventListener('click', toggleSidebar);
  }

  /**
   * Alternar visibilidade da sidebar
   */
  function toggleSidebar() {
    var sidebar = document.querySelector('.side');
    var overlay = document.querySelector('.menu-overlay');
    
    if (!sidebar) {
      console.warn('Sidebar não encontrada');
      return;
    }
    
    // Alternar classe 'show' (não 'active')
    sidebar.classList.toggle('show');
    
    // Criar/remover overlay
    if (sidebar.classList.contains('show')) {
      criarOverlay();
    } else {
      removerOverlay();
    }
  }

  /**
   * Criar overlay escuro atrás da sidebar
   */
  function criarOverlay() {
    // Verificar se já existe
    var overlay = document.querySelector('.menu-overlay');
    if (overlay) {
      overlay.classList.add('show');
      return;
    }
    
    // Criar novo overlay
    overlay = document.createElement('div');
    overlay.className = 'menu-overlay show';
    
    // Fechar ao clicar no overlay
    overlay.addEventListener('click', function() {
      toggleSidebar();
    });
    
    document.body.appendChild(overlay);
  }

  /**
   * Remover overlay
   */
  function removerOverlay() {
    var overlay = document.querySelector('.menu-overlay');
    if (overlay) {
      overlay.classList.remove('show');
    }
  }

  /**
   * Configurar comportamento do menu mobile
   */
  function configurarMenuMobile() {
    var sidebar = document.querySelector('.side');
    if (!sidebar) return;
    
    // Fechar sidebar ao clicar em um link (apenas em mobile)
    var links = sidebar.querySelectorAll('.nav a');
    links.forEach(function(link) {
      link.addEventListener('click', function() {
        // Verificar se está em mobile (largura < 768px)
        if (window.innerWidth < 768) {
          setTimeout(function() {
            toggleSidebar();
          }, 200); // Pequeno delay para feedback visual
        }
      });
    });
    
    // Fechar sidebar ao pressionar ESC
    document.addEventListener('keydown', function(e) {
      if (e.key === 'Escape' && sidebar.classList.contains('show')) {
        toggleSidebar();
      }
    });
  }

  /**
   * Configurar scroll horizontal em tabelas
   */
  function configurarScrollTabelas() {
    var tabelas = document.querySelectorAll('table');
    
    tabelas.forEach(function(tabela) {
      // Verificar se já está dentro de um wrapper responsivo
      if (tabela.parentElement.classList.contains('table-responsive')) {
        return;
      }
      
      // Criar wrapper responsivo
      var wrapper = document.createElement('div');
      wrapper.className = 'table-responsive';
      wrapper.style.cssText = 'overflow-x:auto;-webkit-overflow-scrolling:touch;margin-bottom:20px;';
      
      // Envolver tabela
      tabela.parentNode.insertBefore(wrapper, tabela);
      wrapper.appendChild(tabela);
    });
  }

  /**
   * Fechar sidebar automaticamente ao redimensionar para desktop
   */
  function configurarFechamentoAutomatico() {
    var sidebar = document.querySelector('.side');
    if (!sidebar) return;
    
    window.addEventListener('resize', function() {
      // Se redimensionar para desktop (>= 768px), fechar sidebar
      if (window.innerWidth >= 768 && sidebar.classList.contains('show')) {
        sidebar.classList.remove('show');
        removerOverlay();
      }
    });
  }

  /**
   * Prevenir scroll do body quando sidebar está aberta (mobile)
   */
  function prevenirScrollBody() {
    var sidebar = document.querySelector('.side');
    if (!sidebar) return;
    
    // Observar mudanças na classe 'show'
    var observer = new MutationObserver(function(mutations) {
      mutations.forEach(function(mutation) {
        if (mutation.attributeName === 'class') {
          if (sidebar.classList.contains('show') && window.innerWidth < 768) {
            document.body.style.overflow = 'hidden';
          } else {
            document.body.style.overflow = '';
          }
        }
      });
    });
    
    observer.observe(sidebar, { attributes: true });
  }

  // Iniciar prevenção de scroll
  prevenirScrollBody();

})();

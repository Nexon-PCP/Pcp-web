// Script para colorir badges de status automaticamente
document.addEventListener('DOMContentLoaded', function() {
  // Encontrar todos os badges
  const badges = document.querySelectorAll('.badge');
  
  badges.forEach(badge => {
    const texto = badge.textContent.trim().toUpperCase();
    
    // Remover classes de status anteriores
    badge.classList.remove(
      'status-aberta',
      'status-em-execucao',
      'status-concluida',
      'status-pausada',
      'status-planejado',
      'status-pausado',
      'status-concluido',
      'status-atrasada'
    );
    
    // Adicionar classe baseada no status
    if (texto.includes('ABERTA')) {
      badge.classList.add('status-aberta');
    } else if (texto.includes('EM_EXECUCAO') || texto.includes('EM EXECUCAO')) {
      badge.classList.add('status-em-execucao');
    } else if (texto.includes('CONCLUIDA')) {
      badge.classList.add('status-concluida');
    } else if (texto.includes('CONCLUIDO')) {
      badge.classList.add('status-concluido');
    } else if (texto.includes('PAUSADA')) {
      badge.classList.add('status-pausada');
    } else if (texto.includes('PAUSADO')) {
      badge.classList.add('status-pausado');
    } else if (texto.includes('PLANEJADO')) {
      badge.classList.add('status-planejado');
    } else if (texto.includes('ATRASADA')) {
      badge.classList.add('status-atrasada');
    }
  });
});

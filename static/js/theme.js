/**
 * TIPIKUS - GESTION DU THÈME DARK/LIGHT
 * Sauvegarde la préférence dans localStorage
 */

(function() {
  'use strict';
  
  const THEME_KEY = 'tipikus_theme';
  const THEME_LIGHT = 'light';
  const THEME_DARK = 'dark';
  
  /**
   * Récupère le thème sauvegardé ou celui du système
   */
  function getSavedTheme() {
    const saved = localStorage.getItem(THEME_KEY);
    if (saved) return saved;
    
    // Détection du thème système
    if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
      return THEME_DARK;
    }
    
    return THEME_LIGHT;
  }
  
  /**
   * Applique le thème
   */
  function applyTheme(theme) {
    const root = document.documentElement;
    
    if (theme === THEME_DARK) {
      root.setAttribute('data-theme', 'dark');
    } else {
      root.removeAttribute('data-theme');
    }
    
    // Mettre à jour l'icône du bouton toggle
    updateThemeIcon(theme);
  }
  
  /**
   * Met à jour l'icône du bouton toggle
   */
  function updateThemeIcon(theme) {
    const toggleBtn = document.querySelector('.theme-toggle');
    if (!toggleBtn) return;
    
    const icon = toggleBtn.querySelector('.theme-icon');
    if (!icon) return;
    
    if (theme === THEME_DARK) {
      icon.textContent = '☀️';
      toggleBtn.setAttribute('aria-label', 'Passer en mode clair');
      toggleBtn.setAttribute('title', 'Mode clair');
    } else {
      icon.textContent = '🌙';
      toggleBtn.setAttribute('aria-label', 'Passer en mode sombre');
      toggleBtn.setAttribute('title', 'Mode sombre');
    }
  }
  
  /**
   * Sauvegarde le thème
   */
  function saveTheme(theme) {
    localStorage.setItem(THEME_KEY, theme);
  }
  
  /**
   * Toggle le thème
   */
  function toggleTheme() {
    const currentTheme = getSavedTheme();
    const newTheme = currentTheme === THEME_DARK ? THEME_LIGHT : THEME_DARK;
    
    applyTheme(newTheme);
    saveTheme(newTheme);
  }
  
  /**
   * Initialisation au chargement de la page
   */
  function init() {
    // Appliquer le thème sauvegardé immédiatement
    const theme = getSavedTheme();
    applyTheme(theme);
    
    // Attacher l'événement au bouton toggle
    document.addEventListener('DOMContentLoaded', function() {
      const toggleBtn = document.querySelector('.theme-toggle');
      
      if (toggleBtn) {
        toggleBtn.addEventListener('click', toggleTheme);
        
        // Ajouter un effet de transition
        toggleBtn.addEventListener('click', function() {
          this.style.transform = 'rotate(360deg)';
          setTimeout(() => {
            this.style.transform = '';
          }, 300);
        });
      }
      
      // Écouter les changements du thème système
      if (window.matchMedia) {
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', function(e) {
          // Ne changer que si l'utilisateur n'a pas de préférence sauvegardée
          if (!localStorage.getItem(THEME_KEY)) {
            const newTheme = e.matches ? THEME_DARK : THEME_LIGHT;
            applyTheme(newTheme);
          }
        });
      }
    });
  }
  
  // Exposer les fonctions globalement si nécessaire
  window.TipikusTheme = {
    toggle: toggleTheme,
    set: function(theme) {
      applyTheme(theme);
      saveTheme(theme);
    },
    get: getSavedTheme
  };
  
  // Initialiser
  init();
})();
#!/usr/bin/env python3
"""
Tipikus OAuth Configuration Checker
====================================
Vérifie que toutes les configurations OAuth sont correctes
"""

import os
from dotenv import load_dotenv

def check_env_var(name, min_length=10):
    """Vérifie qu'une variable d'environnement existe et a une longueur minimale"""
    value = os.getenv(name)
    
    if not value:
        return False, "❌ MANQUANT"
    
    if len(value) < min_length:
        return False, f"⚠️  TROP COURT ({len(value)} chars)"
    
    return True, f"✅ OK ({len(value)} chars)"


def main():
    # Charger les variables d'environnement
    load_dotenv()
    
    print("=" * 70)
    print("🔍 VÉRIFICATION DE LA CONFIGURATION OAUTH - TIPIKUS")
    print("=" * 70)
    print()
    
    # Liste des variables à vérifier
    configs = [
        ("SECRET_KEY", 20, "Clé secrète Flask"),
        ("GOOGLE_CLIENT_ID", 30, "Google Client ID"),
        ("GOOGLE_CLIENT_SECRET", 15, "Google Client Secret"),
        ("GITHUB_CLIENT_ID", 15, "GitHub Client ID"),
        ("GITHUB_CLIENT_SECRET", 20, "GitHub Client Secret"),
        ("APP_URL", 10, "URL de l'application"),
    ]
    
    all_ok = True
    
    for var_name, min_len, description in configs:
        ok, status = check_env_var(var_name, min_len)
        
        if not ok:
            all_ok = False
        
        print(f"{description:30} : {status}")
        
        # Afficher un extrait de la valeur (masqué)
        if ok:
            value = os.getenv(var_name)
            if len(value) > 20:
                preview = value[:10] + "..." + value[-7:]
            else:
                preview = value[:5] + "..." + value[-3:]
            print(f"{'':30}   → {preview}")
    
    print()
    print("=" * 70)
    
    if all_ok:
        print("✅ CONFIGURATION COMPLÈTE - Prêt à démarrer l'application !")
        print()
        print("Prochaines étapes :")
        print("  1. python3 app.py")
        print("  2. Ouvrir http://localhost:5000/login")
        print("  3. Tester les 3 méthodes de connexion")
    else:
        print("❌ CONFIGURATION INCOMPLÈTE")
        print()
        print("Actions requises :")
        print("  1. Créer un fichier .env à la racine du projet")
        print("  2. Suivre le guide OAUTH_SETUP_GUIDE.md")
        print("  3. Relancer ce script : python3 check_oauth_config.py")
    
    print("=" * 70)
    print()
    
    return all_ok


if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)
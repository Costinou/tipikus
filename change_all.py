#!/usr/bin/env python3
"""
Diagnostic des imports database dans app.py
"""

import re
import sys

def check_imports_in_file(filepath):
    """Vérifie quels imports database sont présents dans le fichier"""
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        print(f"❌ Fichier non trouvé: {filepath}")
        return False
    
    print("=" * 70)
    print(f"🔍 ANALYSE DES IMPORTS - {filepath}")
    print("=" * 70)
    print()
    
    # Fonctions qui doivent être importées pour OAuth
    required_functions = [
        'authenticate_local',
        'authenticate_oauth',
        'get_user_by_id',
        'get_user_by_email',
        'create_user',
        'add_auth_provider',
        'update_password',
    ]
    
    # Chercher la ligne d'import depuis database
    import_pattern = r'from database import \((.*?)\)'
    match = re.search(import_pattern, content, re.DOTALL)
    
    if not match:
        # Essayer sans parenthèses
        import_pattern = r'from database import (.+)'
        match = re.search(import_pattern, content)
    
    if not match:
        print("❌ AUCUN IMPORT 'from database import ...' trouvé !")
        print()
        print("Ajoutez ceci en haut de app.py :")
        print()
        print("from database import (")
        for func in required_functions:
            print(f"    {func},")
        print("    # ... autres imports existants")
        print(")")
        return False
    
    imports_text = match.group(1)
    imported_functions = [f.strip() for f in re.split(r'[,\n]', imports_text) if f.strip()]
    
    print("✅ Imports trouvés:")
    for func in imported_functions:
        print(f"   - {func}")
    print()
    
    # Vérifier les imports manquants
    missing = [f for f in required_functions if f not in imported_functions]
    
    if missing:
        print("⚠️  IMPORTS MANQUANTS pour OAuth:")
        for func in missing:
            print(f"   ❌ {func}")
        print()
        print("Ajoutez ces imports à la ligne 'from database import ...':")
        print()
        for func in missing:
            print(f"    {func},")
        print()
        return False
    else:
        print("✅ Tous les imports OAuth nécessaires sont présents!")
        print()
        return True


def check_function_usage(filepath):
    """Vérifie si les fonctions OAuth sont utilisées dans le code"""
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        return
    
    print("=" * 70)
    print("🔍 UTILISATION DES FONCTIONS OAUTH")
    print("=" * 70)
    print()
    
    oauth_functions = [
        ('authenticate_oauth', 'Routes Google/GitHub callback'),
        ('authenticate_local', 'Route /login/local'),
        ('update_password', 'Route change password'),
        ('add_auth_provider', 'Création auth provider'),
    ]
    
    for func, description in oauth_functions:
        count = len(re.findall(rf'\b{func}\(', content))
        status = "✅" if count > 0 else "⚠️ "
        print(f"{status} {func:25} : {count} utilisation(s) - {description}")
    
    print()


if __name__ == "__main__":
    filepath = "/home/c/Documents/_dev/tipikus/app.py"
    
    # Permettre de passer le chemin en argument
    if len(sys.argv) > 1:
        filepath = sys.argv[1]
    
    success = check_imports_in_file(filepath)
    check_function_usage(filepath)
    
    print("=" * 70)
    
    if not success:
        print("❌ ACTION REQUISE : Ajouter les imports manquants")
        print()
        print("SOLUTION RAPIDE:")
        print(f"  1. Ouvrir {filepath}")
        print("  2. Trouver la ligne 'from database import ...'")
        print("  3. Ajouter les fonctions manquantes listées ci-dessus")
        print()
    else:
        print("✅ Imports OK - L'erreur vient peut-être d'ailleurs")
    
    print("=" * 70)
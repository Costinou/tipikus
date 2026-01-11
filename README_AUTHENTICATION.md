# 🔐 Système d'Authentification - Tipikus

## 🎯 Vue d'ensemble

Tipikus dispose maintenant d'un système d'authentification sécurisé avec :
- **Login obligatoire** pour accéder à l'application
- **Mots de passe hashés** (bcrypt via werkzeug)
- **Sessions permanentes** (1 an via cookie)
- **Panel admin** pour gérer les utilisateurs (réservé à "c")

## 👥 Rôles

### Administrateur ("c")
- Peut créer des utilisateurs avec mot de passe
- Peut supprimer des utilisateurs (sauf lui-même)
- Peut créer des lessons
- Peut gérer les decks communs
- Accès au panel admin

### Utilisateurs normaux
- Se connectent avec nom + mot de passe
- Peuvent changer leur mot de passe
- Créent leurs propres decks personnels
- Accèdent aux lessons et decks communs

## 🚀 Installation

### 1. Exécuter la migration

```bash
python3 migrate_add_auth.py
```

**Sortie attendue :**
```
=== Migration: Système d'authentification ===

[1/3] Ajout de la colonne password_hash...
  ✓ Colonne password_hash ajoutée

[2/3] Vérification de l'utilisateur admin 'c'...
  ✓ Utilisateur admin 'c' créé
  → Mot de passe par défaut: admin123
  ⚠️  CHANGEZ CE MOT DE PASSE dès la première connexion!

[3/3] Mise à jour des utilisateurs existants...
  → 2 utilisateur(s) sans mot de passe trouvé(s)
    • Pierre: mot de passe = Pierre123
    • Marie: mot de passe = Marie123
  ✓ Mots de passe temporaires définis

✅ Migration terminée avec succès!

🔑 INFORMATIONS DE CONNEXION:
──────────────────────────────────────────────────
Administrateur:
  • Nom: c
  • Mot de passe: admin123
  ⚠️  CHANGEZ-LE IMMÉDIATEMENT!
──────────────────────────────────────────────────
```

### 2. Redémarrer l'application

```bash
./tipikus.sh restart
```

## 🔑 Première connexion

### Administrateur

1. Allez sur l'application
2. Connectez-vous :
   - **Nom** : `c`
   - **Mot de passe** : `admin123`
3. **IMPORTANT** : Changez immédiatement le mot de passe :
   - Cliquez sur l'icône 🔐
   - Entrez votre nouveau mot de passe

### Utilisateurs existants

Si vous avez migré depuis une ancienne version, vos utilisateurs ont reçu des mots de passe temporaires :

- **Format** : `[nom]123`
- **Exemples** :
  - Pierre → `Pierre123`
  - Marie → `Marie123`

Ils doivent changer leur mot de passe après la première connexion.

## 📖 Guide d'utilisation

### Créer un utilisateur (Admin uniquement)

1. Connectez-vous en tant que **"c"**
2. Sur la page d'accueil, cliquez sur l'icône **👥**
3. Remplissez le formulaire :
   - **Nom d'utilisateur** : ex. "Pierre"
   - **Mot de passe** : min. 4 caractères
4. Cliquez sur **"Créer"**

L'utilisateur peut maintenant se connecter avec ces identifiants.

### Changer son mot de passe

1. Sur la page d'accueil, cliquez sur l'icône **🔐**
2. Entrez :
   - Mot de passe actuel
   - Nouveau mot de passe
   - Confirmation du nouveau mot de passe
3. Cliquez sur **"Changer le mot de passe"**

### Supprimer un utilisateur (Admin uniquement)

1. Allez dans **👥 Gestion des utilisateurs**
2. Cliquez sur **🗑️** à côté de l'utilisateur
3. Confirmez la suppression

**Attention** : Toutes les données de l'utilisateur seront supprimées (decks personnels, sessions, etc.).

### Se déconnecter

Sur la page d'accueil, cliquez sur l'icône **🚪** (déconnexion).

## 🔒 Sécurité

### Mots de passe

- **Hashage** : bcrypt via `werkzeug.security`
- **Stockage** : Seul le hash est stocké en base de données
- **Minimum** : 4 caractères (recommandé : 8+)

### Sessions

- **Durée** : 1 an (cookie permanent)
- **Protection** : HttpOnly, SameSite=Lax
- **Stockage** : Cookie sécurisé côté client

### Permissions

| Action | Utilisateur normal | Admin (c) |
|--------|-------------------|-----------|
| Créer un deck personnel | ✅ | ✅ |
| Créer un deck commun | ❌ | ✅ |
| Créer une lesson | ❌ | ✅ |
| Créer/Supprimer des users | ❌ | ✅ |
| Changer son mot de passe | ✅ | ✅ |

## 📂 Structure de la base de données

### Table `users` (après migration)

| Colonne | Type | Description |
|---------|------|-------------|
| `id` | INTEGER | Identifiant unique |
| `nom` | TEXT | Nom d'utilisateur (UNIQUE) |
| `password_hash` | TEXT | Hash bcrypt du mot de passe |
| `created_at` | TIMESTAMP | Date de création |

### Exemple de hash

```
Mot de passe: admin123
Hash stocké: $2b$12$KIXxJ7yF0...9uKWqN8e (60 caractères)
```

## 🔧 Dépannage

### Mot de passe oublié (Admin)

Si vous avez oublié le mot de passe admin :

```python
# Dans Python shell ou script
from werkzeug.security import generate_password_hash
import sqlite3

conn = sqlite3.connect('tipikus.db')
new_hash = generate_password_hash('nouveau_mot_de_passe')
conn.execute("UPDATE users SET password_hash = ? WHERE nom = 'c'", (new_hash,))
conn.commit()
conn.close()
```

### Mot de passe oublié (Utilisateur normal)

Seul l'admin peut réinitialiser :
1. Connectez-vous en tant que "c"
2. Allez dans **👥 Gestion des utilisateurs**
3. **Supprimez** l'utilisateur
4. **Recréez-le** avec un nouveau mot de passe

### Session expirée

Les sessions durent 1 an. Si déconnecté :
- Reconnectez-vous avec vos identifiants
- Le cookie sera renouvelé automatiquement

### "Accès refusé" sur les pages admin

Vous n'êtes pas connecté en tant que "c". Seul cet utilisateur peut :
- Créer/supprimer des utilisateurs
- Créer des lessons
- Créer des decks communs

## 🔄 Migration depuis l'ancien système

### Avant la migration

Ancien système : Sélection simple d'utilisateur (pas de mot de passe)

### Après la migration

1. **Utilisateur "c"** créé automatiquement avec mot de passe `admin123`
2. **Utilisateurs existants** reçoivent mot de passe temporaire : `[nom]123`
3. **Nouvelle connexion** : Login obligatoire avec nom + mot de passe

### Que se passe-t-il avec les données ?

✅ **Conservées** :
- Tous les decks (personnels et communs)
- Toutes les lessons
- Toutes les sessions/statistiques
- Tous les mots

❌ **Ajoutées** :
- Colonne `password_hash` dans la table `users`
- Mots de passe hashés pour tous les utilisateurs

## ⚙️ Configuration avancée

### Changer la durée de session

Dans `app.py` :

```python
# 1 an (par défaut)
app.config['PERMANENT_SESSION_LIFETIME'] = 31536000

# 30 jours
app.config['PERMANENT_SESSION_LIFETIME'] = 2592000

# 1 semaine
app.config['PERMANENT_SESSION_LIFETIME'] = 604800
```

### Renforcer les exigences de mot de passe

Dans `app.py`, modifiez les validations :

```python
# Longueur minimale
if len(new_password) < 8:  # Au lieu de 4
    flash('Le mot de passe doit contenir au moins 8 caractères')
    return redirect(...)

# Ajouter d'autres règles
import re
if not re.search(r'[A-Z]', new_password):
    flash('Le mot de passe doit contenir une majuscule')
    return redirect(...)
```

## 📊 Exemple de workflow

### Mise en place d'une nouvelle installation

1. **Admin (c)** :
   ```
   - Se connecte avec admin123
   - Change son mot de passe → admin_secure_2024
   - Crée 3 utilisateurs:
     • Pierre (mot de passe: pierre2024)
     • Marie (mot de passe: marie2024)
     • Lucas (mot de passe: lucas2024)
   - Crée lessons A1, A2
   - Crée decks communs
   ```

2. **Pierre** :
   ```
   - Se connecte avec pierre2024
   - Change son mot de passe
   - Crée ses decks personnels
   - Fait les lessons et quiz
   ```

3. **Marie** :
   ```
   - Se connecte avec marie2024
   - Garde son mot de passe
   - Utilise les decks communs
   ```

## 🆘 Support

Si vous rencontrez des problèmes :

1. **Vérifiez les logs** de l'application
2. **Testez la connexion** avec l'admin "c"
3. **Vérifiez la base de données** :
   ```bash
   sqlite3 tipikus.db "SELECT id, nom FROM users;"
   ```
4. **Restaurez la sauvegarde** si nécessaire :
   ```bash
   cp tipikus.db.backup tipikus.db
   ```

---

**Bon apprentissage sécurisé ! 🔐🇭🇺**
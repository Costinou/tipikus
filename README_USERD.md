# 👤 Système d'Utilisateurs - Tipikus

## 📋 Vue d'ensemble

Tipikus inclut maintenant un système d'utilisateurs multi-profils qui permet à plusieurs personnes d'utiliser l'application tout en gardant leurs decks et statistiques séparés.

### Fonctionnalités

- ✅ **Sélection d'utilisateur au démarrage**
- ✅ **Création de nouveaux profils** (prénom uniquement)
- ✅ **Mémorisation automatique** via localStorage
- ✅ **Statistiques personnelles** par utilisateur
- ✅ **Decks séparés** par utilisateur
- ✅ **Changement d'utilisateur** facile

## 🚀 Installation / Migration

### Pour une nouvelle installation

```bash
# 1. Initialiser la base de données
python3 database.py

# 2. Lancer l'application
./tipikus.sh start
```

### Pour migrer depuis une version sans utilisateurs

```bash
# 1. Arrêter l'application
./tipikus.sh stop

# 2. Exécuter le script de migration
python3 migrate_add_users.py

# 3. Relancer l'application
./tipikus.sh start
```

⚠️ **Important**: Le script de migration crée automatiquement un utilisateur "Utilisateur" et lui attribue tous les decks existants.

## 💡 Utilisation

### Premier accès

1. Ouvrez l'application dans votre navigateur
2. Vous arrivez sur la page de sélection d'utilisateur
3. **Option 1**: Sélectionnez un utilisateur existant
4. **Option 2**: Créez un nouveau profil avec votre prénom

### Changement d'utilisateur

1. Sur la page d'accueil, cliquez sur le bouton **"Changer"** à côté de votre nom
2. Sélectionnez un autre utilisateur ou créez-en un nouveau

### Données stockées

- **localStorage (navigateur)**: 
  - `tipikus_user_id`: ID de l'utilisateur actuel
  - `tipikus_user_name`: Nom de l'utilisateur actuel

- **Base de données**:
  - Table `users`: Liste des utilisateurs
  - Table `decks`: Decks avec `user_id`
  - Table `sessions`: Sessions liées aux decks (donc aux users)

## 🔧 Architecture technique

### Flux d'authentification

```
1. Utilisateur visite le site
   ↓
2. JavaScript vérifie localStorage
   ↓
3a. User ID trouvé → Continue normalement
3b. Pas d'User ID → Redirige vers /select-user
   ↓
4. Utilisateur sélectionné/créé
   ↓
5. ID stocké dans localStorage
   ↓
6. Redirection vers page d'accueil
```

### Envoi de l'User ID

L'user_id est envoyé au serveur de deux façons:

1. **Header HTTP**: `X-User-Id` (pour les requêtes Ajax/Fetch)
2. **Champ de formulaire caché**: `user_id` (pour les formulaires POST)

Ceci est géré automatiquement par le JavaScript dans `base.html`.

## 📊 Statistiques par utilisateur

Toutes les statistiques sont automatiquement filtrées par utilisateur:

- Sessions d'apprentissage
- Scores aux quiz
- Streaks
- Temps passé
- Progression par deck

## 🔒 Sécurité

⚠️ **Note importante**: Ce système est conçu pour un usage familial/personnel. Il n'y a **pas de mot de passe** ni d'authentification réelle.

**C'est un système de séparation de profils, pas un système de sécurité.**

Pour une utilisation en production avec authentification:
- Implémentez Flask-Login
- Ajoutez des mots de passe hashés
- Utilisez des sessions serveur sécurisées

## 🐛 Dépannage

### Problème: "Aucun utilisateur sélectionné" en boucle

```bash
# Effacer le localStorage du navigateur
# Dans la console du navigateur (F12):
localStorage.clear()
```

### Problème: Les decks n'apparaissent pas

Vérifiez que la migration a bien été exécutée:

```bash
sqlite3 tipikus.db "SELECT * FROM users;"
sqlite3 tipikus.db "PRAGMA table_info(decks);"
```

La colonne `user_id` doit exister dans la table `decks`.

## 📝 Exemples d'utilisation

### Famille avec plusieurs enfants

```
Marie (8 ans)  → Decks de vocabulaire niveau débutant
Lucas (12 ans) → Decks plus avancés + quiz
Papa          → Decks professionnels hongrois
```

Chacun a ses propres statistiques et progression !

### Cours de langue

```
Classe A → Vocabulaire semaine 1-5
Classe B → Vocabulaire semaine 6-10
Prof     → Tous les decks + statistiques globales
```

## 🔄 Prochaines améliorations possibles

- [ ] Avatar/photo de profil
- [ ] Couleur personnalisée par utilisateur
- [ ] Statistiques comparatives entre utilisateurs
- [ ] Badges et récompenses par utilisateur
- [ ] Export des données par utilisateur
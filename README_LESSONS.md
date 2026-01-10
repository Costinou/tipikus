# 📖 Système de Lessons - Tipikus

## 🎯 Vue d'ensemble

Le système de lessons permet de créer un parcours d'apprentissage structuré pour chaque niveau (A1, A1+, A2, etc.). Chaque lesson contient :
- Un **contenu théorique** en Markdown (texte, images, exemples)
- Des **decks associés** pour pratiquer le vocabulaire

## 📋 Architecture

```
Niveau A1
├── 📖 Lesson 1: Se présenter (3 decks)
│   ├── Contenu Markdown (théorie)
│   └── Decks associés
│       ├── 📚 Salutations
│       ├── 📚 Prénom et nom
│       └── 📚 Nationalités
├── 📖 Lesson 2: Les nombres (2 decks)
└── 📦 Decks hors lessons
    ├── 🌍 Vocabulaire général (commun)
    └── 👤 Mon vocabulaire (personnel)
```

## 🔐 Permissions

- **Utilisateur "c" (admin)** : Peut créer, modifier, supprimer des lessons et gérer leurs decks
- **Autres utilisateurs** : Peuvent lire les lessons et faire les decks associés

## 🚀 Installation

### 1. Exécuter la migration

```bash
python3 migrate_add_lessons.py
```

Cela va :
- ✅ Créer la table `lessons`
- ✅ Ajouter la colonne `lesson_id` aux decks
- ✅ Créer le dossier `static/lessons/images/`

### 2. Redémarrer l'application

```bash
./tipikus.sh restart
```

## 📝 Créer une lesson

### Étape 1 : Préparer le fichier Markdown

Créez un fichier `.md` avec votre contenu. Exemple : `lesson_a1_01.md`

```markdown
# Se présenter en hongrois

## Introduction

Apprendre à se présenter est la première étape essentielle !

## Les salutations de base

En hongrois, on dit :
- **Jó napot** - Bonjour (formel)
- **Szia** - Salut (informel)
- **Jó reggelt** - Bonjour (le matin)

![Salutations](salutations.jpg)

## Structure de présentation

Pour se présenter, on utilise cette structure :

```
[Nom] vagyok.
```

Exemple : **Anna vagyok.** (Je suis Anna)

## Exercices

Essayez de vous présenter en hongrois !
```

### Étape 2 : Préparer les images

Placez vos images dans le dossier :
```
static/lessons/images/
├── salutations.jpg
├── famille.png
└── nombres.gif
```

Dans votre Markdown, référencez-les simplement par leur nom :
```markdown
![Description](salutations.jpg)
```

### Étape 3 : Créer la lesson dans l'interface

1. Connectez-vous avec l'utilisateur **"c"**
2. Allez sur un niveau (ex: A1)
3. Cliquez sur **"➕ Lesson"**
4. Remplissez le formulaire :
   - **Niveau** : A1
   - **Numéro** : 1
   - **Titre** : Se présenter en hongrois
   - **Fichier .md** : Upload `lesson_a1_01.md`
5. Cliquez sur **"Créer la lesson"**

### Étape 4 : Associer des decks

1. Sur la page de la lesson, cliquez sur **"⚙️ Gérer les decks"**
2. Dans la section "Ajouter des decks", cliquez sur **"✅ Ajouter"** pour chaque deck
3. Les decks apparaissent maintenant dans la lesson

**Note** : Seuls les **decks communs** du même niveau peuvent être ajoutés à une lesson.

## 🎨 Syntaxe Markdown supportée

### Titres
```markdown
# Titre H1
## Titre H2
### Titre H3
```

### Formatage texte
```markdown
**Gras**
*Italique*
`Code inline`
```

### Listes
```markdown
- Élément 1
- Élément 2
  - Sous-élément

1. Premier
2. Deuxième
```

### Images
```markdown
![Texte alternatif](nom_image.jpg)
![Salutation](salutations.jpg)
```

### Liens
```markdown
[Texte du lien](https://example.com)
```

### Code
```markdown
```python
def hello():
    print("Szia!")
```
```

### Citations
```markdown
> Ceci est une citation
```

### Tableaux
```markdown
| Français | Hongrois |
|----------|----------|
| Bonjour  | Jó napot |
| Merci    | Köszönöm |
```

## 📂 Structure des fichiers

```
tipikus/
├── static/
│   └── lessons/
│       └── images/           # Vos images ici
│           ├── salutations.jpg
│           ├── famille.png
│           └── nombres.gif
├── templates/
│   ├── create_lesson.html    # Formulaire création
│   ├── lesson.html           # Affichage d'une lesson
│   └── manage_lesson_decks.html  # Gestion des decks
├── migrate_add_lessons.py    # Script de migration
└── tipikus.db
```

## 🔧 Gestion des lessons

### Modifier une lesson

Pour l'instant, vous ne pouvez pas modifier directement. Pour changer le contenu :
1. Supprimez l'ancienne lesson (les decks ne seront pas supprimés)
2. Créez-la à nouveau avec le nouveau fichier .md

### Supprimer une lesson

1. Sur la page de la lesson, cliquez sur **"🗑️ Supprimer"** (visible uniquement pour "c")
2. Confirmez

**Important** : Les decks associés ne sont PAS supprimés, ils redeviennent des "decks libres".

### Retirer un deck d'une lesson

1. Allez sur **"⚙️ Gérer les decks"**
2. Cliquez sur **"❌ Retirer"** à côté du deck
3. Le deck redevient un deck libre

## 💡 Bonnes pratiques

### Organisation des lessons

```
A1 (Débutant absolu)
├── Lesson 1: Salutations et présentation
├── Lesson 2: Les nombres 1-100
├── Lesson 3: La famille
├── Lesson 4: Les couleurs et objets quotidiens
├── Lesson 5: Se déplacer en ville
├── Lesson 6: Au restaurant
├── Lesson 7: Le temps et la météo
└── Lesson 8: Révision A1

A1+ (Débutant avancé)
├── Lesson 1: Conjugaison présent
├── Lesson 2: Les cas hongrois (introduction)
└── ...
```

### Contenu d'une lesson

1. **Introduction** (2-3 phrases)
2. **Points de grammaire** (si applicable)
3. **Vocabulaire clé** avec exemples
4. **Images** pour illustrer
5. **Exercices ou conseils** de pratique
6. **Lien vers les decks** (automatique)

### Nommage des fichiers

```
lesson_[niveau]_[numero].md

Exemples:
- lesson_a1_01.md
- lesson_a1_02.md
- lesson_a2_01.md
```

## 🐛 Dépannage

### Les images ne s'affichent pas

Vérifiez :
1. Les images sont bien dans `static/lessons/images/`
2. Le nom du fichier correspond exactement (sensible à la casse)
3. Dans le Markdown, vous utilisez juste le nom : `![](image.jpg)` et pas le chemin complet

### Erreur "Lesson existe déjà"

Une lesson avec le même **niveau + numéro** existe déjà. Changez le numéro ou supprimez l'ancienne.

### Je ne vois pas le bouton "➕ Lesson"

Connectez-vous avec l'utilisateur **"c"**. Seul cet utilisateur peut créer des lessons.

### Un deck ne peut pas être ajouté à une lesson

Vérifiez :
- Le deck est un **deck commun** (pas personnel)
- Le deck a le **même niveau** que la lesson
- Le deck n'est **pas déjà dans une autre lesson**

## 📊 Exemple complet

### Fichier `lesson_a1_01.md` :

```markdown
# Lesson 1 : Se présenter en hongrois

## Objectifs de cette lesson

À la fin de cette lesson, vous saurez :
- Dire bonjour et au revoir
- Vous présenter (nom, nationalité)
- Demander "Comment allez-vous ?"

## Les salutations essentielles

### Formelles
- **Jó napot kívánok** - Bonjour (très formel)
- **Jó napot** - Bonjour (formel standard)

### Informelles
- **Szia** - Salut (singulier)
- **Sziasztok** - Salut (pluriel)

![Salutations](salutations_hongroises.jpg)

## Se présenter

La structure de base :

```
[Prénom] vagyok.
```

Exemples :
- **Anna vagyok.** → Je suis Anna
- **Péter vagyok.** → Je suis Péter

## Dire sa nationalité

| Français | Hongrois |
|----------|----------|
| Je suis français(e) | Francia vagyok |
| Je suis hongrois(e) | Magyar vagyok |
| Je suis américain(e) | Amerikai vagyok |

## À vous de jouer !

Pratiquez avec les decks ci-dessous pour mémoriser le vocabulaire essentiel !
```

### Decks associés :
1. 📚 Salutations de base
2. 📚 Prénom et nationalité
3. 📚 Phrases de présentation

---

**Bon apprentissage ! 🇭🇺📚**
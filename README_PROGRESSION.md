# 📊 Système de Progression - Tipikus

## 🎯 Vue d'ensemble

Le système de progression permet de suivre l'avancement des utilisateurs dans leur apprentissage du hongrois. Il calcule automatiquement des pourcentages de complétion pour :
- **Les lessons** (0-100%)
- **Les niveaux** (0-100%)

## 📐 Calcul de la progression

### Progression d'une Lesson (0-100%)

Une lesson est considérée comme complétée à 100% quand :

**50% - Toutes les cartes vues** ✅
- L'utilisateur doit avoir vu **toutes les cartes** de **tous les decks** associés à la lesson
- Validation : Au moins une session flashcard **complète** par deck

**50% - Taux de réussite aux quiz ≥ 80%** 🎯
- Le taux de réussite **moyen** aux quiz de tous les decks doit être ≥ 80%
- Formule : `(Total bonnes réponses / Total questions) × 100 ≥ 80%`

**Exemples :**

```
Lesson 1 : Se présenter (3 decks)

Deck A: Salutations
  - 20 cartes → Toutes vues ✅
  - Quiz: 15/20 = 75% ❌

Deck B: Prénom et nom
  - 15 cartes → Toutes vues ✅
  - Quiz: 18/20 = 90% ✅

Deck C: Nationalités
  - 25 cartes → Toutes vues ✅
  - Quiz: 22/25 = 88% ✅

Calcul:
  - Toutes cartes vues: ✅ → +50%
  - Taux moyen quiz: (75 + 90 + 88) / 3 = 84.3% ✅ → +50%
  - Total: 100% 🎉
```

```
Lesson 2 : Les nombres (2 decks)

Deck A: Nombres 1-50
  - 50 cartes → 35 vues ❌
  - Quiz: 40/50 = 80% ✅

Deck B: Nombres 51-100
  - 50 cartes → Toutes vues ✅
  - Quiz: 45/50 = 90% ✅

Calcul:
  - Toutes cartes vues: ❌ (deck A incomplet) → 0%
  - Taux moyen quiz: (80 + 90) / 2 = 85% ✅ → +50%
  - Total: 50%
```

### Progression d'un Niveau (0-100%) - GRANULAIRE

Un niveau a maintenant une progression **progressive et granulaire** :

**50% - Progression moyenne des lessons** 📖
- Chaque lesson contribue proportionnellement
- Formule : `(Somme progression de toutes les lessons / Nombre de lessons) × 50%`
- **Exemple** : 3 lessons dont 1 à 100%, 1 à 50%, 1 à 0%
  - Moyenne : (100 + 50 + 0) / 3 = 50%
  - Contribution : 50% × 0.5 = **25%** du total

**50% - Cartes vues dans les decks hors lessons (linéaire)** 📚
- Progression basée sur le nombre de cartes réellement vues
- Formule : `(Cartes vues / Cartes totales) × 50%`
- **Exemple** : 25 cartes vues sur 100 cartes totales
  - Progression cartes : 25%
  - Contribution : 25% × 0.5 = **12.5%** du total

**Exemples complets :**

```
Niveau A1
├── 3 Lessons : 100%, 100%, 0% → Moyenne 66.67%
│   Contribution : 66.67% × 0.5 = 33.33%
└── Decks hors lessons : 75/150 cartes vues = 50%
    Contribution : 50% × 0.5 = 25%

Total niveau A1 : 33.33% + 25% = 58.33%
```

```
Niveau A1+ (aucune lesson, seulement decks hors lessons)
└── Decks hors lessons : 120/200 cartes vues = 60%
    Contribution lessons : 50% (pas de lessons = automatique)
    Contribution cartes : 60% × 0.5 = 30%

Total niveau A1+ : 50% + 30% = 80%
```

```
Niveau A2 (seulement des lessons, pas de decks hors lessons)
├── 5 Lessons : 100%, 100%, 50%, 0%, 0% → Moyenne 50%
│   Contribution : 50% × 0.5 = 25%
└── Decks hors lessons : aucun
    Contribution : 50% (pas de decks = automatique)

Total niveau A2 : 25% + 50% = 75%
```

## 📊 Affichage visuel

### Page d'accueil (niveaux)

```
┌─────────────────────────────────────┐
│ A1                     3 decks      │
│ ▓▓▓▓▓▓▓▓▓▓▓▓▓░░░░░░░  65%          │
└─────────────────────────────────────┘
```

- **Barre verte** : Progression visualisée
- **Pourcentage** : Affiché uniquement si > 0%

### Page d'un niveau (lessons)

```
┌─────────────────────────────────────┐
│ ① Lesson 1: Se présenter            │
│    2 decks                           │
│    ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓ 100% complété│
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│ ② Lesson 2: Les nombres             │
│    3 decks                           │
│    ▓▓▓▓▓▓▓▓▓▓░░░░░░░░░░  50% complété│
└─────────────────────────────────────┘
```

- **Barre violette** : Progression de la lesson
- **Badge "complété"** : Visible si > 0%

## 🔄 Mise à jour de la progression

La progression est recalculée **en temps réel** à chaque chargement de page :

### Quand est-elle mise à jour ?

✅ **Après chaque session flashcard complète**
- Chaque carte vue contribue à la progression du niveau

✅ **Après chaque quiz**
- Le taux de réussite est recalculé instantanément (pour les lessons)

✅ **Chaque fois que vous consultez** :
- La page d'accueil (niveaux)
- Une page de niveau (lessons)

### Ce qui impacte la progression

| Action | Impact sur progression Niveau |
|--------|------------------------------|
| Terminer une session flashcard | ✅ Progression linéaire des cartes vues |
| Compléter une lesson à 100% | ✅ +X% selon nombre de lessons (ex: 1/3 = +16.67%) |
| Compléter une lesson à 50% | ✅ +X/2 selon nombre de lessons (ex: 1/3 à 50% = +8.33%) |
| Voir 10 cartes sur un deck hors lesson | ✅ Progression linéaire immédiate |
| Créer un nouveau deck hors lesson | ⚠️ Abaisse temporairement le % (plus de cartes totales) |
| Supprimer un deck | ℹ️ Recalcul automatique |

## 💡 Stratégies pour progresser

### Pour compléter une lesson à 100%

1. **D'abord, voir toutes les cartes** (flashcards)
   - Utilisez le mode "Apprentissage" pour chaque deck
   - Finissez la session complète (voyez toutes les cartes)
   - ✅ Vous obtenez 50%

2. **Ensuite, maîtriser les quiz**
   - Faites les quiz de chaque deck
   - Visez minimum 80% de réussite
   - Si <80%, refaites les flashcards et recommencez
   - ✅ Vous obtenez les 50% restants

### Pour progresser rapidement dans un niveau

**Stratégie optimale :**

1. 🎯 **Complétez d'abord les lessons**
   - Chaque lesson complétée à 100% augmente directement le % du niveau
   - Ex: 1 lesson sur 3 = +16.67% du niveau
   
2. 📚 **Voyez des cartes des decks hors lessons**
   - Même sans terminer, chaque carte vue compte !
   - Ex: 50 cartes vues sur 200 = +12.5% du niveau
   
3. 🔄 **Priorisez selon votre style**
   - **Apprentissage structuré** : Lessons d'abord (50% du niveau)
   - **Apprentissage libre** : Decks hors lessons d'abord (50% du niveau)
   - **Équilibré** : Alternez entre les deux

### Conseils pour optimiser

- 🎯 **Progression visible immédiate** : Chaque carte vue fait monter la barre !
- 📚 **Les lessons comptent double** : 1 lesson = plusieurs decks, donc plus de valeur
- 🔄 **Pas besoin de tout finir** : 25% des cartes vues = 12.5% du niveau
- 📖 **Lisez le contenu Markdown** : Ça aide vraiment pour les quiz

## 🐛 Dépannage

### Ma progression niveau stagne

**Problème** : La barre de progression du niveau ne bouge pas ou peu

**Solutions** :
1. **Complétez des lessons** : Chaque lesson à 100% contribue significativement
   - Ex: 1 lesson sur 3 = +16.67% du niveau
2. **Voyez plus de cartes** : Chaque carte vue dans les decks hors lessons compte
   - Ex: +10 cartes = environ +2-5% selon le total de cartes

### Ma progression lesson ne bouge pas

**Problème** : La lesson reste à 0% ou 50%

**À 0%** : Vous n'avez pas encore terminé de voir toutes les cartes ET votre taux de quiz est <80%
- **Solution** : Terminez au moins toutes les sessions flashcards → +50%

**À 50%** : Vous avez vu toutes les cartes MAIS votre taux de quiz est <80%
- **Solution** : Améliorez vos scores aux quiz → +50%

### Le pourcentage du niveau a baissé

**Cause** : Vous avez ajouté un nouveau deck hors lessons avec beaucoup de cartes

**Explication** : 
- Avant : 50/100 cartes = 25% du niveau
- Après ajout deck (100 cartes) : 50/200 cartes = 12.5% du niveau

**Solution** : C'est normal ! Voyez les cartes des nouveaux decks pour remonter.

### Progression bloquée à un certain %

**Causes possibles** :
1. **Lessons incomplètes** : Certaines lessons sont à 0% ou 50%
   - Voyez leur progression individuelle sur la page du niveau
2. **Cartes non vues** : Il reste des cartes dans les decks hors lessons
   - Faites les sessions flashcards pour progresser linéairement

## 📈 Exemples de parcours

### Parcours optimal (Lesson → 100%)

```
Jour 1:
  ✅ Flashcards Deck A (toutes cartes)
  ✅ Flashcards Deck B (toutes cartes)
  → Progression lesson: 50%

Jour 2:
  ✅ Quiz Deck A: 18/20 (90%)
  ✅ Quiz Deck B: 17/20 (85%)
  → Progression lesson: 100% 🎉
```

### Parcours niveau avec granularité

```
Niveau A1 (3 lessons + 100 cartes dans decks hors lessons)

Semaine 1:
  ✅ Lesson 1 complétée à 100%
  → Lessons: (100+0+0)/3 = 33.33% → 16.67% du niveau
  → Cartes hors lessons: 0/100 → 0%
  → Total niveau: 16.67%

Semaine 2:
  ✅ Lesson 2 complétée à 50%
  → Lessons: (100+50+0)/3 = 50% → 25% du niveau
  → Cartes hors lessons: 0/100 → 0%
  → Total niveau: 25%

Semaine 3:
  ✅ Vu 60 cartes sur 100 dans decks hors lessons
  → Lessons: 50% → 25% du niveau
  → Cartes: 60/100 = 60% → 30% du niveau
  → Total niveau: 55%

Semaine 4:
  ✅ Lesson 3 complétée à 100%
  ✅ Toutes les 100 cartes vues
  → Lessons: (100+50+100)/3 = 83.33% → 41.67% du niveau
  → Cartes: 100/100 = 100% → 50% du niveau
  → Total niveau: 91.67%
```

### Progression visible à chaque carte

```
Deck hors lesson avec 50 cartes

Carte 1 vue:   1/50 = 2% → +1% au niveau (0.02 × 50%)
Carte 10 vue:  10/50 = 20% → +10% au niveau
Carte 25 vue:  25/50 = 50% → +25% au niveau
Carte 50 vue:  50/50 = 100% → +50% au niveau (max pour decks hors lessons)

Chaque carte compte ! 📊
```

## 🔢 Formules exactes

### Progression Lesson (inchangée)

```python
# 1. Cartes vues (50%)
all_cards_seen = Tous les decks ont une session flashcard complète
cards_progress = 50 if all_cards_seen else 0

# 2. Quiz (50%)
quiz_rates = [taux_deck_1, taux_deck_2, ...]
avg_quiz_rate = sum(quiz_rates) / len(quiz_rates)
quiz_progress = 50 if avg_quiz_rate >= 80 else 0

# Total
total = cards_progress + quiz_progress  # 0, 50 ou 100
```

### Progression Niveau (NOUVEAU - granulaire)

```python
# 1. Progression des lessons (50% du total)
lessons = get_lessons_by_niveau(niveau)

if lessons:
    # Calculer la progression de chaque lesson (0-100)
    lessons_progressions = [calculate_lesson_progress(user, lesson) for lesson in lessons]
    
    # Moyenne des progressions
    avg_lessons = sum(lessons_progressions) / len(lessons)
    
    # Contribution au total (50%)
    lessons_contribution = avg_lessons * 0.5
else:
    # Pas de lessons = 50% automatique
    lessons_contribution = 50.0

# 2. Progression des cartes hors lessons (50% du total)
decks_hors_lessons = get_decks_hors_lessons(niveau, user)

if decks_hors_lessons:
    total_cards = sum(get_deck_total_words(deck) for deck in decks_hors_lessons)
    seen_cards = sum(get_user_seen_cards(user, deck) for deck in decks_hors_lessons)
    
    if total_cards > 0:
        # Progression linéaire
        cards_ratio = seen_cards / total_cards
        cards_contribution = cards_ratio * 50.0
    else:
        cards_contribution = 50.0
else:
    # Pas de decks hors lessons = 50% automatique
    cards_contribution = 50.0

# Total niveau
total_niveau = lessons_contribution + cards_contribution  # 0-100%
```

### Exemples de calcul

**Niveau avec 3 lessons et 200 cartes hors lessons :**

```python
# Lessons: 100%, 50%, 0%
lessons_avg = (100 + 50 + 0) / 3 = 50%
lessons_contribution = 50 * 0.5 = 25%

# Cartes: 75 vues sur 200
cards_ratio = 75 / 200 = 0.375 = 37.5%
cards_contribution = 37.5 * 0.5 = 18.75%

# Total
total = 25 + 18.75 = 43.75%
```

**Niveau sans lessons (seulement decks hors lessons) :**

```python
# Pas de lessons
lessons_contribution = 50%  # Automatique

# Cartes: 120 vues sur 150
cards_ratio = 120 / 150 = 0.8 = 80%
cards_contribution = 80 * 0.5 = 40%

# Total
total = 50 + 40 = 90%
```

---

**Bon apprentissage et bonne progression ! 📚🇭🇺**
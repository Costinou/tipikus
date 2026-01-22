# Tipikus Language Learning Platform - AI Agent Instructions

## Project Overview
**Tipikus** is a Flask-based language learning web application focused on Hungarian (Magyarul) vocabulary and grammar mastery through progressive difficulty levels (A1 to B1+). The app uses a deck-based learning system with lessons, exercises, and real-time progress tracking.

### Tech Stack
- **Backend**: Flask 2.3.3 (Python)
- **Database**: SQLite3 with sqlite3.Row factory
- **Frontend**: HTML/Jinja2 templates with vanilla JS
- **Deployment**: Gunicorn + Nginx
- **Optional**: gTTS for text-to-speech

---

## Architecture

### 1. **Blueprint-Based Route Organization**
Routes are split across modular blueprints registered in [app.py](app.py):
- `auth_bp` → User authentication & password management
- `admin_bp` → User administration (hardcoded admin check: `user_name == 'c'`)
- `main_bp`, `lessons_bp`, `decks_bp`, `learning_bp`, `exercises_bp`, `api_bp`, `progression_bp` → All combined in [app_routes/combined.py](app_routes/combined.py) (~884 lines)

**Pattern**: Each blueprint defines routes, and Flask registers them via `app.register_blueprint()`.

### 2. **Database Layer** 
[database.py](database.py) handles all SQLite operations with utility functions:
- **Core tables**: `users`, `decks`, `mots` (vocabulary), `sessions`, `lessons`, `exercices`
- **Key constants**: `AVAILABLE_LEVELS = ['A1', 'A1+', 'A2', 'A2+', 'B1', 'B1+', 'Custom']`
- **Query pattern**: Use `sqlite3.Row` for dict-like access
- **Session management**: Stored in Flask session; user login sets `session['user_id']` and `session['user_name']`

### 3. **Frontend PWA Architecture**
[templates/base.html](templates/base.html) is the master template with:
- **Service Worker registration** for offline support & updates
- **Jinja2 block structure** for page inheritance
- **Theme support** via [static/js/theme.js](static/js/theme.js)
- **Icons & manifest** for PWA installability

---

## Key Workflows

### User Authentication Flow
1. **Login** ([auth.py](app_routes/auth.py) line 14-34): Form POST → `verify_user_password()` → set session
2. **Password change**: Requires current password verification before update
3. **Admin access**: Hardcoded check `if user_name != 'c': return 403` in admin routes

### Learning Content Structure
**Hierarchy**: Niveau (level) → Lessons → Decks → Vocabulary (mots)
- Each **deck** belongs to a niveau and optionally to a user (is_commun for shared decks)
- **Sessions** track learning activity: score, time spent, words seen
- **Exercises** are created per lesson with fill-blank and quiz types

### Data Persistence Patterns
- Database functions return `list(dict(row))` (converted from `sqlite3.Row`)
- Always use `conn.close()` after queries
- Foreign key constraints enforce referential integrity

---

## Critical Developer Workflows

### Running Locally
```bash
# Development server (debug mode)
python3 app.py  # Runs on http://0.0.0.0:5000

# Production with Gunicorn
gunicorn -c gunicorn_config.py app:app  # Binds to 127.0.0.1:8000
```

### Database Migrations
**Never run migrations multiple times.** Migration scripts like [migrate_to_niveaux.py](migrate_to_niveaux.py) are one-time operations:
- Create temp tables with new schema
- Copy existing data → map old columns to new
- Drop old table → rename new table
- Run: `python3 migrate_to_niveaux.py`

### Adding a New Table
1. Define schema in `init_db()` within [database.py](database.py)
2. Add CRUD functions using the existing pattern
3. Import in routes and use via `get_db()`

---

## Project Conventions

### Session & Authentication
- **Always check**: `user_id = session.get('user_id')` before protected routes
- **Admin-only routes**: Verify `session['user_name'] == 'c'` (hardcoded superuser)
- **Redirect pattern**: `/login` for unauthenticated; `/` for authenticated

### French Language Context
- All UI labels, validation messages, and flash messages are **in French**
- Database field names use French (e.g., `mot_francais`, `traduction`, `niveau`)
- Template variables often use French (`niveaux`, `mots`, `utilisateurs`)

### Error Handling
- Use `flash('message')` for user-visible errors (logged to session)
- 404 errors redirect to homepage via custom error handler
- No exceptions leak to users; always provide user-friendly messages

### Frontend Patterns
- **Service Worker** handles offline caching and update detection
- **Theme toggle** stored in localStorage via `theme.js`
- **Static files** (CSS, JS, images) served from [static/](static/) with cache headers

### Database Query Pattern
```python
def get_something(id):
    conn = get_db()
    result = conn.execute('SELECT * FROM table WHERE id = ?', (id,)).fetchone()
    conn.close()
    return dict(result) if result else None
```

---

## Integration Points

### External Dependencies
- **gTTS** (optional): Check `GTTS_AVAILABLE` flag before use (line 16 in combined.py)
- **Flask session**: Configured with 1-year timeout; HTTPONLY & Lax SameSite
- **Nginx**: Reverse proxy with static file caching (30-day expires)

### API Routes
All API endpoints use `api_bp` with `/api` prefix. Return JSON responses.

### Configuration & Deployment
- **Local**: `app.run(host='0.0.0.0', port=5000, debug=True)`
- **Production**: [gunicorn_config.py](gunicorn_config.py) - CPU*2+1 workers, 120s timeout
- **Systemd service**: Runs as non-root user with www-data group
- **SSL**: Let's Encrypt via Certbot (configured in [README_CONFIG_SERVER.md](README_CONFIG_SERVER.md))

---

## Quick Reference: File Locations

| Purpose | File |
|---------|------|
| App initialization | [app.py](app.py) |
| Database functions | [database.py](database.py) |
| Auth routes | [app_routes/auth.py](app_routes/auth.py) |
| All other routes | [app_routes/combined.py](app_routes/combined.py) |
| Admin routes | [app_routes/admin.py](app_routes/admin.py) |
| Master HTML template | [templates/base.html](templates/base.html) |
| Styles | [static/css/style.css](static/css/style.css) |
| Service Worker | [static/service-worker.js](static/service-worker.js) |

---

## Common Pitfalls to Avoid

1. **Database**: Don't forget `conn.close()` or use context managers
2. **Sessions**: Check `session.get('user_id')` exists before using it
3. **Migrations**: Never repeat one-time migration scripts
4. **Flask**: Always `redirect()` after form POST (prevents double-submit)
5. **Admin access**: Verify `user_name == 'c'` for admin endpoints

# 📋 GitHub Upload Checklist

Diese Anleitung führt dich durch den Upload von Liara auf GitHub.

## ✅ Vorbereitete Dateien

### Hauptdokumentation
- [x] `README.md` - Vollständige Projektübersicht (369 Zeilen)
- [x] `CHANGELOG.md` - Versionsverlauf v1.0 → v2.7.2 (266 Zeilen)
- [x] `CONTRIBUTING.md` - Contribution Guidelines (445 Zeilen)
- [x] `LICENSE` - MIT License

### GitHub-Konfiguration
- [x] `.gitignore` - Python, Node, Secrets, Logs, Backups
- [x] `.env.example` - Environment Template
- [x] `.dockerignore` - Docker Build Exclusions
- [x] `.github/ISSUE_TEMPLATE/bug_report.md`
- [x] `.github/ISSUE_TEMPLATE/feature_request.md`
- [x] `.github/PULL_REQUEST_TEMPLATE.md`
- [x] `.github/workflows/tests.yml` - CI/CD Pipeline

### Assets
- [x] `docs/images/README.md` - Screenshot Guidelines

---

## 🚀 Upload-Schritte

### 1. Repository erstellen (auf GitHub)
```bash
# Gehe zu github.com und erstelle neues Repository:
# Name: liara
# Description: Privacy-First AI Assistant with 4D Memory
# Visibility: Public (oder Private)
# NICHT initialisieren (kein README, .gitignore, License)
```

### 2. Git-Repository initialisieren (lokal)
```bash
cd /opt/liara

# Git initialisieren
git init

# Alle Dateien hinzufügen
git add .

# Status prüfen (sollte .gitignore respektieren)
git status

# Initial Commit
git commit -m "feat: initial commit - Liara v2.7.2 with mobile-first UI"
```

### 3. Repository verknüpfen
```bash
# Ersetze <username> mit deinem GitHub-Benutzernamen
git remote add origin https://github.com/<username>/liara.git

# Oder mit SSH:
# git remote add origin git@github.com:<username>/liara.git

# Remote prüfen
git remote -v
```

### 4. Erste Push
```bash
# Branch umbenennen (falls nötig)
git branch -M main

# Push
git push -u origin main
```

---

## 📸 Screenshots hinzufügen (Optional)

```bash
# Screenshots manuell in docs/images/ platzieren
# Empfohlene Dateien (siehe docs/images/README.md):
# - landing.png
# - chat.png
# - dashboard.png
# - admin.png
# - mobile.png

# Dann committen:
git add docs/images/*.png
git commit -m "docs: add screenshots"
git push
```

---

## 🔐 Secrets prüfen (WICHTIG!)

**Vor dem Push UNBEDINGT prüfen:**

```bash
# Nach sensiblen Daten suchen
grep -r "password" --exclude-dir={venv,node_modules,.git} .
grep -r "secret" --exclude-dir={venv,node_modules,.git} .
grep -r "api_key" --exclude-dir={venv,node_modules,.git} .

# .env-Dateien überprüfen
find . -name ".env*" -not -name ".env.example"

# Private Keys prüfen
find . -name "*.key" -o -name "*.pem"
```

**Falls Secrets gefunden:**
```bash
# Zu .gitignore hinzufügen
echo "path/to/secret/file" >> .gitignore

# Falls bereits committed:
git rm --cached path/to/secret/file
git commit -m "chore: remove secrets from tracking"
```

---

## 🎨 GitHub Repository-Einstellungen

Nach dem Upload auf GitHub:

### 1. Repository Settings
- **Description**: Privacy-First AI Assistant with 4D Memory
- **Website**: (Optional: deine Demo-URL)
- **Topics**: 
  - `ai-assistant`
  - `privacy-first`
  - `4d-memory`
  - `fastapi`
  - `react`
  - `ollama`
  - `mobile-first`
  - `python`
  - `typescript`

### 2. GitHub Pages (Optional)
- Settings → Pages
- Source: Deploy from branch `main` → `/docs`

### 3. Branch Protection (Optional)
- Settings → Branches → Add rule
- Branch name: `main`
- Enable:
  - Require pull request reviews
  - Require status checks (tests)
  - Require linear history

### 4. Labels (Optional)
- Issues → Labels
- Standardlabels sind bereits vorhanden durch Templates

---

## 📦 Release erstellen (Optional)

```bash
# Tag erstellen
git tag -a v2.7.2 -m "Mobile-First Optimization"

# Tag pushen
git push origin v2.7.2
```

Dann auf GitHub:
- Releases → Create new release
- Tag: v2.7.2
- Title: Liara v2.7.2 - Mobile-First Optimization
- Description: (Aus CHANGELOG.md kopieren)
- Publish release

---

## ✨ Nach dem Upload

### Badges aktivieren
Falls du CI/CD nutzt, füge Badges zu README.md hinzu:

```markdown
![Tests](https://github.com/<username>/liara/workflows/Tests/badge.svg)
![License](https://img.shields.io/github/license/<username>/liara)
![Stars](https://img.shields.io/github/stars/<username>/liara)
```

### Community Features
- **Discussions**: Settings → Features → Discussions aktivieren
- **Sponsorships**: (Optional) GitHub Sponsors einrichten
- **Security Policy**: `.github/SECURITY.md` erstellen

---

## 🐛 Troubleshooting

### "Permission denied (publickey)"
```bash
# SSH-Key generieren
ssh-keygen -t ed25519 -C "your-email@example.com"

# Key zu GitHub hinzufügen
cat ~/.ssh/id_ed25519.pub
# Kopieren und zu GitHub → Settings → SSH Keys hinzufügen
```

### "Repository too large"
```bash
# Git-History analysieren
git rev-list --objects --all | \
  git cat-file --batch-check='%(objecttype) %(objectname) %(objectsize) %(rest)' | \
  awk '/^blob/ {print substr($0,6)}' | \
  sort --numeric-sort --key=2 | \
  tail -20

# Große Dateien aus History entfernen:
git filter-branch --tree-filter 'rm -f path/to/large/file' HEAD
```

### ".gitignore wird ignoriert"
```bash
# Git-Cache leeren
git rm -r --cached .
git add .
git commit -m "chore: fix .gitignore"
```

---

## �� Weitere Schritte

1. **README aktualisieren** mit GitHub-spezifischen Badges
2. **CHANGELOG pflegen** bei jedem Release
3. **Issues nutzen** für Bug-Tracking
4. **Pull Requests** für neue Features
5. **Discussions** für Community-Fragen
6. **Wiki** (Optional) für ausführliche Guides

---

## 🎉 Fertig!

Dein Repository ist jetzt bereit für GitHub! 🚀

**Next Steps:**
- [ ] Repository auf GitHub erstellen
- [ ] `git push -u origin main` ausführen
- [ ] Screenshots hinzufügen
- [ ] Release v2.7.2 erstellen
- [ ] Community informieren

**Hilfe benötigt?**
- GitHub Docs: https://docs.github.com
- Liara Docs: `/opt/liara/docs/`
- Issues: https://github.com/<username>/liara/issues

### 4. GitHub Actions — déploiement automatique

```yaml
name: Deploy Docs

on:
  push:
    branches: [main]
  workflow_dispatch:

permissions:
  contents: write

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install dependencies
        run: |
          pip install mkdocs-material mkdocstrings[python] mkdocs-jupyter
          pip install -e .

      - name: Build & deploy
        run: mkdocs gh-deploy --force
```

---

### 5. Commandes locales

```bash
# Preview en local (hot-reload)
mkdocs serve
# → http://127.0.0.1:8000

# Build statique
mkdocs build

# Déployer manuellement sur gh-pages
mkdocs gh-deploy --force
```

---

### 6. Activer GitHub Pages

1. **GitHub → Settings → Pages**
2. Source : **Deploy from a branch**
3. Branch : **`gh-pages`** / `/ (root)`
4. Save

Après le premier `mkdocs gh-deploy` ou le premier run de l'Action, le site sera live sur :

```
https://ICM-Frontlab-CDPR.github.io/simnibs-reader/
```

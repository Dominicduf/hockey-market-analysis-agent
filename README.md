# Agent d'analyse de marché d'équipement de hockey

## Lancer le projet

### Prérequis

- [Docker](https://www.docker.com/) et Docker Compose
- Une clé API [OpenRouter](https://openrouter.ai/)

### Configuration

Copiez le fichier d'exemple et renseignez votre clé API :

```bash
cp .env.example .env
```

Ouvrez `.env` et remplacez la valeur de `OPENROUTER_API_KEY` par votre clé. Les autres paramètres n'ont pas besoin d'être modifiés.

> Le projet a principalement été testé avec le modèle **`openai/gpt-oss-120b:free`**, déjà configuré par défaut dans `.env.example`.

### Démarrage avec Docker

```bash
docker compose up --build
```

L'API sera accessible à l'adresse : **http://localhost:8000**


## Exemples de rapports

Trois rapports d'exemple sont disponibles dans le dossier [`reports/`](reports/).

### Rapport 1 — Bâtons de hockey

> *Prompt utilisé : Produce a market analysis on hockey sticks*

[report_ex_sticks.pdf](reports/report_ex_sticks.pdf)

---

### Rapport 2 — Jambières

> *Prompt utilisé : Produce a market analysis on hockey pads*

[report_ex_pads.pdf](reports/report_ex_pads.pdf)

---

### Rapport 3 — Bâtons et jambières

> *Prompt utilisé : Produce a market analysis on hockey sticks and pads*

[report_ex_sticks_pads.pdf](reports/report_ex_sticks_pads.pdf)


---

## Avertissements et limites connues

### Fiabilité du modèle

Le modèle `openai/gpt-oss-120b:free` peut occasionnellement échouer à retourner l'analyse de sentiment au format JSON attendu, entraînant une erreur lors de la génération du rapport. Relancer simplement l'analyse règle le problème dans la grande majorité des cas. L'utilisation d'un modèle plus performant éliminerait cette instabilité.

### Bonnes pratiques de développement

Dans un contexte professionnel réel, aucun commit ne serait poussé directement sur la branche `main`. Tout changement passerait par une branche de fonctionnalité et une *pull request* soumise à révision.

### CI/CD

Un pipeline CI/CD serait mis en place avec les outils disponibles dans l'environnement client (GitHub Actions, GitLab CI, Jenkins, etc.), incluant au minimum l'exécution automatique des tests à chaque *pull request* et le déploiement continu.

---

## Développement local (sans Docker)

Installez les dépendances avec [uv](https://docs.astral.sh/uv/) :

```bash
uv sync
```

Lancez le serveur :

```bash
uv run uvicorn app.main:app --reload
```

### Lancer les tests

```bash
uv run pytest
```
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

## Architecture et choix de solution

L'application est une API REST développée en FastAPI. Le frontend HTML est seulement présent pour faciliter l'interaction avec le backend. L'API prend en entrée un prompt et le délègue à l'agent. L'agent a accès à 4 outils :

- **list_products** : retourne la liste des produits disponibles, filtrée par catégorie. Cet outil a été intégré pour s'assurer que l'agent découvre dynamiquement les produits pertinents plutôt que de les supposer. En production, il pourrait interroger une liste de sites à parcourir ou une base de données de produits.
- **web_scraper** : lit des pages HTML (données mock locales) et les convertit en markdown via BeautifulSoup. Le markdown a été choisi car c'est la représentation textuelle la plus compacte en termes de tokens. L'outil accepte une liste de produits en un seul appel pour limiter les allers-retours avec le LLM.
- **sentiment_analyzer** : appelle un LLM pour analyser le sentiment des reviews. La réponse est validée via un schéma Pydantic (`with_structured_output`) pour garantir un JSON structuré et cohérent, qui sera utilisé pour générer les graphiques. Pour les tests, le même modèle est utilisé, mais en production il faudrait évaluer un modèle plus petit pour réduire les coûts.
- **report_generator** : génère un rapport PDF (ReportLab) contenant un graphique à barres des scores de sentiment (matplotlib) et un tableau récapitulatif par produit. 

Pour l'orchestration de l'agent, LangGraph a été choisi pour la facilité de mise en place d'un premier MVP et pour ses fonctionnalités natives : state management, routage conditionnel, et intégration simple avec LangSmith pour le tracking. C'est également la librairie avec laquelle j'ai le plus de familiarité. Pour un projet avec des exigences de performance ou de sécurité plus strictes, une implémentation native en Python serait préférable.

L'agent suit un flux séquentiel : `guardrail → call_llm ↔ outils (boucle) → réponse finale`. Plusieurs mécanismes de contrôle ont été implémentés :

- **Grounding** : un effort de prompt engineering a été consacré à contraindre l'agent à ne produire aucune analyse basée sur ses connaissances internes — uniquement sur les données retournées par les outils.
- **Forçage des outils** : `tool_choice="required"` est utilisé pour forcer l'agent à toujours appeler un outil tant que le pipeline n'est pas terminé. Une fois tous les sentiments analysés (`all_sentiment_done`), seul `generate_report` est disponible, empêchant l'agent de terminer prématurément.
- **Gestion des erreurs dans les outils** : au lieu de lever des exceptions, chaque outil retourne une chaîne préfixée `[TOOL ERROR]`, ce qui permet à l'agent de gérer l'échec gracieusement et d'en informer l'utilisateur.
- **Retry automatique** : tous les appels LLM réessaient automatiquement sur les erreurs transitoires (`RateLimitError`, `APIConnectionError`, `APITimeoutError`).
- **Limites de récursion et timeout** : une limite de récursion LangGraph (`max_recursion`) prévient les boucles infinies, et un timeout global (`asyncio.wait_for`) évite les attentes indéfinies.
- **Gestion du contexte** : `trim_messages` supprime les messages les plus anciens lorsque la fenêtre de contexte est pleine. Ce n'est pas optimal — en production, les résultats des outils devraient être mis en cache ou stockés en base de données pour être réintroduits dans un nouveau contexte.

Deux couches de guardrails protègent l'agent contre les injections de prompt et les requêtes hors-périmètre :

1. Un **nœud LLM dédié** (`guardrail`) en entrée de graphe classifie l'entrée utilisateur comme `SAFE` ou `UNSAFE` avant tout traitement.
2. Une **notice de sécurité dans le system prompt** instruite l'agent d'ignorer toute tentative de manipulation provenant des messages utilisateur *ou* des sorties d'outils.

---

## Architecture de données et stockage

Trois systèmes complémentaires :
- **PostgreSQL** — données relationnelles persistantes (résultats, historique, configs). Permet de faire la recherche dans le format JSONB. Faire facilement le lien relationnel entre les rapports, les requêtes, les analyses et la configuration d'agent. Les données pourraient aussi être utilisé par des pipelines analytiques.
- **Redis** — cache des données scrapées avec TTL (évite de re-scraper et de re-appeler le LLM pour les mêmes produits)
- **Object Storage** (S3 / Azure Blob) — stockage des rapports PDF générés.

```sql
-- Historique des requêtes
queries         (id, user_query, status, created_at, completed_at, error_message)

-- Résultats d'analyse
analyses        (id, query_id → queries, report_url, created_at)
product_sentiments (id, analysis_id → analyses, product_id, overall_score,
                    sentiment_distribution JSONB, aspects JSONB, top_praised JSONB)

-- Configurations d'agents
agent_configs   (id, name, model_name, max_recursion, agent_timeout, is_active)
```
---

## Monitoring et observabilité

Tracing — LangSmith : LangGraph s'intègre nativement avec LangSmith via deux variables d'environnement, sans modifier le code. Chaque exécution devient une trace complète.

Métriques clés à surveiller :  Les logs structurés déjà en place (`[TOOL ERROR]`, `[GUARDRAIL]`, `[AGENT]`) sont directement consultables dans LangSmith.

| Métrique | Pourquoi |
|---|---|
| Taux de succès des analyses | Détecte les régressions générales |
| Latence end-to-end | Anticipe les timeouts |
| Taux d'erreurs `[TOOL ERROR]` | Problème de données source ou de connectivité |
| Taux de blocage guardrail (`UNSAFE`) | Trop élevé = guardrail trop agressif, trop bas = potentielle vulnérabilité |
| Tokens consommés par analyse | Suivi des coûts LLM |


Alertes et qualité des outputs : Des alertes seraient configurées sur les seuils critiques : taux d'échec trop élevé, latence dépassant le timeout, ou erreurs 5xx répétées sur `/analyze`.

Pour la qualité des outputs, on pourrait intégrer un mécanisme de feedback des réponses par les utilisateurs pour savoir si c'est une bonne ou mauvaise analyse. Le feedback sera ensuite logger dans LangSmith à la du sdk.

---

## Scaling et optimisation

Pics de charge : l'application étant conteneurisée avec Docker, le scaling horizontal est direct et on peut multiplier les instances derrière un load balancer sans modifier le code. FastAPI étant asynchrone, chaque instance gère déjà bien la concurrence.

Coûts LLM: deux leviers principaux. D'abord, utiliser un modèle moins coûteux pour le `sentiment_analyzer` (tâche simple et répétitive) et pour le `guardrail` (classification binaire) tout en gardant un modèle plus capable pour l'orchestration principale. Ensuite, le cache Redis décrit dans la section stockage évite de réappeler le LLM pour des produits déjà analysés récemment.

**Cache intelligent** : Peu importe la formulation de la requête, si les produits ont déjà été scrapés et analysés récemment, les appels LLM coûteux sont évités. Un cache au niveau de la requête complète serait possible mais nécessiterait une étape de normalisation (ex: extraire les catégories demandées via LLM) pour ne pas dépendre de la formulation exacte.

**Parallélisation** : actuellement, `analyze_sentiment` est appelé séquentiellement un produit à la fois. Avec `asyncio.gather`, tous les appels de sentiment pourraient tourner en parallèle, ce qui diviserait la latence totale par le nombre de produits analysés.

---

## Amélioration continue et A/B testing

**LLM as Judge** : en collaboration avec le client, définir des critères d'évaluation (pertinence, ancrage dans les données, clarté) sous forme de prompt passé à un LLM performant sur un échantillon de rapports. Les scores produits seraient intégrés comme métriques custom dans LangSmith pour suivre la qualité dans le temps.

**A/B testing de prompts** : en traitant les prompts comme on traiterait des hyperparamètres ML — une base de requêtes de référence établie avec le client, sur laquelle on compare différentes versions du system prompt ou du prompt de sentiment, et on évalue sur une métrique définie (score LLM as Judge, taux de validation Pydantic, etc.).

**Feedback loop** : le système de scoring mentionné dans la section monitoring alimente directement cette boucle. Les analyses mal notées deviennent des cas de test prioritaires pour itérer sur les prompts.

**Évolution des capacités** : les améliorations les plus naturelles à partir de la base actuelle seraient de remplacer les fichiers HTML mock par du vrai scraping web, d'élargir le catalogue de produits, et de remplacer `trim_messages` par une gestion de contexte persistante (comme décrit dans la section architecture).

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
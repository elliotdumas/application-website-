# Radar Carrière — consignes pour Claude

Site personnel d'Elliot Dumas : il rassemble et classe les offres d'emploi qui correspondent à son profil
(Strategy, Chief of Staff, Founder's Associate, BizOps, Corporate Development, Associate en fonds ;
startups en priorité ; Paris, Europe, Afrique ; Amérique du Nord seulement si le poste demande le français).
Le profil et les mots-clés sont dans `profil.json`. Réponds à Elliot en français.

Pages publiées :
- GitHub Pages : `docs/index.html`, mis à jour à chaque push sur main (https://elliotdumas.github.io/application-website-/)
- claude.ai (privée) : https://claude.ai/artifact/NGBzQrBbixKfbv8ryr7he2

## Organisation

- `scripts/sources.json` : pages carrières publiques suivies (Ashby, Lever, Greenhouse, Recruitee, Workable).
- `scripts/fetch_jobs.py` : récupère, filtre, classe et écrit `data/jobs.json`. `data/seen.json` garde la date de première apparition.
- `data/extra.json` : offres trouvées par recherche web (LinkedIn, Welcome to the Jungle, Indeed, cabinets de conseil…). Le format est décrit dans le fichier.
- `web/radar.html` : la page. `scripts/build.py` y insère les données et produit `dist/radar.html` (publié sur claude.ai) et `docs/index.html` (GitHub Pages).
- `inspiration/` et `images/` : fichiers déposés par Elliot. Regarde-les au début d'une session.

## Mise à jour quotidienne

1. `git pull origin main`
2. `python3 scripts/fetch_jobs.py`
3. Recherche web des offres que les pages carrières ne couvrent pas, publiées dans les 7 derniers jours :
   - LinkedIn, Welcome to the Jungle, Indeed, Station F, APEC : Founder's Associate, Chief of Staff, Strategy & Operations, BizOps, Strategy Associate, en startup, à Paris et en Europe ;
   - cabinets de conseil en stratégie à Paris (consultant / senior consultant) : McKinsey, BCG, Bain, Roland Berger, Kearney, Oliver Wyman, OC&C, Advancy, Eleven, Simon-Kucher, Estin, Circle Strategy, Accuracy… ;
   - Afrique : Dakar, Abidjan, Casablanca, Lagos, Nairobi (startups, fonds, conseil) ;
   - États-Unis et Canada : uniquement les postes qui demandent le français.
   Ouvre chaque offre pour vérifier qu'elle est en ligne et récente. N'ajoute jamais une offre que tu n'as pas vue.
   Ajoute-la dans `data/extra.json` avec son lien direct, et retire celles de plus de 45 jours ou fermées.
   Ne mets dans `extra.json` ni doublon des pages carrières ni offre inventée.
4. `python3 scripts/fetch_jobs.py && python3 scripts/build.py`
5. Commit (`Mise à jour des offres du JJ/MM`) puis `git push origin main`.
6. Republie la page : outil Artifact, `action: "read"` sur l'URL ci-dessus, puis publish de `dist/radar.html` avec cette `url`.
7. Si une source de `sources.json` échoue plusieurs jours de suite, signale-le dans le message de commit.

## Règles

- Ne jamais postuler à la place d'Elliot ni remplir un formulaire de candidature.
- Ne pas lire automatiquement LinkedIn ou Welcome to the Jungle par des moyens détournés : passer par la recherche web et les pages publiques.

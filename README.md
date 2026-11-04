# Radar Carrière

Les offres d'emploi qui correspondent au profil d'Elliot Dumas, rassemblées en un seul endroit,
classées de 0 à 100 et mises à jour chaque matin.

**Voir le site :** https://claude.ai/artifact/NGBzQrBbixKfbv8ryr7he2 (page privée, visible seulement par toi tant que tu ne la partages pas)

## Comment ça marche

1. `scripts/fetch_jobs.py` lit les pages carrières publiques d'environ 70 startups et scale-ups (liste dans `scripts/sources.json`).
2. Claude ajoute chaque matin les offres trouvées par recherche web sur LinkedIn, Welcome to the Jungle, Indeed et les sites des cabinets de conseil (`data/extra.json`).
3. Chaque offre reçoit une note selon `profil.json` : intitulé du poste, lieu, type d'entreprise, langue, fraîcheur.
4. `scripts/build.py` produit la page `dist/radar.html`, publiée sur claude.ai.

## Modifier le classement

- Ajoute ou retire des mots-clés dans `profil.json`.
- Ajoute une entreprise à suivre dans `scripts/sources.json`.

## Lancer à la main

    python3 scripts/fetch_jobs.py
    python3 scripts/build.py

puis ouvre `dist/radar.html` dans un navigateur.

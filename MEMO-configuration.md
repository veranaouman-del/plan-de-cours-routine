# Mémo de configuration — carte du jour

Tout ce qu'il faut pour reconstruire le système si la session Claude est perdue.

## Les fichiers du système

| Fichier | Rôle |
|---|---|
| `donnees-session.json` | **Source de vérité unique** : horaire, blocs de travail, toutes les évaluations, lectures, tâches admin. C'est le seul fichier à modifier au quotidien. |
| `carte.py` | Génère la carte du jour à partir du JSON. `python3 carte.py` (image), `--texte` (Slack), + une date en argument pour n'importe quel jour. |
| `notion.py` | Génère la page Notion complète à partir du même JSON. `python3 notion.py` (sortie standard), `--sortie page.md`, + une date en argument. Le texte produit se colle tel quel dans `replace_content`. |
| `PLAN-DE-SESSION.md` | Le plan complet de la session : semaines rouges, semaine type, découpage des gros travaux, méthodes par cours, rattrapage. |

## Identifiants à conserver

- Page Notion « Ma session — Automne 2026 » : **3df73824-e620-811e-9e6c-d07440cb6ec7**
  (https://app.notion.com/p/3df73824e620811e9e6cd07440cb6ec7)
- Design Canva du tableau de bord : **DAHVgw0Y3QU**
- Doc Canva du plan de session : **DAHVg0-l5S0**
- Canal Slack, message direct avec moi-même : **D0C2RFRRWKU**
- Mon identifiant Slack : **U0C2LN4A7SR** (workspace daniel30)
- Canal #tous-daniel-30 : C0C3KUYLC9W
- Canal #omnivox : C0C2M49TG0M (créé mais non rejoint)

## Mon horaire — Automne 2026

| Jour | Cours | Heure | Local |
|---|---|---|---|
| Lundi | Développement de logiciels | 10 h 45 – 12 h 30 | A307 |
| Lundi | Programmation Web I | 13 h 30 – 16 h 10 | A307 |
| Mardi | Littérature et imaginaire | 8 h 55 – 12 h 30 | A208 |
| Mercredi | Développement de logiciels | 8 h – 10 h 40 | A307 |
| Jeudi | Anglais propre au programme | 8 h 55 – 11 h 35 | A311 |
| Vendredi | Philosophie (Éthique et politique) | 8 h 55 – 11 h 35 | E204 |
| Vendredi | Programmation Web I | 13 h 30 – 16 h 10 | A307 |

Après-midis libres : mardi, mercredi, jeudi. Ce sont mes trois vrais blocs de travail.

## Prompt à coller dans une routine Claude (tous les jours à 6 h 30)

Depuis que le système est piloté par `donnees-session.json`, le prompt n'a plus besoin de
répéter l'horaire ni les échéances : tout est dans le dépôt. Version courte à utiliser :

> Génère ma carte du jour.
> 1. `pip install --quiet pillow` si nécessaire, puis `python3 carte.py --texte`
>    à la racine du dépôt. Le script lit `donnees-session.json` et sort la carte
>    d'aujourd'hui : cours, priorité, tâches avec leur étape de préparation,
>    échéances avec compteurs J-x, blocs de travail, avancement par cours.
> 2. Poste ce texte tel quel dans mon DM Slack, canal D0C2RFRRWKU.
>    Titres en MAJUSCULES, puces, JAMAIS de tableau Markdown — Slack les supprime.
> 2b. `python3 notion.py` et colle le résultat dans `replace_content` de la page Notion
>    3df73824-e620-811e-9e6c-d07440cb6ec7.
> 3. Envoie-moi une notification push avec ma priorité du jour et tout ce qui
>    tombe à J-3 ou moins.
> 4. Si une échéance est dépassée ou qu'une tâche admin est réglée, mets à jour
>    `donnees-session.json` et pousse le commit.

> 2c. Mettre le visuel Canva DAHVgw0Y3QU à la journée du jour : `read-design` avec
>    `open_transaction`, puis `replace_text` sur les quatre blocs — la date et le bloc,
>    les 4 puces d'« À FAIRE AUJOURD'HUI », la liste de la semaine (déplacer le ▸),
>    et la ligne « ÉCHÉANCES » avec ses compteurs J-x.

Le visuel Canva **se met bien à jour tous les jours** : c'est la pièce qu'on regarde le matin.
Ce qui ne se refait pas tous les jours, c'est son *export* — les liens expirent en quelques
heures, alors que le texte Slack et la page Notion restent lisibles pour toujours.

⚠ **Les routines se configurent dans l'application Claude, pas depuis une session.**
Une session peut créer un `cron`, mais il meurt avec elle et expire après 7 jours.
Pour une routine qui tient toute la session d'automne, coller le prompt ci-dessus dans
Réglages → Routines de l'app Claude, tous les jours à 6 h 30.

## Pièges rencontrés, à ne pas refaire

1. **Slack supprime les tableaux Markdown.** Utiliser des puces.
2. **Le gras `*texte*` ressort en italique** après conversion. Mettre les titres en MAJUSCULES.
3. **Slack ne notifie jamais de mes propres messages.** Le connecteur poste sous mon compte,
   donc aucune notification Slack n'arrivera. La notification doit venir du push de la routine,
   ou d'un `/remind` Slackbot, ou d'un second compte membre du MÊME workspace.
4. **La carte n'est plus codée en dur.** Avant, `carte.py` contenait le contenu du
   18 septembre en clair. Maintenant tout vient de `donnees-session.json` : une échéance
   qui bouge se change à un seul endroit.
5. **Les liens d'export Canva expirent** (~16 à 24 h). Le texte, lui, reste lisible pour toujours.
6. **Le téléchargement de fichiers vers Slack est bloqué** par la politique réseau de
   l'environnement Claude. L'image doit être glissée à la main, ou passer par un lien.
7. **Un script écrit en session et non commité est perdu.** `notion.py` a été écrit lors
   d'une session de la fin septembre, utilisé pour fabriquer la page Notion, puis effacé
   avec le conteneur. Il a fallu le réécrire le 13 octobre à partir de la page Notion
   elle-même. **Tout ce qui sert plus d'une fois se commite le jour même.**
8. **`python3` n'est pas toujours la même version que `pip`.** Dans le conteneur du
   13 octobre, `pip` installait pour Python 3.13 alors que `python3` était en 3.11, et
   `carte.py` échouait sur `ModuleNotFoundError: PIL`. La commande sûre :
   `/usr/local/bin/python3 -m pip install --break-system-packages pillow`.
9. **`fait: true` veut dire « l'évaluation a eu lieu », pas « j'ai eu une note ».**
   Pour une remise dont le dépôt n'est pas confirmé sur LÉA, ajouter `"a_verifier_lea": true` :
   elle sort des échéances à venir mais reste affichée en rouge tant qu'elle n'est pas vérifiée.

10. **Les blocs de texte Canva ne se redimensionnent pas tout seuls.** Une puce qui passe
    sur deux lignes pousse le bloc vers le bas et chevauche la section suivante. Les limites
    du gabarit : **~50 caractères** par puce d'« À FAIRE », **~50** par ligne de la date,
    **~80** par ligne de la liste de la semaine. Après chaque `replace_text`, vérifier que
    la `height` du bloc est revenue à sa valeur d'origine (172,8 / 54,7 / 122,25) avant de
    `commit` — si elle a grandi, le texte est trop long.
11. **La branche `main` du dépôt ne bouge plus depuis le 18 septembre.** Chaque exécution
    de la routine crée une branche `claude/epic-newton-xxxxxx` et ne la fusionne jamais :
    31 branches au 14 octobre. La session du jour repart donc de `main`, c'est-à-dire d'un
    dépôt vieux de trois semaines — c'est exactement pourquoi `notion.py` a dû être réécrit
    cinq fois. **Premier geste de chaque session : `git fetch origin`, repérer la branche
    qui porte le commit le plus récent, et `git merge --ff-only` dessus** avant de toucher
    à quoi que ce soit. Le vrai correctif serait de fusionner dans `main` une fois pour
    toutes — à faire quand j'ai cinq minutes.

## Points à confirmer auprès des profs

- **Anglais** : je suis dans le groupe du jeudi. La note « Thursday group: READING WEEK »
  en semaine 7 me vise — mon midterm oral du 8 octobre est à confirmer par MIO.
- **Français** : mon groupe 00009 ne se réunit que le mardi. La colonne du mardi du plan de cours
  saute le 6 octobre sans explication. À vérifier avec Julie Chamberland.
- **Éthique** : le PDF reçu est une version « Hiver 2026 / services sociaux ».
  Confirmer les pondérations avec Cyndelle Gagnon.
- **Anglais** : carton #723 et photo du reçu à téléverser — échéance semaine 3, dépassée.

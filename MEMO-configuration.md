# Mémo de configuration — carte du jour

Tout ce qu'il faut pour reconstruire le système si la session Claude est perdue.

## Les fichiers du système

| Fichier | Rôle |
|---|---|
| `donnees-session.json` | **Source de vérité unique** : horaire, blocs de travail, toutes les évaluations, lectures, tâches admin. C'est le seul fichier à modifier au quotidien. |
| `carte.py` | Génère la carte du jour à partir du JSON. `python3 carte.py` (image), `--texte` (Slack), + une date en argument pour n'importe quel jour. |
| `notion.py` | Génère la page Notion complète à partir du même JSON. `python3 notion.py --focus focus-du-jour.md`. La sortie se colle telle quelle dans `notion-update-page` (commande `replace_content`). |
| `focus-du-jour.md` | Les encadrés écrits à la main pour la journée : le seul fichier à réécrire chaque matin. Tout le reste est calculé. |
| `PLAN-DE-SESSION.md` | Le plan complet de la session : semaines rouges, semaine type, découpage des gros travaux, méthodes par cours, rattrapage. |

## Identifiants à conserver

- Design Canva du tableau de bord : **DAHVgw0Y3QU**
- Doc Canva du plan de session : **DAHVg0-l5S0**
- Canal Slack, message direct avec moi-même : **D0C2RFRRWKU**
- Mon identifiant Slack : **U0C2LN4A7SR** (workspace daniel30)
- Canal #tous-daniel-30 : C0C3KUYLC9W
- Canal #omnivox : C0C2M49TG0M (créé mais non rejoint)
- Page Notion « Ma session — Automne 2026 » : **3df73824-e620-811e-9e6c-d07440cb6ec7**

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
> 0. **D'abord** : `git fetch --all`, puis repartir de la branche au commit le plus
>    récent (`git for-each-ref --sort=-committerdate refs/remotes/origin | head -1`).
>    Le dépôt n'a pas de branche de suivi unique et `main` est resté au 18 septembre.
> 1. `pip install --quiet pillow` si nécessaire, puis `python3 carte.py --texte`
>    à la racine du dépôt. Le script lit `donnees-session.json` et sort la carte
>    d'aujourd'hui : cours, priorité, tâches avec leur étape de préparation,
>    échéances avec compteurs J-x, blocs de travail, avancement par cours.
> 2. Poste ce texte tel quel dans mon DM Slack, canal D0C2RFRRWKU.
>    Titres en MAJUSCULES, puces, JAMAIS de tableau Markdown — Slack les supprime.
> 3. Envoie-moi une notification push avec ma priorité du jour et tout ce qui
>    tombe à J-3 ou moins.
> 4. Mets aussi la page Notion à jour : réécris `focus-du-jour.md` pour la journée,
>    puis `python3 notion.py --focus focus-du-jour.md` et colle la sortie dans la page
>    (`replace_content`).
> 5. Si une échéance est dépassée ou qu'une tâche admin est réglée, mets à jour
>    `donnees-session.json` et pousse le commit **le jour même**.

Le visuel Canva (design DAHVgw0Y3QU) se met à jour à part, pas tous les jours : ses liens
d'export expirent en quelques heures, alors que le texte Slack reste lisible pour toujours.

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
7. **Le design Canva a des boîtes de texte à taille fixe.** Une ligne plus longue que
   l'originale se replie, la boîte grandit et écrase le bloc d'en dessous. Garder les
   longueurs de ligne : sous-titre ≤ 46 caractères, puces « À faire » ≤ 47, lignes des
   7 jours ≤ 78. Vérifier la vignette renvoyée par `edit-design` **avant** de committer.
8. **`replace_text` dans Canva remet parfois le formatage à zéro** (taille, couleur,
   alignement). Le cas échéant, rattraper avec une opération `format_text` dans le même
   appel, puis revérifier la vignette.
9. **Pillow est cassé dans l'image Claude** (`cannot import name '_imaging'`). Créer un
   venv dans le répertoire temporaire de la session : `python3 -m venv venv && ./venv/bin/pip
   install pillow`, puis lancer `./venv/bin/python carte.py`. La sortie texte, elle, n'a
   besoin de rien.
10. **Les sessions Claude ne gardent rien.** Un conteneur est recyclé à la fin. Tout ce qui
   doit survivre — `notion.py`, un nouveau champ du JSON, une tâche réglée — doit être
   committé et poussé le jour même, sinon la session suivante repart de l'avant-veille.
11. **Notion décode les entités HTML.** `notion.py` écrit `&amp;` mais la page stocke `&`.
   Un `old_str` de `update_content` copié depuis la sortie du script ne matchera donc pas
   sur une ligne contenant `&` (ex. « Final Speaking & Listening »). Toujours copier le
   `old_str` depuis le `fetch` de la page, jamais depuis la sortie du générateur.
12. **`update_content` ne remplace que le texte visé.** Si l'`old_str` est le corps d'un
   `<callout>`, l'icône et la couleur du callout restent celles de la veille. Les changer
   demande une opération séparée sur `<callout icon="X" color="Y">`.
13. **Le dépôt n'a pas de branche de suivi unique.** Chaque jour pousse une branche
   `claude/...` neuve, et `main` est resté au 18 septembre. Une nouvelle session part donc
   d'un état vieux de plusieurs semaines : **commencer par `git fetch --all` puis repartir
   de la branche au commit le plus récent** (`git for-each-ref --sort=-committerdate
   refs/remotes/origin | head -1`), sinon `notion.py` et les données à jour sont invisibles.

14. **Le 13 novembre, le piège 13 s'est produit pour de vrai.** La session est partie de
   `main` et a poussé une branche qui avait perdu `notion.py`, `focus-du-jour.md`, le mémo
   complet et les améliorations de `carte.py` du 12 (tri des urgences, points incertains,
   troncature propre). Le 14, tout a été récupéré : `carte.py` et le JSON depuis la branche
   du 12 (`96548dc`), `notion.py` et le mémo depuis celle du 10 (`f57f8c4`). Les données,
   elles, étaient à jour sur la branche du 13 : c'est elle qui sert de base, et on y rapatrie
   les fichiers manquants. **Avant de committer, vérifier que `notion.py` et
   `focus-du-jour.md` existent encore** — leur absence est le symptôme du départ depuis `main`.
15. **`notion-tableau-de-bord.md` est supprimé pour de bon.** C'était un export figé à la
   semaine 4 ; `notion.py` régénère la page à jour pour n'importe quelle date. S'il réapparaît,
   c'est encore le symptôme du piège 13.

## Points à confirmer auprès des profs

- **Anglais** : je suis dans le groupe du jeudi. La note « Thursday group: READING WEEK »
  en semaine 7 me vise — mon midterm oral du 8 octobre est à confirmer par MIO.
- **Français** : mon groupe 00009 ne se réunit que le mardi. La colonne du mardi du plan de cours
  saute le 6 octobre sans explication. À vérifier avec Julie Chamberland.
- **Éthique** : le PDF reçu est une version « Hiver 2026 / services sociaux ».
  Confirmer les pondérations avec Cyndelle Gagnon.
- **Anglais** : carton #723 et photo du reçu à téléverser — échéance semaine 3, dépassée.

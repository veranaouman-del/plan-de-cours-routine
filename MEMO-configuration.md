# Mémo de configuration — carte du jour

Tout ce qu'il faut pour reconstruire le système si la session Claude est perdue.

## Les fichiers du système

| Fichier | Rôle |
|---|---|
| `donnees-session.json` | **Source de vérité unique** : horaire, blocs de travail, toutes les évaluations, lectures, tâches admin. C'est le seul fichier à modifier au quotidien. |
| `carte.py` | Génère la carte du jour à partir du JSON. `python3 carte.py` (image), `--texte` (Slack), + une date en argument pour n'importe quel jour. |
| `PLAN-DE-SESSION.md` | Le plan complet de la session : semaines rouges, semaine type, découpage des gros travaux, méthodes par cours, rattrapage. |
| Page Notion | Le tableau de bord quotidien, mis à jour à la main chaque matin par la routine (le script `notion.py` n'a jamais été commité et a été perdu avec son conteneur). |

## Identifiants à conserver

- Design Canva du tableau de bord : **DAHVgw0Y3QU**
- Doc Canva du plan de session : **DAHVg0-l5S0**
- Canal Slack, message direct avec moi-même : **D0C2RFRRWKU**
- Mon identifiant Slack : **U0C2LN4A7SR** (workspace daniel30)
- Canal #tous-daniel-30 : C0C3KUYLC9W
- Canal #omnivox : C0C2M49TG0M (créé mais non rejoint)
- Page Notion « 🎓 Ma session — Automne 2026 » : `3df73824-e620-811e-9e6c-d07440cb6ec7`

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
> 1. `python3 carte.py --texte`
>    à la racine du dépôt. Le script lit `donnees-session.json` et sort la carte
>    d'aujourd'hui : cours, priorité, tâches avec leur étape de préparation,
>    échéances avec compteurs J-x, blocs de travail, avancement par cours.
> 2. Poste ce texte tel quel dans mon DM Slack, canal D0C2RFRRWKU.
>    Titres en MAJUSCULES, puces, JAMAIS de tableau Markdown — Slack les supprime.
> 3. Envoie-moi une notification push avec ma priorité du jour et tout ce qui
>    tombe à J-3 ou moins.
> 4. Si une échéance est dépassée ou qu'une tâche admin est réglée, mets à jour
>    `donnees-session.json` et pousse le commit.

> 5. Mets à jour le design Canva DAHVgw0Y3QU et la page Notion avec la même journée.
>    Pour Canva : garder le **même nombre de lignes** dans chaque bloc de texte, sinon
>    le bloc grandit et chevauche les tuiles du bas (max ~44 caractères par puce).

Le visuel Canva (design DAHVgw0Y3QU) garde ses liens d'export quelques heures seulement,
alors que le texte Slack et la page Notion restent lisibles pour toujours.

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
7. **`python3` ne sait plus faire l'image.** Dans le conteneur, `python3` est en 3.11
   alors que le Pillow du système est compilé pour 3.12 : `from PIL import Image` échoue
   sur `_imaging`. Réinstaller Pillow n'y change rien. Utiliser **`python3.13 carte.py`**
   pour l'image ; le mode `--texte` marche avec n'importe quel Python.
8. **La page Notion dérivait du JSON.** Les corrections faites directement dans Notion
   (dates du Contrôle 2 et de l'oral d'anglais, liste « À régler », 9 évaluations non
   confirmées) n'étaient pas redescendues dans `donnees-session.json`. Remises d'aplomb
   le 19 novembre. Désormais : **toute correction va d'abord dans le JSON**, la page
   Notion vient après.
9. **Une tâche réglée ne s'efface pas, elle se marque.** `"statut": "regle"` quand c'est
   fait, `"statut": "obsolete"` quand la date est passée et que ça n'a plus d'objet.
   Les deux disparaissent de la carte sans perdre la trace.
10. **Les évaluations passées non confirmées portent `"a_verifier_lea": true`.** Elles
    comptent dans l'avancement mais celui-ci reste une hypothèse tant qu'elles sont là.

## Points à confirmer auprès des profs

- **Anglais** : je suis dans le groupe du jeudi. La note « Thursday group: READING WEEK »
  en semaine 7 me vise — mon midterm oral du 8 octobre est à confirmer par MIO.
- **Français** : mon groupe 00009 ne se réunit que le mardi. La colonne du mardi du plan de cours
  saute le 6 octobre sans explication. À vérifier avec Julie Chamberland.
- **Éthique** : le PDF reçu est une version « Hiver 2026 / services sociaux ».
  Confirmer les pondérations avec Cyndelle Gagnon.
- **Anglais** : carton #723 et photo du reçu à téléverser — échéance semaine 3, dépassée.

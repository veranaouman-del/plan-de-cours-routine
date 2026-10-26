# Mémo de configuration — carte du jour

Tout ce qu'il faut pour reconstruire le système si la session Claude est perdue.

## Les fichiers du système

| Fichier | Rôle |
|---|---|
| `donnees-session.json` | **Source de vérité unique** : horaire, blocs de travail, toutes les évaluations, lectures, tâches admin. C'est le seul fichier à modifier au quotidien. |
| `carte.py` | Génère la carte du jour à partir du JSON. `python3 carte.py` (image), `--texte` (Slack), + une date en argument pour n'importe quel jour. |
| `notion.py` | Génère la page Notion complète à partir du même JSON, en Markdown Notion. `python3 notion.py` (+ une date). Réutilise le moteur de `carte.py` : une seule logique, deux sorties. |
| `plan-du-jour.md` | Le seul morceau écrit à la main : les callouts du plan de la journée, insérés par `notion.py` sous la priorité. À réécrire chaque matin — c'est du jugement, pas de la donnée. |
| `PLAN-DE-SESSION.md` | Le plan complet de la session : semaines rouges, semaine type, découpage des gros travaux, méthodes par cours, rattrapage. |

## Identifiants à conserver

- Design Canva du tableau de bord : **DAHVgw0Y3QU**
- Doc Canva du plan de session : **DAHVg0-l5S0**
- Canal Slack, message direct avec moi-même : **D0C2RFRRWKU**
- Mon identifiant Slack : **U0C2LN4A7SR** (workspace daniel30)
- Canal #tous-daniel-30 : C0C3KUYLC9W
- Canal #omnivox : C0C2M49TG0M (créé mais non rejoint)
- Page Notion du tableau de bord : **3df73824-e620-811e-9e6c-d07440cb6ec7**

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
> 1. `python3 carte.py --texte` à la racine du dépôt. Le script lit
>    `donnees-session.json` et sort la carte d'aujourd'hui : cours, priorité,
>    tâches avec leur étape de préparation, échéances avec compteurs J-x,
>    blocs de travail, points au statut incertain, avancement par cours.
> 2. Réécris `plan-du-jour.md` : le plan heure par heure de la journée, en
>    callouts Notion. C'est là que se met le jugement — quelle fenêtre ne se
>    représentera pas, quel prof est devant moi aujourd'hui, ce qui attend.
> 3. `python3 notion.py` et remplace le contenu de la page Notion du tableau
>    de bord avec la sortie (`replace_content`).
> 4. Poste la carte dans mon DM Slack, canal D0C2RFRRWKU. Titres en
>    MAJUSCULES, puces, JAMAIS de tableau Markdown — Slack les supprime.
> 5. Mets à jour le design Canva DAHVgw0Y3QU : mêmes cadres, textes remplacés.
>    Respecter la longueur des lignes de la veille, sinon ça déborde.
> 6. Envoie-moi une notification push avec ma priorité du jour et tout ce qui
>    tombe à J-3 ou moins.
> 7. Si une échéance est dépassée, qu'une tâche admin est réglée ou qu'une
>    évaluation est confirmée sur LÉA, mets à jour `donnees-session.json`
>    et **pousse le commit** — sans ça, le travail du jour est perdu demain.

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
7. **Les textes Canva ne se replient pas tout seuls.** Chaque cadre a une hauteur fixe :
   une ligne trop longue passe à la ligne, le cadre grandit et chevauche le bloc suivant.
   Garder la longueur des lignes de la veille — ~45 caractères pour la liste « À faire »,
   ~58 pour le sous-titre, ~95 pour les échéances — et vérifier la vignette après coup.
8. **Pillow s'installe dans la mauvaise version de Python.** `pip` vise 3.13, `python3`
   est 3.11. La bonne commande est `python3 -m pip install --break-system-packages
   --force-reinstall pillow`. Sans ça, `ImportError: cannot import name '_imaging'`.
9. **Ce qui n'est pas commité est perdu.** La session Claude repart d'un clone neuf
   à chaque exécution. Les semaines 8 et 9 ont vécu dans Notion et Canva sans jamais
   revenir dans le dépôt : il a fallu les reconstruire à la main. Pousser, chaque jour.

## Points à confirmer auprès des profs

- **Anglais** : je suis dans le groupe du jeudi. La note « Thursday group: READING WEEK »
  en semaine 7 me vise — mon midterm oral du 8 octobre est à confirmer par MIO.
- **Français** : mon groupe 00009 ne se réunit que le mardi. La colonne du mardi du plan de cours
  saute le 6 octobre sans explication. À vérifier avec Julie Chamberland.
- **Éthique** : le PDF reçu est une version « Hiver 2026 / services sociaux ».
  Confirmer les pondérations avec Cyndelle Gagnon.
- **Anglais** : carton #723 et photo du reçu à téléverser — échéance semaine 3, dépassée.

## Le champ `a_verifier_lea`

Une évaluation passée dont rien ne confirme la remise porte `"a_verifier_lea": true`.
Elle compte dans l'avancement, mais `carte.py` et `notion.py` la signalent comme
hypothèse : barre grise sur l'image, section « au statut incertain » dans le texte.
Au 26 octobre, 38 % de la session est dans cet état. Une fois la remise confirmée
sur LÉA ou par le prof, **retirer le champ** — l'avancement redevient un fait.

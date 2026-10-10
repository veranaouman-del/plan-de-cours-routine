# Mémo de configuration — carte du jour

Tout ce qu'il faut pour reconstruire le système si la session Claude est perdue.

## Les fichiers du système

| Fichier | Rôle |
|---|---|
| `donnees-session.json` | **Source de vérité unique** : horaire, blocs de travail, blocs d'exception, toutes les évaluations, lectures, tâches admin. C'est le seul fichier à modifier au quotidien. |
| `carte.py` | Génère la carte du jour à partir du JSON. `python3 carte.py` (image), `--texte` (Slack), + une date en argument pour n'importe quel jour. |
| `PLAN-DE-SESSION.md` | Le plan complet de la session : semaines rouges, semaine type, découpage des gros travaux, méthodes par cours, rattrapage. |

## Identifiants à conserver

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
> 3. Envoie-moi une notification push avec ma priorité du jour et tout ce qui
>    tombe à J-3 ou moins.
> 4. Si une échéance est dépassée ou qu'une tâche admin est réglée, mets à jour
>    `donnees-session.json` et pousse le commit.

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
7. **`python3` n'est pas la bonne version.** Dans l'environnement Claude, `python3` est
   un 3.11 sans Pillow ; Pillow est installé pour 3.13. Pour l'image : `python3.13 carte.py`.
   Le mode `--texte` n'a besoin de rien et marche avec les deux.
8. **Ne jamais ouvrir le JSON en lecture et en écriture dans la même expression Python** —
   le mode `"w"` vide le fichier avant que la lecture s'exécute. Lire, fermer, puis écrire.

## Les semaines sans cours : `blocs_exception`

La semaine type (`blocs_travail`) est calée sur les jours de cours. Une semaine sans cours
— semaine d'études, congé — ne se travaille pas avec cet horaire-là. D'où `blocs_exception` :

```json
{"date": "2026-10-14", "debut": "09:30", "fin": "12:30",
 "titre": "GROS BLOC — Programmation : démarrer le TP3", "focus": ["devlog"]}
```

Dès qu'une date a au moins un bloc d'exception, **ces blocs remplacent entièrement** ceux
de la semaine type pour cette journée. Le champ `focus` pilote aussi les tâches affichées.
La semaine d'études du 12 au 16 octobre est déjà chargée.

## Points à confirmer auprès des profs

*Mis à jour le 10 octobre. Le midterm oral d'anglais et la question du mardi 6 octobre
sont tombés d'eux-mêmes : les deux dates sont passées.*

- **Anglais** : carton #723 et photo du reçu à téléverser — échéance semaine 3, trois
  semaines de retard. À régler avant le retour en classe du 19 octobre.
- **Éthique** : le PDF reçu est une version « Hiver 2026 / services sociaux ».
  Confirmer les pondérations avec Cyndelle Gagnon — c'est la zone d'ombre la plus
  coûteuse, l'entrevue finale vaut 40 %.
- **LÉA** : relever les résultats de la semaine 7 (intra 25 %, Éval. #1 Web 25 %, les deux
  midterms d'anglais, examen de philo 25 %) et **réajuster le champ `difficulte`**.
  C'est ce réglage qui redistribue les blocs de travail d'ici décembre.
- **Prog. Web** : dates officielles de remise des TP et répartition exacte des 20 %,
  à vérifier sur LÉA auprès de David Lacasse.

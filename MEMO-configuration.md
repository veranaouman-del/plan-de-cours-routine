# Mémo de configuration — carte du jour

Tout ce qu'il faut pour reconstruire le système si la session Claude est perdue.

## Les fichiers du système

| Fichier | Rôle |
|---|---|
| `donnees-session.json` | **Source de vérité unique** : horaire, blocs de travail, toutes les évaluations, lectures, tâches admin. C'est le seul fichier à modifier au quotidien. |
| `carte.py` | Génère la carte du jour à partir du JSON. `python3 carte.py` (image), `--texte` (Slack), + une date en argument pour n'importe quel jour. |
| `notion.py` | Génère la **page Notion complète** (Notion-flavored Markdown) à partir du même JSON : aujourd'hui, à faire, 7 prochains jours, à régler, échéances, lectures, semaines rouges, semaine type, méthodes, avancement. Importe `carte.py`, donc les deux sorties ne peuvent pas se contredire. |
| `PLAN-DE-SESSION.md` | Le plan complet de la session : semaines rouges, semaine type, découpage des gros travaux, méthodes par cours, rattrapage. |

### Comment `notion.py` s'utilise

```
python3 notion.py                            # la page d'aujourd'hui
python3 notion.py 2026-11-03                 # la page d'un jour donné
python3 notion.py --coaching bloc.md         # + les encadrés écrits à la main
```

Tout le squelette est calculé. Seuls les **encadrés du jour** (les `<callout>` qui disent
*quoi faire de ce créneau précis*) sont écrits à la main, dans un fragment passé avec
`--coaching`. C'est volontaire : c'est la seule partie qui demande un jugement, et c'est
elle qui fait la différence entre un calendrier et un coach. Le reste ne doit jamais être
retapé à la main.

## Identifiants à conserver

- Page Notion « 🎓 Ma session — Automne 2026 » : **3df73824-e620-811e-9e6c-d07440cb6ec7**
  (c'est elle qu'on met à jour avec `notion-update-page`, commande `replace_content`)
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
> 1. `python3 carte.py --texte` à la racine du dépôt. Le script lit
>    `donnees-session.json` et sort la carte d'aujourd'hui : cours, priorité, tâches
>    avec leur étape de préparation, échéances avec compteurs J-x, blocs de travail,
>    avancement par cours.
> 2. Poste-la dans mon DM Slack, canal D0C2RFRRWKU — version courte et lisible au
>    téléphone. Titres en MAJUSCULES, puces, JAMAIS de tableau Markdown : Slack les
>    supprime.
> 3. Écris les encadrés du jour dans un fragment (`/tmp/coaching-AAAA-MM-JJ.md`) :
>    quoi faire de chaque créneau, et pourquoi aujourd'hui plutôt que demain. Puis
>    `python3 notion.py --coaching <ce fichier>` et pousse la sortie dans la page
>    Notion 3df73824-e620-811e-9e6c-d07440cb6ec7 avec `replace_content`.
> 4. Envoie-moi une notification push avec ma priorité du jour et tout ce qui
>    tombe à J-3 ou moins.
> 5. Si une échéance est dépassée ou qu'une tâche admin est réglée, mets à jour
>    `donnees-session.json` et pousse le commit. **Avant de committer, repartir de la
>    branche `claude/*` la plus récente, pas de `main`** — voir la section suivante.

Le visuel Canva (design DAHVgw0Y3QU) se met à jour **le dimanche**, pas tous les jours :
c'est le jour du bloc « plan de la semaine », et c'est la cadence que le gabarit supporte.
Ses liens d'export expirent en quelques heures, alors que le texte Slack reste lisible pour
toujours. Le gabarit est serré : garder le **même nombre de lignes** dans chaque bloc de
texte, et des lignes de longueur comparable, sinon la boîte grandit et chevauche la suivante.

⚠ **Les routines se configurent dans l'application Claude, pas depuis une session.**
Une session peut créer un `cron`, mais il meurt avec elle et expire après 7 jours.
Pour une routine qui tient toute la session d'automne, coller le prompt ci-dessus dans
Réglages → Routines de l'app Claude, tous les jours à 6 h 30.

## ⚠ Continuité du dépôt — à lire avant de committer

Chaque exécution de la routine ouvre une **nouvelle branche** `claude/epic-newton-xxxxxx`
partant de `main`, et cette branche **n'est jamais fusionnée**. Au 1er novembre il y en a
plus de quarante, toutes à un commit de `main`, et `main` est resté à l'état du 18 septembre.
C'est pour ça que `notion.py` a été « reconstruit » une dizaine de fois : chaque journée
repartait d'un dépôt qui ne l'avait jamais vu.

**La règle, chaque jour :**

```bash
git fetch --all --prune
git for-each-ref --sort=-committerdate \
    --format='%(committerdate:short) %(refname:short)' refs/remotes/origin | head -3
git checkout -B <ma-branche-du-jour> origin/<la-branche-la-plus-recente>
```

Puis committer et pousser sur la branche du jour. Jamais repartir de `main` tant que
`main` n'a pas été remis à niveau.

**Ce qu'il y a à faire une fois, côté humain :** fusionner la branche la plus récente dans
`main` (ou la pousser en force sur `main`) depuis l'application. Après ça, le dépôt redevient
linéaire et la règle ci-dessus n'est plus nécessaire.

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
7. **Le conteneur Claude est jetable : ce qui n'est pas committé est perdu.** `notion.py`
   a existé une première fois sans jamais être poussé, et il a fallu le réécrire en entier.
   Tout script qui sert à la routine va dans le dépôt, le jour même.
8. **Les cellules de tableau Notion sont inline-only.** `<td>texte<br />suite</td>` passe ;
   un bloc (liste, titre, callout) dans une cellule, non. Et on ne mélange pas les tableaux
   `|pipe|` et les tableaux `<table>` : ici c'est `<table>`, pour garder `fit-page-width`.
9. **`notion-tableau-de-bord.md` a été supprimé** : c'était un export figé à la semaine 4,
   que `notion.py` régénère maintenant à jour pour n'importe quelle date.

## Points à confirmer auprès des profs

**Cette liste n'est plus tenue ici.** Elle vivait en double et elle a dérivé (elle datait
encore le midterm oral d'anglais au 8 octobre alors qu'il a été reporté au 22). La liste
à jour est le tableau `taches_admin` de `donnees-session.json` ; `carte.py` et `notion.py`
la rendent avec le nombre de jours de retard. Au 1er novembre, les cinq lignes urgentes :

- **Anglais** — carton #723 + photo du reçu, à téléverser au comptoir COOPSCO (44 j).
- **Éthique** — faire confirmer les pondérations par Cyndelle Gagnon : le PDF reçu est une
  version « Hiver 2026 / services sociaux » (37 j).
- **LÉA** — cinq évaluations passées dont rien ne confirme la remise, soit **38 %** de la
  session au statut incertain (16 j).
- **Français** — faire confirmer par Julie Chamberland la date de la dissertation
  intro + conclusion, et pourquoi le mardi 6 octobre saute au calendrier du groupe 00009 (5 j).
- **Anglais** — demander par MIO si l'oral du midterm (15 %) a bien eu lieu le 22 octobre,
  et quelle est la date du Final Speaking & Listening (30 %) selon le groupe (3 j).

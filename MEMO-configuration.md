# Mémo de configuration — carte du jour

Tout ce qu'il faut pour reconstruire le système si la session Claude est perdue.

## Les fichiers du système

| Fichier | Rôle |
|---|---|
| `donnees-session.json` | **Source de vérité unique** : horaire, blocs de travail, toutes les évaluations, lectures, tâches admin, méthodes par cours. C'est le seul fichier à modifier au quotidien. |
| `carte.py` | Génère la carte du jour à partir du JSON. `python3 carte.py` (image), `--texte` (Slack), + une date en argument pour n'importe quel jour. |
| `notion.py` | Génère la page Notion complète à partir du JSON, en Markdown Notion. `python3 notion.py` (stdout) ou `python3 notion.py 2026-10-11 page.md`. Il importe `carte.py` : les deux sorties disent donc toujours la même chose. |
| `notion-tableau-de-bord.md` | La dernière page Notion générée, gardée au dépôt comme instantané. Ne pas l'éditer à la main : elle se régénère. |
| `PLAN-DE-SESSION.md` | Le plan de session écrit le 18 septembre : semaines rouges, découpage des gros travaux, rattrapage. Document d'époque, gardé pour le raisonnement ; les chiffres vivants sont dans le JSON. |

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

## Les trois mécanismes du JSON qu'il faut connaître

1. **`blocs_travail`** — la semaine type, un bloc par jour de la semaine (1 = lundi). S'applique
   à toutes les semaines.
2. **`blocs_speciaux`** — des blocs calés sur une **date précise**. Ils remplacent la semaine type
   ce jour-là. C'est ce qui a servi à planifier la semaine d'études du 12 au 16 octobre, et c'est
   ce qui servira aux révisions de décembre. Une journée de semaine d'études sans bloc spécial
   reste **vide** : un blanc assumé vaut mieux qu'un bloc de cours qui n'a pas lieu cette semaine-là.
3. **`confirmer_lea`** — un examen passé a eu lieu ; une **remise** passée, non : elle a pu ne jamais
   être déposée. Le drapeau marque les remises dont le dépôt n'est pas confirmé. Tant qu'il est là,
   la carte et la page Notion affichent un bloc « statut inconnu » et l'avancement est annoncé comme
   une hypothèse. Quand LÉA confirme : retirer le drapeau **et** mettre `fait: true`.

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
> 4. Régénère aussi la page Notion : `python3 notion.py` et colle la sortie dans la page
>    « Ma session — Automne 2026 » (`3df73824-e620-811e-9e6c-d07440cb6ec7`) avec
>    `replace_content`.
> 5. Si une échéance est dépassée ou qu'une tâche admin est réglée, mets à jour
>    `donnees-session.json` et pousse le commit. Une remise dont la date vient de passer
>    prend `confirmer_lea: true` — jamais `fait: true` tant que LÉA ne l'a pas confirmé.

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
7. **Le conteneur Claude est jetable : ce qui n'est pas commité est perdu.** `notion.py` a été
   écrit une première fois le 10 octobre, jamais commité, et il avait disparu le lendemain.
   Tout script utile se commite le jour même.
8. **Deux Python coexistent dans le conteneur.** `pip install` vise la 3.13 alors que `python3`
   est la 3.11. Pour Pillow : `python3.11 -m pip install pillow`, sinon `carte.py` échoue sur
   `No module named 'PIL'` alors que pip jure que tout est installé.

## Points à confirmer auprès des profs

- **Anglais** : je suis dans le groupe du jeudi. La note « Thursday group: READING WEEK »
  en semaine 7 me vise — mon midterm oral du 8 octobre est à confirmer par MIO.
- **Français** : mon groupe 00009 ne se réunit que le mardi. La colonne du mardi du plan de cours
  saute le 6 octobre sans explication. À vérifier avec Julie Chamberland.
- **Éthique** : le PDF reçu est une version « Hiver 2026 / services sociaux ».
  Confirmer les pondérations avec Cyndelle Gagnon.
- **Anglais** : carton #723 et photo du reçu à téléverser — échéance semaine 3, dépassée.
- **LÉA, le plus important** : quatre remises passées ne sont pas confirmées déposées —
  dissertation de français 20 %, TP2 ORM 10 %, TP1 VueJS 4 %, TP2 Vue Router 4 %.
  **38 % de points au statut incertain.** Tant que ce n'est pas tranché, l'avancement affiché
  est une hypothèse.

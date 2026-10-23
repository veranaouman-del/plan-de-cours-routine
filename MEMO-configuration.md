# Mémo de configuration — carte du jour

Tout ce qu'il faut pour reconstruire le système si la session Claude est perdue.

## Les fichiers du système

| Fichier | Rôle |
|---|---|
| `donnees-session.json` | **Source de vérité unique** : horaire, blocs de travail, toutes les évaluations, lectures, tâches admin. C'est le seul fichier à modifier au quotidien. |
| `carte.py` | Génère la carte du jour à partir du JSON. `python3 carte.py` (image), `--texte` (Slack), + une date en argument pour n'importe quel jour. |
| `notion.py` | Régénère **toute** la page Notion à partir du même JSON. `python3 notion.py` sort `notion-page.md`, à passer tel quel à l'outil Notion `update-page`, commande `replace_content`. |
| `note-du-jour.md` | Facultatif. S'il existe, son contenu est inséré en encadré sous la priorité de la page Notion. C'est là qu'on écrit le découpage d'une journée particulière. Réécrit chaque jour. |
| `PLAN-DE-SESSION.md` | Le plan complet de la session : semaines rouges, semaine type, découpage des gros travaux, méthodes par cours, rattrapage. |

## Identifiants à conserver

- Design Canva du tableau de bord : **DAHVgw0Y3QU** (page unique, 800 × 2000)
- Doc Canva du plan de session : **DAHVg0-l5S0**
- Page Notion « Ma session — Automne 2026 » : **3df73824-e620-811e-9e6c-d07440cb6ec7**
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

## Ce que fait la routine, chaque matin

1. `python3.13 carte.py --texte` → le texte de la carte du jour.
2. Un message Slack enrichi dans le DM **D0C2RFRRWKU** : priorité, découpage du bloc
   de travail, retards, échéances, suite de la semaine, avancement.
3. Une notification push avec la priorité et tout ce qui tombe à J-1 ou J-0.
4. `python3.13 notion.py` → `notion-page.md`, poussé sur la page Notion en
   `replace_content` (ça remplace, ça n'empile pas — vérifié).
5. Le design Canva **DAHVgw0Y3QU** recalé sur la journée : sous-titre, « À faire
   aujourd'hui », la semaine, les échéances.
6. Les changements de `donnees-session.json` commités et poussés sur la branche du jour
   (`claude/epic-newton-…`, un nom différent à chaque exécution).

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
7. **Pillow n'existe pas pour le `python3` du conteneur (3.11).** `pip install pillow`
   l'installe pour 3.13. Donc : `pip install --break-system-packages pillow`, puis
   lancer les scripts avec `python3.13`, pas `python3`. Le mode `--texte` de `carte.py`,
   lui, n'a besoin de rien.
8. **Les lignes du bloc « À FAIRE » de Canva débordent au-delà de 44 caractères.**
   Au-delà, la ligne se replie, le bloc grandit et recouvre les grands chiffres.
   Celles de la bande « échéances » tiennent jusqu'à ~105 caractères ; celles de la
   bande « ma semaine », jusqu'à ~85. Vérifier la hauteur des blocs dans la réponse
   de `edit-design` : si elle a grandi, une ligne s'est repliée.
9. **La routine repart d'une branche neuve chaque matin, mais le dépôt cloné est
   figé au 18 septembre.** Premier geste de la journée : `git fetch origin`, repérer
   la branche `claude/epic-newton-*` la plus récente et s'y recaler
   (`git merge --ff-only origin/<branche>` ; `git checkout -B` est refusé par le
   classificateur du mode auto). Sans ça, tout le travail de la veille est perdu.
10. **Le dépôt est reparti du 18 septembre pendant un mois.** Chaque exécution
   quotidienne reconstruisait `notion.py` et les mises à jour du JSON, puis les
   perdait avec le conteneur. Tout changement d'état se commite **le jour même**,
   sinon le lendemain repart d'un plan périmé.

## Points à confirmer auprès des profs

- **Anglais** : je suis dans le groupe du jeudi. La note « Thursday group: READING WEEK »
  en semaine 7 me vise — mon midterm oral du 8 octobre est à confirmer par MIO.
- **Français** : mon groupe 00009 ne se réunit que le mardi. La colonne du mardi du plan de cours
  saute le 6 octobre sans explication. À vérifier avec Julie Chamberland.
- **Éthique** : le PDF reçu est une version « Hiver 2026 / services sociaux ».
  Confirmer les pondérations avec Cyndelle Gagnon.
- **Anglais** : carton #723 et photo du reçu à téléverser — échéance semaine 3, dépassée.
- **Anglais** : la date du midterm oral (22 octobre) est **déduite**, pas confirmée — le
  groupe du jeudi était en reading week à la semaine 7. Le champ `a_confirmer` de
  l'évaluation le dit.
- **LÉA** : trois remises passées dont le dépôt n'est pas confirmé (TP2 ORM, TP1 VueJS,
  TP2 Vue Router) — 18 % de points au statut incertain. Marquées `a_verifier_lea` dans
  le JSON ; retirer le drapeau une fois vérifié.

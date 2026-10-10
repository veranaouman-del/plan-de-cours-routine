# Mémo de configuration — carte du jour

Tout ce qu'il faut pour reconstruire le système si la session Claude est perdue.

## Les fichiers du système

| Fichier | Rôle |
|---|---|
| `donnees-session.json` | **Source de vérité unique** : horaire, blocs de travail, toutes les évaluations, lectures, tâches admin. C'est le seul fichier à modifier au quotidien. |
| `carte.py` | Génère la carte du jour à partir du JSON. `python3 carte.py` (image), `--texte` (Slack), + une date en argument pour n'importe quel jour. |
| `notion.py` | Génère la page Notion « Ma session » à partir du même JSON. `python3 notion.py` (aujourd'hui), + une date en argument. Le texte produit se passe tel quel à `notion-update-page` en `replace_content`. |
| `notion-tableau-de-bord.md` | La dernière sortie de `notion.py`, gardée dans le dépôt comme témoin. Ne pas l'éditer à la main : la régénérer. |
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
> 1. `pip install --quiet pillow` si nécessaire, puis `python3 carte.py --texte`
>    à la racine du dépôt. Le script lit `donnees-session.json` et sort la carte
>    d'aujourd'hui : cours, priorité, tâches avec leur étape de préparation,
>    échéances avec compteurs J-x, blocs de travail, avancement par cours.
> 2. Poste ce texte tel quel dans mon DM Slack, canal D0C2RFRRWKU.
>    Titres en MAJUSCULES, puces, JAMAIS de tableau Markdown — Slack les supprime.
> 2b. `python3 notion.py` et passe la sortie à `notion-update-page` en `replace_content`
>    sur la page 3df73824-e620-811e-9e6c-d07440cb6ec7. Là, les tableaux passent.
> 3. Envoie-moi une notification push avec ma priorité du jour et tout ce qui
>    tombe à J-3 ou moins.
> 4. Mets aussi à jour le visuel Canva DAHVgw0Y3QU (voir plus bas pour les contraintes
>    de gabarit) et la page Notion.
> 5. Si une échéance est dépassée ou qu'une tâche admin est réglée, mets à jour
>    `donnees-session.json` et pousse le commit.

Le visuel Canva (design DAHVgw0Y3QU) se met à jour tous les jours lui aussi, directement
dans le design : `read-design` avec `open_transaction` pour récupérer les locator_id, puis
des `replace_text`, puis `commit`. C'est le *lien d'export* qui expire en quelques heures,
pas le design — donc on édite le design, on n'exporte pas.

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
6. **`notion.py` avait disparu.** La page Notion portait « généré par notion.py » en pied
   alors que le script n'avait jamais été commité : chaque exécution le réécrivait de zéro.
   Il est maintenant dans le dépôt, et il importe `carte.py` pour partager le même moteur —
   une échéance modifiée bouge dans les deux sorties à la fois.
7. **Le gabarit Canva ne se redimensionne pas tout seul.** Les blocs de couleur et les
   deux gros chiffres sont à des positions fixes. Une puce de « À FAIRE » qui dépasse
   ~47 caractères passe sur deux lignes, la liste grandit vers le bas et vient toucher le
   trait rouge des chiffres. Garder 4 puces d'au plus 47 caractères, et vérifier la
   vignette renvoyée par `edit-design` **avant** de faire `commit`.
8. **Le téléchargement de fichiers vers Slack est bloqué** par la politique réseau de
   l'environnement Claude. L'image doit être glissée à la main, ou passer par un lien.
9. **Une remise dont la date est passée disparaissait de la carte.** La section
   « À confirmer — remises passées non cochées » remonte tout ce qui est resté à
   `"fait": false` après son échéance, avec le total de points au statut incertain.
   Une évaluation qui a **bel et bien eu lieu** se coche (`"fait": true`) ; une **remise**
   dont on n'est pas sûr reste ouverte et reçoit une note `"a_confirmer"`. Ne jamais
   cocher une remise en bloc parce que sa date est passée : c'est le seul garde-fou
   contre un travail oublié.
10. **`python3` n'est pas la bonne version dans l'environnement Claude** : c'est un 3.11
   sans Pillow, alors que Pillow est installé pour 3.13. Pour l'image : `python3.13 carte.py`.
   Les modes `--texte` et `notion.py` marchent avec les deux.
11. **Ne jamais ouvrir le JSON en lecture et en écriture dans la même expression Python** —
   le mode `"w"` vide le fichier avant que la lecture s'exécute. Lire, fermer, puis écrire.
12. **🔴 Le dépôt se refourche tous les jours.** Chaque exécution de la routine part d'une
   branche neuve tirée de `main`, et **rien n'est jamais fusionné dans `main`**. Résultat :
   26 branches parallèles qui contiennent chacune 1 à 3 commits perdus, et `notion.py`
   réécrit de zéro presque chaque jour depuis le 18 septembre. La branche du jour est
   consolidée, mais **le vrai correctif est de fusionner la branche du jour dans `main`**
   (un seul bouton sur GitHub) pour que le lendemain reparte du bon état.

## Les semaines sans cours : `blocs_exception`

La semaine type (`blocs_travail`) est calée sur les jours de cours. Une semaine sans cours
— semaine d'études, congé — ne se travaille pas avec cet horaire-là. D'où `blocs_exception` :

```json
{"date": "2026-10-14", "debut": "09:30", "fin": "12:30",
 "titre": "GROS BLOC — Programmation : démarrer le TP3", "focus": ["devlog"]}
```

Dès qu'une date porte au moins un bloc d'exception, **ces blocs remplacent entièrement**
ceux de la semaine type pour cette journée. Le champ `focus` pilote aussi les tâches
affichées. La semaine d'études du 12 au 16 octobre est déjà chargée.

## Points à confirmer auprès des profs

*Mis à jour le 10 octobre. Le midterm oral d'anglais (8 oct.) et la question du mardi
6 octobre sont tombés d'eux-mêmes : les deux dates sont passées. Ils sortent de la liste.*

- **LÉA** : quatre remises passées ne sont toujours pas cochées — dissertation de français
  20 %, TP2 ORM 10 %, TP1 VueJS 4 %, TP2 Vue Router 4 %. **38 % au statut incertain.**
  C'est le point le plus urgent de la liste, et il se règle en cinq minutes sur LÉA.
- **Anglais** : carton #723 et photo du reçu à téléverser — échéance semaine 3, trois
  semaines de retard. À régler avant le retour en classe du 19 octobre.
- **Éthique** : le PDF reçu est une version « Hiver 2026 / services sociaux ».
  Confirmer les pondérations avec Cyndelle Gagnon — l'entrevue finale vaut 40 %.
- **LÉA** : relever les résultats de la semaine 7 (intra 25 %, Éval. #1 Web 25 %, les deux
  midterms d'anglais, examen de philo 25 %) et **réajuster le champ `difficulte`**.
  C'est ce réglage qui redistribue les blocs de travail d'ici décembre.
- **Prog. Web** : dates officielles de remise des TP et répartition exacte des 20 %,
  à vérifier auprès de David Lacasse.

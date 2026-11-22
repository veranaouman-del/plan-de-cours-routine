# Mémo de configuration — carte du jour

Tout ce qu'il faut pour reconstruire le système si la session Claude est perdue.

## Les fichiers du système

| Fichier | Rôle |
|---|---|
| `donnees-session.json` | **Source de vérité unique** : horaire, blocs de travail, toutes les évaluations, lectures, tâches admin. C'est le seul fichier à modifier au quotidien. |
| `carte.py` | Génère la carte du jour à partir du JSON. `python3 carte.py` (image), `--texte` (Slack), + une date en argument pour n'importe quel jour. |
| `PLAN-DE-SESSION.md` | Le plan complet de la session : semaines rouges, semaine type, découpage des gros travaux, méthodes par cours, rattrapage. |

## Identifiants à conserver

- Design Canva du tableau de bord : **DAHVgw0Y3QU** (une page, 800 × 2000)
  - édition : https://www.canva.com/d/pwsXJQ5M_1sYEcR · lecture : https://www.canva.com/d/Qsn33CCShz4qcOF
- Page Notion « Ma session — Automne 2026 » : **3df73824-e620-811e-9e6c-d07440cb6ec7**
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
7. **Pillow n'existe que pour `python3.13`** dans le conteneur, alors que `python3` est
   un 3.11 dont le `PIL` système est cassé (`ImportError: cannot import name _imaging`).
   Pour l'image : `python3.13 carte.py`. Le mode `--texte` marche avec n'importe lequel.
8. **Le dépôt prend du retard sur Notion.** La page Notion se met à jour tous les jours,
   `donnees-session.json` non — et c'est lui que lit la carte. Avant de générer la carte,
   relire la page Notion et reporter dans le JSON ce qui a bougé : sinon la carte annonce
   des échéances déjà passées et rate les vraies. Réconcilié le 20 novembre.
9. **Les évaluations passées dont le dépôt n'est pas confirmé** portent `a_verifier_lea`.
   C'est ce qui distingue « joué » de « supposé joué » dans l'avancement.
10. **Chaque exécution de la routine part d'une branche neuve, clonée depuis `main`**, qui
   est resté à l'état de septembre. Le dépôt livré à la session a donc toujours deux mois
   de retard sur le travail de la veille. **Premier geste de chaque routine :**
   `git fetch origin --prune`, puis repérer la branche au commit le plus récent
   (`for b in $(git branch -r | grep -v HEAD); do echo "$(git log -1 --format=%cI $b) $b"; done | sort -r | head -3`)
   et `git merge --ff-only` dessus. Sans ça, la carte du jour régresse d'un mois.
11. **Le visuel Canva se met à jour tous les jours**, contrairement à ce qui était écrit ici
   avant : design `DAHVgw0Y3QU`, une seule page, neuf blocs de texte. `read-design` avec
   `open_transaction: true` donne les `locator_id`, puis `replace_text` sur chacun, puis
   `commit`. Les textes de remplacement doivent faire **le même nombre de lignes** que
   ceux qu'ils remplacent : les blocs ne se redimensionnent pas.
12. **Dans le bloc « À FAIRE AUJOURD'HUI » du Canva, chaque puce doit tenir sur une seule
   ligne : ~50 caractères maximum.** À 27 px, une puce plus longue passe à la ligne, le bloc
   grandit vers le bas (172 px → 313 px le 22 novembre) et vient **recouvrir les deux grands
   chiffres « 55 % » et « 97 % »**. Le `document` renvoyé par `edit-design` donne la
   `height` du bloc : si elle a bougé, raccourcir et rejouer avant de `commit`.
13. **`pip` vise python3.13, `python3` est un 3.11.** `pip install pillow` installe donc des
   roues `cp313` invisibles depuis `python3`, et l'erreur reste la même après réinstallation.
   Le plus simple reste `python3.13 carte.py` (piège 7).

## Points à confirmer auprès des profs

État au 20 novembre. La liste vivante est dans `taches_admin` de `donnees-session.json`,
triée par `priorite` ; celle-ci n'en est que le résumé.

- **Éthique** : s'inscrire sur Microsoft Bookings pour l'entrevue finale (40 %). Ouvert
  depuis le 6 novembre. Plus grosse note de la session, et les plages partent dans l'ordre.
- **Anglais** : le Final Speaking & Listening (30 %) tombe-t-il le 26 novembre ou le
  3 décembre ? Question posée le 12 novembre, toujours sans réponse.
- **LÉA** : neuf évaluations passées, 87 % de points, dont rien ne confirme le dépôt.
  Dont le Contrôle 2, qui n'a peut-être jamais eu lieu.
- **Prog. Web** : les 4 % par TP sont une hypothèse. Demander la répartition réelle des 20 %.
- **Éthique** : le PDF reçu est une version « Hiver 2026 / services sociaux ».
  Confirmer les pondérations avec Cyndelle Gagnon.
- **Anglais** : carton #723 et photo du reçu à téléverser — échéance semaine 3, dépassée.

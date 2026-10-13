# Page Notion — ce fichier ne contient plus le tableau de bord

Le tableau de bord Notion n'est plus écrit à la main. Il est **généré** à partir de
`donnees-session.json`, comme la carte du jour :

```bash
python3 notion.py                     # sur la sortie standard
python3 notion.py --sortie page.md    # dans un fichier
python3 notion.py 2026-12-07          # la page telle qu'elle sera ce jour-là
```

Le texte produit se colle tel quel dans `replace_content` du connecteur Notion, sur la
page **« Ma session — Automne 2026 »** :
`3df73824-e620-811e-9e6c-d07440cb6ec7`
(https://app.notion.com/p/3df73824e620811e9e6cd07440cb6ec7)

## Pourquoi ce fichier a été vidé

Il contenait une copie figée du tableau de bord au **18 septembre** : semaine 4 sur 15,
4 % de la session jouée, des compteurs J-x calculés pour ce jour-là. Un mois plus tard,
chacun de ces chiffres était faux, et rien dans le fichier ne le signalait. Une copie
périmée d'une donnée vivante est pire qu'une absence de copie : on la lit sans se méfier.

La règle du système est la même partout : **une seule source de vérité,
`donnees-session.json`, et des scripts qui en dérivent tout le reste.**

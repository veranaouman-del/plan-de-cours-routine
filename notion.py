# -*- coding: utf-8 -*-
"""Page Notion « Ma session » — générée à partir de donnees-session.json.

    python3 notion.py                 -> le markdown de la page pour aujourd'hui
    python3 notion.py 2026-10-07      -> pour une date précise

Même source de vérité que carte.py : une échéance qui bouge se change à un seul
endroit. Les sections qui périment (compte à rebours, semaine en cours, avancement)
sont recalculées à chaque exécution ; les sections stables (méthodes, semaine type)
sont du texte fixe ci-dessous.
"""
import sys
import datetime as dt

from carte import (JOURS, MOIS, charger, d, semaine_de, chantiers, avancement,
                   cours_du_jour, blocs_du_jour, etape)

def heure(h):
    """08:55 -> « 8 h 55 », 16:00 -> « 16 h »."""
    hh, mm = h.split(":")
    return "%d h" % int(hh) if mm == "00" else "%d h %s" % (int(hh), mm)


ICONE = {"devlog": "💻", "web": "🌐", "litt": "📕", "anglais": "🗣️", "philo": "⚖️"}
ABREV_M = ["janv.", "févr.", "mars", "avril", "mai", "juin", "juil.",
           "août", "sept.", "oct.", "nov.", "déc."]
JOUR_COURT = ["lun.", "mar.", "mer.", "jeu.", "ven.", "sam.", "dim."]


def date_courte(j):
    jour = "1er" if j.day == 1 else str(j.day)
    return "%s %s %s" % (JOUR_COURT[j.weekday()], jour, ABREV_M[j.month - 1])


def puce(reste):
    if reste <= 4:
        return "🔴"
    if reste <= 11:
        return "🟠"
    return "🔵"


def gras(txt, oui):
    return "**%s**" % txt if oui else txt


def entete(data, jour, sem):
    s = data["session"]
    a, b = (d(x) for x in s["semaine_etudes"])
    return [
        "> Cégep de Granby · Techniques de l'informatique (420.B0) · 24 août → 11 décembre",
        "> **Semaine %s sur 15** · Semaine d'études : %d au %d %s" % (
            sem, a.day, b.day, MOIS[b.month - 1]),
        "",
        "---",
        "",
    ]


def section_aujourdhui(data, jour, actifs):
    L = ["## 📍 Aujourd'hui — %s %d %s" % (JOURS[jour.weekday()], jour.day, MOIS[jour.month - 1]), ""]

    cours = cours_du_jour(data, jour)
    if cours:
        for c in cours:
            info = data["cours"][c["cours"]]
            L.append("- %s **%s** · %s – %s · %s" % (
                ICONE[c["cours"]], info["nom"],
                heure(c["debut"]), heure(c["fin"]), c["local"]))
    else:
        L.append("- *Aucun cours aujourd'hui.*")

    for b in blocs_du_jour(data, jour):
        L.append("- 🎯 **%s** · %s – %s" % (
            b["titre"], heure(b["debut"]), heure(b["fin"])))

    if actifs:
        p = actifs[0]
        L += ["", "> 🔥 **Priorité du jour :** %s %s — %s (%s %%), dans %d jour%s." % (
            ICONE[p["cours"]], data["cours"][p["cours"]]["nom"], p["titre"],
            p["poids"], p["reste"], "s" if p["reste"] > 1 else "")]

    return L + ["", "---", ""]


def section_prochains_jours(data, jour, actifs):
    """Les sept prochains jours : ce qui se prépare, pas seulement ce qui tombe."""
    L = ["## 🗓️ Les 7 prochains jours", "",
         "<table header-row=\"true\">", "<tr>", "<td>Jour</td>", "<td>Cours</td>",
         "<td>Ce que je fais</td>", "</tr>"]

    for n in range(7):
        j = jour + dt.timedelta(days=n)
        cours = cours_du_jour(data, j)
        blocs = blocs_du_jour(data, j)
        acts = chantiers(data, j)

        tombe = [e for e in data["evaluations"]
                 if not e.get("fait") and d(e["date"]) == j]
        if tombe:
            quoi = " · ".join("🔥 **%s %s — %s %%**" % (
                ICONE[e["cours"]], e["titre"], e["poids"]) for e in tombe)
        elif blocs:
            focus = set()
            for b in blocs:
                focus.update(b["focus"])
            cible = [e for e in acts if e["cours"] in focus] or acts
            if cible:
                e = cible[0]
                quoi = "%s %s — %s *(%s)*" % (
                    ICONE[e["cours"]], data["cours"][e["cours"]]["court"],
                    e["titre"], etape(e).lower())
            else:
                quoi = "🔁 Rattrapage et plan de la semaine"
        else:
            quoi = "😮‍💨 Journée libre — c'est voulu"

        heures = "<br>".join("%s – %s" % (heure(b["debut"]), heure(b["fin"]))
                     for b in blocs)
        cours_txt = " · ".join(ICONE[c["cours"]] + " " + data["cours"][c["cours"]]["court"]
                               for c in cours) or "—"
        libelle = gras("%s %s" % (JOUR_COURT[j.weekday()],
                          "1er" if j.day == 1 else j.day), n == 0)
        if n == 0:
            libelle += " ← *aujourd'hui*"

        L += ["<tr>", "<td>%s</td>" % libelle,
              "<td>%s%s</td>" % (cours_txt, ("<br>" + heures) if heures else ""),
              "<td>%s</td>" % quoi, "</tr>"]

    return L + ["</table>", "", "---", ""]


def section_echeances(data, jour):
    L = ["## 📅 Toutes mes échéances à venir", "",
         "> 💡 Sélectionne ce tableau → **Transformer en base de données** "
         "pour filtrer par cours et cocher au fur et à mesure.", "",
         "<table header-row=\"true\">", "<tr>", "<td></td>", "<td>Date</td>", "<td>Cours</td>",
         "<td>Évaluation</td>", "<td>Poids</td>", "<td>Compte à rebours</td>", "</tr>"]

    a_venir = sorted((e for e in data["evaluations"]
                      if not e.get("fait") and d(e["date"]) >= jour),
                     key=lambda e: (d(e["date"]), -e["poids"]))
    for e in a_venir:
        reste = (d(e["date"]) - jour).days
        info = data["cours"][e["cours"]]
        poids = "formatif" if e["poids"] == 0 else gras("%s %%" % e["poids"], e["poids"] >= 20)
        L += ["<tr>", "<td>%s</td>" % puce(reste), "<td>%s</td>" % date_courte(d(e["date"])),
              "<td>%s %s</td>" % (ICONE[e["cours"]], info["court"]),
              "<td>%s</td>" % e["titre"], "<td>%s</td>" % poids,
              "<td>%s</td>" % ("**aujourd'hui**" if reste == 0 else "J-%d" % reste), "</tr>"]

    return L + ["</table>", "", "---", ""]


def section_lectures(data, jour):
    a_venir = [l for l in data["lectures"] if d(l["pour"]) >= jour]
    if not a_venir:
        return []
    L = ["## 📖 Mes lectures", "", "<table header-row=\"true\">", "<tr>",
         "<td>Pour le</td>", "<td>Cours</td>", "<td>À lire</td>", "</tr>"]
    for l in sorted(a_venir, key=lambda x: d(x["pour"])):
        j = d(l["pour"])
        L += ["<tr>", "<td>%d %s</td>" % (j.day, ABREV_M[j.month - 1]),
              "<td>%s %s</td>" % (ICONE[l["cours"]], data["cours"][l["cours"]]["court"]),
              "<td>%s</td>" % l["quoi"], "</tr>"]
    return L + ["</table>", "", "---", ""]


def section_admin(data, jour):
    L = ["## ✅ À régler tout de suite", ""]
    rien = True
    for t in data["taches_admin"]:
        if t["pour"] == "recurrent":
            continue
        reste = (d(t["pour"]) - jour).days
        if reste > 30:
            continue
        rien = False
        if reste < 0:
            marque = "🔴 %s — *%d jour%s de retard*" % (
                gras(t["quoi"], True), -reste, "s" if reste < -1 else "")
        else:
            quand = "aujourd'hui" if reste == 0 else "J-%d" % reste
            puce_t = "🟠" if t.get("urgent") else "🔵"
            marque = "%s %s — *%s*" % (puce_t, gras(t["quoi"], t.get("urgent")), quand)
        L.append("- [ ] %s" % marque)
    if rien:
        L.append("- *Rien en attente. C'est rare — profites-en.*")
    return L + ["", "---", ""]


def section_avancement(data, jour):
    av = avancement(data, jour)
    L = ["## 📊 Mon avancement", "", "<table header-row=\"true\">", "<tr>",
         "<td>Cours</td>", "<td>Part de la note déjà jouée</td>", "</tr>"]
    for cle, (nom, pct) in sorted(av.items(), key=lambda kv: -kv[1][1]):
        L += ["<tr>", "<td>%s %s</td>" % (ICONE[cle], nom), "<td>%s %%</td>" % pct, "</tr>"]
    L.append("</table>")
    moyenne = sum(p for _, p in av.values()) / len(av)
    L += ["", "> **%d %%** de la session est joué, tous cours confondus." % round(moyenne),
          "", "---", ""]
    return L


# Sections stables : elles ne dépendent pas de la date.
FIXE = """## 🔴 Mes semaines rouges

<table header-row="true">
<tr>
<td>Semaine</td>
<td>Dates</td>
<td>Ce qui tombe</td>
<td>La règle</td>
</tr>
<tr>
<td>**6**</td>
<td>28 sept. – 2 oct.</td>
<td>Midterm anglais 20 %, examen Éthique 25 %</td>
<td>**45 % en 48 h.** Les tableaux de philo finis mercredi soir</td>
</tr>
<tr>
<td>**7**</td>
<td>5 – 9 oct.</td>
<td>Intra 25 %, oral d'anglais 15 %, Éval. #1 Web 25 %</td>
<td>**65 % en quatre jours.** Tout prêt le 4 octobre</td>
</tr>
<tr>
<td>**11**</td>
<td>9 – 13 nov.</td>
<td>Dissertation de philo 20 %, contrôle 2, remise TP3</td>
<td>Le plan du 6 nov. est la répétition générale</td>
</tr>
<tr>
<td>**15**</td>
<td>7 – 11 déc.</td>
<td>Quatre finaux : 30 %, 35 %, 30 %, 35 % + entrevue 40 %</td>
<td>Les révisions commencent le **16 novembre**</td>
</tr>
</table>

---

## 🗓️ Ma semaine type

<table header-row="true">
<tr>
<td>Quand</td>
<td>Durée</td>
<td>Ce que je fais</td>
</tr>
<tr>
<td>Lundi 16 h 30 – 18 h</td>
<td>1 h 30</td>
<td>🌐 Prog. Web — le TP en cours</td>
</tr>
<tr>
<td>**Mardi 13 h 30 – 16 h 30**</td>
<td>**3 h**</td>
<td>📕⚖️ **Gros bloc — français et philo**</td>
</tr>
<tr>
<td>**Mercredi 11 h 15 – 16 h**</td>
<td>**4 h**</td>
<td>💻🌐 **Gros bloc — programmation**</td>
</tr>
<tr>
<td>**Jeudi 12 h 30 – 15 h 30**</td>
<td>**3 h**</td>
<td>🗣️ **Gros bloc — anglais et prise d'avance**</td>
</tr>
<tr>
<td>Vendredi 11 h 45 – 12 h 45</td>
<td>1 h</td>
<td>⚖️ Philo à chaud, les notes du matin</td>
</tr>
<tr>
<td>Samedi 9 h – 12 h</td>
<td>3 h</td>
<td>📖 Lectures longues</td>
</tr>
<tr>
<td>Dimanche 16 h – 18 h</td>
<td>2 h</td>
<td>🔁 **Rattrapage** et plan de la semaine</td>
</tr>
</table>

> ⚠️ Vendredi soir, samedi après-midi et dimanche matin restent **vides**. Ce n'est pas du temps perdu : c'est ce qui rend les 17 h 30 restantes tenables semaine après semaine.

---

## 🧠 Mes méthodes, cours par cours

### ⚖️ Éthique et politique — *ma matière la plus lourde ce mois-ci*
Droit aux notes de cours à **toutes** les évaluations. La vraie préparation, c'est donc de **construire de bonnes notes**, pas de mémoriser. Un tableau par penseur : thèse, critère du juste, objection principale, exemple concret. C'est ce tableau qu'on apporte à l'examen.

### 📕 Littérature et imaginaire
Annoter **pendant** la lecture, jamais après. Un carnet de citations classées par thème. Garder 10 minutes de relecture linguistique en fin de rédaction — la langue vaut **25 %** de chaque dissertation.

### 🗣️ Anglais
Tout se joue en classe. Remplir le journal Odyssey **le jour même** (5 % garantis). Les évaluations orales valent **45 %** du cours : elles se préparent **à voix haute**, pas par écrit.

### 💻 Développement de logiciels
Le code se retient par les doigts. Refaire les exercices dirigés **sans la correction**, puis comparer. S'entraîner à écrire du code **sur papier** — c'est ce qui est demandé à l'examen.

### 🌐 Programmation Web I
Chaque TP s'appuie sur le précédent. Un TP bâclé se paie deux fois. Après chaque remise, noter en trois lignes **ce qui a bloqué** : c'est exactement ce qui tombera à l'Évaluation #1.

---

## 🔁 Quand je prends du retard

Le bloc du dimanche 16 h – 18 h existe pour ça. L'ordre est toujours le même : **ce qui est noté le plus lourd et qui tombe le plus tôt d'abord.** Une lecture en retard se rattrape ; une remise manquée, non.

Si deux semaines de suite débordent, ce n'est pas un problème d'effort : c'est que le plan est trop chargé. On retire quelque chose plutôt que d'accumuler.

---
"""


def page(data, jour):
    sem = semaine_de(data, jour)
    actifs = chantiers(data, jour)
    L = ["# 🎓 Ma session — Automne 2026", ""]
    L += entete(data, jour, sem)
    L += section_aujourdhui(data, jour, actifs)
    L += section_prochains_jours(data, jour, actifs)
    L += section_admin(data, jour)
    L += section_echeances(data, jour)
    L += section_lectures(data, jour)
    L += FIXE.split("\n")
    L += section_avancement(data, jour)
    L.append("*Mis à jour automatiquement le %d %s %d · source : `donnees-session.json`*"
             % (jour.day, MOIS[jour.month - 1], jour.year))
    return "\n".join(L)


if __name__ == "__main__":
    jour = d(sys.argv[1]) if len(sys.argv) > 1 else dt.date.today()
    sys.stdout.write(page(charger(), jour))

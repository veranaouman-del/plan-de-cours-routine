# -*- coding: utf-8 -*-
"""Tableau de bord Notion — Automne 2026.

Régénère la page Notion « Ma session — Automne 2026 » à partir de
donnees-session.json, en Markdown enrichi Notion (tableaux <table>).

    python3 notion.py                 -> la page d'aujourd'hui sur la sortie standard
    python3 notion.py 2026-10-07      -> la page telle qu'elle serait ce jour-là
    python3 notion.py --sortie x.md   -> écrit dans un fichier

Le contenu est ensuite poussé dans Notion avec la commande `replace_content`
du connecteur (page 3df73824-e620-811e-9e6c-d07440cb6ec7).

Rien n'est codé en dur : carte.py et notion.py lisent le même JSON.
"""
import datetime as dt
import sys

import carte
from carte import (JOURS, MOIS, avancement, blocs_du_jour, chantiers,
                   chantiers_tous, charger, cours_du_jour, court, d,
                   en_semaine_etudes, etape, jx, semaine_de, taches_du_jour)

PAGE_ID = "3df73824-e620-811e-9e6c-d07440cb6ec7"

# Les étiquettes de carte.py, en version lisible pour Notion.
LIBELLE = {"RETARD": "En retard", "ADMIN": "Admin", "LECTURE": "Lecture",
           "REMISE": "Remise", "FINIR": "Finir", "AVANCER": "Avancer",
           "RELIRE": "Relire", "TEST BLANC": "Test blanc", "FICHES": "Fiches",
           "NOTES": "Notes"}


def em(data, cle):
    return data["cours"][cle].get("emoji", "")


def hm(s):
    return s.replace(":", " h ")


def table(entetes, lignes):
    out = ['<table header-row="true">', "<tr>"]
    out += ["<td>%s</td>" % h for h in entetes]
    out.append("</tr>")
    for l in lignes:
        out.append("<tr>")
        out += ["<td>%s</td>" % c for c in l]
        out.append("</tr>")
    out.append("</table>")
    return "\n".join(out)


def gras_si(txt, lourd):
    return "**%s**" % txt if lourd else txt


# --------------------------------------------------------------------------
# Semaines rouges : au moins deux évaluations, ou une seule qui pèse 20 % et plus
# --------------------------------------------------------------------------
def semaines_rouges(data, jour):
    paires = sorted(((int(n), d(debut)) for n, debut in data["session"]["semaines"].items()),
                    key=lambda p: p[1])
    rouges = []
    for i, (num, debut) in enumerate(paires):
        fin = debut + dt.timedelta(days=6)
        dedans = [e for e in data["evaluations"] if debut <= d(e["date"]) <= fin]
        if not dedans:
            continue
        lourde = max(dedans, key=lambda e: e["poids"])
        if len(dedans) < 2 and lourde["poids"] < 20:
            continue
        if fin < jour:            # semaine déjà passée : elle ne compte plus
            continue
        cours_touches = len({e["cours"] for e in dedans})
        quoi = ", ".join("%s %s %s" % (em(data, e["cours"]), e["titre"],
                                       "%d %%" % e["poids"] if e["poids"] else "formatif")
                         for e in sorted(dedans, key=lambda e: d(e["date"])))
        if num == 15:
            regle = ("%d évaluations dans %d cours différents. Les révisions commencent "
                     "trois semaines avant, pas la veille." % (len(dedans), cours_touches))
        else:
            regle = ("%d évaluations dans %d cours. La plus lourde : %s %d %% en %s. "
                     "Rien de neuf ne commence ce lundi-là."
                     % (len(dedans), cours_touches, lourde["titre"], lourde["poids"],
                        data["cours"][lourde["cours"]]["court"]))
        rouges.append(["**%d**" % num,
                       "%s – %s" % (court(debut), court(fin)),
                       quoi, regle])
    return rouges


# --------------------------------------------------------------------------
# La page
# --------------------------------------------------------------------------
def page(data, jour):
    sem = semaine_de(data, jour)
    actifs = chantiers(data, jour)
    L = []

    # ---- en-tête -----------------------------------------------------------
    fin_session = d(data["session"]["fin"])
    L.append("> %s — Cégep de Granby" % data["programme"].split(" - ")[0])
    L.append("> Du %s au %s · Semaine d'études : %s au %s"
             % (court(d(data["session"]["debut"])), court(fin_session),
                court(d(data["session"]["semaine_etudes"][0])),
                court(d(data["session"]["semaine_etudes"][1]))))
    if en_semaine_etudes(data, jour):
        L.append("> **Semaine d'études et d'encadrement.** Page mise à jour le %s %d %s."
                 % (JOURS[jour.weekday()], jour.day, MOIS[jour.month - 1]))
    else:
        L.append("> **Nous sommes en semaine %s sur 15.** Page mise à jour le %s %d %s."
                 % (sem, JOURS[jour.weekday()], jour.day, MOIS[jour.month - 1]))
    L.append("---")

    # ---- aujourd'hui -------------------------------------------------------
    L.append("## ☀️ Aujourd'hui — %s %d %s" % (JOURS[jour.weekday()], jour.day, MOIS[jour.month - 1]))
    cj = cours_du_jour(data, jour)
    L.append("**Mes cours**")
    if cj:
        for c in cj:
            L.append("- %s `%s – %s` %s · %s"
                     % (em(data, c["cours"]), hm(c["debut"]), hm(c["fin"]),
                        data["cours"][c["cours"]]["nom"], c["local"]))
    else:
        L.append("- *Aucun cours aujourd'hui.*")

    if actifs:
        p = actifs[0]
        L.append("> 🔴 **Ma priorité : %s** — %s, %d %%, %s"
                 % (p["titre"], data["cours"][p["cours"]]["court"], p["poids"], jx(p["reste"])))
        L.append("> Si je ne fais qu'une seule chose aujourd'hui, c'est celle-là.")

    aujourdhui = [e for e in chantiers_tous(data, jour) if e["reste"] == 0]
    if len(aujourdhui) > 1:
        L.append("> ⚠️ **%d échéances tombent aujourd'hui** : %s. Tout ce qui se remet en ligne "
                 "part avant le premier cours — un envoi raté ne se rattrape pas."
                 % (len(aujourdhui), ", ".join(e["titre"] for e in aujourdhui)))

    L.append("**À cocher aujourd'hui**")
    for tag, t in taches_du_jour(data, jour, actifs):
        L.append("- [ ] **%s** — %s" % (LIBELLE.get(tag, tag.capitalize()), t))

    L.append("**Mes blocs de travail**")
    bj = blocs_du_jour(data, jour)
    if bj:
        for b in bj:
            L.append("- ⏱️ `%s – %s` %s" % (hm(b["debut"]), hm(b["fin"]), b["titre"]))
    else:
        L.append("- *Journée libre — repos assumé. Ne rien y planifier.*")

    if bj and actifs:
        premiers = actifs[:2]
        if len(premiers) > 1:
            L.append("> 💡 Couper le bloc en deux : d'abord %s, ensuite %s. Dans cet ordre — "
                     "le plus lourd quand la tête est encore fraîche."
                     % (premiers[0]["titre"], premiers[1]["titre"]))
        else:
            L.append("> 💡 Un seul chantier ouvert : %s. Le bloc y passe en entier."
                     % premiers[0]["titre"])
    L.append("---")

    # ---- sept prochains jours ---------------------------------------------
    fin7 = jour + dt.timedelta(days=7)
    L.append("## ⚡ Mes sept prochains jours — %s au %s" % (court(jour), court(fin7)))
    for t in data["taches_admin"]:
        if t["pour"] == "recurrent":
            continue
        ech = d(t["pour"])
        if ech < jour and t.get("urgent"):
            L.append("- [ ] 🔴 %s — **en retard depuis le %s**" % (t["quoi"], court(ech)))
        elif 0 <= (ech - jour).days <= 7:
            L.append("- [ ] %s %s — pour le %s" % ("🔴" if t.get("urgent") else "🔵",
                                                   t["quoi"], court(ech)))
    for l in data["lectures"]:
        reste = (d(l["pour"]) - jour).days
        if 0 <= reste <= 7:
            L.append("- [ ] %s %s — pour le %s" % (em(data, l["cours"]), l["quoi"], court(d(l["pour"]))))
    for e in chantiers_tous(data, jour):
        if e["reste"] <= 7:
            e2 = dict(e)
            L.append("- [ ] %s %s — %s, %s (%s)"
                     % (em(data, e["cours"]), e["titre"], data["cours"][e["cours"]]["court"],
                        jx(e["reste"]), LIBELLE.get(etape(e2), etape(e2)).lower()))
    L.append("---")

    # ---- semaines rouges ---------------------------------------------------
    rouges = semaines_rouges(data, jour)
    L.append("## 🔴 Mes semaines rouges — %d encore devant moi" % len(rouges))
    L.append(table(["Semaine", "Dates", "Ce qui tombe", "La règle"], rouges))
    L.append("---")

    # ---- toutes les échéances ---------------------------------------------
    L.append("## 📅 Toutes mes échéances")
    L.append("> 💡 Sélectionne ce tableau → **Transformer en base de données** pour filtrer "
             "par cours et trier par date.")
    lignes = []
    for ev in sorted(data["evaluations"], key=lambda e: (d(e["date"]), -e["poids"])):
        ech = d(ev["date"])
        reste = (ech - jour).days
        lourd = ev["poids"] >= 20
        if ev.get("fait") or reste < 0:
            puce, cpt = "✅", "✅ fait"
        elif reste == 0:
            puce, cpt = "🔴", "**AUJOURD'HUI**"
        elif reste <= 14:
            puce, cpt = "🟠", jx(reste)
        else:
            puce, cpt = "🔵", jx(reste)
        titre = ev["titre"] + (" *(date à confirmer)*" if ev.get("a_confirmer") else "")
        poids = "%d %%" % ev["poids"] if ev["poids"] else "formatif"
        poids = gras_si(poids, lourd) + (" *(à confirmer)*" if ev.get("poids_approx") else "")
        lignes.append([puce, "%s %d %s" % (JOURS[ech.weekday()], ech.day, MOIS[ech.month - 1]),
                       "%s %s" % (em(data, ev["cours"]), data["cours"][ev["cours"]]["court"]),
                       titre, poids, cpt])
    L.append(table(["", "Date", "Cours", "Évaluation", "Poids", "Compte à rebours"], lignes))
    L.append("---")

    # ---- semaine type ------------------------------------------------------
    total = 0.0
    lignes = []
    for b in sorted(data["blocs_travail"], key=lambda b: (b["jour"], b["debut"])):
        h1, m1 = (int(x) for x in b["debut"].split(":"))
        h2, m2 = (int(x) for x in b["fin"].split(":"))
        duree = (h2 * 60 + m2 - h1 * 60 - m1) / 60.0
        total += duree
        txt = "%d h" % duree if duree == int(duree) else "%d h %02d" % (int(duree), (duree % 1) * 60)
        gros = "GROS BLOC" in b["titre"]
        icones = "".join(em(data, f) for f in b["focus"] if f in data["cours"]) or "🔁"
        lignes.append([gras_si("%s %s – %s" % (JOURS[b["jour"] - 1].capitalize(),
                                               hm(b["debut"]), hm(b["fin"])), gros),
                       gras_si(txt, gros), "%s %s" % (icones, b["titre"])])
    heures = "%d h" % total if total == int(total) else "%d h %02d" % (int(total), (total % 1) * 60)
    L.append("## 🗓️ Ma semaine type — %s de travail" % heures)
    L.append(table(["Quand", "Durée", "Ce que je fais"], lignes))
    L.append("> ⚠️ Vendredi soir, samedi après-midi et dimanche matin restent volontairement "
             "vides. **Ne pas les remplir** : c'est ce qui rend le reste tenable, semaine "
             "après semaine.")
    L.append("---")

    # ---- méthodes ----------------------------------------------------------
    L.append("## 🧠 Mes méthodes, cours par cours")
    dur = max(c["difficulte"] for c in data["cours"].values())
    for cle, c in sorted(data["cours"].items(), key=lambda kv: -kv[1]["difficulte"]):
        L.append("### %s %s" % (c.get("emoji", ""), c["nom"]))
        if c["difficulte"] == dur:
            L.append("*Cours où je me sens le plus fragile — c'est là que va le temps en priorité.*")
        L.append(c.get("methode", ""))
    L.append("---")

    # ---- rattrapage --------------------------------------------------------
    L.append("## 🔁 Si je prends du retard")
    L.append("> Le dimanche 16 h – 18 h ne sert **qu'à ça** : reprendre ce qui a sauté dans la "
             "semaine et refaire le plan des sept jours suivants. Rien d'autre ne s'y planifie.")
    for r in data.get("rattrapage", []):
        L.append("- %s" % r)
    L.append("---")

    # ---- à confirmer -------------------------------------------------------
    L.append("## ✅ À faire confirmer auprès des profs")
    for t in data["taches_admin"]:
        if t["pour"] == "recurrent":
            L.append("- [ ] 🔁 %s" % t["quoi"])
            continue
        ech = d(t["pour"])
        if ech < jour and t.get("urgent"):
            L.append("- [ ] 🔴 %s — **en retard depuis le %s**" % (t["quoi"], court(ech)))
        else:
            L.append("- [ ] %s %s — pour le %s" % ("🔴" if t.get("urgent") else "🔵",
                                                   t["quoi"], court(ech)))
    L.append("---")

    # ---- avancement --------------------------------------------------------
    L.append("## 📊 Mon avancement")
    av = avancement(data, jour)
    lignes = [["%s %s" % (em(data, cle), data["cours"][cle]["court"]), "%d %%" % pct]
              for cle, (nom, pct) in av.items()]
    L.append(table(["Cours", "Part de la note déjà jouée"], lignes))
    moyenne = sum(pct for _, pct in av.values()) / float(len(av))
    L.append("> **%d %%** de la session est joué en moyenne. Il reste %d jours avant le %s."
             % (round(moyenne), (fin_session - jour).days, court(fin_session).rstrip(".")))
    L.append("---")
    L.append("*Page régénérée par **`notion.py`** à partir de **`donnees-session.json`**. "
             "La carte du jour arrive chaque matin dans Slack.*")
    return "\n".join(L)


def main():
    args = sys.argv[1:]
    sortie = None
    if "--sortie" in args:
        i = args.index("--sortie")
        sortie = args[i + 1]
        args = args[:i] + args[i + 2:]
    jour = d(args[0]) if args else dt.date.today()
    txt = page(charger(), jour)
    if sortie:
        with open(sortie, "w", encoding="utf-8") as fh:
            fh.write(txt + "\n")
        print(sortie)
    else:
        print(txt)


if __name__ == "__main__":
    main()

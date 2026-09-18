# -*- coding: utf-8 -*-
"""Tableau de bord Notion — Automne 2026.

Regénère la page « Ma session — Automne 2026 » à partir de donnees-session.json.

    python3 notion.py                 -> le corps de la page, en markdown Notion
    python3 notion.py 2026-10-07      -> la page telle qu'elle serait ce jour-là

Le texte produit se colle tel quel dans Notion (commande replace_content).
Comme carte.py, ce script ne contient aucune donnée : tout vient du JSON.
"""
import datetime as dt
import sys

import carte
from carte import ABREV, JOURS, MOIS, avancement, chantiers_tous, charger, d

SEUIL_ROUGE = 25  # % de session qui tombe dans la semaine


def long(j):
    return "%s %d %s" % (JOURS[j.weekday()], j.day, MOIS[j.month - 1])


def court(j):
    return "%d %s" % (j.day, ABREV[j.month - 1])


def heure(h):
    """« 18:00 » -> « 18 h », « 16:30 » -> « 16 h 30 »."""
    hh, mm = h.split(":")
    return "%d h" % int(hh) if mm == "00" else "%d h %s" % (int(hh), mm)


def poids_txt(e):
    if not e["poids"]:
        return "formatif"
    return "**%d %%**" % e["poids"] if e["poids"] >= 20 else "%d %%" % e["poids"]


def pastille(reste):
    if reste <= 7:
        return "🔴"
    if reste <= 21:
        return "🟠"
    return "🔵"


def ligne(cells):
    return "<tr>\n%s\n</tr>" % "\n".join("<td>%s</td>" % c for c in cells)


def tableau(entete, lignes):
    return "\n".join(['<table header-row="true">', ligne(entete)] + lignes + ["</table>"])


def nom_cours(data, cle):
    c = data["cours"][cle]
    return "%s %s" % (c.get("emoji", ""), c["court"])


# --------------------------------------------------------------------------
# Les semaines rouges : calculées, pas listées à la main
# --------------------------------------------------------------------------
def semaines_rouges(data, jour):
    bornes = sorted(((int(n), d(deb)) for n, deb in data["session"]["semaines"].items()),
                    key=lambda p: p[1])
    out = []
    for num, debut in bornes:
        fin = debut + dt.timedelta(days=6)
        dedans = [e for e in data["evaluations"] if debut <= d(e["date"]) <= fin]
        total = sum(e["poids"] for e in dedans)
        if total < SEUIL_ROUGE or fin < jour:
            continue
        quoi = ", ".join("%s %s%s" % (nom_cours(data, e["cours"]), e["titre"],
                                      " %d %%" % e["poids"] if e["poids"] else "")
                         for e in sorted(dedans, key=lambda e: d(e["date"])))
        regle = data["session"].get("notes_semaines", {}).get(str(num))
        if not regle:
            regle = "%d %% de la session en une semaine. Rien ne commence ce lundi-là." % total
        out.append(ligne(["**%d**" % num, "%s – %s" % (court(debut), court(fin)), quoi, regle]))
    return out


# --------------------------------------------------------------------------
# La page
# --------------------------------------------------------------------------
# --------------------------------------------------------------------------
# Le week-end : affiché à partir du jeudi, quand il est encore temps de le préparer
# --------------------------------------------------------------------------
def week_end(data, jour):
    """Samedi et dimanche du week-end qui vient, avec ce qui y est prévu."""
    if jour.isoweekday() < 4:
        return []
    samedi = jour + dt.timedelta(days=(5 - jour.weekday()) % 7)
    L = ["## 🌙 Mon week-end — %s et %s\n" % (court(samedi), court(samedi + dt.timedelta(days=1)))]
    for j in (samedi, samedi + dt.timedelta(days=1)):
        blocs = carte.blocs_du_jour(data, j)
        if not blocs:
            L.append("### %s" % long(j).capitalize())
            L.append("Rien de prévu. C'est voulu : c'est ce qui rend le reste tenable.")
            continue
        for b_ in blocs:
            L.append("### %s · %s – %s" % (long(j).capitalize(), heure(b_["debut"]), heure(b_["fin"])))
            L.append("**%s**" % b_["titre"])
            # les courses et les MIO ne se font pas le week-end : elles restent
            # dans la liste des sept prochains jours, pas dans un bloc d'étude.
            etudes = [(tag, t) for tag, t in carte.taches_du_jour(data, j, carte.chantiers(data, j))
                      if tag not in ("RETARD", "ADMIN")]
            for tag, t in etudes[:4]:
                L.append("- [ ] %s — *%s*" % (t, tag.lower()))
            L.append("")
    L.append("\n---\n")
    return L


def page(data, jour):
    sess = data["session"]
    sem = carte.semaine_de(data, jour)
    a, b = sess["semaine_etudes"]
    L = []

    L.append("> %s · %s" % (data["programme"], sess["nom"]))
    L.append("> Du %s au %s · Semaine d'études : %s au %s"
             % (court(d(sess["debut"])), court(d(sess["fin"])), court(d(a)), court(d(b))))
    L.append("> **Nous sommes en semaine %s sur 15.** Page mise à jour le %s." % (sem or "—", long(jour)))
    L.append("\n---\n")

    # ----- Les sept prochains jours
    fin7 = jour + dt.timedelta(days=7)
    L.append("## ⚡ Mes sept prochains jours — %s au %s\n" % (court(jour), court(fin7)))
    for t in data["taches_admin"]:
        if t["pour"] == "recurrent":
            continue
        ech = d(t["pour"])
        if ech < jour and t.get("urgent"):
            L.append("- [ ] 🔴 %s — **en retard**" % t["quoi"])
        elif jour <= ech <= fin7:
            L.append("- [ ] ✉️ %s — pour le %s" % (t["quoi"], court(ech)))
    for l in data["lectures"]:
        if jour <= d(l["pour"]) <= fin7:
            L.append("- [ ] %s %s — pour le %s"
                     % (data["cours"][l["cours"]].get("emoji", ""), l["quoi"], court(d(l["pour"]))))
    for e in sorted(carte.chantiers(data, jour)[:5], key=lambda e: e["reste"]):
        L.append("- [ ] %s %s — %s, %s (%s)"
                 % (data["cours"][e["cours"]].get("emoji", ""), e["titre"],
                    data["cours"][e["cours"]]["court"], carte.jx(e["reste"]),
                    carte.etape(e).lower()))
    L.append("\n---\n")

    L.extend(week_end(data, jour))

    # ----- Semaines rouges
    rouges = semaines_rouges(data, jour)
    if rouges:
        L.append("## 🔴 Mes semaines rouges — %d encore devant moi\n" % len(rouges))
        L.append(tableau(["Semaine", "Dates", "Ce qui tombe", "La règle"], rouges))
        L.append("\n---\n")

    # ----- Toutes les échéances
    L.append("## 📅 Toutes mes échéances\n")
    L.append("> 💡 Sélectionne ce tableau → **Transformer en base de données** "
             "pour filtrer par cours et trier par date.\n")
    lignes = []
    for e in sorted(data["evaluations"], key=lambda e: (d(e["date"]), -e["poids"])):
        ech = d(e["date"])
        reste = (ech - jour).days
        if e.get("fait") or reste < 0:
            lignes.append(ligne(["✅", long(ech), nom_cours(data, e["cours"]), e["titre"],
                                 poids_txt(e), "✅ fait"]))
        else:
            lignes.append(ligne([pastille(reste), long(ech), nom_cours(data, e["cours"]),
                                 e["titre"], poids_txt(e), carte.jx(reste)]))
    L.append(tableau(["", "Date", "Cours", "Évaluation", "Poids", "Compte à rebours"], lignes))
    L.append("\n---\n")

    # ----- Semaine type
    total = 0.0
    lignes = []
    for b_ in sorted(data["blocs_travail"], key=lambda b: (b["jour"], b["debut"])):
        h1, m1 = (int(x) for x in b_["debut"].split(":"))
        h2, m2 = (int(x) for x in b_["fin"].split(":"))
        duree = (h2 * 60 + m2 - h1 * 60 - m1) / 60.0
        total += duree
        quand = "%s %s – %s" % (JOURS[b_["jour"] - 1].capitalize(),
                                heure(b_["debut"]), heure(b_["fin"]))
        d_txt = ("%d h" % duree) if duree == int(duree) else ("%d h %02d" % (int(duree), round((duree % 1) * 60)))
        gros = duree >= 3
        emo = "".join(data["cours"][f].get("emoji", "") for f in b_["focus"] if f in data["cours"])
        titre = ("%s %s" % (emo, b_["titre"])).strip()
        lignes.append(ligne(["**%s**" % quand if gros else quand,
                             "**%s**" % d_txt if gros else d_txt,
                             "**%s**" % titre if gros else titre]))
    h_txt = ("%d h" % total) if total == int(total) else ("%d h %02d" % (int(total), round((total % 1) * 60)))
    L.append("## 🗓️ Ma semaine type — %s de travail\n" % h_txt)
    L.append(tableau(["Quand", "Durée", "Ce que je fais"], lignes))
    L.append("\n> ⚠️ %s\n" % data["_blocs"])
    L.append("\n---\n")

    # ----- Méthodes, les cours les plus difficiles d'abord
    L.append("## 🧠 Mes méthodes, cours par cours\n")
    dur = max(c["difficulte"] for c in data["cours"].values())
    for cle, c in sorted(data["cours"].items(), key=lambda kv: -kv[1]["difficulte"]):
        L.append("### %s %s" % (c.get("emoji", ""), c["nom"]))
        if c["difficulte"] == dur:
            L.append("*Cours où je me sens le plus fragile — c'est là que va le temps en priorité.*")
        L.append(c.get("methode", ""))
    L.append("\n---\n")

    # ----- À confirmer
    L.append("## ✅ À faire confirmer auprès des profs\n")
    for t in sorted(data["taches_admin"], key=lambda t: (t["pour"] == "recurrent", t["pour"])):
        if t["pour"] == "recurrent":
            L.append("- [ ] 🔁 %s" % t["quoi"])
            continue
        ech = d(t["pour"])
        reste = (ech - jour).days
        marque = "🔴" if (reste < 0 or t.get("urgent")) else pastille(reste)
        suffixe = "**en retard**" if reste < 0 else "pour le %s" % court(ech)
        L.append("- [ ] %s %s — %s" % (marque, t["quoi"], suffixe))
    L.append("\n---\n")

    # ----- Avancement
    L.append("## 📊 Mon avancement\n")
    lignes, parts = [], []
    for cle, (nom, pct) in avancement(data, jour).items():
        parts.append(pct)
        lignes.append(ligne(["%s %s" % (data["cours"][cle].get("emoji", ""), nom), "%d %%" % pct]))
    L.append(tableau(["Cours", "Part de la note déjà jouée"], lignes))
    reste_j = (d(sess["fin"]) - jour).days
    L.append("\n> **%d %%** de la session est joué en moyenne. Il reste %d jours avant le %s.\n"
             % (round(sum(parts) / len(parts)), reste_j, long(d(sess["fin"]))))
    L.append("\n---\n")
    L.append("*Page regénérée par **`notion.py`** à partir de **`donnees-session.json`**. "
             "La carte du jour arrive chaque matin dans Slack.*")
    return "\n".join(L)


def main():
    args = sys.argv[1:]
    jour = d(args[0]) if args else carte.aujourdhui()
    print(page(charger(), jour))


if __name__ == "__main__":
    main()

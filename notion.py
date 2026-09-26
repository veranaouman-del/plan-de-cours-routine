# -*- coding: utf-8 -*-
"""Tableau de bord Notion — Automne 2026.

Régénère la page Notion « Ma session — Automne 2026 » à partir de
donnees-session.json. Même source de vérité que carte.py : rien n'est
codé en dur ici non plus.

    python3 notion.py                 -> markdown d'aujourd'hui sur la sortie standard
    python3 notion.py 2026-10-07      -> une date précise
    python3 notion.py --ecrire        -> écrit aussi notion-tableau-de-bord.md

Le markdown produit est du Notion-flavored Markdown : il se colle tel quel
dans la commande `replace_content` du connecteur Notion.
"""
import os
import sys
import datetime as dt

import carte
from carte import JOURS, MOIS, court, d, jx

BASE = os.path.dirname(os.path.abspath(__file__))
SORTIE_MD = os.path.join(BASE, "notion-tableau-de-bord.md")

# Les pastilles suivent la même logique que la carte : rouge à 4 jours,
# orange à 12, bleu au-delà.
def pastille(reste):
    return "🔴" if reste <= 4 else ("🟠" if reste <= 12 else "🔵")


def emo(data, cle):
    return data["cours"][cle].get("emoji", "•")


def nom_court(data, cle):
    c = data["cours"][cle]
    return c.get("court", c["nom"])


def poids_txt(ev):
    if not ev["poids"]:
        return "formatif"
    t = "%d %%" % ev["poids"]
    if ev["poids"] >= 20:
        t = "**%s**" % t
    if ev.get("poids_approx"):
        t += " *(à confirmer)*"
    return t


def long_date(j):
    return "%s %d %s" % (JOURS[j.weekday()], j.day, MOIS[j.month - 1])


def hm(t):
    return t.replace(":", " h ")


# --------------------------------------------------------------------------
# Les semaines rouges : deux évaluations ou plus dans la même semaine
# --------------------------------------------------------------------------
def bornes_semaine(data, num):
    debut = d(data["session"]["semaines"][str(num)])
    return debut, debut + dt.timedelta(days=6)


def semaines_rouges(data, jour):
    groupes = {}
    for ev in data["evaluations"]:
        num = carte.semaine_de(data, d(ev["date"]))
        if num:
            groupes.setdefault(num, []).append(ev)

    rouges = {n: evs for n, evs in groupes.items() if len(evs) >= 2}
    # La derniere semaine est la semaine des finaux : elle est lourde par definition,
    # donc elle ne dispute pas le titre de « pire semaine » aux semaines ordinaires.
    finale = max(int(n) for n in data["session"]["semaines"])
    pire = max((sum(e["poids"] for e in evs) for n, evs in rouges.items() if n != finale),
               default=0)

    lignes = []
    for num in sorted(rouges):
        debut, fin = bornes_semaine(data, num)
        if fin < jour:
            continue
        evs = sorted(rouges[num], key=lambda e: (d(e["date"]), -e["poids"]))
        total = sum(e["poids"] for e in evs)
        quoi = " · ".join("%s %s %s" % (emo(data, e["cours"]), e["titre"],
                                        "formatif" if not e["poids"] else "%d %%" % e["poids"])
                          for e in evs)

        jours_distincts = len({e["date"] for e in evs})
        if all(d(e["date"]) < jour for e in evs):
            lignes.append(("~~%d~~" % num, "%s – %s" % (court(debut), court(fin)), quoi,
                           "✅ Semaine bouclée : les %d évaluations sont derrière moi." % len(evs)))
            continue
        if total == pire and num != finale:
            regle = "**La pire semaine de la session : %d %% en %d jour%s.**" % (
                total, jours_distincts, "s" if jours_distincts > 1 else "")
        else:
            lourde = max(evs, key=lambda e: e["poids"])
            regle = "%d évaluations dans %d cours. La plus lourde : %s %d %% en %s." % (
                len(evs), len({e["cours"] for e in evs}), lourde["titre"],
                lourde["poids"], nom_court(data, lourde["cours"]))
        note = data.get("notes_semaines", {}).get(str(num))
        if note:
            regle += " " + note
        elif debut > jour:
            regle += " Rien de neuf ne commence ce lundi-là."

        etat = "**%d**" % num if debut <= jour <= fin else str(num)
        lignes.append((etat, "%s – %s" % (court(debut), court(fin)), quoi, regle))
    return lignes


# --------------------------------------------------------------------------
# Tableau Notion
# --------------------------------------------------------------------------
def tableau(entetes, lignes):
    out = ['<table header-row="true">', "<tr>"]
    out += ["<td>%s</td>" % h for h in entetes]
    out.append("</tr>")
    for l in lignes:
        out.append("<tr>")
        out += ["<td>%s</td>" % c for c in l]
        out.append("</tr>")
    out.append("</table>")
    return "\n".join(out)


# --------------------------------------------------------------------------
def page(data, jour):
    sem = carte.semaine_de(data, jour)
    actifs = carte.chantiers(data, jour)
    tous = carte.chantiers_tous(data, jour)
    s = data["session"]
    L = []

    a, b = s["semaine_etudes"]
    L.append("> %s" % data["programme"].replace(" - ", " — "))
    L.append("> Du %s au %s · Semaine d'études : %s au %s"
             % (court(d(s["debut"])), court(d(s["fin"])), court(d(a)), court(d(b))))
    if carte.en_semaine_etudes(data, jour):
        L.append("> **Semaine d'études et d'encadrement — aucun cours.** Page mise à jour le %s." % long_date(jour))
    else:
        L.append("> **Nous sommes en semaine %s sur 15.** Page mise à jour le %s."
                 % (sem or "—", long_date(jour)))
    L.append("---")

    # ---- Aujourd'hui ----
    L.append("## ☀️ Aujourd'hui — %s" % long_date(jour))
    cj = carte.cours_du_jour(data, jour)
    L.append("**Mes cours**")
    if cj:
        for c in cj:
            L.append("- %s `%s – %s` %s · %s" % (emo(data, c["cours"]), hm(c["debut"]),
                                                 hm(c["fin"]), data["cours"][c["cours"]]["nom"],
                                                 c["local"]))
    else:
        L.append("- Aucun cours — journée de travail libre.")

    if actifs:
        p = actifs[0]
        L.append("> 🔴 **Ma priorité : %s** — %s, %d %%, %s" % (
            p["titre"], nom_court(data, p["cours"]), p["poids"], jx(p["reste"])))
        L.append("> Si je ne fais qu'une seule chose aujourd'hui, c'est celle-là.")
    aujourdhui = [e for e in tous if e["reste"] == 0]
    if aujourdhui:
        L.append("> ⚠️ **%d échéance%s tombe%s aujourd'hui** : %s. Tout ce qui se remet en ligne part avant le premier cours — un envoi raté ne se rattrape pas."
                 % (len(aujourdhui), "s" if len(aujourdhui) > 1 else "",
                    "nt" if len(aujourdhui) > 1 else "",
                    ", ".join(e["titre"] for e in aujourdhui)))

    L.append("**À cocher aujourd'hui**")
    etiquettes = {"RETARD": "**En retard**", "ADMIN": "**Admin**", "LECTURE": "**Lecture**"}
    for tag, t in carte.taches_du_jour(data, jour, actifs):
        if t.startswith("+"):   # le compteur de la carte : inutile ici, tout est listé plus bas
            continue
        L.append("- [ ] %s — %s" % (etiquettes.get(tag, "**%s**" % tag.capitalize()), t))

    L.append("**Mes blocs de travail**")
    bj = carte.blocs_du_jour(data, jour)
    if bj:
        for bl in bj:
            L.append("- ⏱️ `%s – %s` %s" % (hm(bl["debut"]), hm(bl["fin"]), bl["titre"]))
    else:
        L.append("- Journée libre — repos assumé, c'est prévu au plan.")
    L.append("---")

    # ---- Sept prochains jours ----
    fin7 = jour + dt.timedelta(days=7)
    L.append("## ⚡ Mes sept prochains jours — %s au %s" % (court(jour), court(fin7)))
    for t in data["taches_admin"]:
        if t["pour"] == "recurrent":
            continue
        ech = d(t["pour"])
        if ech < jour:
            L.append("- [ ] 🔴 %s — **en retard depuis le %s**" % (t["quoi"], court(ech)))
        elif ech <= fin7:
            L.append("- [ ] %s %s — pour le %s" % ("🟠" if t.get("urgent") else "🔵",
                                                   t["quoi"], court(ech)))
    for l in data["lectures"]:
        if jour <= d(l["pour"]) <= fin7:
            L.append("- [ ] 📖 %s %s — pour le %s" % (emo(data, l["cours"]), l["quoi"],
                                                      court(d(l["pour"]))))
    for e in [x for x in tous if x["reste"] <= 7]:
        L.append("- [ ] %s %s — %s, %s (%s)" % (emo(data, e["cours"]), e["titre"],
                                                nom_court(data, e["cours"]), jx(e["reste"]),
                                                carte.etape(e).lower()))
    L.append("---")

    # ---- Semaines rouges ----
    rouges = semaines_rouges(data, jour)
    devant = sum(1 for r in rouges if not r[0].startswith("~~"))
    L.append("## 🔴 Mes semaines rouges — %d encore devant moi" % devant)
    L.append(tableau(["Semaine", "Dates", "Ce qui tombe", "La règle"], rouges))
    L.append("---")

    # ---- Toutes les échéances ----
    L.append("## 📅 Toutes mes échéances")
    L.append("> 💡 Sélectionne ce tableau → **Transformer en base de données** pour filtrer par cours et trier par date.")
    lignes = []
    for ev in sorted(data["evaluations"], key=lambda e: (e["date"], -e["poids"])):
        ech = d(ev["date"])
        reste = (ech - jour).days
        passe = ev.get("fait") or reste < 0
        titre = ev["titre"] + (" *(date à confirmer)*" if ev.get("a_confirmer") else "")
        lignes.append(["✅" if passe else pastille(reste),
                       long_date(ech),
                       "%s %s" % (emo(data, ev["cours"]), nom_court(data, ev["cours"])),
                       titre, poids_txt(ev),
                       "✅ fait" if passe else ("**%s**" % jx(reste) if reste <= 1 else jx(reste))])
    L.append(tableau(["", "Date", "Cours", "Évaluation", "Poids", "Compte à rebours"], lignes))
    L.append("---")

    # ---- Semaine type ----
    total = 0
    lignes = []
    for bl in sorted(data["blocs_travail"], key=lambda x: (x["jour"], x["debut"])):
        h1 = dt.datetime.strptime(bl["debut"], "%H:%M")
        h2 = dt.datetime.strptime(bl["fin"], "%H:%M")
        mn = int((h2 - h1).total_seconds() // 60)
        total += mn
        duree = "%d h%s" % (mn // 60, " %02d" % (mn % 60) if mn % 60 else "")
        quand = "%s %s – %s" % (JOURS[bl["jour"] - 1].capitalize(), hm(bl["debut"]), hm(bl["fin"]))
        gros = mn >= 180
        lignes.append(["**%s**" % quand if gros else quand,
                       "**%s**" % duree if gros else duree,
                       (("".join(emo(data, f) for f in bl["focus"] if f in data["cours"])
                         or "🔁") + " " + bl["titre"])])
    L.append("## 🗓️ Ma semaine type — %d h%s de travail hors cours"
             % (total // 60, " %02d" % (total % 60) if total % 60 else ""))
    L.append(tableau(["Quand", "Durée", "Ce que je fais"], lignes))
    L.append("> ⚠️ Vendredi soir, samedi après-midi et dimanche matin restent volontairement vides. **Ne pas les remplir** : c'est ce qui rend le reste tenable, semaine après semaine.")
    L.append("---")

    # ---- Méthodes, les cours difficiles en premier ----
    L.append("## 🧠 Mes méthodes, cours par cours")
    ordre = sorted(data["cours"], key=lambda c: -data["cours"][c]["difficulte"])
    dur = max(data["cours"][c]["difficulte"] for c in ordre)
    for cle in ordre:
        c = data["cours"][cle]
        L.append("### %s %s" % (emo(data, cle), c["nom"]))
        if c["difficulte"] == dur:
            L.append("*Cours où je me sens le plus fragile — c'est là que va le temps en priorité.*")
        m = data.get("methodes", {}).get(cle)
        if m:
            L.append(m)
    L.append("---")

    # ---- Rattrapage ----
    L.append("## 🔁 Si je prends du retard")
    L.append("> Le dimanche 16 h – 18 h ne sert **qu'à ça** : reprendre ce qui a sauté dans la semaine et refaire le plan des sept jours suivants. Rien d'autre ne s'y planifie.")
    L.append("- Une journée sautée → elle se reprend dans le bloc du dimanche, pas en empilant sur le lendemain.")
    L.append("- Une semaine sautée → je laisse tomber la prise d'avance du jeudi et je protège les deux gros blocs (mardi, mercredi).")
    L.append("- Deux semaines de retard → j'écris au prof concerné AVANT l'échéance, jamais après. Une remise négociée vaut mieux qu'une remise ratée.")
    if d(s["semaine_etudes"][1]) >= jour:
        L.append("- Coussin suivant : la **semaine d'études du %s au %s**, juste après la pire semaine de la session."
                 % (court(d(a)), court(d(b))))
    L.append("---")

    # ---- À confirmer ----
    L.append("## ✅ À faire confirmer auprès des profs")
    for t in data["taches_admin"]:
        if t["pour"] == "recurrent":
            L.append("- [ ] 🔁 %s" % t["quoi"])
            continue
        ech = d(t["pour"])
        if ech < jour:
            L.append("- [ ] 🔴 %s — **en retard depuis le %s**" % (t["quoi"], court(ech)))
        else:
            L.append("- [ ] %s %s — pour le %s" % ("🟠" if t.get("urgent") else "🔵",
                                                   t["quoi"], court(ech)))
    L.append("---")

    # ---- Avancement ----
    L.append("## 📊 Mon avancement")
    av = carte.avancement(data, jour)
    lignes = [["%s %s" % (emo(data, cle), nom_court(data, cle)), "%d %%" % pct]
              for cle, (_, pct) in av.items()]
    L.append(tableau(["Cours", "Part de la note déjà jouée"], lignes))
    moyenne = sum(p for _, p in av.values()) / len(av)
    restants = (d(s["fin"]) - jour).days
    L.append("> **%d %%** de la session est joué en moyenne. Il reste %d jours avant le %s"
             % (round(moyenne), restants, court(d(s["fin"]))))
    quinzaine = [e for e in tous if e["reste"] <= 14 and e["poids"]]
    if quinzaine:
        lourde = max(quinzaine, key=lambda e: e["poids"])
        L.append("> Les quinze prochains jours comptent **%d évaluations** dans %d cours ; la plus lourde est %s (%d %%, %s)."
                 % (len(quinzaine), len({e["cours"] for e in quinzaine}), lourde["titre"],
                    lourde["poids"], jx(lourde["reste"])))
    L.append("---")
    L.append("*Page régénérée par **`notion.py`** à partir de **`donnees-session.json`**. La carte du jour arrive chaque matin dans Slack.*")
    return "\n".join(L)


def main():
    args = [a for a in sys.argv[1:] if a != "--ecrire"]
    jour = d(args[0]) if args else dt.date.today()
    data = carte.charger()
    md = page(data, jour)
    if "--ecrire" in sys.argv[1:]:
        with open(SORTIE_MD, "w", encoding="utf-8") as fh:
            fh.write("# 🎓 Ma session — Automne 2026\n\n" + md + "\n")
    print(md)


if __name__ == "__main__":
    main()

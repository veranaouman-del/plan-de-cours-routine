# -*- coding: utf-8 -*-
"""Tableau de bord Notion — Automne 2026.

Regénère la page Notion complète à partir de donnees-session.json.

    python3 notion.py                 -> le tableau de bord d'aujourd'hui, sur stdout
    python3 notion.py 2026-10-07      -> une date précise
    python3 notion.py --fichier       -> écrit aussi notion-tableau-de-bord.md

La sortie est du Markdown enrichi Notion : les tableaux sont en <table>, parce que
les tableaux Markdown classiques arrivent aplatis dans Notion.

Comme carte.py, ce script ne code rien en dur : tout vient du JSON.
"""
import os
import sys
import datetime as dt

import carte
from carte import d, court, jx, charger, semaine_de, en_semaine_etudes

BASE = os.path.dirname(os.path.abspath(__file__))
JOURS = carte.JOURS
MOIS = carte.MOIS

SEUIL_ROUGE = 25          # points en jeu à partir desquels une semaine est « rouge »
SEUIL_URGENT, SEUIL_PROCHE = 7, 21   # frontières 🔴 / 🟠 / 🔵


# --------------------------------------------------------------------------
# Petits utilitaires d'affichage
# --------------------------------------------------------------------------
def emo(data, cle):
    return data.get("emojis", {}).get(cle, "•")


def nom_court(data, cle):
    return "%s %s" % (emo(data, cle), data["cours"][cle]["court"])


def long_date(j):
    return "%s %d %s" % (JOURS[j.weekday()], j.day, MOIS[j.month - 1])


def pastille(reste):
    if reste <= SEUIL_URGENT:
        return "🔴"
    if reste <= SEUIL_PROCHE:
        return "🟠"
    return "🔵"


def poids_txt(ev):
    if not ev["poids"]:
        return "formatif"
    t = "%d %%" % ev["poids"]
    if ev["poids"] >= 20:
        t = "**%s**" % t
    if ev.get("poids_approx"):
        t += " *(à confirmer)*"
    return t


def titre_txt(ev):
    return ev["titre"] + (" *(date à confirmer)*" if ev.get("a_confirmer") else "")


def tableau(entetes, lignes):
    out = ['<table header-row="true">', "<tr>"]
    out += ["<td>%s</td>" % e for e in entetes]
    out.append("</tr>")
    for l in lignes:
        out.append("<tr>")
        out += ["<td>%s</td>" % c for c in l]
        out.append("</tr>")
    out.append("</table>")
    return "\n".join(out)


def heures(b):
    def m(s):
        h, mn = (int(x) for x in s.split(":"))
        return h * 60 + mn
    total = m(b["fin"]) - m(b["debut"])
    h, mn = divmod(total, 60)
    return total, ("%d h %02d" % (h, mn) if mn else "%d h" % h)


def hhmm(s):
    """08:55 -> 8 h 55 ; 18:00 -> 18 h (le « 00 » n'apprend rien)."""
    h, mn = (int(x) for x in s.split(":"))
    return "%d h %02d" % (h, mn) if mn else "%d h" % h


def plage(b):
    return "%s – %s" % (hhmm(b["debut"]), hhmm(b["fin"]))


# --------------------------------------------------------------------------
# Les sections
# --------------------------------------------------------------------------
def entete(data, jour, sem):
    s = data["session"]
    a, b = (d(x) for x in s["semaine_etudes"])
    situation = ("**Nous sommes dans la semaine d'études.**" if en_semaine_etudes(data, jour)
                 else "**Nous sommes en semaine %d sur 15.**" % sem if sem
                 else "**La session est terminée.**")
    return ("> %s\n> Du %s au %s · Semaine d'études : %s au %s\n> %s Page mise à jour le %s."
            % (data["programme"], court(d(s["debut"])), court(d(s["fin"])),
               court(a), court(b), situation, long_date(jour)))


def aujourdhui(data, jour):
    actifs = carte.chantiers(data, jour)
    L = ["## ☀️ Aujourd'hui — %s" % long_date(jour), "", "**Mes cours**"]

    cj = carte.cours_du_jour(data, jour)
    if cj:
        for c in cj:
            L.append("- %s `%s – %s` %s · %s"
                     % (emo(data, c["cours"]), hhmm(c["debut"]), hhmm(c["fin"]),
                        data["cours"][c["cours"]]["nom"], c["local"]))
    else:
        L.append("- 🏠 Aucun cours aujourd'hui")
    L.append("")

    if actifs:
        p = actifs[0]
        L.append("> 🔴 **Ma priorité : %s** — %s, %d %%, %s"
                 % (p["titre"], data["cours"][p["cours"]]["nom"], p["poids"], jx(p["reste"])))
        L.append("> Si je ne fais qu'une seule chose aujourd'hui, c'est celle-là.")
        L.append("")

    L.append("**À cocher aujourd'hui**")
    for tag, t in carte.taches_du_jour(data, jour, actifs):
        L.append("- [ ] **%s** — %s" % (tag.capitalize() if tag != "RETARD" else "En retard", t))
    L.append("")

    L.append("**Mes blocs de travail**")
    bj = carte.blocs_du_jour(data, jour)
    if bj:
        for b in bj:
            L.append("- ⏱️ `%s` %s" % (plage(b), b["titre"]))
    else:
        L.append("- 🌙 Journée libre — repos assumé")
    return "\n".join(L)


def sept_jours(data, jour):
    fin = jour + dt.timedelta(days=7)
    L = ["## ⚡ Mes sept prochains jours — %s au %s" % (court(jour), court(fin)), ""]

    for t in data["taches_admin"]:
        if t["pour"] == "recurrent":
            continue
        e = d(t["pour"])
        if e < jour and t.get("urgent"):
            L.append("- [ ] 🔴 %s — **en retard depuis le %s**" % (t["quoi"], court(e)))
        elif jour <= e <= fin:
            L.append("- [ ] %s %s — pour le %s" % ("🔴" if t.get("urgent") else "🟠",
                                                   t["quoi"], court(e)))

    for l in data["lectures"]:
        if jour <= d(l["pour"]) <= fin:
            L.append("- [ ] %s %s — pour le %s" % (emo(data, l["cours"]), l["quoi"],
                                                   court(d(l["pour"]))))

    for e in carte.chantiers(data, jour):
        if e["reste"] <= 7:
            L.append("- [ ] %s %s — %s, %s (%s)"
                     % (emo(data, e["cours"]), e["titre"], data["cours"][e["cours"]]["court"],
                        jx(e["reste"]), carte.etape(e).lower()))
    return "\n".join(L)


def semaines_rouges(data, jour):
    """Une semaine est rouge quand elle met en jeu au moins SEUIL_ROUGE points."""
    bornes = sorted(((int(n), d(deb)) for n, deb in data["session"]["semaines"].items()),
                    key=lambda p: p[1])
    lignes, restantes = [], 0
    for i, (num, debut) in enumerate(bornes):
        # Une semaine de session fait sept jours. Sans ce plafond, la semaine 7
        # avalerait la semaine d'études qui la suit.
        fin = debut + dt.timedelta(days=6)
        if i + 1 < len(bornes):
            fin = min(fin, bornes[i + 1][1] - dt.timedelta(days=1))
        dedans = sorted((e for e in data["evaluations"] if debut <= d(e["date"]) <= fin),
                        key=lambda e: -e["poids"])
        total = sum(e["poids"] for e in dedans)
        if total < SEUIL_ROUGE:
            continue
        if fin >= jour:
            restantes += 1
        quoi = ", ".join("%s %s %s" % (emo(data, e["cours"]), e["titre"],
                                       "%d %%" % e["poids"] if e["poids"] else "formatif")
                         for e in dedans)
        regle = data.get("regles_semaines_rouges", {}).get(
            str(num), "%d %% de la session en une semaine. Rien ne commence ce lundi-là." % total)
        lignes.append(["**%d**" % num, "%s – %s" % (court(debut), court(fin)), quoi, regle])

    return ("## 🔴 Mes semaines rouges — %d encore devant moi\n\n" % restantes
            + tableau(["Semaine", "Dates", "Ce qui tombe", "La règle"], lignes))


def toutes_echeances(data, jour):
    lignes = []
    for ev in sorted(data["evaluations"], key=lambda e: (d(e["date"]), -e["poids"])):
        e = d(ev["date"])
        reste = (e - jour).days
        passe = ev.get("fait") or reste < 0
        lignes.append(["✅" if passe else pastille(reste), long_date(e),
                       nom_court(data, ev["cours"]), titre_txt(ev), poids_txt(ev),
                       "✅ fait" if passe else jx(reste)])
    return ("## 📅 Toutes mes échéances\n\n"
            "> 💡 Sélectionne ce tableau → **Transformer en base de données** "
            "pour filtrer par cours et trier par date.\n\n"
            + tableau(["", "Date", "Cours", "Évaluation", "Poids", "Compte à rebours"], lignes))


def semaine_type(data):
    lignes, total = [], 0
    for b in sorted(data["blocs_travail"], key=lambda b: (b["jour"], b["debut"])):
        mn, lisible = heures(b)
        total += mn
        quand = "%s %s" % (JOURS[b["jour"] - 1].capitalize(), plage(b))
        icones = "".join(emo(data, f) for f in b["focus"] if f in data["cours"]) or "🔁"
        gros = mn >= 180
        lignes.append(["**%s**" % quand if gros else quand,
                       "**%s**" % lisible if gros else lisible,
                       "%s %s" % (icones, b["titre"])])
    h, mn = divmod(total, 60)
    tot = "%d h %02d" % (h, mn) if mn else "%d h" % h
    return ("## 🗓️ Ma semaine type — %s de travail\n\n" % tot
            + tableau(["Quand", "Durée", "Ce que je fais"], lignes)
            + "\n\n> ⚠️ Vendredi soir, samedi après-midi et dimanche matin restent **vides**. "
              "Ce n'est pas du temps perdu : c'est ce qui rend les %s restantes tenables "
              "semaine après semaine." % tot)


def methodes(data):
    L = ["## 🧠 Mes méthodes, cours par cours", ""]
    dur = max(c["difficulte"] for c in data["cours"].values())
    for cle, c in sorted(data["cours"].items(), key=lambda p: -p[1]["difficulte"]):
        L.append("### %s %s" % (emo(data, cle), c["nom"]))
        if c["difficulte"] >= dur:
            L.append("*Cours où je me sens le plus fragile — c'est là que va le temps "
                     "en priorité.*")
        L.append(data.get("methodes", {}).get(cle, ""))
        L.append("")
    return "\n".join(L).rstrip()


def retard(data):
    dim = next((b for b in data["blocs_travail"] if "rattrapage" in b["focus"]), None)
    quand = "%s %s" % (JOURS[dim["jour"] - 1], plage(dim)) if dim else "le bloc de rattrapage"
    L = ["## 🔁 Si je prends du retard", "",
         "> Le %s ne sert **qu'à ça** : reprendre ce qui a sauté dans la semaine et refaire "
         "le plan des sept jours suivants. Rien d'autre ne s'y planifie." % quand, ""]
    L += ["- %s" % r for r in data.get("rattrapage", [])]
    return "\n".join(L)


def a_confirmer(data, jour):
    L = ["## ✅ À faire confirmer auprès des profs", ""]
    for t in data["taches_admin"]:
        if t["pour"] == "recurrent":
            L.append("- [ ] 🔁 %s" % t["quoi"])
            continue
        e = d(t["pour"])
        if e < jour:
            L.append("- [ ] 🔴 %s — **en retard depuis le %s**" % (t["quoi"], court(e)))
        else:
            L.append("- [ ] %s %s — pour le %s"
                     % (pastille((e - jour).days) if t.get("urgent") else "🔵",
                        t["quoi"], court(e)))
    return "\n".join(L)


def avancement(data, jour):
    lignes = sorted(((nom_court(data, cle), pct)
                     for cle, (_, pct) in carte.avancement(data, jour).items()),
                    key=lambda p: -p[1])
    moyenne = sum(p for _, p in lignes) / len(lignes)
    reste = (d(data["session"]["fin"]) - jour).days
    return ("## 📊 Mon avancement\n\n"
            + tableau(["Cours", "Part de la note déjà jouée"],
                      [[nom, "%d %%" % pct] for nom, pct in lignes])
            + "\n\n> **%d %%** de la session est joué en moyenne. "
              "Il reste %d jours avant le %s" % (moyenne, reste,
                                                 court(d(data["session"]["fin"]))))


# --------------------------------------------------------------------------
def page(data, jour):
    sem = semaine_de(data, jour)
    blocs = [entete(data, jour, sem), aujourdhui(data, jour), sept_jours(data, jour),
             semaines_rouges(data, jour), toutes_echeances(data, jour), semaine_type(data),
             methodes(data), retard(data), a_confirmer(data, jour), avancement(data, jour),
             "*Page regénérée par **`notion.py`** à partir de **`donnees-session.json`**. "
             "La carte du jour arrive chaque matin dans Slack.*"]
    return "\n\n---\n\n".join(blocs)


def main():
    args = sys.argv[1:]
    fichier = "--fichier" in args
    args = [a for a in args if a != "--fichier"]
    jour = d(args[0]) if args else dt.date.today()

    texte = page(charger(), jour)
    if fichier:
        chemin = os.path.join(BASE, "notion-tableau-de-bord.md")
        with open(chemin, "w", encoding="utf-8") as fh:
            fh.write("# 🎓 Ma session — Automne 2026\n\n" + texte + "\n")
        print(chemin, file=sys.stderr)
    print(texte)


if __name__ == "__main__":
    main()

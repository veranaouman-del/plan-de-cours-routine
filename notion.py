# -*- coding: utf-8 -*-
"""Page Notion « Ma session » — Automne 2026.

Régénère tout le contenu de la page Notion à partir de donnees-session.json.

    python3 notion.py                 -> le markdown d'aujourd'hui, sur la sortie standard
    python3 notion.py 2026-10-07      -> la page telle qu'elle serait ce jour-là

La sortie se colle dans la page Notion avec l'outil « update page » (replace_content).
Rien n'est codé en dur ici non plus : tout vient du JSON.
"""
import datetime as dt
import sys

import carte
from carte import (ABREV, JOURS, MOIS, avancement, blocs_du_jour, chantiers,
                   chantiers_tous, cours_du_jour, d, etape, jx, semaine_de,
                   taches_du_jour)

SEUIL_ROUGE = 25          # % de la note dans une même semaine = semaine rouge
PAGE = "https://app.notion.com/p/3df73824e620811e9e6cd07440cb6ec7"

ETIQUETTES = {"RETARD": "En retard", "ADMIN": "Admin", "LECTURE": "Lecture",
              "TEST BLANC": "Test blanc", "AVANCER": "Avancer", "FINIR": "Finir",
              "REMISE": "Remise", "RELIRE": "Relire", "FICHES": "Fiches",
              "NOTES": "Notes"}


def long(j):
    return "%s %d %s" % (JOURS[j.weekday()], j.day, MOIS[j.month - 1])


def h(t):
    return t.lstrip("0").replace(":", " h ").replace(" h 00", " h")


def emo(data, cle):
    return data["cours"][cle].get("emoji", "•")


def poids_txt(e):
    if not e["poids"]:
        return "formatif"
    t = "%d %%" % e["poids"]
    if e["poids"] >= 20:
        t = "**%s**" % t
    if e.get("poids_approx"):
        t += " *(à confirmer)*"
    return t


def pastille(reste):
    return "🔴" if reste <= 7 else ("🟠" if reste <= 21 else "🔵")


def duree(b):
    a = dt.datetime.strptime(b["debut"], "%H:%M")
    z = dt.datetime.strptime(b["fin"], "%H:%M")
    m = int((z - a).total_seconds() // 60)
    return m, ("%d h %02d" % (m // 60, m % 60)) if m % 60 else "%d h" % (m // 60)


# --------------------------------------------------------------------------
# Sections
# --------------------------------------------------------------------------
def entete(data, jour):
    s = data["session"]
    sem = semaine_de(data, jour)
    a, b = (d(x) for x in s["semaine_etudes"])
    L = ["> %s" % data["programme"],
         "> Du %s au %s · Semaine d'études : %s au %s" % (
             carte.court(d(s["debut"])), carte.court(d(s["fin"])), carte.court(a), carte.court(b))]
    if sem:
        L.append("> **Nous sommes en semaine %d sur 15.** Page mise à jour le %s." % (sem, long(jour)))
    return L


def aujourdhui(data, jour, actifs):
    L = ["## ☀️ Aujourd'hui — %s" % long(jour), "", "**Mes cours**"]
    cj = cours_du_jour(data, jour)
    if cj:
        for c in cj:
            L.append("- %s `%s – %s` **%s** · %s" % (emo(data, c["cours"]), h(c["debut"]), h(c["fin"]),
                                                     data["cours"][c["cours"]]["nom"], c["local"]))
    else:
        L.append("- 🏠 Aucun cours aujourd'hui")
    L.append("")
    if actifs:
        p = actifs[0]
        L += ["> 🔴 **Ma priorité : %s** — %s, %d %%, %s" % (
                  p["titre"], data["cours"][p["cours"]]["nom"], p["poids"], jx(p["reste"])),
              "> Si je ne fais qu'une seule chose aujourd'hui, c'est celle-là.", ""]
    L.append("**À cocher aujourd'hui**")
    for tag, t in taches_du_jour(data, jour, actifs):
        L.append("- [ ] **%s** — %s" % (ETIQUETTES.get(tag, tag.capitalize()), t))
    L += ["", "**Mes blocs de travail**"]
    bj = blocs_du_jour(data, jour)
    if bj:
        for b in bj:
            L.append("- ⏱️ `%s – %s` %s" % (h(b["debut"]), h(b["fin"]), b["titre"]))
    else:
        L.append("- 🌙 Journée libre — repos assumé, c'est prévu au plan")
    return L


def sept_jours(data, jour):
    fin = jour + dt.timedelta(days=7)
    L = ["## ⚡ Mes sept prochains jours — %s au %s" % (carte.court(jour), carte.court(fin)), ""]
    for t in data["taches_admin"]:
        if t["pour"] == "recurrent":
            continue
        e = d(t["pour"])
        if e < jour:
            L.append("- [ ] 🔴 %s — **en retard depuis le %s**" % (t["quoi"], carte.court(e)))
        elif e <= fin:
            L.append("- [ ] %s %s — pour le %s" % ("🔴" if t.get("urgent") else "🟠",
                                                   t["quoi"], carte.court(e)))
    for l in data["lectures"]:
        if jour <= d(l["pour"]) <= fin:
            L.append("- [ ] %s %s — pour le %s" % (emo(data, l["cours"]), l["quoi"], carte.court(d(l["pour"]))))
    for e in chantiers(data, jour):
        if e["reste"] <= 7:
            L.append("- [ ] %s %s — %s, %s (%s)" % (emo(data, e["cours"]), e["titre"],
                                                    data["cours"][e["cours"]]["court"],
                                                    jx(e["reste"]), ETIQUETTES.get(etape(e), etape(e)).lower()))
    return L


def semaines_rouges(data, jour):
    lignes, total = [], 0
    for num, debut in sorted(((int(n), d(x)) for n, x in data["session"]["semaines"].items())):
        fin = debut + dt.timedelta(days=6)
        if fin < jour:
            continue
        dedans = [e for e in data["evaluations"]
                  if not e.get("fait") and debut <= d(e["date"]) <= fin]
        somme = sum(e["poids"] for e in dedans)
        if somme < SEUIL_ROUGE:
            continue
        total += 1
        quoi = ", ".join("%s %s %s" % (emo(data, e["cours"]), e["titre"],
                                       "%d %%" % e["poids"] if e["poids"] else "formatif")
                         for e in sorted(dedans, key=lambda e: (d(e["date"]), -e["poids"])))
        regle = data.get("notes_semaines", {}).get(str(num),
                "%d %% de la session en une semaine. Rien ne commence ce lundi-là." % somme)
        lignes.append("| **%d** | %s – %s | %s | %s |" % (num, carte.court(debut), carte.court(fin), quoi, regle))
    return (["## 🔴 Mes semaines rouges — %d encore devant moi" % total, "",
             "| Semaine | Dates | Ce qui tombe | La règle |",
             "| --- | --- | --- | --- |"] + lignes)


def echeances(data, jour):
    L = ["## 📅 Toutes mes échéances", "",
         "> 💡 Sélectionne ce tableau → **Transformer en base de données** pour filtrer par cours et trier par date.", "",
         "| | Date | Cours | Évaluation | Poids | Compte à rebours |",
         "| --- | --- | --- | --- | --- | --- |"]
    faites = sorted((e for e in data["evaluations"] if e.get("fait") or d(e["date"]) < jour),
                    key=lambda e: d(e["date"]))
    for e in faites:
        L.append("| ✅ | %s | %s %s | %s | %d %% | ✅ fait |" % (
            long(d(e["date"])), emo(data, e["cours"]), data["cours"][e["cours"]]["court"],
            e["titre"], e["poids"]))
    for e in chantiers_tous(data, jour):
        titre = e["titre"] + (" *(date à confirmer)*" if e.get("a_confirmer") else "")
        L.append("| %s | %s | %s %s | %s | %s | %s |" % (
            pastille(e["reste"]), long(d(e["date"])), emo(data, e["cours"]),
            data["cours"][e["cours"]]["court"], titre, poids_txt(e), jx(e["reste"])))
    return L


def semaine_type(data):
    total = sum(duree(b)[0] for b in data["blocs_travail"])
    L = ["## 🗓️ Ma semaine type — %d h %02d de travail" % (total // 60, total % 60), "",
         "| Quand | Durée | Ce que je fais |", "| --- | --- | --- |"]
    for b in sorted(data["blocs_travail"], key=lambda b: b["jour"]):
        quand = "%s %s – %s" % (JOURS[b["jour"] - 1].capitalize(), h(b["debut"]), h(b["fin"]))
        ico = "".join(emo(data, f) for f in b["focus"] if f in data["cours"]) or "🔁"
        gros = "GROS BLOC" in b["titre"]
        ligne = "| %s | %s | %s %s |" % (quand, duree(b)[1], ico, b["titre"])
        L.append(ligne.replace("| %s | %s |" % (quand, duree(b)[1]),
                               "| **%s** | **%s** |" % (quand, duree(b)[1])) if gros else ligne)
    L += ["", "> ⚠️ Vendredi soir, samedi après-midi et dimanche matin restent **vides**. "
          "Ce n'est pas du temps perdu : c'est ce qui rend les %d h %02d restantes tenables "
          "semaine après semaine." % (total // 60, total % 60)]
    return L


def methodes(data):
    L = ["## 🧠 Mes méthodes, cours par cours", ""]
    ordre = sorted(data["methodes"], key=lambda c: -data["cours"][c]["difficulte"])
    dur = max(data["cours"][c]["difficulte"] for c in ordre)
    for cle in ordre:
        L.append("### %s %s" % (emo(data, cle), data["cours"][cle]["nom"]))
        if data["cours"][cle]["difficulte"] == dur:
            L.append("*Cours où je me sens le plus fragile — c'est là que va le temps en priorité.*")
        L += [data["methodes"][cle], ""]
    return L[:-1]


def retard(data):
    bloc = [b for b in data["blocs_travail"] if "rattrapage" in b["focus"]]
    L = ["## 🔁 Si je prends du retard", ""]
    if bloc:
        b = bloc[0]
        L += ["> Le %s %s – %s ne sert **qu'à ça** : reprendre ce qui a sauté dans la semaine et "
              "refaire le plan des sept jours suivants. Rien d'autre ne s'y planifie."
              % (JOURS[b["jour"] - 1], h(b["debut"]), h(b["fin"])), ""]
    L += ["- %s" % r for r in data["rattrapage"]]
    return L


def a_confirmer(data, jour):
    L = ["## ✅ À faire confirmer auprès des profs", ""]
    for t in data["taches_admin"]:
        if t["pour"] == "recurrent":
            L.append("- [ ] 🔁 %s" % t["quoi"])
            continue
        e = d(t["pour"])
        if e < jour:
            L.append("- [ ] 🔴 %s — **en retard depuis le %s**" % (t["quoi"], carte.court(e)))
        else:
            L.append("- [ ] %s %s — pour le %s" % (pastille((e - jour).days), t["quoi"], carte.court(e)))
    return L


def progression(data, jour):
    av = avancement(data, jour)
    L = ["## 📊 Mon avancement", "", "| Cours | Part de la note déjà jouée |", "| --- | --- |"]
    for cle, (nom, pct) in sorted(av.items(), key=lambda kv: -kv[1][1]):
        L.append("| %s %s | %d %% |" % (emo(data, cle), nom, pct))
    moy = sum(p for _, p in av.values()) / len(av)
    reste = (d(data["session"]["fin"]) - jour).days
    L += ["", "> **%d %%** de la session est joué en moyenne. Il reste %d jours avant le %s"
          % (round(moy), reste, carte.court(d(data["session"]["fin"])))]
    return L


def page(data, jour):
    actifs = chantiers(data, jour)
    blocs = [entete(data, jour), aujourdhui(data, jour, actifs), sept_jours(data, jour),
             semaines_rouges(data, jour), echeances(data, jour), semaine_type(data),
             methodes(data), retard(data), a_confirmer(data, jour), progression(data, jour)]
    out = "\n---\n".join("\n".join(b) for b in blocs)
    return out + "\n\n---\n\n*Page regénérée par `notion.py` à partir de `donnees-session.json`. " \
                 "La carte du jour arrive chaque matin dans Slack.*"


def main():
    args = sys.argv[1:]
    jour = d(args[0]) if args else dt.date.today()
    sys.stdout.write(page(carte.charger(), jour) + "\n")


if __name__ == "__main__":
    main()

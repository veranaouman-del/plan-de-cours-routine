# -*- coding: utf-8 -*-
"""Tableau de bord Notion — Automne 2026.

Régénère le contenu complet de la page Notion « Ma session — Automne 2026 »
à partir de donnees-session.json. Le script n'écrit rien dans Notion : il
imprime le Markdown, qui est ensuite poussé par le connecteur Notion
(`update-page`, commande `replace_content`).

    python3 notion.py                 -> la page d'aujourd'hui
    python3 notion.py 2026-10-07      -> la page telle qu'elle serait ce jour-là
    python3 notion.py /tmp/page.md    -> écrit dans un fichier au lieu de stdout

Rien n'est codé en dur ici non plus : échéances, méthodes, règles des semaines
rouges, tout vient de donnees-session.json.
"""
import sys
import datetime as dt

import carte  # même source de données, mêmes règles de priorité

d = carte.d
JOURS, MOIS = carte.JOURS, carte.MOIS

PAGE_ID = "3df73824-e620-811e-9e6c-d07440cb6ec7"  # Ma session — Automne 2026


def long(j):
    return "%s %d %s" % (JOURS[j.weekday()], j.day, MOIS[j.month - 1])


def emo(data, cle):
    return data["cours"][cle].get("emoji", "•")


def cc(data, cle):
    """« 📕 Littérature » — le libellé court avec son emoji."""
    c = data["cours"][cle]
    return "%s %s" % (c.get("emoji", "•"), c.get("court", c["nom"]))


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
    return "🔴" if reste <= 4 else ("🟠" if reste <= 17 else "🔵")


# --------------------------------------------------------------------------
# Semaines rouges
# --------------------------------------------------------------------------
def semaines_rouges(data, jour):
    """Une semaine est rouge si elle porte 20 % ou plus, ou 3 évaluations et plus."""
    bornes = sorted(((int(n), d(x)) for n, x in data["session"]["semaines"].items()),
                    key=lambda p: p[1])
    out = []
    for num, debut in bornes:
        fin = debut + dt.timedelta(days=6)
        dedans = [e for e in data["evaluations"]
                  if not e.get("fait") and debut <= d(e["date"]) <= fin and d(e["date"]) >= jour]
        if not dedans:
            continue
        total = sum(e["poids"] for e in dedans)
        if total < 20 and len(dedans) < 3:
            continue
        regle = data.get("regles_semaines_rouges", {}).get(str(num))
        if not regle:
            regle = "%d %% en une semaine, sur %d évaluations. Rien ne commence ce lundi-là." % (
                total, len(dedans))
        dedans.sort(key=lambda e: (d(e["date"]), -e["poids"]))
        out.append({"num": num, "debut": debut, "fin": fin, "total": total,
                    "evals": dedans, "regle": regle})
    return out


# --------------------------------------------------------------------------
def rendu(data, jour):
    L = []
    A = L.append
    sem = carte.semaine_de(data, jour)
    actifs = carte.chantiers(data, jour)
    fin = d(data["session"]["fin"])
    a, b = data["session"]["semaine_etudes"]

    # ---- en-tête
    A("> %s" % data["programme"].replace(" - ", " — "))
    A("> Du %s au %s · Semaine d'études : %s au %s" % (
        carte.court(d(data["session"]["debut"])), carte.court(fin),
        carte.court(d(a)), carte.court(d(b))))
    A("> **Nous sommes en semaine %s sur 15.** Page mise à jour le %s." % (sem or "—", long(jour)))
    A("")
    A("---")
    A("")

    # ---- aujourd'hui
    A("## ☀️ Aujourd'hui — %s" % long(jour))
    A("")
    A("**Mes cours**")
    A("")
    cj = carte.cours_du_jour(data, jour)
    if cj:
        for c in cj:
            A("- %s `%s – %s` %s · %s" % (
                emo(data, c["cours"]), c["debut"].replace(":", " h "), c["fin"].replace(":", " h "),
                data["cours"][c["cours"]]["nom"], c["local"]))
    else:
        A("- Aucun cours — journée de travail libre")
    A("")

    ej = carte.evenements_du_jour(data, jour)
    if ej:
        A("**Rendez-vous à ne pas manquer**")
        A("")
        for e in ej:
            A("- 📌 `%s – %s` **%s** · %s" % (
                e["debut"].replace(":", " h "), e["fin"].replace(":", " h "),
                e["quoi"], e.get("lieu", "")))
        A("")

    if actifs:
        p = actifs[0]
        A("> 🔴 **Ma priorité : %s** — %s, %d %%, %s" % (
            p["titre"], data["cours"][p["cours"]]["nom"], p["poids"], carte.jx(p["reste"])))
        A("> Si je ne fais qu'une seule chose aujourd'hui, c'est celle-là.")
        A("")

    A("**À cocher aujourd'hui**")
    A("")
    etiquettes = {"RETARD": "En retard", "ADMIN": "Admin", "LECTURE": "Lecture",
                  "REMISE": "Remise", "FINIR": "Finir", "AVANCER": "Avancer",
                  "RELIRE": "Relire", "TEST BLANC": "Test blanc", "FICHES": "Fiches",
                  "NOTES": "Notes"}
    for tag, t in carte.taches_du_jour(data, jour, actifs):
        A("- [ ] **%s** — %s" % (etiquettes.get(tag, tag.capitalize()), t))
    A("")

    A("**Mes blocs de travail**")
    A("")
    bj = carte.blocs_du_jour(data, jour)
    if bj:
        for bl in bj:
            ligne = "- ⏱️ `%s – %s` %s" % (bl["debut"].replace(":", " h "),
                                           bl["fin"].replace(":", " h "), bl["titre"])
            rogne = [e for e in ej if carte.chevauche(bl, e)]
            if rogne:
                ligne += " — ⚠️ **rogné par : %s**" % ", ".join(e["quoi"] for e in rogne)
            A(ligne)
    else:
        A("- Journée libre — repos assumé, c'est prévu.")
    A("")
    A("---")
    A("")

    # ---- sept prochains jours
    horizon = jour + dt.timedelta(days=7)
    A("## ⚡ Mes sept prochains jours — %s au %s" % (carte.court(jour), carte.court(horizon)))
    A("")
    for t in data["taches_admin"]:
        if t["pour"] == "recurrent":
            continue
        e = d(t["pour"])
        if e < jour and t.get("urgent"):
            A("- [ ] 🔴 %s — **en retard depuis le %s**" % (t["quoi"], carte.court(e)))
        elif jour <= e <= horizon:
            A("- [ ] %s %s — pour le %s" % ("🔴" if t.get("urgent") else "🔵", t["quoi"], carte.court(e)))
    for ev in data.get("evenements", []):
        e = d(ev["date"])
        if jour <= e <= horizon:
            ligne = "- [ ] 📌 %s — %s, %s – %s" % (ev["quoi"], carte.court(e),
                                                   ev["debut"].replace(":", " h "),
                                                   ev["fin"].replace(":", " h "))
            if ev.get("lieu"):
                ligne += " · %s" % ev["lieu"]
            A(ligne)
    for l in data["lectures"]:
        e = d(l["pour"])
        if jour <= e <= horizon:
            A("- [ ] %s %s — pour le %s" % (emo(data, l["cours"]), l["quoi"], carte.court(e)))
    for ev in carte.chantiers_tous(data, jour):
        if ev["reste"] > 7:
            continue
        etape = carte.etape(dict(ev, reste=ev["reste"])).lower()
        A("- [ ] %s %s — %s, %s (%s)" % (emo(data, ev["cours"]), ev["titre"],
                                         data["cours"][ev["cours"]].get("court"),
                                         carte.jx(ev["reste"]), etape))
    A("")
    A("---")
    A("")

    # ---- semaines rouges
    rouges = semaines_rouges(data, jour)
    A("## 🔴 Mes semaines rouges — %d encore devant moi" % len(rouges))
    A("")
    A("| Semaine | Dates | Ce qui tombe | La règle |")
    A("| --- | --- | --- | --- |")
    for r in rouges:
        quoi = ", ".join("%s %s %s" % (emo(data, e["cours"]), e["titre"],
                                       ("%d %%" % e["poids"]) if e["poids"] else "formatif")
                         for e in r["evals"])
        A("| **%d** | %s – %s | %s | %s |" % (r["num"], carte.court(r["debut"]),
                                              carte.court(r["fin"]), quoi, r["regle"]))
    A("")
    A("---")
    A("")

    # ---- toutes les échéances
    A("## 📅 Toutes mes échéances")
    A("")
    A("> 💡 Sélectionne ce tableau → **Transformer en base de données** pour filtrer par cours et trier par date.")
    A("")
    A("|  | Date | Cours | Évaluation | Poids | Compte à rebours |")
    A("| --- | --- | --- | --- | --- | --- |")
    for e in sorted(data["evaluations"], key=lambda e: (d(e["date"]), -e["poids"])):
        date = d(e["date"])
        reste = (date - jour).days
        titre = e["titre"] + (" *(date à confirmer)*" if e.get("a_confirmer") else "")
        if e.get("fait") or reste < 0:
            marque, compte = "✅", "✅ fait"
        else:
            marque, compte = pastille(reste), carte.jx(reste)
        A("| %s | %s | %s | %s | %s | %s |" % (marque, long(date), cc(data, e["cours"]),
                                               titre, poids_txt(e), compte))
    A("")
    A("---")
    A("")

    # ---- semaine type
    heures = 0.0
    for bl in data["blocs_travail"]:
        h1, m1 = (int(x) for x in bl["debut"].split(":"))
        h2, m2 = (int(x) for x in bl["fin"].split(":"))
        heures += (h2 * 60 + m2 - h1 * 60 - m1) / 60.0
    A("## 🗓️ Ma semaine type — %d h %02d de travail" % (int(heures), round((heures % 1) * 60)))
    A("")
    A("| Quand | Durée | Ce que je fais |")
    A("| --- | --- | --- |")
    for bl in sorted(data["blocs_travail"], key=lambda b: (b["jour"], b["debut"])):
        h1, m1 = (int(x) for x in bl["debut"].split(":"))
        h2, m2 = (int(x) for x in bl["fin"].split(":"))
        mn = h2 * 60 + m2 - h1 * 60 - m1
        duree = "%d h %02d" % (mn // 60, mn % 60) if mn % 60 else "%d h" % (mn // 60)
        quand = "%s %s – %s" % (JOURS[bl["jour"] - 1].capitalize(),
                                bl["debut"].replace(":", " h "), bl["fin"].replace(":", " h "))
        icones = "".join(emo(data, c) for c in bl["focus"] if c in data["cours"]) or "🔁"
        gras = mn >= 180
        fmt = (lambda x: "**%s**" % x) if gras else (lambda x: x)
        A("| %s | %s | %s %s |" % (fmt(quand), fmt(duree), icones, bl["titre"]))
    A("")
    A("> ⚠️ %s" % data.get("_blocs", "").replace("Ne pas les remplir", "**Ne pas les remplir**"))
    A("")
    A("---")
    A("")

    # ---- méthodes
    A("## 🧠 Mes méthodes, cours par cours")
    A("")
    dur = max(c.get("difficulte", 1) for c in data["cours"].values())
    for cle, c in sorted(data["cours"].items(), key=lambda kv: -kv[1].get("difficulte", 1)):
        A("### %s %s" % (c.get("emoji", "•"), c["nom"]))
        A("")
        if c.get("difficulte", 1) >= dur:
            A("*Cours où je me sens le plus fragile — c'est là que va le temps en priorité.*")
            A("")
        A(c.get("methode", ""))
        A("")
    A("---")
    A("")

    # ---- rattrapage
    A("## 🔁 Si je prends du retard")
    A("")
    A("> Le dimanche 16 h – 18 h ne sert **qu'à ça** : reprendre ce qui a sauté dans la semaine "
      "et refaire le plan des sept jours suivants. Rien d'autre ne s'y planifie.")
    A("")
    A("- Une journée sautée → elle se reprend dans le bloc du dimanche, pas en empilant sur le lendemain.")
    A("- Une semaine sautée → je laisse tomber la prise d'avance du jeudi et je protège les deux gros blocs (mardi, mercredi).")
    A("- Deux semaines de retard → j'écris au prof concerné **avant** l'échéance, jamais après. "
      "Une remise négociée vaut mieux qu'une remise ratée.")
    A("")
    A("---")
    A("")

    # ---- à confirmer
    A("## ✅ À faire confirmer auprès des profs")
    A("")
    for t in data["taches_admin"]:
        if t["pour"] == "recurrent":
            A("- [ ] 🔁 %s" % t["quoi"])
            continue
        e = d(t["pour"])
        if e < jour and t.get("urgent"):
            A("- [ ] 🔴 %s — **en retard depuis le %s**" % (t["quoi"], carte.court(e)))
        else:
            A("- [ ] %s %s — pour le %s" % ("🔴" if t.get("urgent") else "🔵", t["quoi"], carte.court(e)))
    A("")
    A("---")
    A("")

    # ---- avancement
    A("## 📊 Mon avancement")
    A("")
    A("| Cours | Part de la note déjà jouée |")
    A("| --- | --- |")
    pcts = []
    for cle, (nom, pct) in carte.avancement(data, jour).items():
        pcts.append(pct)
        A("| %s | %d %% |" % (cc(data, cle), pct))
    A("")
    A("> **%d %%** de la session est joué en moyenne. Il reste %d jours avant le %s"
      % (round(sum(pcts) / len(pcts)), (fin - jour).days, carte.court(fin)))
    A("")
    A("---")
    A("")
    A("*Page regénérée par **`notion.py`** à partir de **`donnees-session.json`**. "
      "La carte du jour arrive chaque matin dans Slack.*")

    return "\n".join(L)


def main():
    args = list(sys.argv[1:])
    jour = dt.date.today()
    if args and len(args[0]) == 10 and args[0][4] == "-":
        jour = d(args.pop(0))
    md = rendu(carte.charger(), jour)
    if args:
        with open(args[0], "w", encoding="utf-8") as fh:
            fh.write(md)
        print(args[0])
    else:
        print(md)


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""Page Notion « Ma session » — Automne 2026.

Génère le contenu complet de la page Notion à partir de donnees-session.json.
Rien n'est codé en dur ici : les échéances, les tâches et les méthodes viennent
toutes du JSON, exactement comme la carte du jour.

    python3 notion.py                  -> aujourd'hui, sur la sortie standard
    python3 notion.py 2026-11-13       -> une date précise
    python3 notion.py --focus f.md     -> insère les encadrés du jour (écrits à la main)
                                          juste après la priorité du jour

La sortie est du Markdown Notion (NFM) : <callout>, <table>, <b>, <br />.
Elle se colle telle quelle dans notion-update-page (commande replace_content).
"""
import datetime as dt
import sys

import carte as C

JOURS_COURTS = ["lun.", "mar.", "mer.", "jeu.", "ven.", "sam.", "dim."]


# --------------------------------------------------------------------------
# Petits utilitaires de mise en forme
# --------------------------------------------------------------------------
def longue(j):
    return "%s %d %s" % (C.JOURS[j.weekday()], j.day, C.MOIS[j.month - 1])


def courte(j):
    jour = "1er" if j.day == 1 else str(j.day)
    return "%s %s %s" % (JOURS_COURTS[j.weekday()], jour, C.ABREV[j.month - 1])


def heure(h):
    return h.replace(":", " h ")


def emoji(data, cle):
    return data["cours"][cle].get("emoji", "•")


def nom(data, cle):
    return "%s %s" % (emoji(data, cle), data["cours"][cle]["nom"])


def poids_txt(e):
    if not e["poids"]:
        return "formatif"
    txt = "%d %%" % e["poids"]
    if e["poids"] >= 20:
        txt = "<b>%s</b>" % txt
    if e.get("poids_approx"):
        txt += " <i>(estimé)</i>"
    return txt


def table(entetes, lignes):
    out = ['<table fit-page-width="true" header-row="true">']
    for rangee in [entetes] + lignes:
        out.append("<tr>")
        for cell in rangee:
            out.append("<td></td>" if cell == "" else "<td>\n%s\n</td>" % cell)
        out.append("</tr>")
    out.append("</table>")
    return "\n".join(out)


# --------------------------------------------------------------------------
# Calculs
# --------------------------------------------------------------------------
def points_restants(data, jour):
    """Somme des pondérations encore à jouer."""
    return sum(e["poids"] for e in C.chantiers_tous(data, jour))


def a_confirmer(data, jour):
    """Évaluations passées dont rien ne confirme la remise."""
    out = []
    for e in data["evaluations"]:
        if e.get("a_verifier_lea") and C.d(e["date"]) < jour:
            out.append(e)
    return sorted(out, key=lambda e: e["date"])


def semaines_rouges(data, jour):
    """Toute semaine de session où se joue 30 % ou plus, tous cours confondus."""
    bornes = sorted(((int(n), C.d(x)) for n, x in data["session"]["semaines"].items()),
                    key=lambda p: p[1])
    out = []
    for i, (num, debut) in enumerate(bornes):
        fin = (bornes[i + 1][1] - dt.timedelta(days=1)) if i + 1 < len(bornes) \
            else C.d(data["session"]["fin"]) + dt.timedelta(days=9)
        dedans = [e for e in data["evaluations"] if debut <= C.d(e["date"]) <= fin]
        total = sum(e["poids"] for e in dedans)
        if total >= 30:
            out.append({"num": num, "debut": debut, "fin": fin, "poids": total,
                        "evals": sorted(dedans, key=lambda e: -e["poids"]),
                        "passee": fin < jour})
    return out


def retard(data, jour):
    """Tâches administratives, les plus en retard d'abord."""
    out = []
    for t in data["taches_admin"]:
        if t["pour"] == "recurrent":
            out.append((None, t))
            continue
        out.append(((C.d(t["pour"]) - jour).days, t))
    return sorted(out, key=lambda p: (p[0] is None, p[0] if p[0] is not None else 0))


# --------------------------------------------------------------------------
# La page
# --------------------------------------------------------------------------
def page(data, jour, focus=""):
    L = []
    w = L.append
    sem = C.semaine_de(data, jour)
    actifs = C.chantiers(data, jour)
    tous = C.chantiers_tous(data, jour)

    w("> %s · %s → %s<br /><b>Semaine %s sur 15</b>"
      % (data["programme"], longue(C.d(data["session"]["debut"])),
         longue(C.d(data["session"]["fin"])), sem if sem else "—"))
    w("")
    w("---")
    w("")

    # ---------------------------------------------------------------- aujourd'hui
    w("## 📍 Aujourd'hui — %s" % longue(jour))
    w("")
    cj = C.cours_du_jour(data, jour)
    if cj:
        for c in cj:
            w("- %s <b>%s – %s</b> · %s · %s"
              % (emoji(data, c["cours"]), heure(c["debut"]), heure(c["fin"]),
                 data["cours"][c["cours"]]["nom"], c["local"]))
    else:
        w("- 🛋️ <b>Aucun cours</b> — journée de travail libre")
    for b in C.blocs_du_jour(data, jour):
        w("- 🎯 <b>%s – %s</b> · %s" % (heure(b["debut"]), heure(b["fin"]), b["titre"]))
    w("")

    reste = points_restants(data, jour)
    fin_txt = courte(max(C.d(e["date"]) for e in tous)) if tous else "la fin de la session"
    w('<callout icon="🎯" color="blue_bg">')
    w("<b>%d %% de points restent à jouer d'ici la fin de la session.</b> "
      "Tout se décide entre aujourd'hui et le %s." % (reste, fin_txt.rstrip(".")))
    w("</callout>")
    w("")

    if actifs:
        p = actifs[0]
        w("> 🔥 <b>Priorité du jour :</b> %s — %s (%s), %s. Étape : <b>%s</b>."
          % (nom(data, p["cours"]), p["titre"],
             ("%d %%" % p["poids"]) if p["poids"] else "formatif",
             C.jx(p["reste"]), C.etape(p).lower()))
        w("")

    if focus.strip():
        w(focus.strip())
        w("")

    # ---------------------------------------------------------------- à confirmer
    incertain = a_confirmer(data, jour)
    if incertain:
        w("---")
        w("")
        w("## 🔴 À confirmer — points au statut incertain")
        w("")
        w("> Ces évaluations sont passées, mais rien ne confirme qu'elles ont bien été "
          "déposées, ou même tenues. Tant qu'elles sont là, mon avancement est une "
          "hypothèse, pas un fait.")
        w("")
        w(table(["Évaluation", "Cours", "Poids", "Était prévu le"],
                [[e["titre"], nom(data, e["cours"]), poids_txt(e), courte(C.d(e["date"]))]
                 for e in incertain]))
        w("")
        total = sum(e["poids"] for e in incertain)
        w("- [ ] Vérifier sur LÉA ou par MIO celles qui sont réglées → l'avancement redevient exact")
        w("- [ ] Écrire au prof <b>le jour même</b> pour chaque ligne qui reste — "
          "<b>%d %%</b> de points au statut incertain" % total)
        w("- [ ] Une fois vérifié : retirer <code>a_verifier_lea</code> dans "
          "<code>donnees-session.json</code>")
        w("")

    # ---------------------------------------------------------------- à faire
    w("---")
    w("")
    w("## ✅ À faire aujourd'hui")
    w("")
    puces = {"RETARD": "🔴", "REMISE": "🔴", "ADMIN": "📌", "LECTURE": "📖",
             "FINIR": "🟠", "TEST BLANC": "🟠", "AVANCER": "🔵", "FICHES": "🔵",
             "NOTES": "🔵", "RELIRE": "🟠"}
    for tag, t in C.taches_du_jour(data, jour, actifs):
        w("- [ ] %s <b>%s</b> — %s" % (puces.get(tag, "🔵"), tag, t))
    w("")

    # ---------------------------------------------------------------- 7 jours
    w("---")
    w("")
    w("## 🗓️ Les 7 prochains jours")
    w("")
    lignes = []
    for i in range(7):
        j = jour + dt.timedelta(days=i)
        bouts = []
        for c in C.cours_du_jour(data, j):
            bouts.append("%s %s – %s · %s" % (emoji(data, c["cours"]),
                                              heure(c["debut"]), heure(c["fin"]), c["local"]))
        actifs_j = C.chantiers(data, j)
        for b in C.blocs_du_jour(data, j):
            cible = next((e for e in actifs_j if e["cours"] in b["focus"]),
                         actifs_j[0] if actifs_j else None)
            txt = "<b>%s – %s</b> %s" % (heure(b["debut"]), heure(b["fin"]), b["titre"])
            if cible:
                txt += " — %s : %s <i>(%s)</i>" % (emoji(data, cible["cours"]),
                                                   cible["titre"], C.etape(cible).lower())
            bouts.append(txt)
        for l in data["lectures"]:
            if C.d(l["pour"]) == j:
                bouts.append("📖 %s" % l["quoi"])
        for e in data["evaluations"]:
            if C.d(e["date"]) == j and not e.get("fait"):
                bouts.append("⚠️ <b>%s</b> — %s · %s"
                             % (e["titre"], nom(data, e["cours"]), poids_txt(e)))
        libelle = "<b>%s</b>" % courte(j) + (" ← <i>aujourd'hui</i>" if i == 0 else "")
        lignes.append([libelle, "<br />".join(bouts) if bouts else "<i>journée libre — repos assumé</i>"])
    w(table(["Jour", "Ce que je fais"], lignes))
    w("")

    # ---------------------------------------------------------------- à régler
    w("---")
    w("")
    w("## 📌 À régler")
    w("")
    for jours, t in retard(data, jour):
        if jours is None:
            w("- [ ] 🔁 %s" % t["quoi"])
            continue
        if jours < 0:
            quand = "<i>%d jours de retard</i>" % abs(jours)
            puce = "🔴"
        else:
            quand = "<i>pour le %s</i>" % courte(C.d(t["pour"]))
            puce = "🟠" if jours <= 3 else "🔵"
        ligne = "- [ ] %s <b>%s</b> — %s" % (puce, t["quoi"], quand)
        if t.get("note"):
            ligne += " · %s" % t["note"]
        w(ligne)
    w("")

    # ---------------------------------------------------------------- échéances
    w("---")
    w("")
    w("## 📅 Toutes mes échéances à venir")
    w("")
    w("> 💡 Sélectionne ce tableau → <b>Transformer en base de données</b> pour filtrer "
      "par cours et cocher au fur et à mesure.")
    w("")
    lignes = []
    for e in tous:
        pastille = "🔴" if e["reste"] <= 4 else ("🟠" if e["reste"] <= 12 else "🔵")
        titre = e["titre"] + (" ⚠️" if e.get("a_confirmer") else "")
        lignes.append([pastille, courte(C.d(e["date"])), nom(data, e["cours"]),
                       titre, poids_txt(e), C.jx(e["reste"])])
    w(table(["", "Date", "Cours", "Évaluation", "Poids", "Compte à rebours"], lignes))
    w("")
    w("> ⚠️ = date ou pondération encore à confirmer auprès du prof. Être prêt une semaine "
      "trop tôt ne coûte rien ; l'inverse, oui.")
    w("")

    # ---------------------------------------------------------------- lectures
    futures = [l for l in data["lectures"] if C.d(l["pour"]) >= jour]
    if futures:
        w("---")
        w("")
        w("## 📖 Mes lectures")
        w("")
        w(table(["Pour le", "Cours", "À lire"],
                [[courte(C.d(l["pour"])), nom(data, l["cours"]), l["quoi"]]
                 for l in sorted(futures, key=lambda l: l["pour"])]))
        w("")

    # ---------------------------------------------------------------- semaines rouges
    w("---")
    w("")
    w("## 🔴 Mes semaines rouges")
    w("")
    w("> Toute semaine où il se joue <b>30 % ou plus</b> de points, tous cours confondus. "
      "C'est là que se gagne ou se perd la session.")
    w("")
    lignes = []
    for s in semaines_rouges(data, jour):
        quoi = " · ".join("%s %s %s" % (emoji(data, e["cours"]), e["titre"], poids_txt(e))
                          for e in s["evals"])
        lignes.append(["<b>%d</b>" % s["num"],
                       "%s – %s" % (courte(s["debut"]), courte(s["fin"])),
                       quoi, "<b>%d %%</b>" % s["poids"],
                       "✅ passée" if s["passee"] else "⏳ à venir"])
    w(table(["Semaine", "Dates", "Ce qui tombe", "Poids total", "Statut"], lignes))
    w("")

    # ---------------------------------------------------------------- semaine type
    w("---")
    w("")
    w("## 🗓️ Ma semaine type")
    w("")
    lignes = []
    for b in sorted(data["blocs_travail"], key=lambda b: (b["jour"], b["debut"])):
        h1 = dt.datetime.strptime(b["debut"], "%H:%M")
        h2 = dt.datetime.strptime(b["fin"], "%H:%M")
        mn = int((h2 - h1).total_seconds() // 60)
        duree = ("%d h %02d" % (mn // 60, mn % 60)) if mn % 60 else "%d h" % (mn // 60)
        emojis = "".join(emoji(data, f) for f in b["focus"] if f in data["cours"]) or "🔁"
        gros = b["titre"].startswith("GROS") or "Lectures" in b["titre"]
        quand = "%s %s – %s" % (C.JOURS[b["jour"] - 1].capitalize(),
                                heure(b["debut"]), heure(b["fin"]))
        ligne = [quand, duree, "%s %s" % (emojis, b["titre"])]
        if gros:
            ligne = ["<b>%s</b>" % x for x in ligne]
        lignes.append(ligne)
    w(table(["Quand", "Durée", "Ce que je fais"], lignes))
    w("")
    w("> ⚠️ Vendredi soir, samedi après-midi et dimanche matin restent <b>vides</b>. "
      "Ce n'est pas du temps perdu : c'est ce qui rend le reste tenable, semaine après semaine.")
    w("")

    # ---------------------------------------------------------------- méthodes
    w("---")
    w("")
    w("## 🧠 Mes méthodes, cours par cours")
    w("")
    ordre = sorted(data["methodes"], key=lambda k: -data["cours"][k]["difficulte"])
    for cle in ordre:
        dur = " — <i>ma matière la plus difficile</i>" if data["cours"][cle]["difficulte"] >= 4 else ""
        w("### %s%s" % (nom(data, cle), dur))
        w("")
        w(data["methodes"][cle])
        w("")

    # ---------------------------------------------------------------- avancement
    w("---")
    w("")
    w("## 📊 Mon avancement")
    w("")
    av = C.avancement(data, jour)
    incertain_par_cours = {}
    for e in incertain:
        incertain_par_cours[e["cours"]] = incertain_par_cours.get(e["cours"], 0) + e["poids"]
    lignes = []
    for cle, (_, pct) in sorted(av.items(), key=lambda p: -p[1][1]):
        note = " <i>(dont %d %% à confirmer)</i>" % incertain_par_cours[cle] \
            if cle in incertain_par_cours else ""
        barre = "▰" * int(round(pct / 10.0)) + "▱" * (10 - int(round(pct / 10.0)))
        lignes.append([nom(data, cle), "%d %%%s" % (pct, note), "<code>%s</code>" % barre])
    w(table(["Cours", "Part de la note déjà jouée", ""], lignes))
    w("")
    moyenne = sum(p for _, p in av.values()) / float(len(av))
    total_incertain = sum(incertain_par_cours.values())
    w("> <b>%d %%</b> de la session est joué en moyenne, tous cours confondus." % round(moyenne)
      + (" Mais <b>%d %%</b> de points restent au statut incertain tant que les évaluations "
         "ci-dessus ne sont pas confirmées." % total_incertain if total_incertain else ""))
    w("")
    w("<i>Mis à jour le %s · source : </i><i><code>donnees-session.json</code></i>"
      "<i> · généré par </i><i><code>notion.py</code></i>" % longue(jour))

    return "\n".join(L)


# --------------------------------------------------------------------------
def main():
    args = sys.argv[1:]
    focus = ""
    if "--focus" in args:
        i = args.index("--focus")
        with open(args[i + 1], encoding="utf-8") as fh:
            focus = fh.read()
        args = args[:i] + args[i + 2:]
    jour = C.d(args[0]) if args else dt.date.today()
    print(page(C.charger(), jour, focus))


if __name__ == "__main__":
    main()

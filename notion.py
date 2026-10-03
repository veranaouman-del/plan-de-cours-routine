# -*- coding: utf-8 -*-
"""Page Notion « Ma session » — générée depuis donnees-session.json.

    python3 notion.py                -> aujourd'hui, markdown enrichi Notion sur stdout
    python3 notion.py 2026-10-07     -> une date précise

La sortie se colle telle quelle dans notion-update-page (commande replace_content).
Rien n'est codé en dur : pour changer une échéance, éditer donnees-session.json.

Le format de tableau est celui que Notion renvoie à la lecture (<table header-row>…),
afin que la page puisse être relue puis réécrite sans se déformer.
"""
import sys
import datetime as dt
import collections

import carte
from carte import d, court, jx, semaine_de, en_semaine_etudes


def long_date(j):
    jour = carte.JOURS[j.weekday()]
    num = "1er" if j.day == 1 else str(j.day)
    return "%s %s %s" % (jour, num, carte.MOIS[j.month - 1])


def court_jour(j):
    """« mar. 22 sept. » — colonne de tableau."""
    abrev = ["lun.", "mar.", "mer.", "jeu.", "ven.", "sam.", "dim."][j.weekday()]
    num = "1er" if j.day == 1 else str(j.day)
    return "%s %s %s" % (abrev, num, carte.ABREV[j.month - 1])


def echeance_txt(reste):
    """« aujourd'hui », « demain », mais « J-4 » garde sa majuscule."""
    t = jx(reste)
    return t if t.startswith("J-") else t.lower()


def em(data, cle):
    return data["cours"][cle].get("emoji", "")


def nom(data, cle):
    return "%s %s" % (em(data, cle), data["cours"][cle]["nom"])


def poids_txt(ev):
    if not ev["poids"]:
        return "formatif"
    t = "%d %%" % ev["poids"]
    return "**%s**" % t if ev["poids"] >= 20 else t


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


# --------------------------------------------------------------------------
# Semaines rouges : toute semaine de session où il se joue >= 30 %
# --------------------------------------------------------------------------
def semaines_rouges(data, jour, seuil=30):
    paires = sorted(((int(n), d(deb)) for n, deb in data["session"]["semaines"].items()),
                    key=lambda p: p[1])
    par_sem = collections.defaultdict(list)
    for ev in data["evaluations"]:
        s = semaine_de(data, d(ev["date"]))
        if s:
            par_sem[s].append(ev)
    courante = semaine_de(data, jour)
    lignes = []
    for num, debut in paires:
        evs = par_sem.get(num, [])
        total = sum(e["poids"] for e in evs)
        if total < seuil:
            continue
        fin = debut + dt.timedelta(days=6)
        etiquette = "**%d**" % num
        if num == courante:
            etiquette += " ← *ici*"
        quoi = " · ".join("%s %s %d %%" % (em(data, e["cours"]), e["titre"], e["poids"])
                          for e in sorted(evs, key=lambda e: -e["poids"]) if e["poids"])
        lignes.append([etiquette,
                       "%s – %s" % (court(debut), court(fin)),
                       quoi,
                       "**%d %%**" % total])
    return lignes


def sept_jours(data, jour):
    lignes = []
    for i in range(7):
        j = jour + dt.timedelta(days=i)
        cj = carte.cours_du_jour(data, j)
        bj = carte.blocs_du_jour(data, j)
        colonne = [ "%s %s" % (em(data, c["cours"]), data["cours"][c["cours"]]["court"]) for c in cj ]
        for b in bj:
            colonne.append("%s – %s" % (b["debut"].replace(":", " h "), b["fin"].replace(":", " h ")))
        if en_semaine_etudes(data, j):
            colonne = ["*semaine d'études*"]

        etiquette = "**%s**" % court_jour(j)
        if i == 0:
            etiquette += " ← *aujourd'hui*"

        # ce qui tombe ce jour-là prime ; sinon le chantier le plus urgent
        du_jour = [e for e in data["evaluations"]
                   if not e.get("fait") and d(e["date"]) == j]
        if du_jour:
            e = max(du_jour, key=lambda e: e["poids"])
            quoi = "🔥 **%s — %s**" % (nom(data, e["cours"]), e["titre"])
        else:
            actifs = carte.chantiers(data, j)
            if actifs:
                e = actifs[0]
                quoi = "%s — %s *(%s)*" % (nom(data, e["cours"]), e["titre"],
                                           carte.etape(e).lower())
            else:
                quoi = "—"
        lignes.append([etiquette, "<br>".join(colonne) or "—", quoi])
    return lignes


# --------------------------------------------------------------------------
def page(data, jour):
    L = []
    sem = semaine_de(data, jour)
    actifs = carte.chantiers(data, jour)
    A = L.append

    A("# 🎓 Ma session — Automne 2026")
    A("> Cégep de Granby · Techniques de l'informatique (420.B0) · 24 août → 11 décembre")
    a, b = data["session"]["semaine_etudes"]
    A("> **Semaine %s sur 15** · Semaine d'études : %s au %s"
      % (sem or "—", d(a).day,
         "%d %s" % (d(b).day, carte.MOIS[d(b).month - 1])))
    A("---")

    # ---- Aujourd'hui
    A("## 📍 Aujourd'hui — %s" % long_date(jour))
    cj = carte.cours_du_jour(data, jour)
    for c in cj:
        A("- %s · %s – %s · %s" % (nom(data, c["cours"]),
                                   c["debut"].replace(":", " h "),
                                   c["fin"].replace(":", " h "), c["local"]))
    if not cj:
        A("- *Aucun cours aujourd'hui*")
    for bl in carte.blocs_du_jour(data, jour):
        A("- 🎯 **%s** · %s – %s" % (bl["titre"], bl["debut"].replace(":", " h "),
                                     bl["fin"].replace(":", " h ")))
    if actifs:
        p = actifs[0]
        A("> 🔥 **Priorité du jour :** %s — %s (%d %%), **%s**."
          % (nom(data, p["cours"]), p["titre"], p["poids"], echeance_txt(p["reste"])))
    A("---")

    # ---- À faire aujourd'hui
    A("## ✅ À faire aujourd'hui")
    for tag, t in carte.taches_du_jour(data, jour, actifs):
        puce = "🔴" if tag == "RETARD" else ("📕" if tag == "LECTURE" else
               ("✉️" if tag == "ADMIN" else "🔵"))
        A("- [ ] %s **%s** — %s" % (puce, tag, t))
    A("---")

    # ---- 7 prochains jours
    A("## 🗓️ Les 7 prochains jours")
    A(table(["Jour", "Cours et blocs", "Ce que je fais"], sept_jours(data, jour)))
    A("---")

    # ---- À confirmer
    retards = carte.a_confirmer(data, jour)
    if retards:
        A("## 🔴 À confirmer — remises passées jamais cochées")
        A("> Ces évaluations sont passées et toujours marquées « non faites » dans "
          "`donnees-session.json`. Tant qu'elles y sont, mon avancement est une "
          "hypothèse, pas un fait.")
        A(table(["Évaluation", "Cours", "Poids", "Était dû le", "Retard"],
                [[e["titre"], nom(data, e["cours"]), poids_txt(e),
                  court_jour(d(e["date"])),
                  "%d jour%s" % (e["passe"], "s" if e["passe"] > 1 else "")]
                 for e in retards]))
        A("- [ ] Cocher celles qui sont remises → l'avancement redevient exact")
        A("- [ ] Écrire au prof **le jour même** pour celles qui ne le sont pas")
        A("---")

    # ---- Admin
    A("## 📌 À régler tout de suite")
    for t in data["taches_admin"]:
        if t["pour"] == "recurrent":
            A("- [ ] 🔁 %s" % t["quoi"])
            continue
        reste = (d(t["pour"]) - jour).days
        if reste < 0:
            A("- [ ] 🔴 **%s** — *%d jour%s de retard*"
              % (t["quoi"], -reste, "s" if -reste > 1 else ""))
        elif reste <= 7:
            A("- [ ] ✉️ %s — *%s*" % (t["quoi"], echeance_txt(reste)))
    A("---")

    # ---- Échéances
    A("## 📅 Toutes mes échéances à venir")
    A("> 💡 Sélectionne ce tableau → **Transformer en base de données** pour filtrer "
      "par cours et cocher au fur et à mesure.")
    lignes = []
    for e in carte.chantiers_tous(data, jour):
        pastille = "🔴" if e["reste"] <= 2 else ("🟠" if e["reste"] <= 10 else "🔵")
        lignes.append([pastille, court_jour(d(e["date"])), nom(data, e["cours"]),
                       e["titre"], poids_txt(e), jx(e["reste"])])
    A(table(["", "Date", "Cours", "Évaluation", "Poids", "Compte à rebours"], lignes))
    A("---")

    # ---- Lectures
    lect = [l for l in data["lectures"] if d(l["pour"]) >= jour]
    if lect:
        A("## 📖 Mes lectures")
        A(table(["Pour le", "Cours", "À lire"],
                [[court_jour(d(l["pour"])), nom(data, l["cours"]), l["quoi"]]
                 for l in sorted(lect, key=lambda l: l["pour"])]))
        A("---")

    # ---- Semaines rouges
    A("## 🔴 Mes semaines rouges")
    A("> Toute semaine de session où il se joue **30 % ou plus** de points, tous cours "
      "confondus. C'est là que se gagne ou se perd la session.")
    A(table(["Semaine", "Dates", "Ce qui tombe", "Poids total"], semaines_rouges(data, jour)))
    A("---")

    # ---- Semaine type
    A("## 🗓️ Ma semaine type")
    lignes = []
    for bl in data["blocs_travail"]:
        jn = carte.JOURS[bl["jour"] - 1].capitalize()
        h1 = dt.datetime.strptime(bl["debut"], "%H:%M")
        h2 = dt.datetime.strptime(bl["fin"], "%H:%M")
        mins = int((h2 - h1).total_seconds() // 60)
        duree = "%d h%s" % (mins // 60, (" %02d" % (mins % 60)) if mins % 60 else "")
        quand = "%s %s – %s" % (jn, bl["debut"].replace(":", " h "), bl["fin"].replace(":", " h "))
        emos = "".join(em(data, f) for f in bl["focus"] if f in data["cours"])
        gros = "GROS BLOC" in bl["titre"] or "RATTRAPAGE" in bl["titre"]
        titre = "%s %s" % (emos or "🔁", bl["titre"])
        if gros:
            quand, duree, titre = "**%s**" % quand, "**%s**" % duree, "**%s**" % titre
        lignes.append([quand, duree, titre])
    A(table(["Quand", "Durée", "Ce que je fais"], lignes))
    A("> ⚠️ Vendredi soir, samedi après-midi et dimanche matin restent **vides**. "
      "Ce n'est pas du temps perdu : c'est ce qui rend le reste tenable semaine après semaine.")
    A("---")

    # ---- Méthodes
    A("## 🧠 Mes méthodes, cours par cours")
    ordre = sorted(data["cours"].items(), key=lambda kv: -kv[1].get("difficulte", 0))
    for cle, c in ordre:
        if cle not in data.get("methodes", {}):
            continue
        dur = " — *ma matière la plus difficile*" if c.get("difficulte", 0) >= 4 else ""
        A("### %s %s%s" % (em(data, cle), c["nom"], dur))
        A(data["methodes"][cle])
    A("---")

    # ---- Rattrapage
    A("## 🔁 Quand je prends du retard")
    for para in data.get("rattrapage", []):
        A(para)
    A("---")

    # ---- Avancement
    A("## 📊 Mon avancement")
    av = carte.avancement(data, jour)
    lignes = sorted(((data["cours"][k], v[1]) for k, v in av.items()), key=lambda t: -t[1])
    A(table(["Cours", "Part de la note déjà jouée"],
            [["%s %s" % (c.get("emoji", ""), c["nom"]), "%d %%" % pct] for c, pct in lignes]))
    moyenne = sum(p for _, p in lignes) / len(lignes) if lignes else 0
    A("> **%d %%** de la session est joué en moyenne, tous cours confondus." % round(moyenne))
    A("---")
    A("*Mis à jour automatiquement le %s · source : **`donnees-session.json`** · "
      "généré par **`notion.py`***" % long_date(jour))
    return "\n".join(L)


def main():
    data = carte.charger()
    args = sys.argv[1:]
    jour = d(args[0]) if args else dt.date.today()
    sys.stdout.write(page(data, jour) + "\n")


if __name__ == "__main__":
    main()

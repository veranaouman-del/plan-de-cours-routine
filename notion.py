# -*- coding: utf-8 -*-
"""Tableau de bord Notion — Automne 2026.

Génère la page complète « Ma session — Automne 2026 » en Markdown Notion,
à partir de donnees-session.json. Le moteur (échéances, étapes de préparation,
avancement) est celui de carte.py : une seule logique, deux sorties.

    python3 notion.py                 -> aujourd'hui, sur la sortie standard
    python3 notion.py 2026-11-03      -> une date précise

Le seul morceau qui ne se calcule pas est le plan de la journée : il relève du
jugement, pas de la donnée. S'il existe un fichier plan-du-jour.md, son contenu
est inséré tel quel sous la priorité du jour ; sinon la section saute.
"""
import datetime as dt
import io
import os
import sys

import carte
from carte import JOURS, MOIS, ABREV, d

BASE = os.path.dirname(os.path.abspath(__file__))
PLAN_DU_JOUR = os.path.join(BASE, "plan-du-jour.md")


# --------------------------------------------------------------------------
# Dates
# --------------------------------------------------------------------------
def longue(j):
    return "%s %d %s" % (JOURS[j.weekday()], j.day, MOIS[j.month - 1])


def courte(j):
    jour = "1er" if j.day == 1 else str(j.day)
    return "%s. %s %s" % (JOURS[j.weekday()][:3], jour, ABREV[j.month - 1])


def jx(reste):
    return carte.jx(reste)


# --------------------------------------------------------------------------
# Briques de mise en page
# --------------------------------------------------------------------------
def tableau(entetes, lignes):
    out = ['<table fit-page-width="true" header-row="true">']
    for rang in [entetes] + lignes:
        out.append("<tr>")
        for cellule in rang:
            out.append("<td>" + ("\n%s<br />\n" % cellule if cellule else "") + "</td>")
        out.append("</tr>")
    out.append("</table>")
    return "\n".join(out)


def callout(icone, couleur, corps):
    return '<callout icon="%s" color="%s">\n%s\n</callout>' % (icone, couleur, corps)


def co(data, cle):
    """Le cours, préfixé de son emoji."""
    c = data["cours"][cle]
    return "%s %s" % (c.get("emoji", ""), c["nom"])


def pct(e):
    if not e["poids"]:
        return "formatif"
    poids = "<b>%d %%</b>" % e["poids"] if e["poids"] >= 20 else "%d %%" % e["poids"]
    return poids + (" <i>(estimé)</i>" if e.get("poids_approx") else "")


# --------------------------------------------------------------------------
# Les semaines rouges : toute semaine où il se joue 30 % ou plus
# --------------------------------------------------------------------------
def semaines_rouges(data, jour, seuil=30):
    semaines = sorted(((int(n), d(debut)) for n, debut in data["session"]["semaines"].items()),
                      key=lambda p: p[1])
    out = []
    for i, (num, debut) in enumerate(semaines):
        fin = (semaines[i + 1][1] - dt.timedelta(days=1)) if i + 1 < len(semaines) \
            else debut + dt.timedelta(days=13)
        etudes = d(data["session"]["semaine_etudes"][0])
        if debut < etudes <= fin:
            fin = etudes - dt.timedelta(days=1)
        dedans = [e for e in data["evaluations"] if debut <= d(e["date"]) <= fin and e["poids"]]
        total = sum(e["poids"] for e in dedans)
        if total >= seuil:
            out.append((num, debut, fin, sorted(dedans, key=lambda e: -e["poids"]), total))
    return out


def points_restants(data, jour):
    return sum(e["poids"] for e in data["evaluations"]
               if not e.get("fait") and d(e["date"]) >= jour)


# --------------------------------------------------------------------------
# La page
# --------------------------------------------------------------------------
def page(data, jour):
    sem = carte.semaine_de(data, jour)
    actifs = carte.chantiers(data, jour)
    a_venir = carte.chantiers_tous(data, jour)
    flous = carte.incertain(data)
    L = []

    # -- en-tête ----------------------------------------------------------
    s = data["session"]
    L.append("> %s · 24 août → 11 décembre<br /><b>%s</b>" % (
        data["programme"],
        "Semaine d'études et d'encadrement" if carte.en_semaine_etudes(data, jour)
        else ("Semaine %d sur 15" % sem if sem else "Hors session")))
    L.append("---")

    # -- aujourd'hui ------------------------------------------------------
    L.append("## 📍 Aujourd'hui — %s" % longue(jour))
    lignes = []
    for c in carte.cours_du_jour(data, jour):
        lignes.append("- %s <b>%s – %s</b> · %s · %s" % (
            data["cours"][c["cours"]].get("emoji", ""),
            c["debut"].replace(":", " h "), c["fin"].replace(":", " h "),
            data["cours"][c["cours"]]["nom"], c["local"]))
    if not lignes:
        lignes.append("- 🏠 Aucun cours aujourd'hui")
    for b in carte.blocs_du_jour(data, jour):
        lignes.append("- 🎯 <b>%s – %s</b> · %s" % (
            b["debut"].replace(":", " h "), b["fin"].replace(":", " h "), b["titre"]))
    if not carte.blocs_du_jour(data, jour):
        lignes.append("- 🛌 Aucun bloc de travail — repos assumé, c'est prévu")
    L.append("\n".join(lignes))

    L.append(callout("🎯", "blue_bg",
                     "<b>%d %% de points restent à jouer d'ici la fin de la session.</b> "
                     "Tout se décide entre aujourd'hui et le %s." % (
                         points_restants(data, jour),
                         courte(max(d(e["date"]) for e in data["evaluations"])).rstrip("."))))

    if actifs:
        p = actifs[0]
        L.append("> 🔥 <b>Priorité du jour :</b> %s — %s (%s), %s. Étape : <b>%s</b>." % (
            co(data, p["cours"]), p["titre"], pct(p).replace("<b>", "").replace("</b>", ""),
            jx(p["reste"]), carte.etape(p).lower()))
    suite = [e for e in a_venir
             if not (actifs and e["titre"] == actifs[0]["titre"] and e["cours"] == actifs[0]["cours"])]
    if suite:
        n = suite[0]
        L.append("> ⏭️ <b>Prochaine échéance :</b> %s — %s (%s), le %s, <b>%s</b>." % (
            co(data, n["cours"]), n["titre"],
            pct(n).replace("<b>", "").replace("</b>", ""), courte(d(n["date"])), jx(n["reste"])))

    # -- le plan de la journée, écrit à la main ---------------------------
    if os.path.exists(PLAN_DU_JOUR):
        plan = io.open(PLAN_DU_JOUR, encoding="utf-8").read().strip()
        if plan:
            L.append(plan)

    # -- ce qui n'est pas confirmé ---------------------------------------
    if flous:
        L.append("---")
        L.append("## 🔴 À confirmer — points au statut incertain")
        L.append("> Ces évaluations sont passées, mais rien ne confirme qu'elles ont bien été "
                 "déposées, ou même tenues. Tant qu'elles sont là, mon avancement est une "
                 "hypothèse, pas un fait.")
        L.append(tableau(
            ["Évaluation", "Cours", "Poids", "Était prévu le"],
            [[e["titre"], co(data, e["cours"]), pct(e), courte(d(e["date"]))] for e in flous]))
        L.append("- [ ] Vérifier sur LÉA ou par MIO celles qui sont réglées → l'avancement "
                 "redevient exact\n- [ ] Écrire au prof <b>le jour même</b> pour chaque ligne qui "
                 "reste — <b>%d %%</b> de points au statut incertain\n- [ ] Une fois vérifié : "
                 "retirer <code>a_verifier_lea</code> dans <code>donnees-session.json</code>"
                 % sum(e["poids"] for e in flous))

    # -- à faire aujourd'hui ----------------------------------------------
    puces = {"RETARD": "🔴", "REMISE": "🔴", "ADMIN": "🟠", "FINIR": "🟠",
             "TEST BLANC": "🟠", "LECTURE": "📖"}
    L.append("---")
    L.append("## ✅ À faire aujourd'hui")
    L.append("\n".join("- [ ] %s <b>%s</b> — %s" % (puces.get(tag, "🔵"), tag, t)
                        for tag, t in carte.taches_du_jour(data, jour, actifs)))

    # -- les sept prochains jours -----------------------------------------
    L.append("---")
    L.append("## 🗓️ Les 7 prochains jours")
    lignes = []
    for i in range(7):
        j = jour + dt.timedelta(days=i)
        cellule = []
        for c in carte.cours_du_jour(data, j):
            cellule.append("%s %s – %s · %s" % (
                data["cours"][c["cours"]].get("emoji", ""),
                c["debut"].replace(":", " h "), c["fin"].replace(":", " h "), c["local"]))
        for b in carte.blocs_du_jour(data, j):
            focus = ""
            pertinents = [e for e in carte.chantiers(data, j) if e["cours"] in b["focus"]]
            if pertinents:
                e = pertinents[0]
                focus = " — %s : %s <i>(%s)</i>" % (
                    data["cours"][e["cours"]].get("emoji", ""), e["titre"],
                    carte.etape(e).lower())
            cellule.append("<b>%s – %s</b> %s%s" % (
                b["debut"].replace(":", " h "), b["fin"].replace(":", " h "), b["titre"], focus))
        for e in data["evaluations"]:
            if d(e["date"]) == j and not e.get("fait"):
                cellule.append("⚠️ <b>%s</b> — %s <i>(%s)</i>" % (
                    e["titre"], co(data, e["cours"]),
                    "formatif" if not e["poids"] else "%d %%" % e["poids"]))
        for l in data["lectures"]:
            if d(l["pour"]) == j:
                cellule.append("📖 %s" % l["quoi"])
        etiquette = "<b>%s</b>" % courte(j) + (" ← <i>aujourd'hui</i>" if i == 0 else "")
        lignes.append([etiquette, "<br />".join(cellule) or "<i>rien de prévu</i>"])
    L.append(tableau(["Jour", "Ce que je fais"], lignes))

    # -- à régler ----------------------------------------------------------
    L.append("---")
    L.append("## 📌 À régler")
    regler = []
    for t in data["taches_admin"]:
        note = " · %s" % t["note"] if t.get("note") else ""
        if t["pour"] == "recurrent":
            regler.append("- [ ] 🔁 %s%s" % (t["quoi"], note))
            continue
        reste = (d(t["pour"]) - jour).days
        if reste < 0:
            regler.append("- [ ] 🔴 <b>%s</b> — <i>%d jour%s de retard</i>%s" % (
                t["quoi"], -reste, "s" if reste < -1 else "", note))
        else:
            regler.append("- [ ] 🔵 %s — <i>pour le %s</i>%s" % (t["quoi"], courte(d(t["pour"])), note))
    L.append("\n".join(regler))

    # -- toutes les échéances ---------------------------------------------
    L.append("---")
    L.append("## 📅 Toutes mes échéances à venir")
    L.append("> 💡 Sélectionne ce tableau → <b>Transformer en base de données</b> pour filtrer "
             "par cours et cocher au fur et à mesure.")
    lignes = []
    for e in a_venir:
        pastille = "🔴" if e["reste"] <= 4 else ("🟠" if e["reste"] <= 12 else "🔵")
        titre = e["titre"] + (" ⚠️" if e.get("a_confirmer") else "")
        lignes.append([pastille, courte(d(e["date"])), co(data, e["cours"]), titre,
                       pct(e), jx(e["reste"])])
    L.append(tableau(["", "Date", "Cours", "Évaluation", "Poids", "Compte à rebours"], lignes))
    L.append("> ⚠️ = date ou pondération encore à confirmer auprès du prof. Être prêt une "
             "semaine trop tôt ne coûte rien ; l'inverse, oui.")

    # -- lectures ----------------------------------------------------------
    futures = sorted([l for l in data["lectures"] if d(l["pour"]) >= jour],
                     key=lambda l: d(l["pour"]))
    if futures:
        L.append("---")
        L.append("## 📖 Mes lectures")
        L.append(tableau(["Pour le", "Cours", "À lire"],
                         [[courte(d(l["pour"])), co(data, l["cours"]), l["quoi"]]
                          for l in futures]))

    # -- semaines rouges ---------------------------------------------------
    L.append("---")
    L.append("## 🔴 Mes semaines rouges")
    L.append("> Toute semaine où il se joue <b>30 % ou plus</b> de points, tous cours confondus. "
             "C'est là que se gagne ou se perd la session.")
    lignes = []
    for num, debut, fin, evs, total in semaines_rouges(data, jour):
        quoi = " · ".join("%s %s %s" % (data["cours"][e["cours"]].get("emoji", ""), e["titre"],
                                        pct(e).replace("<b>", "").replace("</b>", ""))
                          for e in evs)
        statut = "✅ passée" if fin < jour else ("🔥 en cours" if debut <= jour <= fin else "⏳ à venir")
        lignes.append([("<b>%d</b>" % num), "%s – %s" % (courte(debut), courte(fin)),
                       quoi, "<b>%d %%</b>" % total, statut])
    L.append(tableau(["Semaine", "Dates", "Ce qui tombe", "Poids total", "Statut"], lignes))

    # -- semaine type ------------------------------------------------------
    L.append("---")
    L.append("## 🗓️ Ma semaine type")
    lignes = []
    for b in sorted(data["blocs_travail"], key=lambda b: (b["jour"], b["debut"])):
        h1 = dt.datetime.strptime(b["debut"], "%H:%M")
        h2 = dt.datetime.strptime(b["fin"], "%H:%M")
        minutes = int((h2 - h1).total_seconds() // 60)
        duree = "%d h%s" % (minutes // 60, " %02d" % (minutes % 60) if minutes % 60 else "")
        emojis = "".join(data["cours"][f].get("emoji", "") if f in data["cours"] else "🔁"
                         for f in b["focus"])
        gros = b["titre"].startswith("GROS") or "RATTRAPAGE" in b["titre"]
        ligne = ["%s %s – %s" % (JOURS[b["jour"] - 1].capitalize(),
                                 b["debut"].replace(":", " h "), b["fin"].replace(":", " h ")),
                 duree, ("%s %s" % (emojis, b["titre"])).strip()]
        L_ = ["<b>%s</b>" % x for x in ligne] if gros else ligne
        lignes.append(L_)
    L.append(tableau(["Quand", "Durée", "Ce que je fais"], lignes))
    L.append("> ⚠️ Vendredi soir, samedi après-midi et dimanche matin restent <b>vides</b>. "
             "Ce n'est pas du temps perdu : c'est ce qui rend le reste tenable, "
             "semaine après semaine.")

    # -- méthodes ----------------------------------------------------------
    L.append("---")
    L.append("## 🧠 Mes méthodes, cours par cours")
    dur = max(c["difficulte"] for c in data["cours"].values())
    for cle, c in sorted(data["cours"].items(), key=lambda kv: -kv[1]["difficulte"]):
        marque = " — <i>ma matière la plus difficile</i>" if c["difficulte"] == dur else ""
        L.append("### %s %s%s" % (c.get("emoji", ""), c["nom"], marque))
        L.append(c.get("methode", ""))

    # -- avancement --------------------------------------------------------
    L.append("---")
    L.append("## 📊 Mon avancement")
    av = sorted(carte.avancement(data, jour).items(), key=lambda kv: -kv[1][1])
    lignes = []
    for cle, (nom, p, flou) in av:
        barre = "▰" * round(p / 10) + "▱" * (10 - round(p / 10))
        valeur = "%d %%" % p + (" <i>(dont %d %% à confirmer)</i>" % flou if flou else "")
        lignes.append(["%s %s" % (data["cours"][cle].get("emoji", ""), nom), valeur,
                       "<code>%s</code>" % barre])
    L.append(tableau(["Cours", "Part de la note déjà jouée", ""], lignes))
    moyenne = sum(p for _, (_, p, _) in av) / len(av)
    note = "> <b>%d %%</b> de la session est joué en moyenne, tous cours confondus." % moyenne
    if flous:
        note += (" Mais <b>%d %%</b> de points restent au statut incertain tant que les "
                 "évaluations ci-dessus ne sont pas confirmées." % sum(e["poids"] for e in flous))
    L.append(note)

    L.append("---")
    L.append("<i>Mis à jour le %s · source : </i><i><code>donnees-session.json</code></i>"
             "<i> · généré par </i><i><code>notion.py</code></i>" % longue(jour))
    return "\n\n".join(bloc.strip("\n") for bloc in L if bloc.strip())


def main():
    args = sys.argv[1:]
    jour = d(args[0]) if args else dt.date.today()
    data = carte.charger()
    sys.stdout.write(page(data, jour) + "\n")


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""Tableau de bord Notion — Automne 2026.

Génère le Markdown enrichi de la page Notion « Ma session — Automne 2026 »
à partir de donnees-session.json. Rien n'est codé en dur ici.

    python3 notion.py                 -> la page pour aujourd'hui, sur stdout
    python3 notion.py 2026-10-07      -> pour une date précise
    python3 notion.py 2026-10-07 x.md -> écrit dans un fichier

Le texte produit se colle tel quel dans la page Notion
(ou se passe à notion-update-page, commande replace_content).
"""
import os
import sys
import datetime as dt

import carte  # moteur commun : semaines, chantiers, étapes, avancement

d = carte.d
JOURS = carte.JOURS
MOIS = carte.MOIS

ABREV_J = ["lun.", "mar.", "mer.", "jeu.", "ven.", "sam.", "dim."]


def jour_court(j):
    """« mar. 27 oct. » — et « 1er » pour le premier du mois, comme en français."""
    num = "1er" if j.day == 1 else str(j.day)
    return "%s %s %s" % (ABREV_J[j.weekday()], num, carte.ABREV[j.month - 1])


def etiquette(data, cle):
    c = data["cours"][cle]
    return "%s %s" % (c["emoji"], c["nom"])


def poids_txt(e):
    if not e["poids"]:
        return "formatif"
    # au-dessus de 15 %, on met en gras : c'est ce qui décide la note du cours
    return ("**%d %%**" if e["poids"] >= 15 else "%d %%") % e["poids"]


def pastille(reste):
    return "🔴" if reste <= 4 else ("🟠" if reste <= 12 else "🔵")


# --------------------------------------------------------------------------
# Les semaines rouges : calculées, pas recopiées à la main
# --------------------------------------------------------------------------
def semaines_rouges(data, seuil=30):
    paires = sorted(((int(n), d(x)) for n, x in data["session"]["semaines"].items()),
                    key=lambda p: p[1])
    out = []
    for num, debut in paires:
        fin = debut + dt.timedelta(days=6)
        dedans = [e for e in data["evaluations"] if debut <= d(e["date"]) <= fin]
        total = sum(e["poids"] for e in dedans)
        if total >= seuil:
            out.append((num, debut, fin, sorted(dedans, key=lambda e: -e["poids"]), total))
    return out


def prochains_jours(data, jour, n=7):
    """Ce que je fais chaque jour, en tenant compte des blocs et de ce qui presse."""
    lignes = []
    for i in range(n):
        j = jour + dt.timedelta(days=i)
        actifs = carte.chantiers(data, j)
        cj = carte.cours_du_jour(data, j)
        bj = carte.blocs_du_jour(data, j)

        agenda = ["%s %s" % (data["cours"][c["cours"]]["emoji"],
                             data["cours"][c["cours"]].get("court", c["cours"]))
                  for c in cj]
        for b in bj:
            agenda.append("%s – %s" % (b["debut"].replace(":", " h "), b["fin"].replace(":", " h ")))
        if carte.en_semaine_etudes(data, j):
            agenda.insert(0, "*semaine d'études*")

        # ce qui tombe aujourd'hui passe devant tout le reste
        du_jour = [e for e in actifs if e["reste"] == 0]
        if du_jour:
            quoi = " · ".join("🔥 **%s %s**" % (data["cours"][e["cours"]]["emoji"], e["titre"])
                              for e in du_jour)
        elif actifs:
            focus = set()
            for b in bj:
                focus.update(b["focus"])
            cible = next((e for e in actifs if e["cours"] in focus), actifs[0])
            quoi = "%s — %s *(%s)*" % (etiquette(data, cible["cours"]), cible["titre"],
                                       carte.etape(cible).lower())
        else:
            quoi = "—"

        libelle = "**%s**" % jour_court(j)
        if i == 0:
            libelle += " ← *aujourd'hui*"
        lignes.append((libelle, "<br>".join(agenda) or "—", quoi))
    return lignes


def tableau(entetes, lignes):
    out = ['<table header-row="true">', "<tr>"]
    out += ["<td>%s</td>" % h for h in entetes]
    out.append("</tr>")
    for ligne in lignes:
        out.append("<tr>")
        out += ["<td>%s</td>" % c for c in ligne]
        out.append("</tr>")
    out.append("</table>")
    return "\n".join(out)


# --------------------------------------------------------------------------
def page(data, jour):
    sem = carte.semaine_de(data, jour)
    actifs = carte.chantiers(data, jour)
    tous = carte.chantiers_tous(data, jour)
    L = []

    L.append("# 🎓 Ma session — Automne 2026")
    L.append("> Cégep de Granby · Techniques de l'informatique (420.B0) · 24 août → 11 déc")
    a, b = data["session"]["semaine_etudes"]
    L.append("> **Semaine %s sur 15** · Semaine d'études : %s au %s"
             % (sem or "—", jour_court(d(a)), jour_court(d(b))))
    L.append("---")

    # ---- aujourd'hui
    L.append("## 📍 Aujourd'hui — %s %d %s" % (JOURS[jour.weekday()], jour.day, MOIS[jour.month - 1]))
    cj = carte.cours_du_jour(data, jour)
    for c in cj:
        L.append("- %s · **%s – %s** · local %s"
                 % (etiquette(data, c["cours"]), c["debut"].replace(":", " h "),
                    c["fin"].replace(":", " h "), c["local"]))
    bj = carte.blocs_du_jour(data, jour)
    for bl in bj:
        L.append("- 🎯 **%s** · %s – %s" % (bl["titre"], bl["debut"].replace(":", " h "),
                                            bl["fin"].replace(":", " h ")))
    if not cj and not bj:
        L.append("- Journée libre — repos assumé, c'est prévu.")

    if actifs:
        p = actifs[0]
        L.append("")
        L.append("> 🔥 **Priorité du jour :** %s — %s (%d %%), **%s**."
                 % (etiquette(data, p["cours"]), p["titre"], p["poids"],
                    carte.jx(p["reste"])))
        # le bloc prévu ne colle pas toujours à ce qui presse : on le dit
        focus = set()
        for bl in bj:
            focus.update(bl["focus"])
        if focus and "rattrapage" not in focus and p["cours"] not in focus:
            L.append("> ⚠️ **Le bloc du jour porte sur autre chose, mais %s (%d %%) tombe %s :"
                     " bascule le bloc sur %s.**"
                     % (p["titre"], p["poids"], carte.jx(p["reste"]).lower(),
                        data["cours"][p["cours"]].get("court", "")))
    L.append("---")

    # ---- à faire
    L.append("## ✅ À faire aujourd'hui")
    couleur = {"RETARD": "🔴", "REMISE": "🔴", "FINIR": "🟠", "TEST BLANC": "🟠", "ADMIN": "🟠",
               "RELIRE": "🟠", "LECTURE": "📖"}
    for tag, t in carte.taches_du_jour(data, jour, actifs):
        L.append("- [ ] %s **%s** — %s" % (couleur.get(tag, "🔵"), tag, t))
    L.append("---")

    # ---- 7 jours
    L.append("## 🗓️ Les 7 prochains jours")
    L.append(tableau(["Jour", "Cours et blocs", "Ce que je fais"], prochains_jours(data, jour)))
    L.append("---")

    # ---- remises passées non cochées
    douteuses = [e for e in data["evaluations"]
                 if e.get("a_confirmer_remise") and not e.get("fait") and d(e["date"]) < jour]
    if douteuses:
        total = sum(e["poids"] for e in douteuses)
        L.append("## 🔴 À confirmer — remises passées jamais cochées")
        L.append("> Ces remises sont passées et toujours marquées « non faites ». Tant qu'elles y sont,"
                 " mon avancement est une hypothèse, pas un fait.")
        L.append(tableau(["Évaluation", "Cours", "Poids", "Était dû le", "Retard"],
                         [(e["titre"], etiquette(data, e["cours"]), poids_txt(e),
                           jour_court(d(e["date"])), "%d jours" % (jour - d(e["date"])).days)
                          for e in sorted(douteuses, key=lambda e: e["date"])]))
        L.append("- [ ] Cocher celles qui sont remises → l'avancement redevient exact")
        L.append("- [ ] Écrire au prof **le jour même** pour celles qui ne le sont pas — **%d %%**"
                 " de points au statut incertain" % total)
        L.append("---")

    # ---- admin
    L.append("## 📌 À régler tout de suite")
    for t in data["taches_admin"]:
        if t["pour"] == "recurrent":
            L.append("- [ ] 🔁 %s" % t["quoi"])
            continue
        reste = (d(t["pour"]) - jour).days
        if reste < 0:
            L.append("- [ ] 🔴 **%s** — *%d jours de retard*" % (t["quoi"], -reste))
        elif reste <= 3:
            L.append("- [ ] 🟠 **%s** — *%s*" % (t["quoi"], carte.jx(reste).lower()))
        else:
            L.append("- [ ] 🔵 %s — *pour le %s*" % (t["quoi"], jour_court(d(t["pour"]))))
    L.append("---")

    # ---- toutes les échéances
    L.append("## 📅 Toutes mes échéances à venir")
    L.append("> 💡 Sélectionne ce tableau → **Transformer en base de données** pour filtrer par cours"
             " et cocher au fur et à mesure.")
    L.append(tableau(["", "Date", "Cours", "Évaluation", "Poids", "Compte à rebours"],
                     [(pastille(e["reste"]), jour_court(d(e["date"])), etiquette(data, e["cours"]),
                       e["titre"], poids_txt(e), carte.jx(e["reste"])) for e in tous]))
    L.append("---")

    # ---- lectures
    futures = [l for l in data["lectures"] if d(l["pour"]) >= jour]
    if futures:
        L.append("## 📖 Mes lectures")
        L.append(tableau(["Pour le", "Cours", "À lire"],
                         [(jour_court(d(l["pour"])), etiquette(data, l["cours"]), l["quoi"])
                          for l in sorted(futures, key=lambda l: l["pour"])]))
        L.append("---")

    # ---- semaines rouges
    L.append("## 🔴 Mes semaines rouges")
    L.append("> Toute semaine de session où il se joue **30 % ou plus** de points, tous cours"
             " confondus. C'est là que se gagne ou se perd la session.")
    lignes = []
    for num, debut, fin, evs, total in semaines_rouges(data):
        marque = "**%d**%s" % (num, " ← *ici*" if num == sem else "")
        quoi = " · ".join("%s %s %d %%" % (data["cours"][e["cours"]]["emoji"], e["titre"], e["poids"])
                          for e in evs)
        lignes.append((marque, "%s – %s" % (jour_court(debut), jour_court(fin)), quoi, "**%d %%**" % total))
    L.append(tableau(["Semaine", "Dates", "Ce qui tombe", "Poids total"], lignes))
    L.append("---")

    # ---- semaine type
    L.append("## 🗓️ Ma semaine type")
    lignes = []
    for bl in sorted(data["blocs_travail"], key=lambda b: (b["jour"], b["debut"])):
        h1, h2 = (dt.datetime.strptime(bl[k], "%H:%M") for k in ("debut", "fin"))
        mins = int((h2 - h1).total_seconds() // 60)
        duree = "%d h %02d" % (mins // 60, mins % 60) if mins % 60 else "%d h" % (mins // 60)
        quand = "%s %s – %s" % (JOURS[bl["jour"] - 1].capitalize(),
                                bl["debut"].replace(":", " h "), bl["fin"].replace(":", " h "))
        emos = "".join(data["cours"][f]["emoji"] for f in bl["focus"] if f in data["cours"]) or "🔁"
        gros = mins >= 180
        lignes.append(tuple(("**%s**" % x if gros else x)
                            for x in (quand, duree, "%s %s" % (emos, bl["titre"]))))
    L.append(tableau(["Quand", "Durée", "Ce que je fais"], lignes))
    L.append("> ⚠️ Vendredi soir, samedi après-midi et dimanche matin restent **vides**. Ce n'est pas"
             " du temps perdu : c'est ce qui rend le reste tenable semaine après semaine.")
    L.append("---")

    # ---- méthodes
    L.append("## 🧠 Mes méthodes, cours par cours")
    dur = max(c["difficulte"] for c in data["cours"].values())
    for cle in sorted(data["methodes"], key=lambda k: -data["cours"][k]["difficulte"]):
        c = data["cours"][cle]
        titre = "### %s %s" % (c["emoji"], c["nom"])
        if c["difficulte"] >= dur:
            titre += " — *ma matière la plus difficile*"
        L.append(titre)
        L.append(data["methodes"][cle])
    L.append("---")

    # ---- avancement
    L.append("## 📊 Mon avancement")
    av = sorted(carte.avancement(data, jour).items(), key=lambda kv: -kv[1][1])
    lignes = []
    for cle, (nom, pct) in av:
        plein = round(pct / 10)
        lignes.append((etiquette(data, cle), "%d %%" % pct,
                       "`%s%s`" % ("▰" * plein, "▱" * (10 - plein))))
    L.append(tableau(["Cours", "Part de la note déjà jouée", ""], lignes))
    moy = sum(p for _, (_, p) in av) / len(av)
    L.append("> **%d %%** de la session est joué en moyenne, tous cours confondus." % round(moy))
    L.append("---")
    L.append("*Mis à jour automatiquement le %s %d %s · source : **`donnees-session.json`** ·"
             " généré par **`notion.py`***"
             % (JOURS[jour.weekday()], jour.day, MOIS[jour.month - 1]))
    return "\n".join(L)


def main():
    args = sys.argv[1:]
    jour = d(args[0]) if args else dt.date.today()
    texte = page(carte.charger(), jour)
    if len(args) > 1:
        with open(args[1], "w", encoding="utf-8") as fh:
            fh.write(texte + "\n")
        print(args[1])
    else:
        print(texte)


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""Page Notion « Ma session » — Automne 2026.

Fabrique le contenu complet de la page Notion à partir de donnees-session.json.

    python3 notion.py                  -> le markdown Notion d'aujourd'hui
    python3 notion.py 2026-10-22       -> celui d'une date précise

La sortie se colle telle quelle dans `notion-update-page` (command
`replace_content`). Comme `carte.py`, ce script ne contient aucune date en dur :
il réutilise le même moteur, donc Slack, l'image et Notion disent toujours
exactement la même chose.
"""
import os
import sys
import datetime as dt

import carte
from carte import d, JOURS, MOIS, ABREV

JOURS_COURT = ["lun.", "mar.", "mer.", "jeu.", "ven.", "sam.", "dim."]

BASE = os.path.dirname(os.path.abspath(__file__))


# --------------------------------------------------------------------------
# Formats
# --------------------------------------------------------------------------
def jour_long(j):
    return "%s %s %s" % (JOURS[j.weekday()], num(j), MOIS[j.month - 1])


def jour_court(j):
    return "%s %s %s" % (JOURS_COURT[j.weekday()], num(j), ABREV[j.month - 1])


def num(j):
    return "1er" if j.day == 1 else str(j.day)


def heure(h):
    return h.replace(":", " h ")


def em(data, cle):
    return data["cours"][cle].get("emoji", "•")


def poids_txt(ev):
    if not ev["poids"]:
        return "formatif"
    txt = "%d %%" % ev["poids"]
    if ev["poids"] >= 20:
        txt = "**%s**" % txt
    if ev.get("poids_approx"):
        txt += " *(estimé)*"
    return txt


def pastille(reste):
    if reste <= 2:
        return "🔴"
    if reste <= 12:
        return "🟠"
    return "🔵"


def retard_txt(jours):
    if jours == 1:
        return "*1 jour de retard*"
    return "*%d jours de retard*" % jours


# --------------------------------------------------------------------------
# Calculs propres à la page
# --------------------------------------------------------------------------
def points_restants(data, jour):
    return sum(e["poids"] for e in data["evaluations"]
               if not e.get("fait") and d(e["date"]) >= jour)


def semaines_rouges(data, jour, seuil=30):
    """Toute semaine où il se joue `seuil` % de points ou plus, tous cours confondus.
    C'est là que se gagne ou se perd la session — donc c'est là qu'il faut arriver prêt."""
    paires = sorted(((int(n), d(x)) for n, x in data["session"]["semaines"].items()),
                    key=lambda p: p[1])
    derniere = paires[-1][0]
    fin_session = max(d(e["date"]) for e in data["evaluations"])
    out = []
    for num_sem, debut in paires:
        if num_sem == derniere:
            # la dernière semaine ramasse tout ce qui reste, examens finaux compris
            fin = fin_session + dt.timedelta(days=6 - fin_session.weekday())
        else:
            fin = debut + dt.timedelta(days=6)
        dedans = [e for e in data["evaluations"] if debut <= d(e["date"]) <= fin]
        total = sum(e["poids"] for e in dedans)
        if total < seuil:
            continue
        if fin < jour:
            statut = "✅ passée"
        elif debut <= jour <= fin:
            statut = "🔥 en cours"
        else:
            statut = "⏳ à venir"
        out.append({"num": num_sem, "debut": debut, "fin": fin, "total": total,
                    "statut": statut,
                    "quoi": sorted(dedans, key=lambda e: -e["poids"])})
    return out


def etape_lisible(e):
    return carte.etape(e).lower()


def chantier_du_bloc(data, bloc, actifs):
    for e in actifs:
        if e["cours"] in bloc["focus"]:
            return e
    return actifs[0] if actifs and "rattrapage" in bloc["focus"] else None


# --------------------------------------------------------------------------
# La page
# --------------------------------------------------------------------------
def page(data, jour):
    actifs = carte.chantiers(data, jour)
    aucun_cours = not carte.cours_du_jour(data, jour)
    L = []

    # ---- en-tête --------------------------------------------------------
    etiquette = carte.etiquette_semaine(data, jour) or "Session terminée"
    sem = carte.semaine_de(data, jour)
    suite = data["session"]["semaines"].get(str((sem or 0) + 1))
    if suite and 0 < (d(suite) - jour).days <= 2:
        etiquette = "**Semaine %d sur 15** · retour en classe %s" % (
            (sem or 0) + 1,
            "demain, %s" % jour_court(d(suite)) if (d(suite) - jour).days == 1
            else jour_court(d(suite)))
    else:
        etiquette = "**%s**" % etiquette
    L.append("> %s · %s · 24 août → 11 décembre<br>%s" % (
        data["programme"].split(" - ")[0], "Cégep de Granby", etiquette))
    L.append("---")

    # ---- aujourd'hui ----------------------------------------------------
    L.append("## 📍 Aujourd'hui — %s" % jour_long(jour))
    if aucun_cours:
        L.append("- 🎉 **Aucun cours aujourd'hui.**")
    else:
        for c in carte.cours_du_jour(data, jour):
            co = data["cours"][c["cours"]]
            L.append("- %s **%s – %s** · %s · %s" % (co.get("emoji", "•"),
                     heure(c["debut"]), heure(c["fin"]), co["nom"], c["local"]))
    for b in carte.blocs_du_jour(data, jour):
        L.append("- 🎯 **%s – %s** · %s" % (heure(b["debut"]), heure(b["fin"]), b["titre"]))
    if not carte.blocs_du_jour(data, jour):
        L.append("- 😴 Aucun bloc de travail prévu — repos assumé, c'est au programme.")

    L.append('<callout icon="🎯" color="blue_bg">')
    L.append("\t**%d %% de points restent à jouer d'ici la fin de la session.** "
             "Rien n'est joué : tout se décide entre aujourd'hui et le %s"
             % (points_restants(data, jour), jour_court(d(data["session"]["fin"]))))
    L.append("</callout>")

    if actifs:
        p = actifs[0]
        L.append("> 🔥 **Priorité du jour :** %s %s — %s (%s), %s. Étape : **%s**."
                 % (em(data, p["cours"]), data["cours"][p["cours"]]["nom"], p["titre"],
                    poids_txt(p).replace("**", ""), carte.jx(p["reste"]), etape_lisible(p)))
    suivantes = carte.chantiers_tous(data, jour)
    if suivantes:
        n = suivantes[0]
        L.append("> ⏭️ **Prochaine échéance :** %s %s — %s (%s), le %s, **%s**."
                 % (em(data, n["cours"]), data["cours"][n["cours"]]["nom"], n["titre"],
                    poids_txt(n).replace("**", ""), jour_court(d(n["date"])),
                    carte.jx(n["reste"])))

    # ---- remises au statut incertain ------------------------------------
    douteuses = carte.a_verifier_lea(data, jour)
    if douteuses:
        incertain = sum(e["poids"] for e in douteuses)
        L.append("## 🔴 À confirmer sur LÉA — remises au dépôt non confirmé")
        L.append("> Ces remises sont passées, mais rien ne confirme que le dépôt a bien été "
                 "enregistré. Tant qu'elles sont là, mon avancement est une hypothèse, pas un fait.")
        L.append('<table fit-page-width="true" header-row="true">')
        L.append(ligne(["Évaluation", "Cours", "Poids", "Était dû le"]))
        for e in sorted(douteuses, key=lambda x: d(x["date"])):
            L.append(ligne([e["titre"],
                            "%s %s" % (em(data, e["cours"]), data["cours"][e["cours"]]["nom"]),
                            poids_txt(e), jour_court(d(e["date"]))]))
        L.append("</table>")
        L.append("- [ ] Vérifier sur LÉA celles qui sont bien déposées → l'avancement redevient exact")
        L.append("- [ ] Écrire au prof **le jour même** pour celles qui ne le sont pas — "
                 "**%d %%** de points au statut incertain" % incertain)
        L.append("- [ ] Une fois vérifié : retirer `a_verifier_lea` dans `donnees-session.json`")
        L.append("---")

    # ---- à faire aujourd'hui --------------------------------------------
    L.append("## ✅ À faire aujourd'hui")
    for tag, t in carte.taches_du_jour(data, jour, actifs):
        puce = "🔴" if tag in ("RETARD", "REMISE") else ("🟠" if tag in ("FINIR", "ADMIN") else "🔵")
        vedette = "**%s**" % tag if puce == "🔴" else "**%s**" % tag
        L.append("- [ ] %s %s — %s" % (puce, vedette, t))
    L.append("---")

    # ---- les 7 prochains jours ------------------------------------------
    L.append("## 🗓️ Les 7 prochains jours")
    L.append('<table fit-page-width="true" header-row="true">')
    L.append(ligne(["Jour", "Ce que je fais"]))
    for i in range(7):
        j = jour + dt.timedelta(days=i)
        titre = "**%s**" % jour_court(j)
        if i == 0:
            titre += " ← *aujourd'hui*"
        morceaux = []
        for c in carte.cours_du_jour(data, j):
            morceaux.append("%s %s – %s · %s" % (em(data, c["cours"]),
                            heure(c["debut"]), heure(c["fin"]), c["local"]))
        actifs_j = carte.chantiers(data, j)
        for b in carte.blocs_du_jour(data, j):
            txt = "**%s – %s** %s" % (heure(b["debut"]), heure(b["fin"]), b["titre"])
            ch = chantier_du_bloc(data, b, actifs_j)
            if ch:
                txt += " — %s : %s *(%s)*" % (em(data, ch["cours"]), ch["titre"], etape_lisible(ch))
            morceaux.append(txt)
        for e in data["evaluations"]:
            if d(e["date"]) == j and not e.get("fait"):
                morceaux.append("⚠️ **%s** — %s %s *(%s)*" % (
                    e["titre"], em(data, e["cours"]), data["cours"][e["cours"]]["nom"],
                    poids_txt(e).replace("**", "")))
        L.append(ligne([titre, "<br>".join(morceaux) or "*Rien de prévu — journée libre*"]))
    L.append("</table>")
    L.append("---")

    # ---- à régler --------------------------------------------------------
    L.append("## 📌 À régler")
    for t in data["taches_admin"]:
        if t["pour"] == "recurrent":
            L.append("- [ ] 🔁 %s" % t["quoi"])
            continue
        reste = (d(t["pour"]) - jour).days
        note = " · %s" % t["note"] if t.get("note") else ""
        if reste < 0:
            L.append("- [ ] 🔴 **%s** — %s%s" % (t["quoi"], retard_txt(-reste), note))
        else:
            L.append("- [ ] 🔵 %s — *pour le %s*%s" % (t["quoi"], jour_court(d(t["pour"])), note))
    L.append("---")

    # ---- toutes les échéances -------------------------------------------
    L.append("## 📅 Toutes mes échéances à venir")
    L.append("> 💡 Sélectionne ce tableau → **Transformer en base de données** pour filtrer "
             "par cours et cocher au fur et à mesure.")
    L.append('<table fit-page-width="true" header-row="true">')
    L.append(ligne(["", "Date", "Cours", "Évaluation", "Poids", "Compte à rebours"]))
    for e in carte.chantiers_tous(data, jour):
        titre = e["titre"] + (" ⚠️" if e.get("a_confirmer") else "")
        L.append(ligne([pastille(e["reste"]), jour_court(d(e["date"])),
                        "%s %s" % (em(data, e["cours"]), data["cours"][e["cours"]]["nom"]),
                        titre, poids_txt(e), carte.jx(e["reste"])]))
    L.append("</table>")
    L.append("> ⚠️ = date ou pondération encore à confirmer auprès du prof. Être prêt une "
             "semaine trop tôt ne coûte rien ; l'inverse, oui.")
    L.append("---")

    # ---- lectures --------------------------------------------------------
    futures = [l for l in data["lectures"] if d(l["pour"]) >= jour]
    if futures:
        L.append("## 📖 Mes lectures")
        L.append('<table fit-page-width="true" header-row="true">')
        L.append(ligne(["Pour le", "Cours", "À lire"]))
        for l in sorted(futures, key=lambda x: d(x["pour"])):
            L.append(ligne([jour_court(d(l["pour"])),
                            "%s %s" % (em(data, l["cours"]), data["cours"][l["cours"]]["nom"]),
                            l["quoi"]]))
        L.append("</table>")
        L.append("---")

    # ---- semaines rouges -------------------------------------------------
    rouges = semaines_rouges(data, jour)
    if rouges:
        L.append("## 🔴 Mes semaines rouges")
        L.append("> Toute semaine où il se joue **30 % ou plus** de points, tous cours "
                 "confondus. C'est là que se gagne ou se perd la session.")
        L.append('<table fit-page-width="true" header-row="true">')
        L.append(ligne(["Semaine", "Dates", "Ce qui tombe", "Poids total", "Statut"]))
        for r in rouges:
            quoi = " · ".join("%s %s %s" % (em(data, e["cours"]), e["titre"],
                                            poids_txt(e).replace("**", ""))
                              for e in r["quoi"])
            L.append(ligne(["**%d**" % r["num"],
                            "%s – %s" % (jour_court(r["debut"]), jour_court(r["fin"])),
                            quoi, "**%d %%**" % r["total"], r["statut"]]))
        L.append("</table>")
        L.append("---")

    # ---- semaine type ----------------------------------------------------
    L.append("## 🗓️ Ma semaine type")
    L.append('<table fit-page-width="true" header-row="true">')
    L.append(ligne(["Quand", "Durée", "Ce que je fais"]))
    for b in data["blocs_travail"]:
        h1 = dt.datetime.strptime(b["debut"], "%H:%M")
        h2 = dt.datetime.strptime(b["fin"], "%H:%M")
        mn = int((h2 - h1).total_seconds() // 60)
        duree = "%d h" % (mn // 60) + (" %02d" % (mn % 60) if mn % 60 else "")
        emojis = "".join(em(data, c) for c in b["focus"] if c in data["cours"]) or "🔁"
        quand = "%s %s – %s" % (JOURS[b["jour"] - 1].capitalize(), heure(b["debut"]), heure(b["fin"]))
        gros = mn >= 180
        if gros:
            L.append(ligne(["**%s**" % quand, "**%s**" % duree, "**%s %s**" % (emojis, b["titre"])]))
        else:
            L.append(ligne([quand, duree, "%s %s" % (emojis, b["titre"])]))
    L.append("</table>")
    L.append("> ⚠️ Vendredi soir, samedi après-midi et dimanche matin restent **vides**. "
             "Ce n'est pas du temps perdu : c'est ce qui rend le reste tenable, semaine après semaine.")
    L.append("---")

    # ---- méthodes --------------------------------------------------------
    L.append("## 🧠 Mes méthodes, cours par cours")
    dur = max(c["difficulte"] for c in data["cours"].values())
    for cle, c in sorted(data["cours"].items(), key=lambda p: -p[1]["difficulte"]):
        if cle not in data.get("methodes", {}):
            continue
        marque = " — *ma matière la plus difficile*" if c["difficulte"] == dur else ""
        L.append("### %s %s%s" % (c.get("emoji", "•"), c["nom"], marque))
        L.append(data["methodes"][cle])

    # ---- avancement ------------------------------------------------------
    L.append("---")
    L.append("## 📊 Mon avancement")
    L.append('<table fit-page-width="true" header-row="true">')
    L.append(ligne(["Cours", "Part de la note déjà jouée", ""]))
    av = carte.avancement(data, jour)
    for cle, (nom, pct, inc) in sorted(av.items(), key=lambda p: -p[1][1]):
        barre = "▰" * int(round(pct / 10.0)) + "▱" * (10 - int(round(pct / 10.0)))
        valeur = "%d %%" % pct + (" *(dont %d %% à confirmer)*" % inc if inc else "")
        L.append(ligne(["%s %s" % (em(data, cle), nom), valeur, "`%s`" % barre]))
    L.append("</table>")
    moyenne = sum(p for _, p, _ in av.values()) / float(len(av))
    incertain = sum(i for _, _, i in av.values())
    phrase = ("> **%d %%** de la session est joué en moyenne, tous cours confondus."
              % round(moyenne))
    if incertain:
        phrase += (" Mais **%d %%** de points restent au statut incertain tant que les remises "
                   "ci-dessus ne sont pas confirmées sur LÉA." % incertain)
    L.append(phrase)
    L.append("---")
    L.append("*Mis à jour le %s · source : **`donnees-session.json`** · généré par **`notion.py`***"
             % jour_long(jour))
    return "\n".join(L)


def ligne(cellules):
    return "\t<tr>\n" + "\n".join("\t\t<td>%s</td>" % c for c in cellules) + "\n\t</tr>"


def main():
    args = sys.argv[1:]
    jour = d(args[0]) if args else dt.date.today()
    data = carte.charger()
    sortie = page(data, jour)
    if len(args) > 1:
        open(args[1], "w", encoding="utf-8").write(sortie)
        print(args[1])
    else:
        print(sortie)


if __name__ == "__main__":
    main()

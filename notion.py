# -*- coding: utf-8 -*-
"""Tableau de bord Notion — Automne 2026.

Régénère la page Notion « Ma session » à partir de donnees-session.json, en
Notion-flavored Markdown prêt à passer à `notion-update-page` / `replace_content`.

    python3 notion.py                  -> la page d'aujourd'hui sur stdout
    python3 notion.py 2026-11-03       -> la page telle qu'elle sera ce jour-là
    python3 notion.py > /tmp/page.md

Si un fichier `focus-du-jour.md` existe à la racine, son contenu est injecté
juste après la priorité du jour. C'est là que va le jugement du jour — les
rappels que ni l'horaire ni les dates ne peuvent déduire tout seuls.

Rien n'est codé en dur ici non plus : la source de vérité reste le JSON.
"""
import os
import sys
import datetime as dt

import carte

BASE = os.path.dirname(os.path.abspath(__file__))
FOCUS = os.path.join(BASE, "focus-du-jour.md")

d = carte.d
court = carte.court
jx = carte.jx
JOURS = carte.JOURS
MOIS = carte.MOIS


def emo(data, cle):
    return data["cours"][cle].get("emoji", "•")


def nom(data, cle, court_=False):
    c = data["cours"][cle]
    return "%s %s" % (c.get("emoji", ""), c["court"] if court_ else c["nom"])


def long_date(j):
    return "%s %s %s" % (JOURS[j.weekday()], "1er" if j.day == 1 else j.day, MOIS[j.month - 1])


def date_courte(j):
    abrev = ["lun.", "mar.", "mer.", "jeu.", "ven.", "sam.", "dim."]
    return "%s %s %s" % (abrev[j.weekday()], "1er" if j.day == 1 else j.day, carte.ABREV[j.month - 1])


def poids_txt(ev):
    if not ev["poids"]:
        return "formatif"
    s = "%d %%" % ev["poids"]
    if ev["poids"] >= 20:
        s = "<b>%s</b>" % s
    if ev.get("poids_approx"):
        s += " <i>(estimé)</i>"
    return s


def pastille(reste):
    return "🔴" if reste <= 4 else ("🟠" if reste <= 12 else "🔵")


def table(entetes, lignes):
    """Un tableau Notion stylé. Les cellules sont inline seulement."""
    out = ['<table fit-page-width="true" header-row="true">']
    for rang in [entetes] + lignes:
        out.append("<tr>")
        for cell in rang:
            out.append("<td>\n%s<br />\n</td>" % cell if cell else "<td></td>")
        out.append("</tr>")
    out.append("</table>")
    return "\n".join(out)


# --------------------------------------------------------------------------
def page(data, jour):
    L = []
    W = L.append
    sem = carte.semaine_de(data, jour)
    actifs = carte.chantiers(data, jour)
    a_venir = carte.chantiers_tous(data, jour)
    nc = carte.non_confirmees(data)

    # ---- en-tête ---------------------------------------------------------
    entete = "> %s · Cégep de Granby · 24 août → 11 décembre\\\n" % data["programme"].replace(
        "420.B0 Techniques de l'informatique - Cegep de Granby",
        "420.B0 Techniques de l'informatique")
    entete += "> <b>Semaine %s sur 15</b>" % (sem if sem else "—")
    W(entete)
    W("\n---\n")

    # ---- aujourd'hui -----------------------------------------------------
    W("## 📍 Aujourd'hui — %s\n" % long_date(jour))
    cj = carte.cours_du_jour(data, jour)
    bj = carte.blocs_du_jour(data, jour)
    if not cj and not bj:
        W("- 😮‍💨 Aucun cours, aucun bloc — journée libre, repos assumé.\n")
    for c in cj:
        W("- %s <b>%s</b> · %s · %s" % (emo(data, c["cours"]), hh(c["debut"]) + " – " + hh(c["fin"]),
                                        data["cours"][c["cours"]]["nom"], c["local"]))
    for b in bj:
        W("- 🎯 <b>%s</b> · %s" % (hh(b["debut"]) + " – " + hh(b["fin"]), b["titre"]))
    W("")

    restant = sum(e["poids"] for e in a_venir)
    if restant:
        W('<callout icon="🎯" color="blue_bg">')
        W("<b>%d %% de points restent à jouer d'ici la fin de la session.</b> "
          "Tout se décide entre aujourd'hui et le %s" % (restant, date_courte(d(a_venir[-1]["date"]))))
        W("</callout>\n")

    if actifs:
        p = actifs[0]
        W("> 🔥 <b>Priorité du jour :</b> %s — %s (%s), %s. Étape : <b>%s</b>.\n"
          % (nom(data, p["cours"]), p["titre"], poids_txt(p).replace("<b>", "").replace("</b>", ""),
             jx(p["reste"]), carte.etape(p).lower()))
    suivante = a_venir[0] if a_venir else None
    if suivante and not (actifs and suivante["titre"] == actifs[0]["titre"]):
        W("> ⏭️ <b>Prochaine échéance :</b> %s — %s (%s), le %s, <b>%s</b>.\n"
          % (nom(data, suivante["cours"]), suivante["titre"],
             poids_txt(suivante).replace("<b>", "").replace("</b>", ""),
             date_courte(d(suivante["date"])), jx(suivante["reste"])))

    if os.path.exists(FOCUS):
        texte = open(FOCUS, encoding="utf-8").read().strip()
        if texte:
            W(texte + "\n")

    W("---\n")

    # ---- points au statut incertain --------------------------------------
    if nc:
        W("## 🔴 À confirmer — points au statut incertain\n")
        W("> Ces évaluations sont passées, mais rien ne confirme qu'elles ont bien été "
          "déposées, ou même tenues. Tant qu'elles sont là, mon avancement est une "
          "hypothèse, pas un fait.\n")
        W(table(["Évaluation", "Cours", "Poids", "Était prévu le"],
                [[e["titre"], nom(data, e["cours"]), poids_txt(e), date_courte(d(e["date"]))]
                 for e in nc]))
        W("")
        W("- [ ] Vérifier sur LÉA ou par MIO celles qui sont réglées → l'avancement redevient exact")
        W("- [ ] Écrire au prof <b>le jour même</b> pour chaque ligne qui reste — <b>%d %%</b> "
          "de points au statut incertain" % sum(e["poids"] for e in nc))
        W("- [ ] Une fois vérifié : retirer <code>a_verifier_lea</code> dans <code>donnees-session.json</code>\n")
        W("---\n")

    # ---- à faire aujourd'hui ---------------------------------------------
    W("## ✅ À faire aujourd'hui\n")
    puces = {"RETARD": "🔴", "REMISE": "🔴", "ADMIN": "📌", "LECTURE": "📖",
             "FINIR": "🟠", "TEST BLANC": "🟠", "AVANCER": "🔵", "FICHES": "🔵",
             "NOTES": "🔵", "RELIRE": "🔵"}
    for tag, t in carte.taches_du_jour(data, jour, actifs):
        W("- [ ] %s <b>%s</b> — %s" % (puces.get(tag, "🔵"), tag, t))
    W("\n---\n")

    # ---- les 7 prochains jours -------------------------------------------
    W("## 🗓️ Les 7 prochains jours\n")
    lignes = []
    for i in range(7):
        j = jour + dt.timedelta(days=i)
        cell = []
        for c in carte.cours_du_jour(data, j):
            cell.append("%s %s · %s" % (emo(data, c["cours"]), hh(c["debut"]) + " – " + hh(c["fin"]), c["local"]))
        for b in carte.blocs_du_jour(data, j):
            ouverts = [e for e in carte.chantiers(data, j)
                       if e["cours"] in b["focus"] and not deja_remis(data, e, j, b)]
            detail = ""
            if ouverts:
                detail = " — %s : %s <i>(%s)</i>" % (emo(data, ouverts[0]["cours"]), ouverts[0]["titre"],
                                                     carte.etape(ouverts[0]).lower())
            elif "rattrapage" not in b["focus"]:
                detail = " — <i>aucune échéance ouverte : prise d'avance ou rattrapage</i>"
            cell.append("<b>%s</b> %s%s" % (hh(b["debut"]) + " – " + hh(b["fin"]), b["titre"], detail))
        for l in data["lectures"]:
            if d(l["pour"]) == j:
                cell.append("📖 %s" % l["quoi"])
        for e in a_venir:
            if d(e["date"]) == j:
                cell.append("⚠️ <b>%s</b> — %s <i>(%s)</i>"
                            % (e["titre"], nom(data, e["cours"]), poids_txt(e).replace("<b>", "").replace("</b>", "")))
        if not cell:
            cell.append("<i>—</i>")
        etiquette = "<b>%s</b>" % date_courte(j) + (" ← <i>aujourd'hui</i>" if i == 0 else "")
        lignes.append([etiquette, "<br />".join(cell)])
    W(table(["Jour", "Ce que je fais"], lignes))
    W("\n---\n")

    # ---- à régler --------------------------------------------------------
    W("## 📌 À régler\n")
    admin = []
    for t in data["taches_admin"]:
        if t["pour"] == "recurrent":
            admin.append((9999, "- [ ] 🔁 %s" % t["quoi"]))
            continue
        reste = (d(t["pour"]) - jour).days
        note = " · %s" % t["note"] if t.get("note") else ""
        if reste < 0:
            admin.append((reste, "- [ ] 🔴 <b>%s</b> — <i>%d %s de retard</i>%s"
                          % (t["quoi"], -reste, "jour" if reste == -1 else "jours", note)))
        else:
            admin.append((reste, "- [ ] 🔵 %s — <i>pour le %s</i>%s"
                          % (t["quoi"], date_courte(d(t["pour"])), note)))
    for _, ligne in sorted(admin):
        W(ligne)
    W("\n---\n")

    # ---- toutes les échéances --------------------------------------------
    W("## 📅 Toutes mes échéances à venir\n")
    W("> 💡 Sélectionne ce tableau → <b>Transformer en base de données</b> pour filtrer "
      "par cours et cocher au fur et à mesure.\n")
    W(table(["", "Date", "Cours", "Évaluation", "Poids", "Compte à rebours"],
            [[pastille(e["reste"]), date_courte(d(e["date"])), nom(data, e["cours"]),
              e["titre"] + (" ⚠️" if e.get("a_confirmer") else ""), poids_txt(e), jx(e["reste"])]
             for e in a_venir]))
    W("")
    W("> ⚠️ = date ou pondération encore à confirmer auprès du prof. Être prêt une semaine "
      "trop tôt ne coûte rien ; l'inverse, oui.\n")
    W("---\n")

    # ---- lectures --------------------------------------------------------
    futures = sorted((l for l in data["lectures"] if d(l["pour"]) >= jour),
                     key=lambda l: l["pour"])   # par date, pas par ordre de saisie
    if futures:
        W("## 📖 Mes lectures\n")
        W(table(["Pour le", "Cours", "À lire"],
                [[date_courte(d(l["pour"])), nom(data, l["cours"]), l["quoi"]] for l in futures]))
        W("\n---\n")

    # ---- semaines rouges -------------------------------------------------
    W("## 🔴 Mes semaines rouges\n")
    W("> Toute semaine où il se joue <b>30 % ou plus</b> de points, tous cours confondus. "
      "C'est là que se gagne ou se perd la session.\n")
    W(table(["Semaine", "Dates", "Ce qui tombe", "Poids total", "Statut"], semaines_rouges(data, jour)))
    W("\n---\n")

    # ---- semaine type ----------------------------------------------------
    W("## 🗓️ Ma semaine type\n")
    lignes = []
    for b in sorted(data["blocs_travail"], key=lambda b: (b["jour"], b["debut"])):
        duree = minutes(b["fin"]) - minutes(b["debut"])
        libelle = "%s %s – %s" % (JOURS[b["jour"] - 1].capitalize(), hh(b["debut"]), hh(b["fin"]))
        icones = "".join(emo(data, f) for f in b["focus"] if f in data["cours"]) or "🔁"
        gros = duree >= 180
        ligne = [libelle, duree_txt(duree), "%s %s" % (icones, b["titre"])]
        lignes.append(["<b>%s</b>" % c if gros else c for c in ligne])
    W(table(["Quand", "Durée", "Ce que je fais"], lignes))
    W("")
    W("> ⚠️ Vendredi soir, samedi après-midi et dimanche matin restent <b>vides</b>. Ce n'est "
      "pas du temps perdu : c'est ce qui rend le reste tenable, semaine après semaine.\n")
    W("---\n")

    # ---- méthodes --------------------------------------------------------
    W("## 🧠 Mes méthodes, cours par cours\n")
    dur = max(c["difficulte"] for c in data["cours"].values())
    for cle, c in sorted(data["cours"].items(), key=lambda kv: -kv[1]["difficulte"]):
        if not c.get("methode"):
            continue
        titre = "### %s %s" % (c.get("emoji", ""), c["nom"])
        if c["difficulte"] == dur:
            titre += " — <i>ma matière la plus difficile</i>"
        W(titre + "\n")
        W(c["methode"] + "\n")
    W("---\n")

    # ---- avancement ------------------------------------------------------
    W("## 📊 Mon avancement\n")
    incertain = {}
    for e in nc:
        incertain[e["cours"]] = incertain.get(e["cours"], 0) + e["poids"]
    lignes = []
    av = carte.avancement(data, jour)
    for cle, (_, pct) in sorted(av.items(), key=lambda kv: -kv[1][1]):
        suffixe = " <i>(dont %d %% à confirmer)</i>" % incertain[cle] if cle in incertain else ""
        plein = int(round(pct / 10.0))
        lignes.append([nom(data, cle), "%d %%%s" % (pct, suffixe),
                       "<code>%s%s</code>" % ("▰" * plein, "▱" * (10 - plein))])
    W(table(["Cours", "Part de la note déjà jouée", ""], lignes))
    W("")
    moyen = int(round(sum(p for _, p in av.values()) / float(len(av))))
    phrase = "> <b>%d %%</b> de la session est joué en moyenne, tous cours confondus." % moyen
    if nc:
        phrase += (" Mais <b>%d %%</b> de points restent au statut incertain tant que les "
                   "évaluations ci-dessus ne sont pas confirmées." % sum(e["poids"] for e in nc))
    W(phrase + "\n")
    W("<i>Mis à jour le %s · source : </i><i><code>donnees-session.json</code></i>"
      "<i> · généré par </i><i><code>notion.py</code></i>" % long_date(jour))

    return "\n".join(L)


# --------------------------------------------------------------------------
def semaines_rouges(data, jour, seuil=30):
    """Une semaine est rouge quand il s'y joue 30 % ou plus, tous cours confondus."""
    paires = sorted(((int(n), d(deb)) for n, deb in data["session"]["semaines"].items()),
                    key=lambda p: p[1])
    lignes = []
    for i, (num, debut) in enumerate(paires):
        fin = (paires[i + 1][1] - dt.timedelta(days=1)) if i + 1 < len(paires) \
            else debut + dt.timedelta(days=13)
        dedans = [e for e in data["evaluations"] if debut <= d(e["date"]) <= fin]
        total = sum(e["poids"] for e in dedans)
        if total < seuil:
            continue
        quoi = " · ".join("%s %s %s" % (emo(data, e["cours"]), e["titre"], poids_txt(e)
                                        .replace("<b>", "").replace("</b>", ""))
                          for e in sorted(dedans, key=lambda e: -e["poids"]))
        statut = "✅ passée" if fin < jour else ("🔥 en cours" if debut <= jour <= fin else "⏳ à venir")
        lignes.append(["<b>%d</b>" % num, "%s – %s" % (date_courte(debut), date_courte(fin)),
                       quoi, "<b>%d %%</b>" % total, statut])
    return lignes


def deja_remis(data, ev, jour, bloc):
    """Une remise du jour est derrière soi si son cours a eu lieu avant le bloc.

    Sans ça, le plan de la semaine proposait de « relire » une dissertation
    remise le matin même en classe.
    """
    if d(ev["date"]) != jour:
        return False
    return any(c["cours"] == ev["cours"] and minutes(c["fin"]) <= minutes(bloc["debut"])
               for c in carte.cours_du_jour(data, jour))


def hh(t):
    return t.replace(":", " h ")


def minutes(t):
    h, m = t.split(":")
    return int(h) * 60 + int(m)


def duree_txt(mn):
    h, m = divmod(mn, 60)
    return "%d h" % h if not m else ("%d h %02d" % (h, m) if h else "%d min" % m)


def main():
    args = sys.argv[1:]
    jour = d(args[0]) if args else dt.date.today()
    print(page(carte.charger(), jour))


if __name__ == "__main__":
    main()

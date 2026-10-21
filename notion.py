# -*- coding: utf-8 -*-
"""Tableau de bord Notion — Automne 2026.

Génère le contenu complet de la page Notion « Ma session — Automne 2026 »
à partir de donnees-session.json, en Markdown Notion-flavored.

    python3 notion.py                 -> la page d'aujourd'hui, sur stdout
    python3 notion.py 2026-10-21      -> une date précise
    python3 notion.py --out page.md   -> écrit dans un fichier

Le texte produit se pousse avec l'outil Notion `update-page`, commande
`replace_content`. La page est entièrement regénérée à chaque fois : il n'y a
aucun état côté Notion, tout vient du JSON.

Page cible : 3df73824-e620-811e-9e6c-d07440cb6ec7
Rien n'est codé en dur ici — pour changer une échéance, éditer le JSON.
"""
import io
import sys
import datetime as dt

import carte
from carte import d, jx, court, JOURS, MOIS

PAGE_ID = "3df73824-e620-811e-9e6c-d07440cb6ec7"


# --------------------------------------------------------------------------
# Helpers de rendu
# --------------------------------------------------------------------------
def long_date(j):
    """« mar. 27 oct. » — compact mais sans ambiguïté."""
    jour = court(j)
    if j.day == 1:
        jour = "1er" + jour[1:]
    return "%s %s" % (JOURS[j.weekday()][:3] + ".", jour)


def jour_complet(j):
    return "%s %d %s" % (JOURS[j.weekday()], j.day, MOIS[j.month - 1])


def nom(data, cle):
    c = data["cours"][cle]
    return "%s %s" % (c.get("emoji", ""), c["nom"])


def pct(e):
    """Pondération affichée, avec la mention « estimé » quand elle l'est."""
    if not e["poids"]:
        return "formatif"
    s = "%d %%" % e["poids"]
    if e["poids"] >= 20:
        s = "<b>%s</b>" % s
    if e.get("poids_approx"):
        s += " <i>(estimé)</i>"
    return s


def table(entetes, lignes, large=True):
    out = ['<table fit-page-width="%s" header-row="true">' % ("true" if large else "false")]
    for rang in [entetes] + lignes:
        out.append("<tr>")
        for cell in rang:
            out.append("<td>" if cell == "" else "<td>\n%s\n" % cell)
            out.append("</td>" if cell == "" else "</td>")
        out.append("</tr>")
    # recoller les <td></td> vides proprement
    txt = "\n".join(out).replace("<td>\n</td>", "<td></td>")
    return txt + "\n</table>"


def pastille(reste):
    return "🔴" if reste <= 3 else ("🟠" if reste <= 10 else "🔵")


def barre(p):
    pleins = max(0, min(10, int(round(p / 10.0))))
    return "<code>%s%s</code>" % ("▰" * pleins, "▱" * (10 - pleins))


# --------------------------------------------------------------------------
# Calculs
# --------------------------------------------------------------------------
def a_venir(data, jour):
    return carte.chantiers_tous(data, jour)


def points_restants(data, jour):
    return sum(e["poids"] for e in a_venir(data, jour))


def incertain(data, cle=None):
    """Points dont la remise n'est pas confirmée sur LÉA."""
    return sum(e["poids"] for e in data["evaluations"]
               if e.get("a_verifier_lea") and (cle is None or e["cours"] == cle))


def semaines_rouges(data, jour):
    """Toute semaine où il se joue 30 % ou plus, tous cours confondus."""
    paires = sorted(((int(n), d(deb)) for n, deb in data["session"]["semaines"].items()),
                    key=lambda p: p[1])
    bornes = {}
    for i, (num, deb) in enumerate(paires):
        if i + 1 < len(paires):
            fin = min(paires[i + 1][1] - dt.timedelta(days=1), deb + dt.timedelta(days=6))
        else:
            fin = deb + dt.timedelta(days=13)   # la derniere absorbe la semaine d'examens
        bornes[num] = (deb, fin)

    groupes = {}
    for e in data["evaluations"]:
        ed = d(e["date"])
        for num, (deb, fin) in bornes.items():
            if deb <= ed <= fin:
                groupes.setdefault(num, []).append(e)
                break

    out = []
    for num in sorted(groupes):
        evs = sorted(groupes[num], key=lambda e: -e["poids"])
        total = sum(e["poids"] for e in evs)
        if total < 30:
            continue
        deb, fin = bornes[num]
        statut = "✅ passée" if fin < jour else ("🔥 EN COURS" if deb <= jour <= fin else "⏳ à venir")
        quoi = " · ".join("%s %s %s" % (data["cours"][e["cours"]].get("emoji", ""), e["titre"],
                                        "%d %%" % e["poids"] if e["poids"] else "formatif")
                          + (" <i>(estimé)</i>" if e.get("poids_approx") else "")
                          for e in evs)
        out.append((num, deb, fin, quoi, total, statut))
    return out


def sept_jours(data, jour):
    """Ce qui occupe chacun des 7 prochains jours : cours, bloc, chantier, échéance."""
    lignes = []
    for i in range(7):
        j = jour + dt.timedelta(days=i)
        morceaux = []
        for c in carte.cours_du_jour(data, j):
            co = data["cours"][c["cours"]]
            morceaux.append("%s %s – %s · %s" % (co.get("emoji", ""),
                                                 c["debut"].replace(":", " h "),
                                                 c["fin"].replace(":", " h "), c["local"]))
        actifs = carte.chantiers(data, j)
        focus_par_bloc = []
        for b in carte.blocs_du_jour(data, j):
            txt = "<b>%s – %s</b> %s" % (b["debut"].replace(":", " h "),
                                         b["fin"].replace(":", " h "), b["titre"])
            cible = next((e for e in actifs if e["cours"] in b["focus"]), None)
            if cible is None and "rattrapage" in b["focus"] and actifs:
                cible = actifs[0]
            if cible:
                co = data["cours"][cible["cours"]]
                txt += " — %s : %s <i>(%s)</i>" % (co.get("emoji", ""), cible["titre"],
                                                   carte.etape(cible).lower())
            focus_par_bloc.append(txt)
        morceaux += focus_par_bloc
        for e in data["evaluations"]:
            if not e.get("fait") and d(e["date"]) == j:
                morceaux.append("⚠️ <b>%s</b> — %s <i>(%s)</i>"
                                % (e["titre"], nom(data, e["cours"]),
                                   "%d %%" % e["poids"] if e["poids"] else "formatif"))
        if not morceaux:
            morceaux = ["<i>Journée libre — repos assumé, c'est prévu.</i>"]
        etiquette = "<b>%s</b>" % long_date(j) + (" ← <i>aujourd'hui</i>" if i == 0 else "")
        lignes.append([etiquette, "<br />".join(morceaux)])
    return lignes


# --------------------------------------------------------------------------
# La page
# --------------------------------------------------------------------------
def page(data, jour):
    L = []
    sem = carte.semaine_de(data, jour)
    actifs = carte.chantiers(data, jour)
    prochaines = a_venir(data, jour)
    s = data["session"]

    L.append("> %s · Cégep de Granby · 24 août → 11 décembre<br /><b>Semaine %s sur 15</b>"
             % (data["programme"].split(" - ")[0], sem or "—"))
    L.append("")
    L.append("---")
    L.append("")

    # ---- aujourd'hui
    L.append("## 📍 Aujourd'hui — %s" % jour_complet(jour))
    L.append("")
    for c in carte.cours_du_jour(data, jour):
        co = data["cours"][c["cours"]]
        L.append("- %s <b>%s – %s</b> · %s · %s"
                 % (co.get("emoji", ""), c["debut"].replace(":", " h "),
                    c["fin"].replace(":", " h "), co["nom"], c["local"]))
    for b in carte.blocs_du_jour(data, jour):
        L.append("- 🎯 <b>%s – %s</b> · %s"
                 % (b["debut"].replace(":", " h "), b["fin"].replace(":", " h "), b["titre"]))
    if not carte.cours_du_jour(data, jour) and not carte.blocs_du_jour(data, jour):
        L.append("- <i>Journée libre — repos assumé, c'est prévu.</i>")
    L.append("")

    reste = points_restants(data, jour)
    fin = d(prochaines[-1]["date"]) if prochaines else d(s["fin"])
    L.append('<callout icon="🎯" color="blue_bg">')
    L.append("<b>%d %% de points restent à jouer d'ici la fin de la session.</b> "
             "Tout se décide entre aujourd'hui et le %s." % (reste, long_date(fin).rstrip(".")))
    L.append("</callout>")
    L.append("")

    if actifs:
        p = actifs[0]
        L.append("> 🔥 <b>Priorité du jour :</b> %s — %s (%s), %s. Étape : <b>%s</b>."
                 % (nom(data, p["cours"]), p["titre"],
                    "%d %%" % p["poids"] if p["poids"] else "formatif",
                    jx(p["reste"]), carte.etape(p).lower()))
        L.append("")
    if prochaines:
        n = prochaines[0]
        L.append("> ⏭️ <b>Prochaine échéance :</b> %s — %s (%s), le %s, <b>%s</b>."
                 % (nom(data, n["cours"]), n["titre"],
                    "%d %%" % n["poids"] if n["poids"] else "formatif",
                    long_date(d(n["date"])), jx(n["reste"])))
        L.append("")

    # ---- remises a verifier sur LEA
    douteuses = [e for e in data["evaluations"] if e.get("a_verifier_lea")]
    if douteuses:
        L.append("## 🔴 À confirmer sur LÉA — remises au dépôt non confirmé")
        L.append("")
        L.append("> Ces remises sont passées, mais rien ne confirme que le dépôt a bien été "
                 "enregistré. Tant qu'elles sont là, mon avancement est une hypothèse, pas un fait.")
        L.append("")
        L.append(table(["Évaluation", "Cours", "Poids", "Était dû le"],
                       [[e["titre"], nom(data, e["cours"]), pct(e), long_date(d(e["date"]))]
                        for e in sorted(douteuses, key=lambda e: e["date"])]))
        L.append("")
        L.append("- [ ] Vérifier sur LÉA celles qui sont bien déposées → l'avancement redevient exact")
        L.append("- [ ] Écrire au prof <b>le jour même</b> pour celles qui ne le sont pas — "
                 "<b>%d %%</b> de points au statut incertain" % incertain(data))
        L.append("- [ ] Une fois vérifié : retirer <code>a_verifier_lea</code> dans "
                 "<code>donnees-session.json</code>")
        L.append("")
        L.append("---")
        L.append("")

    # ---- a faire aujourd'hui
    L.append("## ✅ À faire aujourd'hui")
    L.append("")
    couleur = {"RETARD": "🔴", "REMISE": "🔴", "ADMIN": "🟠", "FINIR": "🟠",
               "TEST BLANC": "🟠", "RELIRE": "🟠", "LECTURE": "📖"}
    for tag, t in carte.taches_du_jour(data, jour, actifs):
        L.append("- [ ] %s <b>%s</b> — %s" % (couleur.get(tag, "🔵"), tag, t))
    L.append("")
    L.append("---")
    L.append("")

    # ---- 7 prochains jours
    L.append("## 🗓️ Les 7 prochains jours")
    L.append("")
    L.append(table(["Jour", "Ce que je fais"], sept_jours(data, jour)))
    L.append("")
    L.append("---")
    L.append("")

    # ---- a regler
    L.append("## 📌 À régler")
    L.append("")
    for t in sorted(data["taches_admin"],
                    key=lambda t: (t["pour"] == "recurrent", t["pour"])):
        if t["pour"] == "recurrent":
            L.append("- [ ] 🔁 %s" % t["quoi"])
            continue
        retard = (jour - d(t["pour"])).days
        note = " · %s" % t["note"] if t.get("note") else ""
        if retard > 0:
            L.append("- [ ] 🔴 <b>%s</b> — <i>%d jour%s de retard</i>%s"
                     % (t["quoi"], retard, "s" if retard > 1 else "", note))
        else:
            L.append("- [ ] 🔵 %s — <i>pour le %s</i>%s"
                     % (t["quoi"], long_date(d(t["pour"])), note))
    L.append("")
    L.append("---")
    L.append("")

    # ---- toutes les echeances
    L.append("## 📅 Toutes mes échéances à venir")
    L.append("")
    L.append("> 💡 Sélectionne ce tableau → <b>Transformer en base de données</b> pour filtrer "
             "par cours et cocher au fur et à mesure.")
    L.append("")
    lignes = []
    for e in prochaines:
        titre = e["titre"] + (" ⚠️" if e.get("a_confirmer") else "")
        lignes.append([pastille(e["reste"]), long_date(d(e["date"])), nom(data, e["cours"]),
                       titre, pct(e), jx(e["reste"])])
    L.append(table(["", "Date", "Cours", "Évaluation", "Poids", "Compte à rebours"], lignes))
    L.append("")
    L.append("> ⚠️ = date ou pondération encore à confirmer auprès du prof. Être prêt une semaine "
             "trop tôt ne coûte rien ; l'inverse, oui.")
    L.append("")
    L.append("---")
    L.append("")

    # ---- lectures
    futures = sorted((l for l in data["lectures"] if d(l["pour"]) >= jour),
                     key=lambda l: l["pour"])
    if futures:
        L.append("## 📖 Mes lectures")
        L.append("")
        L.append(table(["Pour le", "Cours", "À lire"],
                       [[long_date(d(l["pour"])), nom(data, l["cours"]), l["quoi"]]
                        for l in futures]))
        L.append("")
        L.append("---")
        L.append("")

    # ---- semaines rouges
    L.append("## 🔴 Mes semaines rouges")
    L.append("")
    L.append("> Toute semaine où il se joue <b>30 % ou plus</b> de points, tous cours confondus. "
             "C'est là que se gagne ou se perd la session.")
    L.append("")
    L.append(table(["Semaine", "Dates", "Ce qui tombe", "Poids total", "Statut"],
                   [["<b>%d</b>" % num, "%s – %s" % (long_date(deb), long_date(f)),
                     quoi, "<b>%d %%</b>" % total, statut]
                    for num, deb, f, quoi, total, statut in semaines_rouges(data, jour)]))
    L.append("")
    L.append("---")
    L.append("")

    # ---- semaine type
    L.append("## 🗓️ Ma semaine type")
    L.append("")
    lignes = []
    for b in sorted(data["blocs_travail"], key=lambda b: (b["jour"], b["debut"])):
        h1 = dt.datetime.strptime(b["debut"], "%H:%M")
        h2 = dt.datetime.strptime(b["fin"], "%H:%M")
        mins = int((h2 - h1).total_seconds() // 60)
        duree = "%d h%s" % (mins // 60, " %02d" % (mins % 60) if mins % 60 else "")
        emos = "".join(data["cours"][f].get("emoji", "") for f in b["focus"] if f in data["cours"])
        quand = "%s %s – %s" % (JOURS[b["jour"] - 1].capitalize(),
                                b["debut"].replace(":", " h "), b["fin"].replace(":", " h "))
        gros = b["titre"].startswith("GROS BLOC")
        env = (lambda x: "<b>%s</b>" % x) if gros else (lambda x: x)
        lignes.append([env(quand), env(duree), env("%s %s" % (emos or "🔁", b["titre"]))])
    L.append(table(["Quand", "Durée", "Ce que je fais"], lignes))
    L.append("")
    L.append("> ⚠️ Vendredi soir, samedi après-midi et dimanche matin restent <b>vides</b>. "
             "Ce n'est pas du temps perdu : c'est ce qui rend le reste tenable, semaine après semaine.")
    L.append("")
    L.append("---")
    L.append("")

    # ---- methodes, les plus difficiles d'abord
    L.append("## 🧠 Mes méthodes, cours par cours")
    L.append("")
    dur_max = max(c.get("difficulte", 3) for c in data["cours"].values())
    for cle, c in sorted(data["cours"].items(), key=lambda kv: -kv[1].get("difficulte", 3)):
        if not c.get("methode"):
            continue
        suffixe = " — <i>ma matière la plus difficile</i>" if c.get("difficulte") == dur_max else ""
        L.append("### %s %s%s" % (c.get("emoji", ""), c["nom"], suffixe))
        L.append("")
        L.append(c["methode"])
        L.append("")
    L.append("---")
    L.append("")

    # ---- avancement
    L.append("## 📊 Mon avancement")
    L.append("")
    av = carte.avancement(data, jour)
    lignes = []
    for cle, (_, p) in sorted(av.items(), key=lambda kv: -kv[1][1]):
        inc = incertain(data, cle)
        txt = "%d %%" % p + (" <i>(dont %d %% à confirmer)</i>" % inc if inc else "")
        lignes.append([nom(data, cle), txt, barre(p)])
    L.append(table(["Cours", "Part de la note déjà jouée", ""], lignes))
    L.append("")
    moy = sum(p for _, p in av.values()) / float(len(av))
    note = ("<b>%d %%</b> de la session est joué en moyenne, tous cours confondus." % round(moy))
    if incertain(data):
        note += (" Mais <b>%d %%</b> de points restent au statut incertain tant que les remises "
                 "ci-dessus ne sont pas confirmées sur LÉA." % incertain(data))
    L.append("> " + note)
    L.append("")
    L.append("---")
    L.append("")
    L.append("<i>Mis à jour le %s · source : </i><i><code>donnees-session.json</code></i>"
             "<i> · généré par </i><i><code>notion.py</code></i>" % jour_complet(jour))

    return "\n".join(L)


def main():
    args = sys.argv[1:]
    sortie = None
    if "--out" in args:
        i = args.index("--out")
        sortie = args[i + 1]
        args = args[:i] + args[i + 2:]
    jour = d(args[0]) if args else dt.date.today()

    txt = page(carte.charger(), jour)
    if sortie:
        io.open(sortie, "w", encoding="utf-8").write(txt)
        print(sortie)
    else:
        print(txt)


if __name__ == "__main__":
    main()

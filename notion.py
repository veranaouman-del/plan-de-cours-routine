# -*- coding: utf-8 -*-
"""Tableau de bord Notion — Automne 2026.

Produit le contenu complet de la page Notion « Ma session — Automne 2026 »
à partir de donnees-session.json, en Markdown enrichi Notion.

    python3 notion.py                 -> la page d'aujourd'hui, sur la sortie standard
    python3 notion.py 2026-10-15      -> la page telle qu'elle serait à cette date
    python3 notion.py --section apercu  -> seulement le haut de la page (aperçu rapide)

La sortie se colle dans Notion avec `update-page` / `replace_content`. Le script
n'appelle pas Notion lui-même : l'accès passe par le connecteur, pas par le shell.

Rien n'est codé en dur ici non plus : pour changer une date, éditer
donnees-session.json. carte.py (Slack, image) et ce script lisent le même fichier,
donc les deux sorties ne peuvent pas se contredire.
"""
import sys
import datetime as dt

import carte
from carte import (JOURS, MOIS, d, court, jx, charger, semaine_de, en_semaine_etudes,
                   chantiers, chantiers_tous, cours_du_jour, blocs_du_jour,
                   taches_du_jour, avancement, a_verifier)

PASTILLES = [(4, "🔴"), (12, "🟠")]      # au-delà : 🔵
SEUIL_SEMAINE_ROUGE = 30                 # % de points dans la même semaine


def emo(data, cle):
    return data["cours"][cle].get("emoji", "•")


def nom_emo(data, cle):
    return "%s %s" % (emo(data, cle), data["cours"][cle]["nom"])


def pastille(reste):
    for limite, p in PASTILLES:
        if reste <= limite:
            return p
    return "🔵"


def gras_si_lourd(poids):
    """Un poids de 20 % ou plus se lit en gras : c'est ce qui décide de la session."""
    if not poids:
        return "formatif"
    return "**%d %%**" % poids if poids >= 20 else "%d %%" % poids


def long_date(j):
    return "%s %d %s" % (JOURS[j.weekday()], j.day, MOIS[j.month - 1])


def court_jour(j):
    abrev = ["lun.", "mar.", "mer.", "jeu.", "ven.", "sam.", "dim."]
    # « 1er », pas « 1 » : c'est un document qu'on lit en français.
    jour = "1er" if j.day == 1 else str(j.day)
    return "%s %s %s" % (abrev[j.weekday()], jour, carte.ABREV[j.month - 1])


def table(entetes, lignes):
    out = ['<table fit-page-width="true" header-row="true">', "<tr>"]
    out += ["<td>%s</td>" % h for h in entetes]
    out.append("</tr>")
    for ligne in lignes:
        out.append("<tr>")
        out += ["<td>%s</td>" % c for c in ligne]
        out.append("</tr>")
    out.append("</table>")
    return "\n".join(out)


# --------------------------------------------------------------------------
# Semaines rouges : calculées, pas listées à la main
# --------------------------------------------------------------------------
def semaines_rouges(data, jour):
    paires = sorted(((int(n), d(debut)) for n, debut in data["session"]["semaines"].items()),
                    key=lambda p: p[1])
    fin_session = paires[-1][1] + dt.timedelta(days=13)
    derniere, debut_derniere = paires[-1]
    groupes = {}
    for ev in data["evaluations"]:
        jour_ev = d(ev["date"])
        num = semaine_de(data, jour_ev)
        # La session se termine le 11 décembre, mais la période d'examens déborde :
        # tout ce qui tombe après la semaine 15 se joue quand même dans la semaine 15.
        if num is None and jour_ev >= debut_derniere:
            num = derniere
        if num:
            groupes.setdefault(num, []).append(ev)
    out = []
    for num, debut in paires:
        evs = sorted(groupes.get(num, []), key=lambda e: -e["poids"])
        total = sum(e["poids"] for e in evs)
        if total < SEUIL_SEMAINE_ROUGE:
            continue
        fin = fin_session if num == paires[-1][0] else debut + dt.timedelta(days=6)
        out.append((num, debut, fin, evs, total))
    return out


# --------------------------------------------------------------------------
# Les sections
# --------------------------------------------------------------------------
def apercu(data, jour):
    """Le haut de la page : ce qu'on doit pouvoir lire en trois secondes."""
    sem = semaine_de(data, jour)
    actifs = chantiers(data, jour)
    prochaines = chantiers_tous(data, jour)
    L = []

    debut, fin = d(data["session"]["debut"]), d(data["session"]["fin"])
    a, b = [d(x) for x in data["session"]["semaine_etudes"]]
    retour = b + dt.timedelta(days=3 if b.weekday() == 4 else 1)
    L.append("> %s · %s · %s → %s<br>**Semaine d'études** · %s au %s · retour en classe le %s" % (
        data["programme"].split(" - ")[0], data["programme"].split(" - ")[-1],
        "%d %s" % (debut.day, MOIS[debut.month - 1]), "%d %s" % (fin.day, MOIS[fin.month - 1]),
        court_jour(a), court_jour(b), court_jour(retour)))
    L.append("---")

    L.append("## 📍 Aujourd'hui — %s" % long_date(jour))
    cj = cours_du_jour(data, jour)
    if cj:
        for c in cj:
            L.append("- %s **%s – %s** · %s · %s" % (
                emo(data, c["cours"]), c["debut"].replace(":", " h "),
                c["fin"].replace(":", " h "), data["cours"][c["cours"]]["nom"], c["local"]))
    else:
        L.append("- 🎉 **Aucun cours aujourd'hui.**")
    for b_ in blocs_du_jour(data, jour):
        L.append("- 🎯 **%s – %s** · %s" % (b_["debut"].replace(":", " h "),
                                            b_["fin"].replace(":", " h "), b_["titre"]))
    if not blocs_du_jour(data, jour):
        L.append("- 😮‍💨 Journée libre — repos assumé, c'est prévu.")

    L.append(callout(data, jour, sem))

    if actifs:
        p = actifs[0]
        L.append("> 🔥 **Priorité du jour :** %s — %s (%s), %s. Étape : **%s**." % (
            nom_emo(data, p["cours"]), p["titre"],
            ("%d %%" % p["poids"]) if p["poids"] else "formatif",
            jx(p["reste"]), carte.etape(p).lower()))
    if prochaines:
        e = prochaines[0]
        L.append("> ⏭️ **Prochaine échéance :** %s — %s (%s), le %s, **%s**." % (
            nom_emo(data, e["cours"]), e["titre"],
            ("%d %%" % e["poids"]) if e["poids"] else "formatif",
            court_jour(d(e["date"])), jx(e["reste"])))
    return "\n".join(L)


def callout(data, jour, sem):
    """Le mot qui situe la journée dans la session. Un seul, le plus utile."""
    if en_semaine_etudes(data, jour):
        fin = d(data["session"]["semaine_etudes"][1])
        reste = (fin - jour).days
        return ('<callout icon="⏳" color="orange_bg">\n'
                "\t**Il reste %s de semaine d'études.** Les gros blocs retombent à 1 h 30 – 3 h "
                "dès le retour en classe : ce qui n'est pas réglé avant le %s attendra une "
                "vraie semaine de cours.\n</callout>" % (
                    "1 jour" if reste <= 1 else "%d jours" % reste, court_jour(fin)))

    rouges = [(n, debut, f, evs, t) for n, debut, f, evs, t in semaines_rouges(data, jour)
              if f >= jour]
    if rouges:
        n, debut, fin, evs, total = rouges[0]
        jours = (debut - jour).days
        if jours <= 14:
            quand = "Elle commence %s." % ("cette semaine" if jours <= 0 else jx(jours).lower())
            return ('<callout icon="🔴" color="red_bg">\n'
                    "\t**Semaine %d — semaine rouge : %d %% de points en jeu.** %s "
                    "Ce qui s'y joue se prépare maintenant, pas pendant.\n</callout>" % (
                        n, total, quand))
    restant = sum(e["poids"] for e in chantiers_tous(data, jour))
    return ('<callout icon="🎯" color="blue_bg">\n'
            "\t**%d %% de points restent à jouer d'ici la fin de la session.** "
            "Rien n'est joué : tout se décide entre aujourd'hui et le %s.\n</callout>" % (
                restant, court_jour(d(data["session"]["fin"]))))


def section_lea(data, jour):
    douteuses = a_verifier(data, jour)
    if not douteuses:
        return ""
    total = sum(e["poids"] for e in douteuses)
    L = ["## 🔴 À confirmer sur LÉA — remises au dépôt non confirmé",
         "> Ces remises sont passées, mais rien ne confirme que le dépôt a bien été "
         "enregistré. Tant qu'elles sont là, mon avancement est une hypothèse, pas un fait.",
         table(["Évaluation", "Cours", "Poids", "Était dû le"],
               [[e["titre"], nom_emo(data, e["cours"]),
                 "%d %%%s" % (e["poids"], " *(estimé)*" if e.get("poids_approx") else ""),
                 court_jour(d(e["date"]))] for e in douteuses]),
         "- [ ] Vérifier sur LÉA celles qui sont bien déposées → l'avancement redevient exact",
         "- [ ] Écrire au prof **le jour même** pour celles qui ne le sont pas — **%d %%** "
         "de points au statut incertain" % total,
         "- [ ] Une fois vérifié : retirer `a_verifier_lea` dans `donnees-session.json`",
         "---"]
    return "\n".join(L)


def section_a_faire(data, jour):
    icones = {"RETARD": "🔴", "REMISE": "🔴", "ADMIN": "🟠", "FINIR": "🟠",
              "TEST BLANC": "🟠", "LECTURE": "🔵"}
    L = ["## ✅ À faire aujourd'hui"]
    for tag, t in taches_du_jour(data, jour, chantiers(data, jour)):
        L.append("- [ ] %s **%s** — %s" % (icones.get(tag, "🔵"), tag, t))
    L.append("---")
    return "\n".join(L)


def section_sept_jours(data, jour):
    """Les sept prochains jours : c'est ce qui évite de découvrir une remise la veille."""
    lignes = []
    for i in range(7):
        j = jour + dt.timedelta(days=i)
        quoi = []
        for c in cours_du_jour(data, j):
            quoi.append("%s %s – %s · %s" % (emo(data, c["cours"]),
                                             c["debut"].replace(":", " h "),
                                             c["fin"].replace(":", " h "), c["local"]))
        for b in blocs_du_jour(data, j):
            focus = set(b["focus"])
            # Un bloc de rattrapage attaque ce qui presse le plus, peu importe le cours.
            cible = next((e for e in chantiers(data, j)
                          if "rattrapage" in focus or e["cours"] in focus), None)
            suffixe = ""
            if cible:
                suffixe = " — %s : %s *(%s)*" % (emo(data, cible["cours"]), cible["titre"],
                                                 carte.etape(cible).lower())
            quoi.append("**%s – %s** %s%s" % (b["debut"].replace(":", " h "),
                                              b["fin"].replace(":", " h "), b["titre"], suffixe))
        echues = [e for e in chantiers_tous(data, j) if e["reste"] == 0]
        for e in echues:
            quoi.append("⚠️ **%s** — %s *(%s)*" % (e["titre"], nom_emo(data, e["cours"]),
                                                   gras_si_lourd(e["poids"]).replace("**", "")))
        contexte = "*semaine d'études*" if en_semaine_etudes(data, j) else ""
        etiquette = "**%s**%s" % (court_jour(j), " ← *aujourd'hui*" if i == 0 else "")
        lignes.append([etiquette, contexte, "<br>".join(quoi) or "*rien de prévu — journée libre*"])
    return "## 🗓️ Les 7 prochains jours\n" + table(["Jour", "", "Ce que je fais"], lignes) + "\n---"


def section_a_regler(data, jour):
    L = ["## 📌 À régler"]
    for t in data["taches_admin"]:
        if t["pour"] == "recurrent":
            L.append("- [ ] 🔁 %s" % t["quoi"])
            continue
        echeance = d(t["pour"])
        retard = (jour - echeance).days
        if retard > 0:
            marque = "🔴 **%s** — *%d jours de retard*" % (t["quoi"], retard)
        else:
            marque = "%s %s — *pour le %s*" % ("🟠" if t.get("urgent") else "🔵",
                                               t["quoi"], court_jour(echeance))
        if t.get("note"):
            marque += " · %s" % t["note"]
        L.append("- [ ] %s" % marque)
    L.append("---")
    return "\n".join(L)


def section_echeances(data, jour):
    lignes = []
    for e in chantiers_tous(data, jour):
        titre = e["titre"] + (" ⚠️" if e.get("a_confirmer") else "")
        lignes.append([pastille(e["reste"]), court_jour(d(e["date"])),
                       nom_emo(data, e["cours"]), titre,
                       gras_si_lourd(e["poids"]) +
                       (" *(estimé)*" if e.get("poids_approx") else ""),
                       jx(e["reste"])])
    return ("## 📅 Toutes mes échéances à venir\n"
            "> 💡 Sélectionne ce tableau → **Transformer en base de données** pour filtrer "
            "par cours et cocher au fur et à mesure.\n"
            + table(["", "Date", "Cours", "Évaluation", "Poids", "Compte à rebours"], lignes)
            + "\n> ⚠️ = date ou pondération encore à confirmer auprès du prof. Être prêt une "
              "semaine trop tôt ne coûte rien ; l'inverse, oui.\n---")


def section_lectures(data, jour):
    lignes = [[court_jour(d(l["pour"])), nom_emo(data, l["cours"]), l["quoi"]]
              for l in sorted(data["lectures"], key=lambda l: l["pour"])
              if d(l["pour"]) >= jour]
    if not lignes:
        return ""
    return "## 📖 Mes lectures\n" + table(["Pour le", "Cours", "À lire"], lignes) + "\n---"


def section_semaines_rouges(data, jour):
    lignes = []
    for num, debut, fin, evs, total in semaines_rouges(data, jour):
        quoi = " · ".join("%s %s %s" % (emo(data, e["cours"]), e["titre"],
                                        ("%d %%" % e["poids"]) if e["poids"] else "formatif")
                          for e in evs)
        statut = "✅ passée" if fin < jour else ("🔥 en cours" if debut <= jour else "⏳ à venir")
        lignes.append(["**%d**" % num, "%s – %s" % (court_jour(debut), court_jour(fin)),
                       quoi, "**%d %%**" % total, statut])
    return ("## 🔴 Mes semaines rouges\n"
            "> Toute semaine où il se joue **%d %% ou plus** de points, tous cours confondus. "
            "C'est là que se gagne ou se perd la session.\n" % SEUIL_SEMAINE_ROUGE
            + table(["Semaine", "Dates", "Ce qui tombe", "Poids total", "Statut"], lignes)
            + "\n---")


def section_semaine_type(data, jour):
    lignes = []
    for b in sorted(data["blocs_travail"], key=lambda b: (b["jour"], b["debut"])):
        h1 = dt.datetime.strptime(b["debut"], "%H:%M")
        h2 = dt.datetime.strptime(b["fin"], "%H:%M")
        mn = int((h2 - h1).total_seconds() // 60)
        duree = "%d h%s" % (mn // 60, " %02d" % (mn % 60) if mn % 60 else "")
        quand = "%s %s – %s" % (JOURS[b["jour"] - 1].capitalize(),
                                b["debut"].replace(":", " h "), b["fin"].replace(":", " h "))
        emos = "".join(emo(data, c) for c in b["focus"] if c in data["cours"]) or "🔁"
        gros = mn >= 180
        envelope = (lambda t: "**%s**" % t) if gros else (lambda t: t)
        lignes.append([envelope(quand), envelope(duree), envelope("%s %s" % (emos, b["titre"]))])
    return ("## 🗓️ Ma semaine type\n"
            + table(["Quand", "Durée", "Ce que je fais"], lignes)
            + "\n> ⚠️ Vendredi soir, samedi après-midi et dimanche matin restent **vides**. "
              "Ce n'est pas du temps perdu : c'est ce qui rend le reste tenable, semaine "
              "après semaine.\n---")


def section_methodes(data):
    if "methodes" not in data:
        return ""
    dur = max(c["difficulte"] for c in data["cours"].values())
    L = ["## 🧠 Mes méthodes, cours par cours"]
    for cle in sorted(data["cours"], key=lambda k: -data["cours"][k]["difficulte"]):
        if cle not in data["methodes"]:
            continue
        marque = " — *ma matière la plus difficile*" if data["cours"][cle]["difficulte"] == dur else ""
        L.append("### %s%s" % (nom_emo(data, cle), marque))
        L.append(data["methodes"][cle])
    L.append("---")
    return "\n".join(L)


def section_avancement(data, jour):
    lignes = []
    total, incertain_total = [], 0
    for cle, (nom, pct, incertain) in sorted(avancement(data, jour).items(),
                                             key=lambda kv: -kv[1][1]):
        plein = int(round(pct / 10.0))
        barre = "`%s%s`" % ("▰" * plein, "▱" * (10 - plein))
        note = "%d %%" % pct + (" *(dont %d %% à confirmer)*" % incertain if incertain else "")
        lignes.append([nom_emo(data, cle), note, barre])
        total.append(pct)
        incertain_total += incertain
    moyenne = int(round(sum(total) / float(len(total)))) if total else 0
    pied = "> **%d %%** de la session est joué en moyenne, tous cours confondus." % moyenne
    if incertain_total:
        pied += (" Mais **%d %%** de points restent au statut incertain tant que les remises "
                 "ci-dessus ne sont pas confirmées sur LÉA." % incertain_total)
    return ("## 📊 Mon avancement\n"
            + table(["Cours", "Part de la note déjà jouée", ""], lignes) + "\n" + pied + "\n---")


# --------------------------------------------------------------------------
def page(data, jour):
    morceaux = [apercu(data, jour), section_lea(data, jour), section_a_faire(data, jour),
                section_sept_jours(data, jour), section_a_regler(data, jour),
                section_echeances(data, jour), section_lectures(data, jour),
                section_semaines_rouges(data, jour), section_semaine_type(data, jour),
                section_methodes(data), section_avancement(data, jour)]
    morceaux.append("*Mis à jour le %s · source : **`donnees-session.json`** · "
                    "généré par **`notion.py`***" % long_date(jour))
    return "\n".join(m for m in morceaux if m)


def main():
    args = sys.argv[1:]
    section = None
    if "--section" in args:
        i = args.index("--section")
        section = args[i + 1]
        del args[i:i + 2]
    jour = d(args[0]) if args else dt.date.today()
    data = charger()
    if section == "apercu":
        print(apercu(data, jour))
    else:
        print(page(data, jour))


if __name__ == "__main__":
    main()

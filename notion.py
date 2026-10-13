# -*- coding: utf-8 -*-
"""Tableau de bord Notion — Automne 2026.

Fabrique la page Notion « Ma session » à partir de donnees-session.json, en
Markdown enrichi Notion (tableaux `<table>`, cases à cocher, callouts).

    python3 notion.py                 -> la page d'aujourd'hui, sur la sortie standard
    python3 notion.py 2026-10-23      -> la page telle qu'elle sera ce jour-là
    python3 notion.py --sortie p.md   -> écrite dans un fichier

Le texte produit se colle tel quel dans `replace_content` du connecteur Notion.

Comme carte.py, ce script ne contient aucune donnée : tout vient du JSON. Il
réutilise directement les fonctions de carte.py pour que la carte du jour et la
page Notion ne puissent jamais se contredire.
"""
import datetime as dt
import os
import sys

import carte

JOURS_COURTS = ["lun.", "mar.", "mer.", "jeu.", "ven.", "sam.", "dim."]
EMOJI = {"devlog": "💻", "web": "🌐", "litt": "📕", "anglais": "🗣️", "philo": "⚖️"}

# Seuil au-delà duquel une semaine est « rouge » : part de points, tous cours confondus.
SEUIL_SEMAINE_ROUGE = 30


# --------------------------------------------------------------------------
# Petits formateurs
# --------------------------------------------------------------------------
def jour_long(j):
    """« mar. 13 oct. » — avec le « 1er » du français."""
    numero = "1er" if j.day == 1 else str(j.day)
    return "%s %s %s" % (JOURS_COURTS[j.weekday()], numero, carte.ABREV[j.month - 1])


def pastille(reste):
    if reste <= 4:
        return "🔴"
    if reste <= 12:
        return "🟠"
    return "🔵"


def poids_txt(ev):
    if not ev["poids"]:
        return "formatif"
    gras = "**%d %%**" % ev["poids"] if ev["poids"] >= 20 else "%d %%" % ev["poids"]
    return gras + (" *(estimé)*" if ev.get("poids_approx") else "")


def nom(data, cle):
    return "%s %s" % (EMOJI.get(cle, ""), data["cours"][cle]["nom"])


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
# Lectures de la donnée
# --------------------------------------------------------------------------
def a_verifier(data):
    """Remises passées dont le dépôt sur LÉA n'a jamais été confirmé."""
    return [e for e in data["evaluations"] if e.get("a_verifier_lea")]


def admin_ouvertes(data, jour):
    """Tâches administratives encore ouvertes, les plus en retard d'abord."""
    out = []
    for t in data["taches_admin"]:
        if t["pour"] == "recurrent":
            out.append((None, t))
            continue
        out.append(((carte.d(t["pour"]) - jour).days, t))
    return sorted(out, key=lambda p: (p[0] is None, p[0]))


def semaines_rouges(data):
    """Toute semaine de session où il se joue SEUIL_SEMAINE_ROUGE % ou plus."""
    bornes = sorted(((int(n), carte.d(deb)) for n, deb in data["session"]["semaines"].items()),
                    key=lambda p: p[1])
    out = []
    for i, (num, debut) in enumerate(bornes):
        # Une semaine de session dure sept jours. Sans ce plafond, la semaine 7
        # avalerait la semaine d'études qui la suit. La dernière, elle, s'étire
        # jusqu'à la fin de la période d'examens.
        if i + 1 < len(bornes):
            fin = min(bornes[i + 1][1] - dt.timedelta(days=1), debut + dt.timedelta(days=6))
        else:
            fin = carte.d("2026-12-20")
        dedans = [e for e in data["evaluations"] if debut <= carte.d(e["date"]) <= fin]
        total = sum(e["poids"] for e in dedans)
        if total >= SEUIL_SEMAINE_ROUGE:
            out.append({"num": num, "debut": debut, "fin": fin, "poids": total,
                        "evals": sorted(dedans, key=lambda e: -e["poids"])})
    return out


def sept_jours(data, jour):
    """Les sept prochains jours : cours, blocs de travail et ce qu'on y met."""
    out = []
    for n in range(7):
        j = jour + dt.timedelta(days=n)
        actifs = carte.chantiers(data, j)
        lignes = []
        for c in carte.cours_du_jour(data, j):
            lignes.append("%s %s – %s · %s" % (EMOJI.get(c["cours"], ""),
                                               c["debut"].replace(":", " h "),
                                               c["fin"].replace(":", " h "), c["local"]))
        for b in carte.blocs_du_jour(data, j):
            cibles = [e for e in actifs if e["cours"] in b["focus"]]
            if not cibles and "rattrapage" in b["focus"]:
                cibles = actifs
            quoi = ""
            if cibles:
                tete = cibles[0]
                quoi = " — %s : %s *(%s)*" % (EMOJI.get(tete["cours"], ""), tete["titre"],
                                              carte.etape(tete).lower())
            lignes.append("**%s – %s** %s%s" % (b["debut"].replace(":", " h "),
                                                b["fin"].replace(":", " h "), b["titre"], quoi))
        if not lignes:
            lignes.append("*Journée libre — repos assumé, c'est au programme.*")
        etiquette = "**%s**" % jour_long(j)
        if n == 0:
            etiquette += " ← *aujourd'hui*"
        contexte = "*semaine d'études*" if carte.en_semaine_etudes(data, j) else ""
        out.append([etiquette, contexte, "<br>".join(lignes)])
    return out


# --------------------------------------------------------------------------
# La page
# --------------------------------------------------------------------------
def page(data, jour):
    L = []
    sem = carte.semaine_de(data, jour)
    actifs = carte.chantiers(data, jour)
    avenir = carte.chantiers_tous(data, jour)
    douteuses = a_verifier(data)

    # ---- en-tête
    if carte.en_semaine_etudes(data, jour):
        a, b = data["session"]["semaine_etudes"]
        situation = ("**Semaine d'études** · %s au %s · retour en classe le %s"
                     % (jour_long(carte.d(a)), jour_long(carte.d(b)),
                        jour_long(carte.d(b) + dt.timedelta(days=3))))
    else:
        situation = "**Semaine %s sur 15**" % sem
    L.append("> %s · %s<br>%s"
             % (data["programme"].replace(" - ", " · "),
                "24 août → 11 décembre", situation))
    L.append("---")

    # ---- aujourd'hui
    L.append("## 📍 Aujourd'hui — %s %d %s"
             % (carte.JOURS[jour.weekday()], jour.day, carte.MOIS[jour.month - 1]))
    cj = carte.cours_du_jour(data, jour)
    if cj:
        for c in cj:
            L.append("- %s **%s** · %s – %s · local %s"
                     % (EMOJI.get(c["cours"], ""), data["cours"][c["cours"]]["nom"],
                        c["debut"].replace(":", " h "), c["fin"].replace(":", " h "), c["local"]))
    else:
        L.append("- 🎉 **Aucun cours aujourd'hui.**")
    for b in carte.blocs_du_jour(data, jour):
        L.append("- 🎯 **%s – %s** · %s"
                 % (b["debut"].replace(":", " h "), b["fin"].replace(":", " h "), b["titre"]))
    if actifs:
        p = actifs[0]
        L.append("> 🔥 **Priorité du jour :** %s — %s (%s), %s. Étape : **%s**."
                 % (nom(data, p["cours"]), p["titre"], poids_txt(p),
                    carte.jx(p["reste"]), carte.etape(p).lower()))
    if avenir:
        s = avenir[0]
        L.append("> ⏭️ **Prochaine échéance :** %s — %s (%s), le %s, **%s**."
                 % (nom(data, s["cours"]), s["titre"], poids_txt(s),
                    jour_long(carte.d(s["date"])), carte.jx(s["reste"])))
    L.append("---")

    # ---- remises au statut incertain
    if douteuses:
        enjeu = sum(e["poids"] for e in douteuses)
        L.append("## 🔴 À confirmer sur LÉA — remises au dépôt non confirmé")
        L.append("> Ces remises sont passées, mais rien ne confirme que le dépôt a bien été "
                 "enregistré. Tant qu'elles sont là, mon avancement est une hypothèse, pas un fait.")
        L.append(table(["Évaluation", "Cours", "Poids", "Était dû le"],
                       [[e["titre"], nom(data, e["cours"]), poids_txt(e),
                         jour_long(carte.d(e["date"]))] for e in douteuses]))
        L.append("- [ ] Vérifier sur LÉA celles qui sont bien déposées → l'avancement redevient exact")
        L.append("- [ ] Écrire au prof **le jour même** pour celles qui ne le sont pas — "
                 "**%d %%** de points au statut incertain" % enjeu)
        L.append("- [ ] Une fois vérifié : retirer `a_verifier_lea` dans `donnees-session.json`")
        L.append("---")

    # ---- à faire aujourd'hui
    L.append("## ✅ À faire aujourd'hui")
    for tag, t in carte.taches_du_jour(data, jour, actifs):
        puce = "🔴" if tag in ("RETARD", "REMISE") else ("🟠" if tag in ("FINIR", "TEST BLANC", "ADMIN") else "🔵")
        L.append("- [ ] %s **%s** — %s" % (puce, tag, t))
    L.append("---")

    # ---- les sept prochains jours
    L.append("## 🗓️ Les 7 prochains jours")
    L.append(table(["Jour", "", "Ce que je fais"], sept_jours(data, jour)))
    L.append("---")

    # ---- administratif
    L.append("## 📌 À régler")
    for reste, t in admin_ouvertes(data, jour):
        if reste is None:
            L.append("- [ ] 🔁 %s" % t["quoi"])
        elif reste < 0:
            L.append("- [ ] 🔴 **%s** — *%d jours de retard*%s"
                     % (t["quoi"], -reste, " · " + t["note"] if t.get("note") else ""))
        else:
            puce = "🟠" if reste <= 7 else "🔵"
            L.append("- [ ] %s %s — *pour le %s*"
                     % (puce, t["quoi"], jour_long(carte.d(t["pour"]))))
    L.append("---")

    # ---- échéances
    L.append("## 📅 Toutes mes échéances à venir")
    L.append("> 💡 Sélectionne ce tableau → **Transformer en base de données** pour filtrer "
             "par cours et cocher au fur et à mesure.")
    L.append(table(["", "Date", "Cours", "Évaluation", "Poids", "Compte à rebours"],
                   [[pastille(e["reste"]), jour_long(carte.d(e["date"])), nom(data, e["cours"]),
                     e["titre"] + (" ⚠️" if e.get("a_confirmer") else ""),
                     poids_txt(e), carte.jx(e["reste"])] for e in avenir]))
    if any(e.get("a_confirmer") for e in avenir):
        L.append("> ⚠️ = date ou pondération encore à confirmer auprès du prof. "
                 "Être prêt une semaine trop tôt ne coûte rien ; l'inverse, oui.")
    L.append("---")

    # ---- lectures
    futures = [l for l in data["lectures"] if carte.d(l["pour"]) >= jour]
    if futures:
        L.append("## 📖 Mes lectures")
        L.append(table(["Pour le", "Cours", "À lire"],
                       [[jour_long(carte.d(l["pour"])), nom(data, l["cours"]), l["quoi"]]
                        for l in sorted(futures, key=lambda l: l["pour"])]))
        L.append("---")

    # ---- semaines rouges
    L.append("## 🔴 Mes semaines rouges")
    L.append("> Toute semaine où il se joue **%d %% ou plus** de points, tous cours confondus. "
             "C'est là que se gagne ou se perd la session." % SEUIL_SEMAINE_ROUGE)
    lignes = []
    for s in semaines_rouges(data):
        quoi = " · ".join("%s %s %s" % (EMOJI.get(e["cours"], ""), e["titre"],
                                        ("%d %%" % e["poids"]) if e["poids"] else "formatif")
                          for e in s["evals"])
        statut = "✅ passée" if s["fin"] < jour else ("🔥 **en cours**" if s["debut"] <= jour else "⏳ à venir")
        lignes.append(["**%d**" % s["num"], "%s – %s" % (jour_long(s["debut"]), jour_long(s["fin"])),
                       quoi, "**%d %%**" % s["poids"], statut])
    L.append(table(["Semaine", "Dates", "Ce qui tombe", "Poids total", "Statut"], lignes))
    L.append("---")

    # ---- semaine type
    L.append("## 🗓️ Ma semaine type")
    lignes = []
    for b in data["blocs_travail"]:
        deb = dt.datetime.strptime(b["debut"], "%H:%M")
        fin = dt.datetime.strptime(b["fin"], "%H:%M")
        minutes = int((fin - deb).total_seconds() // 60)
        duree = "%d h%s" % (minutes // 60, " %02d" % (minutes % 60) if minutes % 60 else "")
        titre = "%s %s" % ("".join(EMOJI.get(f, "🔁") for f in b["focus"]), b["titre"])
        gros = b["titre"].startswith("GROS")
        lignes.append(["**%s %s – %s**" % (carte.JOURS[b["jour"] - 1].capitalize(),
                                           b["debut"].replace(":", " h "), b["fin"].replace(":", " h "))
                       if gros else "%s %s – %s" % (carte.JOURS[b["jour"] - 1].capitalize(),
                                                    b["debut"].replace(":", " h "), b["fin"].replace(":", " h ")),
                       "**%s**" % duree if gros else duree,
                       "**%s**" % titre if gros else titre])
    L.append(table(["Quand", "Durée", "Ce que je fais"], lignes))
    L.append("> ⚠️ Vendredi soir, samedi après-midi et dimanche matin restent **vides**. "
             "Ce n'est pas du temps perdu : c'est ce qui rend le reste tenable, semaine après semaine.")
    L.append("---")

    # ---- méthodes
    if data.get("methodes"):
        L.append("## 🧠 Mes méthodes, cours par cours")
        dur = max(c["difficulte"] for c in data["cours"].values())
        ordre = sorted(data["methodes"], key=lambda c: -data["cours"][c]["difficulte"])
        for cle in ordre:
            suffixe = " — *ma matière la plus difficile*" if data["cours"][cle]["difficulte"] == dur else ""
            L.append("### %s%s" % (nom(data, cle), suffixe))
            L.append(data["methodes"][cle])
        L.append("---")

    # ---- avancement
    L.append("## 📊 Mon avancement")
    av = sorted(carte.avancement(data, jour).items(), key=lambda p: -p[1][1])
    lignes = []
    for cle, (libelle, pct) in av:
        plein = int(round(pct / 10.0))
        lignes.append([nom(data, cle), "%d %%" % pct,
                       "`%s`" % ("▰" * plein + "▱" * (10 - plein))])
    L.append(table(["Cours", "Part de la note déjà jouée", ""], lignes))
    moyenne = sum(p[1][1] for p in av) / float(len(av))
    note = ("> **%d %%** de la session est joué en moyenne, tous cours confondus."
            % round(moyenne))
    if douteuses:
        note += (" Mais **%d %%** de points restent au statut incertain tant que les remises "
                 "ci-dessus ne sont pas confirmées sur LÉA." % sum(e["poids"] for e in douteuses))
    L.append(note)
    L.append("---")

    L.append("*Mis à jour le %s %d %s · source : `donnees-session.json` · généré par `notion.py`*"
             % (carte.JOURS[jour.weekday()], jour.day, carte.MOIS[jour.month - 1]))
    return "\n".join(L)


def main():
    args = sys.argv[1:]
    sortie = None
    if "--sortie" in args:
        i = args.index("--sortie")
        sortie = args[i + 1]
        args = args[:i] + args[i + 2:]
    jour = carte.d(args[0]) if args else dt.date.today()

    texte = page(carte.charger(), jour)
    if sortie:
        with open(sortie, "w", encoding="utf-8") as fh:
            fh.write(texte)
        print(sortie)
    else:
        print(texte)


if __name__ == "__main__":
    main()

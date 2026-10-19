# -*- coding: utf-8 -*-
"""Tableau de bord Notion — Automne 2026.

Fabrique le corps complet de la page Notion « Ma session » à partir de
donnees-session.json, en réutilisant le moteur de carte.py.

    python3 notion.py                 -> aujourd'hui, sur la sortie standard
    python3 notion.py 2026-10-19      -> une date précise

Le texte produit est du Markdown enrichi Notion (balises <table>, <callout>) :
il se colle tel quel dans notion-update-page, commande replace_content.
"""
import sys
import datetime as dt

import carte
from carte import d, court, chantiers, chantiers_tous, cours_du_jour, blocs_du_jour, \
    taches_du_jour, blocs_du_jour as _bj, avancement, a_verifier, etape, jx, \
    semaine_de, en_semaine_etudes, JOURS, MOIS

JOURS_COURTS = ["lun.", "mar.", "mer.", "jeu.", "ven.", "sam.", "dim."]

EMOJI = {"devlog": "💻", "web": "🌐", "litt": "📕", "anglais": "🗣️", "philo": "⚖️"}

METHODES = {
    "litt": "Annoter PENDANT la lecture, jamais après. Un carnet de citations classées par "
            "thème — c'est lui qui sauve quand le sujet tombe. Garder 10 minutes de relecture "
            "linguistique en fin de rédaction : la langue vaut 25 % de chaque dissertation.",
    "philo": "Droit aux notes de cours à TOUTES les évaluations : la vraie préparation, c'est de "
             "construire de bonnes notes, pas de mémoriser. Un tableau par penseur — thèse, "
             "critère du juste, objection, exemple. Lire les extraits AVANT le cours du vendredi.",
    "anglais": "Tout se joue en classe, rien ne se rattrape. Remplir le journal Odyssey le jour "
               "même (5 % garantis). Les oraux valent 45 % du cours : ils se préparent À VOIX "
               "HAUTE. S'enregistrer deux minutes au téléphone et se réécouter.",
    "devlog": "Le code se retient par les doigts. Refaire les exercices dirigés sans la "
              "correction, puis comparer. S'entraîner à écrire du code SUR PAPIER, sans "
              "autocomplétion — c'est ce qui est demandé à l'examen.",
    "web": "Chaque TP s'appuie sur le précédent (VueJS → Router → WebAPI → EF Core → fetch) : "
           "un TP bâclé se paie deux fois. Après chaque remise, noter en trois lignes ce qui a "
           "bloqué — c'est exactement ce qui tombera aux évaluations.",
}


# --------------------------------------------------------------------------
# Petits utilitaires d'écriture
# --------------------------------------------------------------------------
def jc(j):
    """« lun. 19 oct. » — le format court utilisé partout dans la page."""
    jour = "1er" if j.day == 1 else str(j.day)
    return "%s %s %s" % (JOURS_COURTS[j.weekday()], jour, carte.ABREV[j.month - 1])


def jlong(j):
    return "%s %d %s" % (JOURS[j.weekday()], j.day, MOIS[j.month - 1])


def h(x):
    return x.replace(":", " h ")


def poids(e):
    if not e["poids"]:
        return "formatif"
    t = "%d %%" % e["poids"]
    if e["poids"] >= 20:
        t = "**%s**" % t
    if e.get("poids_approx"):
        t += " *(estimé)*"
    return t


def nom(data, cle, court_nom=False):
    c = data["cours"][cle]
    return "%s %s" % (EMOJI[cle], c["court"] if court_nom else c["nom"])


def table(entetes, lignes):
    out = ['<table fit-page-width="true" header-row="true">', "<tr>"]
    out += ["<td>%s</td>" % e for e in entetes]
    out.append("</tr>")
    for l in lignes:
        out.append("<tr>")
        out += ["<td>%s</td>" % c for c in l]
        out.append("</tr>")
    out.append("</table>")
    return "\n".join(out)


def pastille(reste):
    return "🔴" if reste <= 4 else ("🟠" if reste <= 12 else "🔵")


def barre(pct):
    plein = int(round(pct / 10.0))
    return "`%s%s`" % ("▰" * min(plein, 10), "▱" * max(10 - plein, 0))


# --------------------------------------------------------------------------
# Les blocs de la page
# --------------------------------------------------------------------------
def semaines_rouges(data, jour, seuil=30):
    """Toute semaine où il se joue `seuil` % ou plus, tous cours confondus."""
    paires = sorted(((int(n), d(deb)) for n, deb in data["session"]["semaines"].items()),
                    key=lambda p: p[1])
    out = []
    for i, (num, debut) in enumerate(paires):
        # une semaine de session fait 7 jours ; la derniere avale la periode d'examens
        fin = min(paires[i + 1][1] - dt.timedelta(days=1), debut + dt.timedelta(days=6)) \
            if i + 1 < len(paires) else debut + dt.timedelta(days=13)
        dedans = [e for e in data["evaluations"] if debut <= d(e["date"]) <= fin]
        total = sum(e["poids"] for e in dedans)
        if total >= seuil:
            out.append((num, debut, fin, sorted(dedans, key=lambda e: -e["poids"]), total))
    return out


def sept_prochains_jours(data, jour):
    lignes = []
    for i in range(7):
        j = jour + dt.timedelta(days=i)
        cases = []
        for c in cours_du_jour(data, j):
            cases.append("%s %s – %s · %s" % (EMOJI[c["cours"]], h(c["debut"]), h(c["fin"]), c["local"]))
        actifs = chantiers(data, j)
        for b in blocs_du_jour(data, j):
            txt = "**%s – %s** %s" % (h(b["debut"]), h(b["fin"]), b["titre"])
            vise = [e for e in actifs if e["cours"] in b["focus"]]
            if vise:
                e = vise[0]
                txt += " — %s : %s *(%s)*" % (EMOJI[e["cours"]], e["titre"], etape(e).lower())
            cases.append(txt)
        for e in data["evaluations"]:
            if not e.get("fait") and d(e["date"]) == j:
                cases.append("⚠️ **%s** — %s *(%s)*" % (e["titre"], nom(data, e["cours"]),
                                                        "formatif" if not e["poids"] else "%d %%" % e["poids"]))
        if not cases:
            cases = ["*Journée libre — repos assumé, c'est prévu.*"]
        etiquette = "**%s**" % jc(j) + (" ← *aujourd'hui*" if i == 0 else "")
        lignes.append([etiquette, "<br>".join(cases)])
    return table(["Jour", "Ce que je fais"], lignes)


def corps(data, jour):
    L = []
    sem = semaine_de(data, jour)
    actifs = chantiers(data, jour)
    prochaines = chantiers_tous(data, jour)
    av = a_verifier(data, jour)
    restant = sum(e["poids"] for e in prochaines)

    # --- en-tête ---------------------------------------------------------
    entete = "> 420.B0 Techniques de l'informatique · Cégep de Granby · 24 août → 11 décembre<br>"
    if en_semaine_etudes(data, jour):
        entete += "**Semaine d'études et d'encadrement** · aucun cours cette semaine"
    else:
        entete += "**Semaine %s sur 15**" % sem
    L.append(entete)
    L.append("---")

    # --- aujourd'hui -----------------------------------------------------
    L.append("## 📍 Aujourd'hui — %s" % jlong(jour))
    cj = cours_du_jour(data, jour)
    if cj:
        for c in cj:
            L.append("- %s **%s – %s** · %s · %s" % (EMOJI[c["cours"]], h(c["debut"]), h(c["fin"]),
                                                     data["cours"][c["cours"]]["nom"], c["local"]))
    else:
        L.append("- 🎉 **Aucun cours aujourd'hui.**")
    for b in blocs_du_jour(data, jour):
        L.append("- 🎯 **%s – %s** · %s" % (h(b["debut"]), h(b["fin"]), b["titre"]))

    L.append('<callout icon="🎯" color="blue_bg">')
    L.append("\t**%d %% de points restent à jouer d'ici la fin de la session.** "
             "Tout se décide entre aujourd'hui et le %s" % (restant, jc(d(data["session"]["fin"]))))
    L.append("</callout>")

    if actifs:
        p = actifs[0]
        L.append("> 🔥 **Priorité du jour :** %s — %s (%s), %s. Étape : **%s**."
                 % (nom(data, p["cours"]), p["titre"], poids(p).replace("**", ""),
                    jx(p["reste"]), etape(p).lower()))
    if prochaines:
        e = prochaines[0]
        L.append("> ⏭️ **Prochaine échéance :** %s — %s (%s), le %s, **%s**."
                 % (nom(data, e["cours"]), e["titre"], poids(e).replace("**", ""),
                    jc(d(e["date"])), jx(e["reste"])))

    # --- remises au statut incertain -------------------------------------
    if av:
        L.append("## 🔴 À confirmer sur LÉA — remises au dépôt non confirmé")
        L.append("> Ces remises sont passées, mais rien ne confirme que le dépôt a bien été "
                 "enregistré. Tant qu'elles sont là, mon avancement est une hypothèse, pas un fait.")
        L.append(table(["Évaluation", "Cours", "Poids", "Était dû le"],
                       [[e["titre"], nom(data, e["cours"]), poids(e), jc(d(e["date"]))] for e in av]))
        L.append("- [ ] Vérifier sur LÉA celles qui sont bien déposées → l'avancement redevient exact")
        L.append("- [ ] Écrire au prof **le jour même** pour celles qui ne le sont pas — **%d %%** "
                 "de points au statut incertain" % sum(e["poids"] for e in av))
        L.append("- [ ] Une fois vérifié : retirer `a_verifier_lea` dans `donnees-session.json`")
    L.append("---")

    # --- à faire aujourd'hui ---------------------------------------------
    L.append("## ✅ À faire aujourd'hui")
    for tag, t in taches_du_jour(data, jour, actifs):
        puce = "🔴" if tag in ("RETARD", "REMISE") else ("🟠" if tag in ("FINIR", "TEST BLANC", "ADMIN") else "🔵")
        L.append("- [ ] %s **%s** — %s" % (puce, tag, t))
    L.append("---")

    # --- la semaine qui vient --------------------------------------------
    L.append("## 🗓️ Les 7 prochains jours")
    L.append(sept_prochains_jours(data, jour))
    L.append("---")

    # --- à régler --------------------------------------------------------
    L.append("## 📌 À régler")
    for t in data["taches_admin"]:
        suffixe = " · %s" % t["note"] if t.get("note") else ""
        if t["pour"] == "recurrent":
            L.append("- [ ] 🔁 %s%s" % (t["quoi"], suffixe))
            continue
        retard = (jour - d(t["pour"])).days
        if retard > 0:
            L.append("- [ ] 🔴 **%s** — *%d jour%s de retard*%s"
                     % (t["quoi"], retard, "s" if retard > 1 else "", suffixe))
        else:
            L.append("- [ ] 🔵 %s — *pour le %s*%s" % (t["quoi"], jc(d(t["pour"])), suffixe))
    L.append("---")

    # --- toutes les échéances --------------------------------------------
    L.append("## 📅 Toutes mes échéances à venir")
    L.append("> 💡 Sélectionne ce tableau → **Transformer en base de données** pour filtrer par "
             "cours et cocher au fur et à mesure.")
    lignes = []
    for e in prochaines:
        titre = e["titre"] + (" ⚠️" if e.get("a_confirmer") else "")
        lignes.append([pastille(e["reste"]), jc(d(e["date"])), nom(data, e["cours"]),
                       titre, poids(e), jx(e["reste"])])
    L.append(table(["", "Date", "Cours", "Évaluation", "Poids", "Compte à rebours"], lignes))
    L.append("> ⚠️ = date ou pondération encore à confirmer auprès du prof. Être prêt une semaine "
             "trop tôt ne coûte rien ; l'inverse, oui.")
    L.append("---")

    # --- lectures --------------------------------------------------------
    lectures = sorted([l for l in data["lectures"] if d(l["pour"]) >= jour], key=lambda l: l["pour"])
    if lectures:
        L.append("## 📖 Mes lectures")
        L.append(table(["Pour le", "Cours", "À lire"],
                       [[jc(d(l["pour"])), nom(data, l["cours"]), l["quoi"]] for l in lectures]))
        L.append("---")

    # --- semaines rouges -------------------------------------------------
    L.append("## 🔴 Mes semaines rouges")
    L.append("> Toute semaine où il se joue **30 % ou plus** de points, tous cours confondus. "
             "C'est là que se gagne ou se perd la session.")
    lignes = []
    for num, debut, fin, evals, total in semaines_rouges(data, jour):
        quoi = " · ".join("%s %s %s" % (EMOJI[e["cours"]], e["titre"], poids(e).replace("**", ""))
                          for e in evals)
        statut = "✅ passée" if fin < jour else ("🔥 **en cours**" if debut <= jour <= fin else "⏳ à venir")
        lignes.append(["**%d**" % num, "%s – %s" % (jc(debut), jc(fin)), quoi, "**%d %%**" % total, statut])
    L.append(table(["Semaine", "Dates", "Ce qui tombe", "Poids total", "Statut"], lignes))
    L.append("---")

    # --- semaine type ----------------------------------------------------
    L.append("## 🗓️ Ma semaine type")
    lignes = []
    for b in data["blocs_travail"]:
        deb = dt.datetime.strptime(b["debut"], "%H:%M")
        f = dt.datetime.strptime(b["fin"], "%H:%M")
        mins = int((f - deb).total_seconds() // 60)
        duree = "%d h" % (mins // 60) + (" %02d" % (mins % 60) if mins % 60 else "")
        quand = "%s %s – %s" % (JOURS[b["jour"] - 1].capitalize(), h(b["debut"]), h(b["fin"]))
        emo = "".join(EMOJI[c] for c in b["focus"] if c in EMOJI) or "🔁"
        libelle = "%s %s" % (emo, b["titre"])
        if mins >= 180:
            quand, duree, libelle = "**%s**" % quand, "**%s**" % duree, "**%s**" % libelle
        lignes.append([quand, duree, libelle])
    L.append(table(["Quand", "Durée", "Ce que je fais"], lignes))
    L.append("> ⚠️ Vendredi soir, samedi après-midi et dimanche matin restent **vides**. Ce n'est "
             "pas du temps perdu : c'est ce qui rend le reste tenable, semaine après semaine.")
    L.append("---")

    # --- méthodes --------------------------------------------------------
    L.append("## 🧠 Mes méthodes, cours par cours")
    for cle in sorted(data["cours"], key=lambda c: -data["cours"][c]["difficulte"]):
        dur = " — *ma matière la plus difficile*" if data["cours"][cle]["difficulte"] >= 4 else ""
        L.append("### %s%s" % (nom(data, cle), dur))
        L.append(METHODES[cle])
    L.append("---")

    # --- avancement ------------------------------------------------------
    L.append("## 📊 Mon avancement")
    av_cours = sorted(avancement(data, jour).items(), key=lambda kv: -kv[1][1])
    lignes = []
    for cle, (n, pct, incertain) in av_cours:
        note = "%d %%" % pct + (" *(dont %d %% à confirmer)*" % incertain if incertain else "")
        lignes.append([nom(data, cle), note, barre(pct)])
    L.append(table(["Cours", "Part de la note déjà jouée", ""], lignes))
    moyenne = round(sum(v[1] for _, v in av_cours) / float(len(av_cours)))
    pied = "> **%d %%** de la session est joué en moyenne, tous cours confondus." % moyenne
    if av:
        pied += " Mais **%d %%** de points restent au statut incertain tant que les remises " \
                "ci-dessus ne sont pas confirmées sur LÉA." % sum(e["poids"] for e in av)
    L.append(pied)
    L.append("---")
    L.append("*Mis à jour le %s · source : **`donnees-session.json`** · généré par **`notion.py`***"
             % jlong(jour))
    return "\n".join(L)


def main():
    args = sys.argv[1:]
    jour = d(args[0]) if args else dt.date.today()
    print(corps(carte.charger(), jour))


if __name__ == "__main__":
    main()

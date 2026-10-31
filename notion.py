# -*- coding: utf-8 -*-
"""Tableau de bord Notion — Automne 2026.

Génère le contenu complet de la page Notion « Ma session — Automne 2026 »
à partir de donnees-session.json, en Notion-flavored Markdown.

    python3 notion.py                          -> la page d'aujourd'hui
    python3 notion.py 2026-11-03               -> la page d'un jour donné
    python3 notion.py --coaching bloc.md       -> insère un fragment écrit à la main
                                                  (les encadrés du jour) après la priorité

Le texte est destiné à `notion-update-page` / command `replace_content`.
Rien n'est codé en dur : pour changer une échéance, éditer donnees-session.json.
"""
import os
import sys
import datetime as dt

import carte

JOURS_C = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
JOURS_A = ["lun.", "mar.", "mer.", "jeu.", "ven.", "sam.", "dim."]

EMOJI = {"devlog": "💻", "web": "🌐", "litt": "📕", "anglais": "🗣️", "philo": "⚖️"}

d = carte.d


# --------------------------------------------------------------------------
def jour_long(j):
    return "%s %s %s" % (JOURS_C[j.weekday()].lower(), jour_num(j), carte.MOIS[j.month - 1])


def jour_court(j):
    return "%s %s %s" % (JOURS_A[j.weekday()], jour_num(j), carte.ABREV[j.month - 1])


def jour_num(j):
    return "1er" if j.day == 1 else str(j.day)


def heure(h):
    return h.replace(":", " h ")


def poids_txt(e):
    if not e["poids"]:
        return "formatif"
    t = "%d %%" % e["poids"]
    if e["poids"] >= 20:
        t = "<b>%s</b>" % t
    if e.get("poids_approx"):
        t += " <i>(estimé)</i>"
    return t


def pastille(reste):
    return "🔴" if reste <= 4 else ("🟠" if reste <= 12 else "🔵")


def table(entetes, lignes):
    """Tableau Notion stylé (pleine largeur, ligne d'en-tête). Les cellules sont
    inline-only : <br /> pour un retour à la ligne, jamais de bloc."""
    out = ['<table fit-page-width="true" header-row="true">']
    out.append("<tr>%s</tr>" % "".join("<th>%s</th>" % h for h in entetes))
    for ligne in lignes:
        out.append("<tr>%s</tr>" % "".join("<td>%s</td>" % c for c in ligne))
    out.append("</table>")
    return "\n".join(out)


# --------------------------------------------------------------------------
def points_restants(data, jour):
    return sum(e["poids"] for e in carte.chantiers_tous(data, jour))


def a_verifier(data):
    return [e for e in data["evaluations"] if e.get("a_verifier_lea")]


def retard_jours(t, jour):
    return (jour - d(t["pour"])).days


def sept_jours(data, jour):
    """Le tableau des 7 prochains jours : cours, blocs, échéances, lectures."""
    lignes = []
    for i in range(7):
        j = jour + dt.timedelta(days=i)
        cases = []
        for c in carte.cours_du_jour(data, j):
            co = data["cours"][c["cours"]]
            cases.append("%s %s – %s · %s" % (EMOJI[c["cours"]], heure(c["debut"]),
                                              heure(c["fin"]), c["local"]))
        actifs = carte.chantiers(data, j)
        for b in carte.blocs_du_jour(data, j):
            # une remise du matin n'est plus un chantier pour le bloc de l'apres-midi
            ouverts = [e for e in actifs if e["reste"] > 0]
            cible = next((e for e in ouverts if e["cours"] in b["focus"]), None)
            if cible is None and "rattrapage" in b["focus"]:
                cible = ouverts[0] if ouverts else None
            suite = ""
            if cible is not None:
                suite = " — %s : %s <i>(%s)</i>" % (EMOJI[cible["cours"]], cible["titre"],
                                                    carte.etape(cible).lower())
            elif b["focus"] != ["rattrapage"]:
                suite = " — <i>aucune échéance ouverte : prise d'avance ou rattrapage</i>"
            cases.append("<b>%s – %s</b> %s%s" % (heure(b["debut"]), heure(b["fin"]), b["titre"], suite))
        for e in data["evaluations"]:
            if not e.get("fait") and d(e["date"]) == j:
                cases.append("⚠️ <b>%s</b> — %s %s <i>(%s)</i>" % (
                    e["titre"], EMOJI[e["cours"]], data["cours"][e["cours"]]["nom"], poids_txt(e)))
        for l in data["lectures"]:
            if d(l["pour"]) == j:
                cases.append("📖 %s" % l["quoi"])
        if not cases:
            cases.append("<i>journée libre</i>")
        etiquette = "<b>%s</b>" % jour_court(j)
        if i == 0:
            etiquette += " ← <i>aujourd'hui</i>"
        lignes.append([etiquette, "<br />".join(cases)])
    return table(["Jour", "Ce que je fais"], lignes)


# --------------------------------------------------------------------------
def page(data, jour, coaching=""):
    sem = carte.semaine_de(data, jour)
    actifs = carte.chantiers(data, jour)
    tous = carte.chantiers_tous(data, jour)
    L = []

    L.append("> 420.B0 Techniques de l'informatique · Cégep de Granby · 24 août → 11 décembre"
             "<br /><b>Semaine %s sur 15</b>" % (sem if sem else "—"))
    L.append("")
    L.append("---")
    L.append("")

    # ---- aujourd'hui
    L.append("## 📍 Aujourd'hui — %s" % jour_long(jour))
    L.append("")
    cj = carte.cours_du_jour(data, jour)
    if not cj:
        L.append("- 🛋️ <b>Aucun cours</b> — journée de travail libre")
    for c in cj:
        L.append("- %s <b>%s – %s</b> · %s · %s" % (EMOJI[c["cours"]], heure(c["debut"]),
                                                    heure(c["fin"]),
                                                    data["cours"][c["cours"]]["nom"], c["local"]))
    for b in carte.blocs_du_jour(data, jour):
        L.append("- 🎯 <b>%s – %s</b> · %s" % (heure(b["debut"]), heure(b["fin"]), b["titre"]))
    L.append("")

    reste_pts = points_restants(data, jour)
    derniere = d(max(e["date"] for e in tous)) if tous else jour
    L.append('<callout icon="🎯" color="blue_bg">')
    L.append("<b>%d %% de points restent à jouer d'ici la fin de la session.</b> "
             "Tout se décide entre aujourd'hui et le %s." % (reste_pts, jour_court(derniere).rstrip(".")))
    L.append("</callout>")
    L.append("")

    if actifs:
        p = actifs[0]
        L.append("> 🔥 <b>Priorité du jour :</b> %s %s — %s (%s), %s. Étape : <b>%s</b>."
                 % (EMOJI[p["cours"]], data["cours"][p["cours"]]["nom"], p["titre"],
                    poids_txt(p).replace("<b>", "").replace("</b>", ""),
                    carte.jx(p["reste"]), carte.etape(p).lower()))
        L.append("")

    if coaching:
        L.append(coaching.strip())
        L.append("")

    # ---- points incertains
    douteux = a_verifier(data)
    if douteux:
        L.append("---")
        L.append("")
        L.append("## 🔴 À confirmer — points au statut incertain")
        L.append("")
        L.append("> Ces évaluations sont passées, mais rien ne confirme qu'elles ont bien été "
                 "déposées, ou même tenues. Tant qu'elles sont là, mon avancement est une "
                 "hypothèse, pas un fait.")
        L.append("")
        L.append(table(["Évaluation", "Cours", "Poids", "Était prévu le"],
                       [[e["titre"],
                         "%s %s" % (EMOJI[e["cours"]], data["cours"][e["cours"]]["nom"]),
                         poids_txt(e).replace("<b>", "").replace("</b>", ""),
                         jour_court(d(e["date"]))] for e in douteux]))
        L.append("")
        total = sum(e["poids"] for e in douteux)
        L.append("- [ ] Vérifier sur LÉA ou par MIO celles qui sont réglées → l'avancement redevient exact")
        L.append("- [ ] Écrire au prof <b>le jour même</b> pour chaque ligne qui reste — "
                 "<b>%d %%</b> de points au statut incertain" % total)
        L.append("- [ ] Une fois vérifié : retirer <code>a_verifier_lea</code> dans "
                 "<code>donnees-session.json</code>")
        L.append("")

    # ---- à faire aujourd'hui
    L.append("---")
    L.append("")
    L.append("## ✅ À faire aujourd'hui")
    L.append("")
    puces = {"RETARD": "🔴", "REMISE": "🔴", "ADMIN": "📌", "LECTURE": "📖",
             "FINIR": "🟠", "TEST BLANC": "🟠", "AVANCER": "🔵", "FICHES": "🔵", "NOTES": "🔵",
             "RELIRE": "🟠"}
    for tag, t in carte.taches_du_jour(data, jour, actifs):
        L.append("- [ ] %s <b>%s</b> — %s" % (puces.get(tag, "🔵"), tag, t))
    L.append("")

    # ---- 7 jours
    L.append("---")
    L.append("")
    L.append("## 🗓️ Les 7 prochains jours")
    L.append("")
    L.append(sept_jours(data, jour))
    L.append("")

    # ---- à régler
    L.append("---")
    L.append("")
    L.append("## 📌 À régler")
    L.append("")
    recurrents = []
    for t in data["taches_admin"]:
        if t["pour"] == "recurrent":
            recurrents.append("- [ ] 🔁 %s" % t["quoi"])
            continue
        r = retard_jours(t, jour)
        note = " · %s" % t["note"] if t.get("note") else ""
        if r > 0:
            L.append("- [ ] 🔴 <b>%s</b> — <i>%d jour%s de retard</i>%s"
                     % (t["quoi"], r, "s" if r > 1 else "", note))
        else:
            L.append("- [ ] 🔵 %s — <i>pour le %s</i>%s"
                     % (t["quoi"], jour_court(d(t["pour"])), note))
    L.extend(recurrents)
    L.append("")

    # ---- échéances
    L.append("---")
    L.append("")
    L.append("## 📅 Toutes mes échéances à venir")
    L.append("")
    L.append("> 💡 Sélectionne ce tableau → <b>Transformer en base de données</b> pour filtrer "
             "par cours et cocher au fur et à mesure.")
    L.append("")
    lignes = []
    for e in tous:
        titre = e["titre"] + (" ⚠️" if e.get("a_confirmer") else "")
        lignes.append([pastille(e["reste"]), jour_court(d(e["date"])),
                       "%s %s" % (EMOJI[e["cours"]], data["cours"][e["cours"]]["nom"]),
                       titre, poids_txt(e), carte.jx(e["reste"])])
    L.append(table(["", "Date", "Cours", "Évaluation", "Poids", "Compte à rebours"], lignes))
    L.append("")
    L.append("> ⚠️ = date ou pondération encore à confirmer auprès du prof. Être prêt une "
             "semaine trop tôt ne coûte rien ; l'inverse, oui.")
    L.append("")

    # ---- lectures
    futures = [l for l in data["lectures"] if d(l["pour"]) >= jour]
    if futures:
        L.append("---")
        L.append("")
        L.append("## 📖 Mes lectures")
        L.append("")
        L.append(table(["Pour le", "Cours", "À lire"],
                       [[jour_court(d(l["pour"])),
                         "%s %s" % (EMOJI[l["cours"]], data["cours"][l["cours"]]["nom"]),
                         l["quoi"]] for l in sorted(futures, key=lambda x: x["pour"])]))
        L.append("")

    # ---- semaines rouges
    L.append("---")
    L.append("")
    L.append("## 🔴 Mes semaines rouges")
    L.append("")
    L.append("> Toute semaine où il se joue <b>30 % ou plus</b> de points, tous cours "
             "confondus. C'est là que se gagne ou se perd la session.")
    L.append("")
    L.append(table(["Semaine", "Dates", "Ce qui tombe", "Poids total", "Statut"],
                   semaines_rouges(data, jour)))
    L.append("")

    # ---- semaine type
    L.append("---")
    L.append("")
    L.append("## 🗓️ Ma semaine type")
    L.append("")
    lignes = []
    for b in data["blocs_travail"]:
        h1 = dt.datetime.strptime(b["debut"], "%H:%M")
        h2 = dt.datetime.strptime(b["fin"], "%H:%M")
        mins = int((h2 - h1).total_seconds() // 60)
        duree = "%d h%s" % (mins // 60, (" %02d" % (mins % 60)) if mins % 60 else "")
        gros = b["titre"].startswith("GROS BLOC") or "Lectures longues" in b["titre"]
        libelle = "".join(EMOJI[c] for c in b["focus"] if c in EMOJI) or "🔁"
        libelle += " " + b["titre"]
        quand = "%s %s – %s" % (JOURS_C[b["jour"] - 1], heure(b["debut"]), heure(b["fin"]))
        if gros:
            lignes.append(["<b>%s</b>" % quand, "<b>%s</b>" % duree, "<b>%s</b>" % libelle])
        else:
            lignes.append([quand, duree, libelle])
    L.append(table(["Quand", "Durée", "Ce que je fais"], lignes))
    L.append("")
    L.append("> ⚠️ Vendredi soir, samedi après-midi et dimanche matin restent <b>vides</b>. "
             "Ce n'est pas du temps perdu : c'est ce qui rend le reste tenable, semaine "
             "après semaine.")
    L.append("")

    # ---- méthodes
    L.append("---")
    L.append("")
    L.append("## 🧠 Mes méthodes, cours par cours")
    L.append("")
    for cle in sorted(data["cours"], key=lambda c: -data["cours"][c]["difficulte"]):
        c = data["cours"][cle]
        if cle not in METHODES:
            continue
        dur = " — <i>ma matière la plus difficile</i>" if c["difficulte"] >= 4 else ""
        L.append("### %s %s%s" % (EMOJI[cle], c["nom"], dur))
        L.append("")
        L.append(METHODES[cle])
        L.append("")

    # ---- avancement
    L.append("---")
    L.append("")
    L.append("## 📊 Mon avancement")
    L.append("")
    av = carte.avancement(data, jour)
    incertain = {}
    for e in a_verifier(data):
        incertain[e["cours"]] = incertain.get(e["cours"], 0) + e["poids"]
    lignes = []
    for cle, (nom, pct) in sorted(av.items(), key=lambda kv: -kv[1][1]):
        suffixe = " <i>(dont %d %% à confirmer)</i>" % incertain[cle] if cle in incertain else ""
        pleins = int(round(pct / 10.0))
        barre = "<code>%s%s</code>" % ("▰" * pleins, "▱" * (10 - pleins))
        lignes.append(["%s %s" % (EMOJI[cle], nom), "%d %%%s" % (pct, suffixe), barre])
    L.append(table(["Cours", "Part de la note déjà jouée", ""], lignes))
    L.append("")
    moyenne = sum(p for _, p in av.values()) / float(len(av))
    total_douteux = sum(incertain.values())
    L.append("> <b>%d %%</b> de la session est joué en moyenne, tous cours confondus."
             "%s" % (round(moyenne),
                     (" Mais <b>%d %%</b> de points restent au statut incertain tant que les "
                      "évaluations ci-dessus ne sont pas confirmées." % total_douteux)
                     if total_douteux else ""))
    L.append("")
    L.append("<i>Mis à jour le %s · source : </i><i><code>donnees-session.json</code></i>"
             "<i> · généré par </i><i><code>notion.py</code></i>" % jour_long(jour))

    return "\n".join(L)


METHODES = {
    "litt": "Annoter PENDANT la lecture, jamais après. Un carnet de citations classées par "
            "thème — c'est lui qui sauve quand le sujet tombe. Garder 10 minutes de relecture "
            "linguistique en fin de rédaction : la langue vaut 25 % de chaque dissertation.",
    "philo": "Droit aux notes de cours à TOUTES les évaluations : la vraie préparation, c'est "
             "de construire de bonnes notes, pas de mémoriser. Un tableau par penseur — thèse, "
             "critère du juste, objection, exemple. Lire les extraits AVANT le cours du "
             "vendredi. Chaque faute de français retranche 0,5 % de la note globale, "
             "jusqu'à 10 %.",
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


def semaines_rouges(data, jour, seuil=30):
    """Semaines de session où il se joue au moins `seuil` % de points."""
    paires = sorted(((int(n), d(x)) for n, x in data["session"]["semaines"].items()),
                    key=lambda p: p[1])
    lignes = []
    for i, (num, debut) in enumerate(paires):
        fin = (paires[i + 1][1] - dt.timedelta(days=1)) if i + 1 < len(paires) \
            else debut + dt.timedelta(days=13)
        dedans = [e for e in data["evaluations"] if debut <= d(e["date"]) <= fin and e["poids"]]
        total = sum(e["poids"] for e in dedans)
        if total < seuil:
            continue
        quoi = " · ".join("%s %s %s" % (EMOJI[e["cours"]], e["titre"], poids_txt(e)
                                        .replace("<b>", "").replace("</b>", ""))
                          for e in sorted(dedans, key=lambda e: -e["poids"]))
        statut = "✅ passée" if fin < jour else ("🔥 en cours" if debut <= jour <= fin
                                                 else "⏳ à venir")
        lignes.append(["<b>%d</b>" % num,
                       "%s – %s" % (jour_court(debut), jour_court(fin)),
                       quoi, "<b>%d %%</b>" % total, statut])
    return lignes


# --------------------------------------------------------------------------
def main():
    args = sys.argv[1:]
    coaching = ""
    if "--coaching" in args:
        i = args.index("--coaching")
        with open(args[i + 1], encoding="utf-8") as fh:
            coaching = fh.read()
        del args[i:i + 2]
    jour = d(args[0]) if args else dt.date.today()
    print(page(carte.charger(), jour, coaching))


if __name__ == "__main__":
    main()

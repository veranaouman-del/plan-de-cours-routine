# -*- coding: utf-8 -*-
"""Page Notion « Ma session » — Automne 2026.

Génère, à partir de donnees-session.json, le Markdown enrichi de la page Notion
« 🎓 Ma session — Automne 2026 ». Même source de vérité que carte.py : on édite
le JSON, jamais la page à la main.

    python3 notion.py                 -> la page d'aujourd'hui, sur la sortie standard
    python3 notion.py 2026-10-08      -> une date précise
    python3 notion.py 2026-10-08 x.md -> dans un fichier

Le texte produit est à passer tel quel à notion-update-page / replace_content.
"""
import os
import sys
import datetime as dt

import carte
from carte import (ABREV, JOURS, MOIS, avancement, blocs_du_jour, chantiers,
                   chantiers_tous, charger, cours_du_jour, d, en_semaine_etudes,
                   en_souffrance, etape, jx, semaine_de, taches_du_jour)

BASE = os.path.dirname(os.path.abspath(__file__))

EMOJI = {"devlog": "💻", "web": "🌐", "litt": "📕", "anglais": "🗣️", "philo": "⚖️"}

JOURS_COURTS = ["lun.", "mar.", "mer.", "jeu.", "ven.", "sam.", "dim."]

PASTILLE_TACHE = {"RETARD": "🔴", "REMISE": "🔴", "ADMIN": "🟠", "FINIR": "🟠",
                  "TEST BLANC": "🟠", "RELIRE": "🟠", "FICHES": "🔵",
                  "AVANCER": "🔵", "NOTES": "🔵", "LECTURE": "📖"}

METHODES = {
    "litt": "Annoter **pendant** la lecture, jamais après. Un carnet de citations classées par "
            "thème. Garder 10 minutes de relecture linguistique en fin de rédaction — la langue "
            "vaut **25 %** de chaque dissertation.",
    "philo": "Droit aux notes de cours à **toutes** les évaluations. La vraie préparation, c'est "
             "donc de **construire de bonnes notes**, pas de mémoriser. Un tableau par penseur : "
             "thèse, critère du juste, objection principale, exemple concret. C'est ce tableau "
             "qu'on apporte à l'examen.",
    "anglais": "Tout se joue en classe. Remplir le journal Odyssey **le jour même** (5 % "
               "garantis). Les évaluations orales valent **45 %** du cours : elles se préparent "
               "**à voix haute**, pas par écrit. Enregistrer deux minutes au téléphone et se "
               "réécouter.",
    "devlog": "Le code se retient par les doigts. Refaire les exercices dirigés **sans la "
              "correction**, puis comparer. S'entraîner à écrire du code **sur papier** — c'est "
              "ce qui est demandé à l'examen.",
    "web": "Chaque TP s'appuie sur le précédent. Un TP bâclé se paie deux fois. Après chaque "
           "remise, noter en trois lignes **ce qui a bloqué** : c'est exactement ce qui tombera "
           "aux évaluations.",
}


# --------------------------------------------------------------------------
def libelle(data, cle):
    return "%s %s" % (EMOJI.get(cle, "•"), data["cours"][cle]["nom"])


def court_jour(j):
    jour = "1er" if j.day == 1 else str(j.day)
    return "%s %s %s" % (JOURS_COURTS[j.weekday()], jour, ABREV[j.month - 1])


def poids_fmt(poids):
    if not poids:
        return "formatif"
    return "**%d %%**" % poids if poids >= 20 else "%d %%" % poids


def table(entetes, lignes):
    out = ['<table header-row="true">', "<tr>"]
    out += ["<td>%s</td>" % e for e in entetes]
    out.append("</tr>")
    for ligne in lignes:
        out.append("<tr>")
        out += ["<td>%s</td>" % c for c in ligne]
        out.append("</tr>")
    out.append("</table>")
    return "\n".join(out)


def jours_restants_semaine(data, jour, n=7):
    """Les n prochains jours : cours, blocs, et ce qu'on y travaille."""
    lignes = []
    for i in range(n):
        j = jour + dt.timedelta(days=i)
        etiquette = "**%s**" % court_jour(j)
        if i == 0:
            etiquette += " ← *aujourd'hui*"

        gauche = []
        if en_semaine_etudes(data, j):
            gauche.append("*semaine d'études*")
        for c in cours_du_jour(data, j):
            gauche.append("%s %s" % (EMOJI[c["cours"]], data["cours"][c["cours"]]["court"]))
        for b in blocs_du_jour(data, j):
            gauche.append("%s – %s" % (b["debut"].replace(":", " h "), b["fin"].replace(":", " h ")))

        du_jour = [e for e in chantiers_tous(data, j) if e["reste"] == 0]
        if du_jour:
            droite = " · ".join("🔥 **%s %s**" % (EMOJI[e["cours"]], e["titre"]) for e in du_jour)
        else:
            # Ce qu'on travaille ce jour-là : les chantiers ouverts à cette date,
            # filtrés sur les cours auxquels les blocs du jour sont consacrés.
            ouverts = chantiers(data, j)
            focus = set()
            for bl in blocs_du_jour(data, j):
                focus.update(bl["focus"])
            cibles = [e for e in ouverts if e["cours"] in focus] or ouverts
            droite = " · ".join("%s %s — *%s*" % (EMOJI[e["cours"]], e["titre"], etape(e).lower())
                                for e in cibles[:2]) or "—"

        lignes.append([etiquette, "<br>".join(gauche) or "—", droite])
    return lignes


def semaines_rouges(data, seuil=30):
    """Toute semaine de session où il se joue seuil % ou plus, tous cours confondus."""
    paires = sorted(((int(n), d(debut)) for n, debut in data["session"]["semaines"].items()),
                    key=lambda p: p[1])
    lignes = []
    for num, debut in paires:
        fin = debut + dt.timedelta(days=6)
        dedans = [e for e in data["evaluations"] if debut <= d(e["date"]) <= fin and e["poids"]]
        total = sum(e["poids"] for e in dedans)
        if total < seuil:
            continue
        dedans.sort(key=lambda e: -e["poids"])
        quoi = " · ".join("%s %s %d %%" % (EMOJI[e["cours"]], e["titre"], e["poids"])
                          for e in dedans)
        lignes.append((num, debut, fin, quoi, total))
    return lignes


# --------------------------------------------------------------------------
def page(data, jour):
    sem = semaine_de(data, jour)
    actifs = chantiers(data, jour)
    souffrance = en_souffrance(data, jour)
    a, b = data["session"]["semaine_etudes"]
    L = []

    L.append("# 🎓 Ma session — Automne 2026")
    L.append("> Cégep de Granby · Techniques de l'informatique (420.B0) · 24 août → 11 déc")
    L.append("> **Semaine %s sur 15** · Semaine d'études : %s au %s"
             % (sem or "—", court_jour(d(a)), court_jour(d(b))))
    L.append("---")

    # ---- aujourd'hui -----------------------------------------------------
    L.append("## 📍 Aujourd'hui — %s %d %s" % (JOURS[jour.weekday()], jour.day, MOIS[jour.month - 1]))
    for c in cours_du_jour(data, jour):
        L.append("- %s · **%s – %s** · local %s"
                 % (libelle(data, c["cours"]), c["debut"].replace(":", " h "),
                    c["fin"].replace(":", " h "), c["local"]))
    for bl in blocs_du_jour(data, jour):
        L.append("- 🎯 **%s** · %s – %s" % (bl["titre"], bl["debut"].replace(":", " h "),
                                            bl["fin"].replace(":", " h ")))
    if not cours_du_jour(data, jour) and not blocs_du_jour(data, jour):
        L.append("- 🌿 Aucun cours, aucun bloc — journée libre assumée.")
    if actifs:
        p = actifs[0]
        L.append("> 🔥 **Priorité du jour :** %s — %s (%d %%), **%s**."
                 % (libelle(data, p["cours"]), p["titre"], p["poids"], jx(p["reste"])))
    L.append("---")

    # ---- remises en souffrance ------------------------------------------
    if souffrance:
        total = sum(e["poids"] for e in souffrance)
        L.append("## 🔴 À confirmer — remises passées jamais cochées")
        L.append("> Ces remises sont passées et toujours marquées « non faites ». Tant qu'elles "
                 "y sont, mon avancement est une hypothèse, pas un fait.")
        L.append(table(["Évaluation", "Cours", "Poids", "Était dû le", "Retard"],
                       [[e["titre"], libelle(data, e["cours"]), poids_fmt(e["poids"]),
                         court_jour(d(e["date"])), "%d jours" % e["retard"]]
                        for e in souffrance]))
        for e in souffrance:
            if e.get("a_confirmer"):
                L.append("- ⚠️ **%s** — %s" % (e["titre"], e["a_confirmer"]))
        L.append("- [ ] Cocher celles qui sont remises → l'avancement redevient exact")
        L.append("- [ ] Écrire au prof **le jour même** pour celles qui ne le sont pas — "
                 "**%d %%** de points au statut incertain" % total)
        L.append("---")

    # ---- à faire ---------------------------------------------------------
    L.append("## ✅ À faire aujourd'hui")
    for tag, t in taches_du_jour(data, jour, actifs):
        L.append("- [ ] %s **%s** — %s" % (PASTILLE_TACHE.get(tag, "🔵"), tag, t))
    L.append("---")

    # ---- les 7 prochains jours ------------------------------------------
    L.append("## 🗓️ Les 7 prochains jours")
    L.append(table(["Jour", "Cours et blocs", "Ce que je fais"],
                   jours_restants_semaine(data, jour)))
    L.append("---")

    # ---- admin -----------------------------------------------------------
    L.append("## 📌 À régler tout de suite")
    for t in data["taches_admin"]:
        if t["pour"] == "recurrent":
            L.append("- [ ] 🔁 %s" % t["quoi"])
            continue
        reste = (d(t["pour"]) - jour).days
        if reste < 0:
            L.append("- [ ] 🔴 **%s** — *%d jours de retard*" % (t["quoi"], -reste))
        elif reste <= 7:
            L.append("- [ ] 🟠 **%s** — *%s*" % (t["quoi"], jx(reste).lower()))
        else:
            L.append("- [ ] 🔵 %s — *pour le %s*" % (t["quoi"], court_jour(d(t["pour"]))))
    L.append("---")

    # ---- échéances -------------------------------------------------------
    L.append("## 📅 Toutes mes échéances à venir")
    L.append("> 💡 Sélectionne ce tableau → **Transformer en base de données** pour filtrer par "
             "cours et cocher au fur et à mesure.")
    lignes = []
    for e in chantiers_tous(data, jour):
        pastille = "🔴" if e["reste"] <= 4 else ("🟠" if e["reste"] <= 12 else "🔵")
        lignes.append([pastille, court_jour(d(e["date"])), libelle(data, e["cours"]),
                       e["titre"], poids_fmt(e["poids"]), jx(e["reste"])])
    L.append(table(["", "Date", "Cours", "Évaluation", "Poids", "Compte à rebours"], lignes))
    L.append("---")

    # ---- lectures --------------------------------------------------------
    futures = sorted((l for l in data["lectures"] if d(l["pour"]) >= jour),
                     key=lambda l: l["pour"])
    if futures:
        L.append("## 📖 Mes lectures")
        L.append(table(["Pour le", "Cours", "À lire"],
                       [[court_jour(d(l["pour"])), libelle(data, l["cours"]), l["quoi"]]
                        for l in futures]))
        L.append("---")

    # ---- semaines rouges -------------------------------------------------
    L.append("## 🔴 Mes semaines rouges")
    L.append("> Toute semaine de session où il se joue **30 % ou plus** de points, tous cours "
             "confondus. C'est là que se gagne ou se perd la session.")
    lignes = []
    for num, debut, fin, quoi, total in semaines_rouges(data):
        etiquette = "**%d**" % num
        if debut <= jour <= fin:
            etiquette += " ← *ici*"
        lignes.append([etiquette, "%s – %s" % (court_jour(debut), court_jour(fin)),
                       quoi, "**%d %%**" % total])
    L.append(table(["Semaine", "Dates", "Ce qui tombe", "Poids total"], lignes))
    L.append("---")

    # ---- semaine type ----------------------------------------------------
    L.append("## 🗓️ Ma semaine type")
    lignes = []
    for bl in sorted(data["blocs_travail"], key=lambda b: (b["jour"], b["debut"])):
        h1 = dt.datetime.strptime(bl["debut"], "%H:%M")
        h2 = dt.datetime.strptime(bl["fin"], "%H:%M")
        minutes = int((h2 - h1).total_seconds() // 60)
        duree = "%d h" % (minutes // 60) + (" %02d" % (minutes % 60) if minutes % 60 else "")
        quand = "%s %s – %s" % (JOURS[bl["jour"] - 1].capitalize(),
                                bl["debut"].replace(":", " h "), bl["fin"].replace(":", " h "))
        emos = "".join(EMOJI.get(c, "🔁") for c in bl["focus"])
        gros = minutes >= 180
        lignes.append(["**%s**" % quand if gros else quand,
                       "**%s**" % duree if gros else duree,
                       "**%s %s**" % (emos, bl["titre"]) if gros else "%s %s" % (emos, bl["titre"])])
    L.append(table(["Quand", "Durée", "Ce que je fais"], lignes))
    L.append("> ⚠️ Vendredi soir, samedi après-midi et dimanche matin restent **vides**. Ce n'est "
             "pas du temps perdu : c'est ce qui rend le reste tenable semaine après semaine.")
    L.append("---")

    # ---- méthodes --------------------------------------------------------
    L.append("## 🧠 Mes méthodes, cours par cours")
    dur = max(c["difficulte"] for c in data["cours"].values())
    for cle, c in sorted(data["cours"].items(), key=lambda kv: -kv[1]["difficulte"]):
        titre = "### %s" % libelle(data, cle)
        if c["difficulte"] == dur:
            titre += " — *ma matière la plus difficile*"
        L.append(titre)
        L.append(METHODES.get(cle, ""))
    L.append("---")

    # ---- avancement ------------------------------------------------------
    L.append("## 📊 Mon avancement")
    av = sorted(avancement(data, jour).items(), key=lambda kv: -kv[1][1])
    lignes = []
    for cle, (nom, pct) in av:
        plein = int(round(pct / 10.0))
        lignes.append(["%s %s" % (EMOJI.get(cle, "•"), nom), "%d %%" % pct,
                       "`%s`" % ("▰" * plein + "▱" * (10 - plein))])
    L.append(table(["Cours", "Part de la note déjà jouée", ""], lignes))
    moyenne = sum(p for _, (_, p) in av) / float(len(av))
    L.append("> **%d %%** de la session est joué en moyenne, tous cours confondus." % round(moyenne))
    L.append("---")

    L.append("*Mis à jour automatiquement le %s %d %s · source : **`donnees-session.json`** · "
             "généré par **`notion.py`***"
             % (JOURS[jour.weekday()], jour.day, MOIS[jour.month - 1]))
    return "\n".join(L)


def main():
    args = sys.argv[1:]
    jour = d(args[0]) if args else dt.date.today()
    texte = page(charger(), jour)
    if len(args) > 1:
        with open(args[1], "w", encoding="utf-8") as fh:
            fh.write(texte)
        print(args[1])
    else:
        print(texte)


if __name__ == "__main__":
    main()

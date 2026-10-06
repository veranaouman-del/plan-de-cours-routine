# -*- coding: utf-8 -*-
"""Tableau de bord Notion — Automne 2026.

Fabrique le Markdown enrichi de la page « Ma session — Automne 2026 » à partir de
donnees-session.json. La sortie se colle telle quelle dans notion-update-page
(commande replace_content).

    python3 notion.py                 -> aujourd'hui
    python3 notion.py 2026-10-06      -> une date précise
    python3 notion.py 2026-10-06 /tmp/page.md

Comme carte.py, rien n'est codé en dur : une échéance qui bouge se change dans le JSON.
"""
import io
import os
import sys
import datetime as dt

import carte

BASE = os.path.dirname(os.path.abspath(__file__))

EMOJI = {"devlog": "💻", "web": "🌐", "litt": "📕", "anglais": "🗣️", "philo": "⚖️"}
JOURS_COURTS = ["lun.", "mar.", "mer.", "jeu.", "ven.", "sam.", "dim."]
PASTILLE_ETAPE = {"RETARD": "🔴", "REMISE": "🔴", "FINIR": "🟠", "TEST BLANC": "🟠",
                  "ADMIN": "🟠", "RELIRE": "🟠"}


def d(s):
    return carte.d(s)


def nom(data, cle):
    return "%s %s" % (EMOJI.get(cle, "•"), data["cours"][cle]["nom"])


def long_date(j):
    """« mar. 6 oct. », avec le 1er qui s'écrit comme il se prononce."""
    jour = "1er" if j.day == 1 else str(j.day)
    return "%s %s %s" % (JOURS_COURTS[j.weekday()], jour, carte.ABREV[j.month - 1])


def gras_si_lourd(poids):
    if not poids:
        return "formatif"
    return "**%d %%**" % poids if poids >= 20 else "%d %%" % poids


def tableau(entetes, lignes):
    out = ['<table header-row="true">', "<tr>"]
    out += ["<td>%s</td>" % h for h in entetes]
    out.append("</tr>")
    for l in lignes:
        out.append("<tr>")
        out += ["<td>%s</td>" % c for c in l]
        out.append("</tr>")
    out.append("</table>")
    return "\n".join(out)


# --------------------------------------------------------------------------
def semaines_rouges(data, jour):
    """Toute semaine de session où il se joue 30 % ou plus, tous cours confondus."""
    sem_actuelle = carte.semaine_de(data, jour)
    bornes = sorted(((int(n), d(x)) for n, x in data["session"]["semaines"].items()),
                    key=lambda p: p[1])
    lignes = []
    for num, debut in bornes:
        fin = debut + dt.timedelta(days=6)
        dedans = [e for e in data["evaluations"] if debut <= d(e["date"]) <= fin]
        total = sum(e["poids"] for e in dedans)
        if total < 30:
            continue
        quoi = " · ".join("%s %s %s" % (EMOJI.get(e["cours"], ""), e["titre"],
                                        ("%d %%" % e["poids"]) if e["poids"] else "formatif")
                          for e in sorted(dedans, key=lambda e: -e["poids"]))
        etiquette = "**%d**" % num + (" ← *ici*" if num == sem_actuelle else "")
        lignes.append([etiquette, "%s – %s" % (long_date(debut).replace(".", "."), long_date(fin)),
                       quoi, "**%d %%**" % total])
    return lignes


def sept_jours(data, jour):
    lignes = []
    for i in range(7):
        j = jour + dt.timedelta(days=i)
        actifs = carte.chantiers(data, j)
        cols = []
        for c in carte.cours_du_jour(data, j):
            cols.append("%s %s" % (EMOJI.get(c["cours"], ""), data["cours"][c["cours"]]["court"]))
        for b in carte.blocs_du_jour(data, j):
            cols.append("%s – %s" % (b["debut"].replace(":", " h "), b["fin"].replace(":", " h ")))
        tombe = [e for e in actifs if e["reste"] == 0]
        # ce qui tombe ce jour-la est deja annonce en 🔥 : le repeter en tache fait doublon
        titres_du_jour = {e["titre"] for e in tombe}
        quoi = []
        for tag, t in carte.taches_du_jour(data, j, actifs)[:3]:
            if tag in ("RETARD", "ADMIN", "LECTURE"):
                continue
            if any(titre in t for titre in titres_du_jour):
                continue
            quoi.append("%s *(%s)*" % (t, tag.lower()))
        for e in tombe:
            quoi.insert(0, "🔥 **%s %s**" % (EMOJI.get(e["cours"], ""), e["titre"]))
        etiquette = "**%s**" % long_date(j) + (" ← *aujourd'hui*" if i == 0 else "")
        lignes.append([etiquette, "<br>".join(cols) or "—", " · ".join(quoi) or "—"])
    return lignes


def barre(pct):
    pleins = int(round(pct / 10.0))
    return "`%s%s`" % ("▰" * pleins, "▱" * (10 - pleins))


# --------------------------------------------------------------------------
def page(data, jour):
    sem = carte.semaine_de(data, jour)
    actifs = carte.chantiers(data, jour)
    dep = carte.depassees(data, jour)
    L = []

    L.append("# 🎓 Ma session — Automne 2026")
    L.append("> Cégep de Granby · Techniques de l'informatique (420.B0) · 24 août → 11 déc")
    a, b = data["session"]["semaine_etudes"]
    L.append("> **Semaine %s sur 15** · Semaine d'études : %s au %s"
             % (sem or "—", carte.court(d(a)), carte.court(d(b))))
    L.append("---")

    # aujourd'hui
    L.append("## 📍 Aujourd'hui — %s %d %s"
             % (carte.JOURS[jour.weekday()], jour.day, carte.MOIS[jour.month - 1]))
    cj = carte.cours_du_jour(data, jour)
    if cj:
        for c in cj:
            L.append("- %s · **%s – %s** · local %s"
                     % (nom(data, c["cours"]), c["debut"].replace(":", " h "),
                        c["fin"].replace(":", " h "), c["local"]))
    else:
        L.append("- *Aucun cours aujourd'hui.*")
    for bl in carte.blocs_du_jour(data, jour):
        L.append("- 🎯 **%s** · %s – %s" % (bl["titre"], bl["debut"].replace(":", " h "),
                                            bl["fin"].replace(":", " h ")))
    if actifs:
        p = actifs[0]
        L.append("> 🔥 **Priorité du jour :** %s — %s (%d %%), **%s**."
                 % (nom(data, p["cours"]), p["titre"], p["poids"], carte.jx(p["reste"])))
    note = carte.bloc_detourne(data, jour, actifs)
    if note:
        L.append("> ⚠️ **%s**" % note)
    L.append("---")

    # à faire
    L.append("## ✅ À faire aujourd'hui")
    for tag, t in carte.taches_du_jour(data, jour, actifs):
        L.append("- [ ] %s **%s** — %s" % (PASTILLE_ETAPE.get(tag, "🔵"), tag, t))
    L.append("---")

    # 7 jours
    L.append("## 🗓️ Les 7 prochains jours")
    L.append(tableau(["Jour", "Cours et blocs", "Ce que je fais"], sept_jours(data, jour)))
    L.append("---")

    # remises dépassées
    if dep:
        L.append("## 🔴 À confirmer — remises passées jamais cochées")
        L.append("> Ces remises sont passées et toujours marquées « non faites » dans "
                 "`donnees-session.json`. Tant qu'elles y sont, mon avancement est une "
                 "hypothèse, pas un fait.")
        L.append(tableau(["Évaluation", "Cours", "Poids", "Était dû le", "Retard"],
                         [[e["titre"], nom(data, e["cours"]), gras_si_lourd(e["poids"]),
                           long_date(d(e["date"])), "%d jours" % e["depuis"]] for e in dep]))
        total = sum(e["poids"] for e in dep)
        L.append("- [ ] Cocher celles qui sont remises → l'avancement redevient exact")
        L.append("- [ ] Écrire au prof **le jour même** pour celles qui ne le sont pas — "
                 "**%d %%** de points au statut incertain" % total)
        L.append("---")

    # admin
    L.append("## 📌 À régler tout de suite")
    for t in data["taches_admin"]:
        if t["pour"] == "recurrent":
            L.append("- [ ] 🔁 %s" % t["quoi"])
            continue
        ecart = (jour - d(t["pour"])).days
        if ecart > 0:
            L.append("- [ ] 🔴 **%s** — *%d jours de retard*" % (t["quoi"], ecart))
        else:
            L.append("- [ ] 🔵 %s — *pour le %s*" % (t["quoi"], long_date(d(t["pour"]))))
    L.append("---")

    # échéances
    L.append("## 📅 Toutes mes échéances à venir")
    L.append("> 💡 Sélectionne ce tableau → **Transformer en base de données** pour filtrer "
             "par cours et cocher au fur et à mesure.")
    lignes = []
    for e in carte.chantiers_tous(data, jour):
        pastille = "🔴" if e["reste"] <= 4 else ("🟠" if e["reste"] <= 12 else "🔵")
        lignes.append([pastille, long_date(d(e["date"])), nom(data, e["cours"]), e["titre"],
                       gras_si_lourd(e["poids"]), carte.jx(e["reste"])])
    L.append(tableau(["", "Date", "Cours", "Évaluation", "Poids", "Compte à rebours"], lignes))
    L.append("---")

    # lectures
    a_lire = [l for l in data["lectures"] if d(l["pour"]) >= jour]
    if a_lire:
        L.append("## 📖 Mes lectures")
        L.append(tableau(["Pour le", "Cours", "À lire"],
                         [[long_date(d(l["pour"])), nom(data, l["cours"]), l["quoi"]]
                          for l in sorted(a_lire, key=lambda l: l["pour"])]))
        L.append("---")

    # semaines rouges
    L.append("## 🔴 Mes semaines rouges")
    L.append("> Toute semaine de session où il se joue **30 % ou plus** de points, tous cours "
             "confondus. C'est là que se gagne ou se perd la session.")
    L.append(tableau(["Semaine", "Dates", "Ce qui tombe", "Poids total"],
                     semaines_rouges(data, jour)))
    L.append("---")

    # semaine type
    L.append("## 🗓️ Ma semaine type")
    lignes = []
    for bl in data["blocs_travail"]:
        h1 = dt.datetime.strptime(bl["debut"], "%H:%M")
        h2 = dt.datetime.strptime(bl["fin"], "%H:%M")
        mins = int((h2 - h1).total_seconds() // 60)
        duree = "%d h%s" % (mins // 60, (" %02d" % (mins % 60)) if mins % 60 else "")
        quand = "%s %s – %s" % (carte.JOURS[bl["jour"] - 1].capitalize(),
                                bl["debut"].replace(":", " h "), bl["fin"].replace(":", " h "))
        pictos = "".join(EMOJI.get(f, "🔁") for f in bl["focus"])
        gros = mins >= 180
        envelopper = (lambda s: "**%s**" % s) if gros else (lambda s: s)
        lignes.append([envelopper(quand), envelopper(duree),
                       envelopper("%s %s" % (pictos, bl["titre"]))])
    L.append(tableau(["Quand", "Durée", "Ce que je fais"], lignes))
    L.append("> ⚠️ Vendredi soir, samedi après-midi et dimanche matin restent **vides**. "
             "Ce n'est pas du temps perdu : c'est ce qui rend le reste tenable semaine "
             "après semaine.")
    L.append("---")

    # méthodes
    L.append("## 🧠 Mes méthodes, cours par cours")
    for cle in sorted(data["cours"], key=lambda c: -data["cours"][c]["difficulte"]):
        c = data["cours"][cle]
        dur = " — *ma matière la plus difficile*" if c["difficulte"] >= 4 else ""
        L.append("### %s %s%s" % (EMOJI.get(cle, ""), c["nom"], dur))
        L.append(METHODES[cle])
    L.append("---")

    # avancement
    L.append("## 📊 Mon avancement")
    av = sorted(carte.avancement(data, jour).items(), key=lambda kv: -kv[1][1])
    L.append(tableau(["Cours", "Part de la note déjà jouée", ""],
                     [[nom(data, cle), "%d %%" % pct, barre(pct)] for cle, (n, pct) in av]))
    moyenne = sum(pct for _, (_, pct) in av) / len(av)
    L.append("> **%d %%** de la session est joué en moyenne, tous cours confondus." % moyenne)
    L.append("---")
    L.append("*Mis à jour automatiquement le %s %d %s · source : **`donnees-session.json`** "
             "· généré par **`notion.py`***"
             % (carte.JOURS[jour.weekday()], jour.day, carte.MOIS[jour.month - 1]))
    return "\n".join(L)


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
           "à l'Évaluation #1.",
}


def main():
    args = sys.argv[1:]
    jour = d(args[0]) if args else dt.date.today()
    data = carte.charger()
    sortie = page(data, jour)
    if len(args) > 1:
        io.open(args[1], "w", encoding="utf-8").write(sortie)
        print(args[1])
    else:
        print(sortie)


if __name__ == "__main__":
    main()

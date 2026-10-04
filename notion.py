# -*- coding: utf-8 -*-
"""Page Notion « Ma session » — Automne 2026.

Reconstruit le tableau de bord Notion à partir de donnees-session.json, en
réutilisant le moteur de carte.py. Rien n'est codé en dur ici non plus :
une échéance qui bouge se change dans le JSON, et la page suit.

    python3 notion.py              -> le Markdown de la page, sur la sortie standard
    python3 notion.py 2026-10-07   -> la page telle qu'elle sera ce jour-là

Le Markdown produit se colle tel quel dans la page Notion
« Ma session — Automne 2026 » (replace_content).
"""
import sys
import datetime as dt

import carte

JOURS_COURTS = ["lun.", "mar.", "mer.", "jeu.", "ven.", "sam.", "dim."]

# Les méthodes ne viennent pas du JSON : ce sont des conseils, pas des données.
METHODES = [
    ("litt", "Annoter **pendant** la lecture, jamais après. Un carnet de citations classées "
             "par thème. Garder 10 minutes de relecture linguistique en fin de rédaction — "
             "la langue vaut **25 %** de chaque dissertation."),
    ("philo", "Droit aux notes de cours à **toutes** les évaluations. La vraie préparation, "
              "c'est donc de **construire de bonnes notes**, pas de mémoriser. Un tableau par "
              "penseur : thèse, critère du juste, objection principale, exemple concret. "
              "C'est ce tableau qu'on apporte à l'examen."),
    ("anglais", "Tout se joue en classe. Remplir le journal Odyssey **le jour même** "
                "(5 % garantis). Les évaluations orales valent **45 %** du cours : elles se "
                "préparent **à voix haute**, pas par écrit. Enregistrer deux minutes au "
                "téléphone et se réécouter."),
    ("devlog", "Le code se retient par les doigts. Refaire les exercices dirigés **sans la "
               "correction**, puis comparer. S'entraîner à écrire du code **sur papier** — "
               "c'est ce qui est demandé à l'examen."),
    ("web", "Chaque TP s'appuie sur le précédent. Un TP bâclé se paie deux fois. Après chaque "
            "remise, noter en trois lignes **ce qui a bloqué** : c'est exactement ce qui "
            "tombera à l'Évaluation #1."),
]

PASTILLES = {"RETARD": "🔴", "ADMIN": "🟠", "REMISE": "🔴", "LECTURE": "📖"}


# --------------------------------------------------------------------------
# Mise en forme
# --------------------------------------------------------------------------
def long(j):
    return "%s %d %s" % (carte.JOURS[j.weekday()], j.day, carte.MOIS[j.month - 1])


def court(j):
    jour = "1er" if j.day == 1 else str(j.day)
    return "%s %s %s" % (JOURS_COURTS[j.weekday()], jour, carte.ABREV[j.month - 1])


def gras_si_lourd(poids):
    if not poids:
        return "formatif"
    return "**%d %%**" % poids if poids >= 20 else "%d %%" % poids


def nom(data, cle):
    c = data["cours"][cle]
    return "%s %s" % (c["emoji"], c["nom"])


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


# --------------------------------------------------------------------------
# Sections
# --------------------------------------------------------------------------
def section_aujourdhui(data, jour, actifs, L):
    L.append("## 📍 Aujourd'hui — %s" % long(jour))
    cj = carte.cours_du_jour(data, jour)
    if cj:
        for c in cj:
            L.append("- **%s** · %s – %s · %s"
                     % (nom(data, c["cours"]), c["debut"].replace(":", " h "),
                        c["fin"].replace(":", " h "), c["local"]))
    else:
        L.append("- *Aucun cours aujourd'hui*")
    for b in carte.blocs_du_jour(data, jour):
        L.append("- 🎯 **%s** · %s – %s"
                 % (b["titre"], b["debut"].replace(":", " h "), b["fin"].replace(":", " h ")))
    if actifs:
        p = actifs[0]
        L.append("> 🔥 **Priorité du jour :** %s — %s (%d %%), **%s**."
                 % (nom(data, p["cours"]), p["titre"], p["poids"], carte.jx(p["reste"])))


def section_a_faire(data, jour, actifs, L):
    L.append("## ✅ À faire aujourd'hui")
    for tag, t in carte.taches_du_jour(data, jour, actifs):
        L.append("- [ ] %s **%s** — %s" % (PASTILLES.get(tag, "🔵"), tag, t))


def section_sept_jours(data, jour, L):
    L.append("## 🗓️ Les 7 prochains jours")
    lignes = []
    for i in range(7):
        j = jour + dt.timedelta(days=i)
        actifs = carte.chantiers(data, j)
        colonne = [data["cours"][c["cours"]]["emoji"] + " " + data["cours"][c["cours"]]["court"]
                   for c in carte.cours_du_jour(data, j)]
        colonne += ["%s – %s" % (b["debut"].replace(":", " h "), b["fin"].replace(":", " h "))
                    for b in carte.blocs_du_jour(data, j)]
        du_jour = [e for e in actifs if e["reste"] == 0]
        if du_jour:
            quoi = " · ".join("🔥 **%s — %s**" % (nom(data, e["cours"]), e["titre"])
                              for e in du_jour)
        elif actifs:
            e = actifs[0]
            quoi = "%s — %s *(%s)*" % (nom(data, e["cours"]), e["titre"],
                                       carte.etape(e).lower())
        else:
            quoi = "*Rien d'imposé*"
        etiquette = "**%s**" % court(j) + (" ← *aujourd'hui*" if i == 0 else "")
        lignes.append([etiquette, "<br>".join(colonne) or "—", quoi])
    L.append(table(["Jour", "Cours et blocs", "Ce que je fais"], lignes))


def section_a_confirmer(data, jour, L):
    """Les remises passées jamais cochées. Une remise manquée vaut zéro : tant qu'elles
    traînent ici, l'avancement affiché est une hypothèse, pas un fait."""
    passees = [e for e in data["evaluations"]
               if not e.get("fait") and carte.d(e["date"]) < jour]
    if not passees:
        return
    passees.sort(key=lambda e: e["date"], reverse=True)
    L.append("## 🔴 À confirmer — remises passées jamais cochées")
    L.append("> Ces évaluations sont passées et toujours marquées « non faites » dans "
             "`donnees-session.json`. Tant qu'elles y sont, mon avancement est une "
             "hypothèse, pas un fait.")
    lignes = []
    for e in passees:
        retard = (jour - carte.d(e["date"])).days
        lignes.append([e["titre"], nom(data, e["cours"]), gras_si_lourd(e["poids"]),
                       court(carte.d(e["date"])),
                       "%d jour%s" % (retard, "s" if retard > 1 else "")])
    L.append(table(["Évaluation", "Cours", "Poids", "Était dû le", "Retard"], lignes))
    L.append("- [ ] Cocher celles qui sont remises → l'avancement redevient exact")
    L.append("- [ ] Écrire au prof **le jour même** pour celles qui ne le sont pas")


def section_admin(data, jour, L):
    L.append("## 📌 À régler tout de suite")
    for t in data["taches_admin"]:
        if t["pour"] == "recurrent":
            L.append("- [ ] 🔁 %s" % t["quoi"])
            continue
        reste = (carte.d(t["pour"]) - jour).days
        if reste < 0:
            L.append("- [ ] 🔴 **%s** — *%d jours de retard*" % (t["quoi"], -reste))
        elif reste <= 14:
            L.append("- [ ] 🟠 **%s** — *%s*" % (t["quoi"], carte.jx(reste)))


def section_echeances(data, jour, L):
    L.append("## 📅 Toutes mes échéances à venir")
    L.append("> 💡 Sélectionne ce tableau → **Transformer en base de données** pour filtrer "
             "par cours et cocher au fur et à mesure.")
    lignes = []
    for e in carte.chantiers_tous(data, jour):
        pastille = "🔴" if e["reste"] <= 4 else ("🟠" if e["reste"] <= 12 else "🔵")
        lignes.append([pastille, court(carte.d(e["date"])), nom(data, e["cours"]),
                       e["titre"], gras_si_lourd(e["poids"]), carte.jx(e["reste"])])
    L.append(table(["", "Date", "Cours", "Évaluation", "Poids", "Compte à rebours"], lignes))


def section_lectures(data, jour, L):
    a_venir = sorted((l for l in data["lectures"] if carte.d(l["pour"]) >= jour),
                     key=lambda l: l["pour"])
    if not a_venir:
        return
    L.append("## 📖 Mes lectures")
    L.append(table(["Pour le", "Cours", "À lire"],
                   [[court(carte.d(l["pour"])), nom(data, l["cours"]), l["quoi"]]
                    for l in a_venir]))


def section_semaines_rouges(data, jour, L):
    """Une semaine rouge n'est pas décrétée : c'est toute semaine où il se joue 30 % ou plus."""
    L.append("## 🔴 Mes semaines rouges")
    L.append("> Toute semaine de session où il se joue **30 % ou plus** de points, tous cours "
             "confondus. C'est là que se gagne ou se perd la session.")
    semaines = sorted(((int(n), carte.d(deb)) for n, deb in data["session"]["semaines"].items()),
                      key=lambda p: p[0])
    lignes = []
    for num, debut in semaines:
        fin = debut + dt.timedelta(days=6)
        dedans = [e for e in data["evaluations"] if debut <= carte.d(e["date"]) <= fin]
        total = sum(e["poids"] for e in dedans)
        if total < 30:
            continue
        dedans.sort(key=lambda e: -e["poids"])
        quoi = " · ".join("%s %s %d %%" % (data["cours"][e["cours"]]["emoji"], e["titre"],
                                           e["poids"]) for e in dedans)
        ici = " ← *ici*" if debut <= jour <= fin else ""
        lignes.append(["**%d**%s" % (num, ici),
                       "%s – %s" % (carte.court(debut), carte.court(fin)),
                       quoi, "**%d %%**" % total])
    L.append(table(["Semaine", "Dates", "Ce qui tombe", "Poids total"], lignes))


def section_semaine_type(data, L):
    L.append("## 🗓️ Ma semaine type")
    lignes = []
    for b in sorted(data["blocs_travail"], key=lambda b: (b["jour"], b["debut"])):
        h1 = dt.datetime.strptime(b["debut"], "%H:%M")
        h2 = dt.datetime.strptime(b["fin"], "%H:%M")
        minutes = int((h2 - h1).total_seconds() // 60)
        duree = "%d h" % (minutes // 60) + (" %d" % (minutes % 60) if minutes % 60 else "")
        emojis = "".join(data["cours"][f]["emoji"] for f in b["focus"] if f in data["cours"])
        quand = "%s %s – %s" % (carte.JOURS[b["jour"] - 1].capitalize(),
                                b["debut"].replace(":", " h "), b["fin"].replace(":", " h "))
        gros = b["titre"].startswith("GROS BLOC") or b["focus"] == ["rattrapage"]
        fmt = (lambda s: "**%s**" % s) if gros else (lambda s: s)
        lignes.append([fmt(quand), fmt(duree), fmt("%s %s" % (emojis or "🔁", b["titre"]))])
    L.append(table(["Quand", "Durée", "Ce que je fais"], lignes))
    L.append("> ⚠️ Vendredi soir, samedi après-midi et dimanche matin restent **vides**. "
             "Ce n'est pas du temps perdu : c'est ce qui rend le reste tenable semaine "
             "après semaine.")


def section_methodes(data, L):
    L.append("## 🧠 Mes méthodes, cours par cours")
    dur = max(c["difficulte"] for c in data["cours"].values())
    for cle, texte in METHODES:
        suffixe = " — *ma matière la plus difficile*" if data["cours"][cle]["difficulte"] == dur else ""
        L.append("### %s%s" % (nom(data, cle), suffixe))
        L.append(texte)


def section_avancement(data, jour, L):
    L.append("## 📊 Mon avancement")
    parts = sorted(carte.avancement(data, jour).items(), key=lambda kv: -kv[1][1])
    L.append(table(["Cours", "Part de la note déjà jouée"],
                   [[nom(data, cle), "%d %%" % pct] for cle, (_, pct) in parts]))
    moyenne = sum(pct for _, (_, pct) in parts) / len(parts)
    L.append("> **%d %%** de la session est joué en moyenne, tous cours confondus." % moyenne)


# --------------------------------------------------------------------------
def page(data, jour):
    sem = carte.semaine_de(data, jour)
    L = ["# 🎓 Ma session — %s" % data["session"]["nom"]]
    L.append("> %s · 24 août → 11 décembre" % data["programme"])
    etat = ("**Semaine d'études** — aucun cours" if carte.en_semaine_etudes(data, jour)
            else "**Semaine %d sur 15**" % sem if sem else "Hors session")
    a, b = data["session"]["semaine_etudes"]
    L.append("> %s · Semaine d'études : %s au %s"
             % (etat, carte.court(carte.d(a)), carte.court(carte.d(b))))

    actifs = carte.chantiers(data, jour)
    for faire in (lambda: section_aujourdhui(data, jour, actifs, L),
                  lambda: section_a_faire(data, jour, actifs, L),
                  lambda: section_sept_jours(data, jour, L),
                  lambda: section_a_confirmer(data, jour, L),
                  lambda: section_admin(data, jour, L),
                  lambda: section_echeances(data, jour, L),
                  lambda: section_lectures(data, jour, L),
                  lambda: section_semaines_rouges(data, jour, L),
                  lambda: section_semaine_type(data, L),
                  lambda: section_methodes(data, L),
                  lambda: section_avancement(data, jour, L)):
        L.append("---")
        faire()

    L.append("---")
    L.append("*Mis à jour automatiquement le %s · source : **`donnees-session.json`** · "
             "généré par **`notion.py`***" % long(jour))
    return "\n".join(L)


def main():
    args = sys.argv[1:]
    jour = carte.d(args[0]) if args else dt.date.today()
    print(page(carte.charger(), jour))


if __name__ == "__main__":
    main()

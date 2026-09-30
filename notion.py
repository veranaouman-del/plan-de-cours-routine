# -*- coding: utf-8 -*-
"""Page Notion « Ma session » — Automne 2026.

Génère le contenu Markdown (saveur Notion) du tableau de bord à partir de
donnees-session.json, pour la date demandée.

    python3 notion.py              -> aujourd'hui, sur la sortie standard
    python3 notion.py 2026-10-07   -> une date précise

La sortie se pousse telle quelle dans la page Notion avec `replace_content`.
Comme carte.py, rien n'est codé en dur : la source de vérité reste le JSON.
"""
import sys
import datetime as dt

import carte

JOURS_COURTS = ["lun.", "mar.", "mer.", "jeu.", "ven.", "sam.", "dim."]
EMOJI = {"devlog": "💻", "web": "🌐", "litt": "📕", "anglais": "🗣️", "philo": "⚖️"}

SEMAINES_ROUGES = [
    (5,  "21 – 25 sept.",   "Dissertation français 20 %, TP2 10 %, TP1 VueJS, test de philo 10 %",
         "Les deux TP finis **dimanche 20 au soir**"),
    (6,  "28 sept. – 2 oct.", "Midterm anglais 20 %, examen Éthique 25 %",
         "**45 % en 48 h.** Les tableaux de philo finis mercredi soir"),
    (7,  "5 – 9 oct.",      "Intra 25 %, oral d'anglais 15 %, Éval. #1 Web 25 %",
         "**65 % en quatre jours.** Tout prêt le 4 octobre"),
    (11, "9 – 13 nov.",     "Dissertation de philo 20 %, contrôle 2, remise TP3",
         "Le plan du 6 nov. est la répétition générale"),
    (15, "7 – 11 déc.",     "Quatre finaux : 30 %, 35 %, 30 %, 35 % + entrevue 40 %",
         "Les révisions commencent le **16 novembre**"),
]

SEMAINE_TYPE = [
    ("Lundi 16 h 30 – 18 h", "1 h 30", "🌐 Prog. Web — le TP en cours"),
    ("**Mardi 13 h 30 – 16 h 30**", "**3 h**", "📕⚖️ **Gros bloc — français et philo**"),
    ("**Mercredi 11 h 15 – 16 h**", "**4 h**", "💻🌐 **Gros bloc — programmation**"),
    ("**Jeudi 12 h 30 – 15 h 30**", "**3 h**", "🗣️ **Gros bloc — anglais et prise d'avance**"),
    ("Vendredi 11 h 45 – 12 h 45", "1 h", "⚖️ Philo à chaud, les notes du matin"),
    ("Samedi 9 h – 12 h", "3 h", "📖 Lectures longues"),
    ("Dimanche 16 h – 18 h", "2 h", "🔁 **Rattrapage** et plan de la semaine"),
]

METHODES = [
    ("⚖️ Éthique et politique", "philo",
     "Droit aux notes de cours à **toutes** les évaluations. La vraie préparation, c'est donc de "
     "**construire de bonnes notes**, pas de mémoriser. Un tableau par penseur : thèse, critère du "
     "juste, objection principale, exemple concret. C'est ce tableau qu'on apporte à l'examen."),
    ("📕 Littérature et imaginaire", "litt",
     "Annoter **pendant** la lecture, jamais après. Un carnet de citations classées par thème. "
     "Garder 10 minutes de relecture linguistique en fin de rédaction — la langue vaut **25 %** "
     "de chaque dissertation."),
    ("🗣️ Anglais", "anglais",
     "Tout se joue en classe. Remplir le journal Odyssey **le jour même** (5 % garantis). "
     "Les évaluations orales valent **45 %** du cours : elles se préparent **à voix haute**, "
     "pas par écrit."),
    ("💻 Développement de logiciels", "devlog",
     "Le code se retient par les doigts. Refaire les exercices dirigés **sans la correction**, "
     "puis comparer. S'entraîner à écrire du code **sur papier** — c'est ce qui est demandé "
     "à l'examen."),
    ("🌐 Programmation Web I", "web",
     "Chaque TP s'appuie sur le précédent. Un TP bâclé se paie deux fois. Après chaque remise, "
     "noter en trois lignes **ce qui a bloqué** : c'est exactement ce qui tombera à l'Évaluation #1."),
]


def tableau(entetes, lignes):
    out = ['<table header-row="true">', "<tr>"]
    out += ["<td>%s</td>" % h for h in entetes]
    out.append("</tr>")
    for ligne in lignes:
        out.append("<tr>")
        out += ["<td>%s</td>" % c for c in ligne]
        out.append("</tr>")
    out.append("</table>")
    return "\n".join(out)


def nom_emoji(data, cle):
    return "%s %s" % (EMOJI.get(cle, ""), data["cours"][cle]["nom"])


def court_emoji(data, cle):
    c = data["cours"][cle]
    return "%s %s" % (EMOJI.get(cle, ""), c.get("court", c["nom"]))


def pastille(reste):
    return "🔴" if reste <= 3 else ("🟠" if reste <= 12 else "🔵")


def heure(h):
    hh, mm = h.split(":")
    return "%d h" % int(hh) if mm == "00" else "%d h %s" % (int(hh), mm)


def date_longue(j):
    jour = carte.JOURS[j.weekday()]
    num = "1er" if j.day == 1 else str(j.day)
    return "%s %s %s" % (jour, num, carte.MOIS[j.month - 1])


def date_courte(j):
    num = "1er" if j.day == 1 else str(j.day)
    return "%s %s %s" % (JOURS_COURTS[j.weekday()], num, carte.ABREV[j.month - 1])


# ---------------------------------------------------------------------------
def bloc_aujourdhui(data, jour):
    L = ["## 📍 Aujourd'hui — %s" % date_longue(jour)]
    for c in carte.cours_du_jour(data, jour):
        L.append("- %s **%s** · %s – %s · %s"
                 % (EMOJI.get(c["cours"], ""), data["cours"][c["cours"]]["nom"],
                    heure(c["debut"]), heure(c["fin"]), c["local"]))
    for b in carte.blocs_du_jour(data, jour):
        L.append("- 🎯 **%s** · %s – %s" % (b["titre"], heure(b["debut"]), heure(b["fin"])))
    if not carte.cours_du_jour(data, jour) and not carte.blocs_du_jour(data, jour):
        L.append("- Journée libre — repos assumé, c'est prévu.")

    actifs = carte.chantiers(data, jour)
    if actifs:
        p = actifs[0]
        quand = ("**aujourd'hui**" if p["reste"] == 0 else
                 "**demain**" if p["reste"] == 1 else "dans %d jours" % p["reste"])
        L.append("")
        L.append("> 🔥 **Priorité du jour :** %s — %s (%d %%), %s."
                 % (nom_emoji(data, p["cours"]), p["titre"], p["poids"], quand))
    return "\n".join(L)


def bloc_sept_jours(data, jour):
    lignes = []
    for i in range(7):
        j = jour + dt.timedelta(days=i)
        libelle = date_courte(j)
        if i == 0:
            libelle = "**%s** ← *aujourd'hui*" % libelle

        cours = carte.cours_du_jour(data, j)
        blocs = carte.blocs_du_jour(data, j)
        col_cours = " · ".join(court_emoji(data, c["cours"]) for c in cours) or "—"
        if blocs:
            col_cours += "<br>%s – %s" % (heure(blocs[0]["debut"]), heure(blocs[0]["fin"]))

        # une échéance qui tombe ce jour-là écrase tout le reste
        du_jour = [e for e in carte.chantiers_tous(data, j) if e["reste"] == 0]
        if du_jour:
            e = max(du_jour, key=lambda x: x["poids"])
            corps = "%s — %s" % (court_emoji(data, e["cours"]), e["titre"])
            if e["poids"]:
                corps += " — %d %%" % e["poids"]
            quoi = "🔥 **%s**" % corps
        else:
            actifs = carte.chantiers(data, j)
            focus = set()
            for b in blocs:
                focus.update(b["focus"])
            candidats = [e for e in actifs if e["cours"] in focus] or actifs
            if candidats:
                e = candidats[0]
                quoi = "%s — %s *(%s)*" % (court_emoji(data, e["cours"]), e["titre"],
                                           carte.etape(e).lower())
            else:
                quoi = "—"
        lignes.append([libelle, col_cours, quoi])
    return "## 🗓️ Les 7 prochains jours\n" + tableau(["Jour", "Cours", "Ce que je fais"], lignes)


def bloc_a_regler(data, jour):
    L = ["## ✅ À régler tout de suite"]
    rien = True
    for t in data["taches_admin"]:
        if t["pour"] == "recurrent":
            continue
        reste = (carte.d(t["pour"]) - jour).days
        if reste < 0:
            marque, quand = "🔴", "*%d jour%s de retard*" % (-reste, "s" if reste < -1 else "")
        elif reste == 0:
            marque, quand = "🟠", "*aujourd'hui*"
        elif reste <= 7:
            marque, quand = "🟠", "*dans %d jours*" % reste
        else:
            continue
        rien = False
        corps = "**%s**" % t["quoi"] if marque == "🔴" else t["quoi"]
        L.append("- [ ] %s %s — %s" % (marque, corps, quand))
    if rien:
        L.append("- Rien en attente. C'est rare, profites-en.")
    return "\n".join(L)


def bloc_echeances(data, jour):
    lignes = []
    for e in carte.chantiers_tous(data, jour):
        poids = "**%d %%**" % e["poids"] if e["poids"] >= 20 else (
            "%d %%" % e["poids"] if e["poids"] else "formatif")
        lignes.append([pastille(e["reste"]), date_courte(carte.d(e["date"])),
                       court_emoji(data, e["cours"]), e["titre"], poids,
                       carte.jx(e["reste"])])
    return ("## 📅 Toutes mes échéances à venir\n"
            "> 💡 Sélectionne ce tableau → **Transformer en base de données** "
            "pour filtrer par cours et cocher au fur et à mesure.\n"
            + tableau(["", "Date", "Cours", "Évaluation", "Poids", "Compte à rebours"], lignes))


def bloc_lectures(data, jour):
    lignes = []
    for l in sorted(data["lectures"], key=lambda x: x["pour"]):
        j = carte.d(l["pour"])
        if j < jour:
            continue
        lignes.append([date_courte(j), court_emoji(data, l["cours"]), l["quoi"]])
    if not lignes:
        return "## 📖 Mes lectures\nPlus aucune lecture imposée d'ici la fin de la session."
    return "## 📖 Mes lectures\n" + tableau(["Pour le", "Cours", "À lire"], lignes)


def bloc_semaines_rouges(data, jour):
    ici = carte.semaine_de(data, jour)
    lignes = []
    for num, dates, quoi, regle in SEMAINES_ROUGES:
        if ici and num < ici:
            continue
        libelle = "**%d**" % num + (" ← *ici*" if num == ici else "")
        lignes.append([libelle, dates, quoi, regle])
    return "## 🔴 Mes semaines rouges\n" + tableau(["Semaine", "Dates", "Ce qui tombe", "La règle"], lignes)


def bloc_methodes(data, jour):
    # le cours qui pèse le plus dans les 30 prochains jours passe en tête
    poids = {}
    for e in carte.chantiers_tous(data, jour):
        if e["reste"] <= 30:
            poids[e["cours"]] = poids.get(e["cours"], 0) + e["poids"]
    tete = max(poids, key=poids.get) if poids else None

    L = ["## 🧠 Mes méthodes, cours par cours"]
    ordonne = sorted(METHODES, key=lambda m: (m[1] != tete, -poids.get(m[1], 0)))
    for titre, cle, corps in ordonne:
        suffixe = " — *ma matière la plus lourde en ce moment*" if cle == tete else ""
        L.append("### %s%s" % (titre, suffixe))
        L.append(corps)
    return "\n".join(L)


def bloc_avancement(data, jour):
    av = carte.avancement(data, jour)
    lignes = []
    for cle, (nom, pct) in sorted(av.items(), key=lambda kv: -kv[1][1]):
        lignes.append(["%s %s" % (EMOJI.get(cle, ""), nom), "%d %%" % pct])
    total = sum(pct for _, pct in av.values()) / len(av)
    return ("## 📊 Mon avancement\n"
            + tableau(["Cours", "Part de la note déjà jouée"], lignes)
            + "\n> **%d %%** de la session est joué, tous cours confondus." % round(total))


def page(data, jour):
    sem = carte.semaine_de(data, jour)
    entete = ["# 🎓 Ma session — Automne 2026",
              "> Cégep de Granby · Techniques de l'informatique (420.B0) · 24 août → 11 décembre"]
    if carte.en_semaine_etudes(data, jour):
        entete.append("> **Semaine d'études** · aucun cours cette semaine")
    elif sem:
        entete.append("> **Semaine %d sur 15** · Semaine d'études : 12 au 16 octobre" % sem)

    sections = [
        "\n".join(entete),
        bloc_aujourdhui(data, jour),
        bloc_sept_jours(data, jour),
        bloc_a_regler(data, jour),
        bloc_echeances(data, jour),
        bloc_lectures(data, jour),
        bloc_semaines_rouges(data, jour),
        "## 🗓️ Ma semaine type\n"
        + tableau(["Quand", "Durée", "Ce que je fais"], SEMAINE_TYPE)
        + "\n> ⚠️ Vendredi soir, samedi après-midi et dimanche matin restent **vides**. "
          "Ce n'est pas du temps perdu : c'est ce qui rend les 17 h 30 restantes tenables "
          "semaine après semaine.",
        bloc_methodes(data, jour),
        "## 🔁 Quand je prends du retard\n"
        "Le bloc du dimanche 16 h – 18 h existe pour ça. L'ordre est toujours le même : "
        "**ce qui est noté le plus lourd et qui tombe le plus tôt d'abord.** Une lecture en "
        "retard se rattrape ; une remise manquée, non.\n"
        "Si deux semaines de suite débordent, ce n'est pas un problème d'effort : c'est que le "
        "plan est trop chargé. On retire quelque chose plutôt que d'accumuler.",
        bloc_avancement(data, jour),
        "*Mis à jour automatiquement le %s · source : `donnees-session.json`*" % date_longue(jour),
    ]
    return "\n---\n".join(sections)


def main():
    jour = carte.d(sys.argv[1]) if len(sys.argv) > 1 else dt.date.today()
    print(page(carte.charger(), jour))


if __name__ == "__main__":
    main()

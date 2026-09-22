# -*- coding: utf-8 -*-
"""Page Notion « Ma session » — Automne 2026.

Regénère le Markdown complet du tableau de bord Notion à partir de
donnees-session.json, en réutilisant le moteur de carte.py.

    python3 notion.py                 -> Markdown d'aujourd'hui sur stdout
    python3 notion.py 2026-10-07      -> une date précise
    python3 notion.py --out page.md   -> écrit dans un fichier

Le Markdown produit se colle dans notion-update-page (commande replace_content).
Rien n'est codé en dur ici : une échéance qui bouge se change dans le JSON.
"""
import sys
import datetime as dt

import carte
from carte import d, jx, court, JOURS, MOIS

ICONE = {"devlog": "💻", "web": "🌐", "litt": "📕", "anglais": "🗣️", "philo": "⚖️"}

# Emoji de la pastille selon l'urgence, pour que la colonne se lise d'un coup d'œil.
def pastille(reste):
    if reste <= 6:
        return "🔴"
    if reste <= 20:
        return "🟠"
    return "🔵"


def poids_md(ev):
    """Le poids en gras dès 20 % : c'est ce qui décide où va le temps."""
    txt = "%d %%" % ev["poids"] if ev["poids"] else "formatif"
    if ev["poids"] >= 20:
        txt = "**%s**" % txt
    if ev.get("poids_approx"):
        txt += " *(à confirmer)*"
    return txt


def titre_md(ev):
    return ev["titre"] + (" *(date à confirmer)*" if ev.get("a_confirmer") else "")


def long_date(j):
    return "%s %d %s" % (JOURS[j.weekday()], j.day, MOIS[j.month - 1])


# --------------------------------------------------------------------------
# Semaines rouges : calculées, pas listées à la main
# --------------------------------------------------------------------------
def semaines_rouges(data, jour, seuil=25):
    """Une semaine est rouge si le total des poids qui y tombent dépasse le seuil.

    Seuil à 25 : c'est ce qui fait entrer la semaine 11 (29 %, la dissertation de
    philo) sans faire entrer la semaine 10 (20 %). Une semaine à plus d'un quart
    de la note ne se prépare pas dans la semaine même.
    """
    paires = sorted(((int(n), d(deb)) for n, deb in data["session"]["semaines"].items()),
                    key=lambda p: p[1])
    out = []
    for num, debut in paires:
        fin = debut + dt.timedelta(days=6)
        evs = [e for e in data["evaluations"] if debut <= d(e["date"]) <= fin]
        total = sum(e["poids"] for e in evs)
        if total >= seuil and fin >= jour:
            out.append((num, debut, fin, total,
                        sorted(evs, key=lambda e: (-e["poids"], e["date"]))))
    return out


def regle_semaine(data, num, evs):
    """La phrase qui résume ce qu'il faut protéger cette semaine-là."""
    tps = [e for e in evs if e["type"] in ("tp", "remise")]
    total = sum(e["poids"] for e in evs)
    if num == 5:
        return "Les deux TP finis dimanche soir, pas lundi."
    if num == 7:
        return "%d %% en quatre jours. Tout doit être prêt le 4 octobre, avant la semaine d'études." % total
    if num == 11:
        return "Le plan de dissertation du 6 nov. est la répétition générale du 13."
    if num == 15:
        return "Quatre finaux plus l'entrevue. Les révisions commencent le 16 novembre."
    if tps:
        return "%d %% en une semaine, dont %d remise%s. Rien ne commence ce lundi-là." % (
            total, len(tps), "s" if len(tps) > 1 else "")
    return "%d %% de la session en une semaine. Rien ne commence ce lundi-là." % total


# --------------------------------------------------------------------------
# Blocs de la page
# --------------------------------------------------------------------------
def bloc_aujourdhui(data, jour, actifs):
    L = ["## ☀️ Aujourd'hui — %s" % long_date(jour), ""]

    cj = carte.cours_du_jour(data, jour)
    L.append("**Mes cours**")
    if cj:
        for c in cj:
            co = data["cours"][c["cours"]]
            L.append("- %s `%s – %s` %s · %s" % (
                ICONE[c["cours"]], c["debut"].replace(":", " h "),
                c["fin"].replace(":", " h "), co["nom"], c["local"]))
    else:
        L.append("- Aucun cours aujourd'hui.")
    L.append("")

    ej = carte.evenements_du_jour(data, jour)
    if ej:
        L.append("**Autres engagements**")
        for e in ej:
            L.append("- 📌 `%s – %s` %s · %s" % (e["debut"].replace(":", " h "),
                                                 e["fin"].replace(":", " h "),
                                                 e["quoi"], e.get("local", "—")))
            b = carte.bloc_ampute(data, jour, e)
            if b:
                L.append("  - ⚠️ Ampute le bloc « %s ».%s" % (
                    b["titre"], " " + e["note"] if e.get("note") else ""))
        L.append("")

    if actifs:
        p = actifs[0]
        co = data["cours"][p["cours"]]
        L.append("> 🔴 **Ma priorité : %s** — %s, %d %%, %s" % (
            p["titre"], co["nom"], p["poids"], jx(p["reste"])))
        L.append("> Si je ne fais qu'une seule chose aujourd'hui, c'est celle-là.")
        L.append("")

    L.append("**À cocher aujourd'hui**")
    for tag, t in carte.taches_du_jour(data, jour, actifs):
        etiquette = {"RETARD": "En retard", "ADMIN": "Admin", "LECTURE": "Lecture"}.get(
            tag, tag.capitalize())
        L.append("- [ ] **%s** — %s" % (etiquette, t))
    L.append("")

    bj = carte.blocs_du_jour(data, jour)
    L.append("**Mes blocs de travail**")
    if bj:
        for b in bj:
            L.append("- ⏱️ `%s – %s` %s" % (b["debut"].replace(":", " h "),
                                            b["fin"].replace(":", " h "), b["titre"]))
    else:
        L.append("- Aucun bloc prévu — journée volontairement libre.")
    return L


def bloc_sept_jours(data, jour):
    fin = jour + dt.timedelta(days=7)
    L = ["## ⚡ Mes sept prochains jours — %s au %s" % (court(jour), court(fin)), ""]

    for t in data["taches_admin"]:
        if t["pour"] == "recurrent":
            continue
        ech = d(t["pour"])
        if ech < jour and t.get("urgent"):
            L.append("- [ ] 🔴 %s — **en retard depuis le %s**" % (t["quoi"], court(ech)))
        elif jour <= ech <= fin:
            L.append("- [ ] %s %s — pour le %s" % ("🔴" if t.get("urgent") else "🔵",
                                                   t["quoi"], court(ech)))

    for e in carte.evenements_a_venir(data, jour):
        b = carte.bloc_ampute(data, jour, e)
        L.append("- [ ] 📌 %s — %s, %s – %s · %s%s" % (
            e["quoi"], court(d(e["date"])), e["debut"].replace(":", " h "),
            e["fin"].replace(":", " h "), e.get("local", "—"),
            " — **ampute le bloc « %s »**" % b["titre"] if b else ""))

    for l in data["lectures"]:
        if jour <= d(l["pour"]) <= fin:
            L.append("- [ ] %s %s — pour le %s" % (ICONE[l["cours"]], l["quoi"],
                                                   court(d(l["pour"]))))

    for e in carte.chantiers(data, jour):
        if e["reste"] <= 7:
            co = data["cours"][e["cours"]]
            L.append("- [ ] %s %s — %s, %s (%s)" % (
                ICONE[e["cours"]], e["titre"], co["court"], jx(e["reste"]),
                carte.etape(e).lower()))
    return L


def bloc_semaines_rouges(data, jour):
    rouges = semaines_rouges(data, jour)
    L = ["## 🔴 Mes semaines rouges — %d encore devant moi" % len(rouges), "",
         '<table header-row="true">', "<tr>",
         "<td>Semaine</td>", "<td>Dates</td>", "<td>Ce qui tombe</td>", "<td>La règle</td>",
         "</tr>"]
    for num, debut, fin, total, evs in rouges:
        quoi = ", ".join("%s %s %s" % (ICONE[e["cours"]], e["titre"],
                                       "%d %%" % e["poids"] if e["poids"] else "formatif")
                         for e in evs)
        L += ["<tr>", "<td>**%d**</td>" % num,
              "<td>%s – %s</td>" % (court(debut), court(fin)),
              "<td>%s</td>" % quoi,
              "<td>%s</td>" % regle_semaine(data, num, evs), "</tr>"]
    L.append("</table>")
    return L


def bloc_echeances(data, jour):
    L = ["## 📅 Toutes mes échéances", "",
         "> 💡 Sélectionne ce tableau → **Transformer en base de données** "
         "pour filtrer par cours et trier par date.", "",
         '<table header-row="true">', "<tr>", "<td></td>", "<td>Date</td>", "<td>Cours</td>",
         "<td>Évaluation</td>", "<td>Poids</td>", "<td>Compte à rebours</td>", "</tr>"]

    faites = sorted((e for e in data["evaluations"]
                     if e.get("fait") or d(e["date"]) < jour), key=lambda e: e["date"])
    for e in faites:
        co = data["cours"][e["cours"]]
        L += ["<tr>", "<td>✅</td>", "<td>%s</td>" % long_date(d(e["date"])),
              "<td>%s %s</td>" % (ICONE[e["cours"]], co["court"]),
              "<td>%s</td>" % e["titre"], "<td>%d %%</td>" % e["poids"],
              "<td>✅ fait</td>", "</tr>"]

    for e in carte.chantiers_tous(data, jour):
        co = data["cours"][e["cours"]]
        L += ["<tr>", "<td>%s</td>" % pastille(e["reste"]),
              "<td>%s</td>" % long_date(d(e["date"])),
              "<td>%s %s</td>" % (ICONE[e["cours"]], co["court"]),
              "<td>%s</td>" % titre_md(e), "<td>%s</td>" % poids_md(e),
              "<td>%s</td>" % jx(e["reste"]), "</tr>"]
    L.append("</table>")
    return L


def bloc_semaine_type(data):
    total = 0
    lignes = []
    for b in data["blocs_travail"]:
        h1, m1 = (int(x) for x in b["debut"].split(":"))
        h2, m2 = (int(x) for x in b["fin"].split(":"))
        minutes = (h2 * 60 + m2) - (h1 * 60 + m1)
        total += minutes
        duree = "%d h %02d" % (minutes // 60, minutes % 60) if minutes % 60 else "%d h" % (minutes // 60)
        icones = "".join(ICONE.get(f, "🔁") for f in b["focus"])
        gros = "GROS BLOC" in b["titre"] or "RATTRAPAGE" in b["titre"]
        quand = "%s %s – %s" % (JOURS[b["jour"] - 1].capitalize(),
                                b["debut"].replace(":", " h "), b["fin"].replace(":", " h "))
        lignes.append((quand, duree, "%s %s" % (icones, b["titre"]), gros))

    h, m = total // 60, total % 60
    tt = "%d h %02d" % (h, m) if m else "%d h" % h
    L = ["## 🗓️ Ma semaine type — %s de travail" % tt, "",
         '<table header-row="true">', "<tr>", "<td>Quand</td>", "<td>Durée</td>",
         "<td>Ce que je fais</td>", "</tr>"]
    for quand, duree, quoi, gros in lignes:
        g = (lambda s: "**%s**" % s) if gros else (lambda s: s)
        L += ["<tr>", "<td>%s</td>" % g(quand), "<td>%s</td>" % g(duree),
              "<td>%s</td>" % quoi, "</tr>"]
    L += ["</table>", "",
          "> ⚠️ Vendredi soir, samedi après-midi et dimanche matin restent **vides**. "
          "Ce n'est pas du temps perdu : c'est ce qui rend les %s restantes tenables "
          "semaine après semaine." % tt]
    return L


METHODES = {
    "litt": "Annoter PENDANT la lecture, jamais après. Un carnet de citations classées par "
            "thème. Garder 10 minutes de relecture linguistique en fin de rédaction : la "
            "langue vaut 25 % de chaque dissertation.",
    "philo": "Droit aux notes de cours à TOUTES les évaluations — donc la vraie préparation, "
             "c'est de construire de bonnes notes. Un tableau par penseur : thèse, critère "
             "du juste, objection, exemple.",
    "anglais": "Tout se joue en classe. Remplir le journal Odyssey le jour même (5 % garantis). "
               "Les évaluations orales valent 45 % du cours : elles se préparent à voix haute, "
               "pas par écrit.",
    "devlog": "Le code se retient par les doigts. Refaire les exercices dirigés SANS la "
              "correction, puis comparer. S'entraîner à écrire du code sur papier : c'est ce "
              "qui est demandé à l'examen.",
    "web": "Chaque TP s'appuie sur le précédent ; un TP bâclé se paie deux fois. Après chaque "
           "remise, noter en trois lignes ce qui a bloqué : c'est exactement ce qui tombera "
           "à l'Évaluation #1.",
}


def bloc_methodes(data):
    L = ["## 🧠 Mes méthodes, cours par cours", ""]
    dur = max(c["difficulte"] for c in data["cours"].values())
    # Les cours les plus difficiles passent en premier : c'est là que va le temps.
    for cle, co in sorted(data["cours"].items(), key=lambda kv: -kv[1]["difficulte"]):
        L.append("### %s %s" % (ICONE[cle], co["nom"]))
        if co["difficulte"] == dur:
            L.append("*Cours où je me sens le plus fragile — c'est là que va le temps en priorité.*")
        L += [METHODES[cle], ""]
    return L


def bloc_confirmer(data, jour):
    L = ["## ✅ À faire confirmer auprès des profs", ""]
    for t in data["taches_admin"]:
        if t["pour"] == "recurrent":
            L.append("- [ ] 🔁 %s" % t["quoi"])
            continue
        ech = d(t["pour"])
        if ech < jour and t.get("urgent"):
            L.append("- [ ] 🔴 %s — **en retard depuis le %s**" % (t["quoi"], court(ech)))
        else:
            L.append("- [ ] %s %s — pour le %s" % ("🔴" if t.get("urgent") else "🔵",
                                                   t["quoi"], court(ech)))
    return L


def bloc_avancement(data, jour):
    av = carte.avancement(data, jour)
    L = ["## 📊 Mon avancement", "", '<table header-row="true">', "<tr>",
         "<td>Cours</td>", "<td>Part de la note déjà jouée</td>", "</tr>"]
    for cle, (nom, fait) in sorted(av.items(), key=lambda kv: -kv[1][1]):
        L += ["<tr>", "<td>%s %s</td>" % (ICONE[cle], data["cours"][cle]["court"]),
              "<td>%d %%</td>" % fait, "</tr>"]
    L.append("</table>")
    moyenne = sum(f for _, f in av.values()) / len(av)
    reste = (d(data["session"]["fin"]) - jour).days
    # court() rend deja "11 dec." avec son point final : ne pas en rajouter un
    L += ["", "> **%d %%** de la session est joué en moyenne. Il reste %d jours avant le %s"
          % (round(moyenne), reste, court(d(data["session"]["fin"])))]
    return L


RATTRAPAGE = [
    "## 🔁 Si je prends du retard", "",
    "> Le dimanche 16 h – 18 h ne sert **qu'à ça** : reprendre ce qui a sauté dans la semaine "
    "et refaire le plan des sept jours suivants. Rien d'autre ne s'y planifie.", "",
    "- Une journée sautée → elle se reprend dans le bloc du dimanche, pas en empilant sur "
    "le lendemain.",
    "- Une semaine sautée → je laisse tomber la prise d'avance du jeudi et je protège les "
    "deux gros blocs (mardi, mercredi).",
    "- Deux semaines de retard → j'écris au prof concerné avant l'échéance, jamais après. "
    "Une remise négociée vaut mieux qu'une remise ratée.",
]


def page(data, jour):
    sem = carte.semaine_de(data, jour)
    a, b = data["session"]["semaine_etudes"]
    L = ["> 420.B0 Techniques de l'informatique — Cégep de Granby",
         "> Du %s au %s · Semaine d'études : %s au %s" % (
             court(d(data["session"]["debut"])), court(d(data["session"]["fin"])),
             court(d(a)), court(d(b))),
         "> **Nous sommes en semaine %s sur 15.** Page mise à jour le %s." % (
             sem or "—", long_date(jour)),
         "", "---", ""]

    actifs = carte.chantiers(data, jour)
    for bloc in (bloc_aujourdhui(data, jour, actifs),
                 bloc_sept_jours(data, jour),
                 bloc_semaines_rouges(data, jour),
                 bloc_echeances(data, jour),
                 bloc_semaine_type(data),
                 bloc_methodes(data),
                 RATTRAPAGE,
                 bloc_confirmer(data, jour),
                 bloc_avancement(data, jour)):
        L += bloc + ["", "---", ""]

    L.append("*Page regénérée par **`notion.py`** à partir de **`donnees-session.json`**. "
             "La carte du jour arrive chaque matin dans Slack.*")
    return "\n".join(L)


def main():
    args = [a for a in sys.argv[1:]]
    sortie = None
    if "--out" in args:
        i = args.index("--out")
        sortie = args[i + 1]
        del args[i:i + 2]
    jour = d(args[0]) if args else dt.date.today()

    md = page(carte.charger(), jour)
    if sortie:
        with open(sortie, "w", encoding="utf-8") as fh:
            fh.write(md)
        print("Écrit dans %s (%d caractères)" % (sortie, len(md)))
    else:
        print(md)


if __name__ == "__main__":
    main()

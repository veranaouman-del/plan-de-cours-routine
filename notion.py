# -*- coding: utf-8 -*-
"""Tableau de bord Notion — Automne 2026.

Regenere le contenu complet de la page Notion a partir de donnees-session.json.

    python3 notion.py                 -> le markdown Notion d'aujourd'hui, sur stdout
    python3 notion.py 2026-10-07      -> une date precise

Le texte est ensuite pousse dans la page avec notion-update-page / replace_content.
Comme carte.py, ce script ne contient aucune date en dur : tout vient du JSON.
Seule la prose stable (methodes de travail, regles de rattrapage) vit ici.
"""
import sys
import datetime as dt

import carte  # meme moteur : semaines, chantiers, urgence, avancement

d, JOURS, MOIS = carte.d, carte.JOURS, carte.MOIS

PAGE_ID = "3df73824-e620-811e-9e6c-d07440cb6ec7"

ICONE = {"devlog": "💻", "web": "🌐", "litt": "📕", "anglais": "🗣️", "philo": "⚖️"}

ETAPE_LISIBLE = {
    "RETARD": "En retard", "ADMIN": "Admin", "LECTURE": "Lecture",
    "REMISE": "Remise", "FINIR": "Finir", "AVANCER": "Avancer",
    "RELIRE": "Relire", "TEST BLANC": "Test blanc", "FICHES": "Fiches",
    "NOTES": "Notes",
}

METHODES = [
    ("litt", "Annoter PENDANT la lecture, jamais après. Un carnet de citations classées par thème. "
             "Garder 10 minutes de relecture linguistique en fin de rédaction : la langue vaut 25 % "
             "de chaque dissertation."),
    ("philo", "Droit aux notes de cours à TOUTES les évaluations — donc la vraie préparation, c'est de "
              "construire de bonnes notes. Un tableau par penseur : thèse, critère du juste, objection, exemple."),
    ("anglais", "Tout se joue en classe. Remplir le journal Odyssey le jour même (5 % garantis). Les "
                "évaluations orales valent 45 % du cours : elles se préparent à voix haute, pas par écrit."),
    ("devlog", "Le code se retient par les doigts. Refaire les exercices dirigés SANS la correction, puis "
               "comparer. S'entraîner à écrire du code sur papier : c'est ce qui est demandé à l'examen."),
    ("web", "Chaque TP s'appuie sur le précédent ; un TP bâclé se paie deux fois. Après chaque remise, noter "
            "en trois lignes ce qui a bloqué : c'est exactement ce qui tombera à l'Évaluation #1."),
]

RATTRAPAGE = [
    "Une journée sautée → elle se reprend dans le bloc du dimanche, pas en empilant sur le lendemain.",
    "Une semaine sautée → je laisse tomber la prise d'avance du jeudi et je protège les deux gros blocs "
    "(mardi, mercredi).",
    "Deux semaines de retard → j'écris au prof concerné **avant** l'échéance, jamais après. Une remise "
    "négociée vaut mieux qu'une remise ratée.",
]


def long_(j):
    return "%s %d %s" % (JOURS[j.weekday()], j.day, MOIS[j.month - 1])


def h(x):
    return x.replace(":", " h ")


def pastille(reste):
    return "🔴" if reste <= 4 else ("🟠" if reste <= 15 else "🔵")


def poids_txt(ev):
    if not ev["poids"]:
        return "formatif"
    t = "%d %%" % ev["poids"]
    if ev["poids"] >= 20:
        t = "**%s**" % t
    if ev.get("poids_approx"):
        t += " *(à confirmer)*"
    return t


def titre_ev(data, ev):
    t = ev["titre"]
    if ev.get("a_confirmer"):
        t += " *(date à confirmer)*"
    return t


def tableau(entetes, lignes):
    out = ['<table header-row="true">', "<tr>"]
    out += ["<td>%s</td>" % e for e in entetes]
    out.append("</tr>")
    for l in lignes:
        out.append("<tr>")
        out += ["<td>%s</td>" % c for c in l]
        out.append("</tr>")
    out.append("</table>")
    return "\n".join(out)


# --------------------------------------------------------------------------
def semaines_rouges(data, jour):
    """Une semaine est rouge des que 2 evaluations tombent dedans ou que le total
    depasse 20 % de la note. Seules celles encore devant moi sont listees."""
    paires = sorted(((int(n), d(deb)) for n, deb in data["session"]["semaines"].items()),
                    key=lambda p: p[1])
    out = []
    for num, debut in paires:
        fin = debut + dt.timedelta(days=6)
        if fin < jour:
            continue
        dedans = [e for e in data["evaluations"]
                  if not e.get("fait") and d(e["date"]) >= jour and debut <= d(e["date"]) <= fin]
        total = sum(e["poids"] for e in dedans)
        if len(dedans) >= 2 or total >= 20:
            out.append((num, debut, fin, dedans, total))
    return out


def regle_semaine(num, dedans, total, data):
    """La phrase qui dit quoi faire de cette semaine-la.

    On ne somme jamais les ponderations de cours differents : 30 % de francais plus
    35 % d'informatique ne font pas 65 % de quoi que ce soit. On nomme plutot le
    nombre d'evaluations, le nombre de cours touches et la plus lourde."""
    gros = [e for e in dedans if e["poids"] >= 20]
    n_cours = len({e["cours"] for e in dedans})
    lourde = max(dedans, key=lambda e: e["poids"])
    nom_lourde = "%s %d %% en %s" % (lourde["titre"], lourde["poids"],
                                     data["cours"][lourde["cours"]]["court"])
    if len(gros) >= 3:
        return ("%d évaluations lourdes dans %d cours différents. Les révisions commencent "
                "trois semaines avant, pas la veille." % (len(gros), n_cours))
    if all(e["type"] in ("tp", "remise") for e in dedans):
        return "Que des remises : tout doit être fini le dimanche soir, pas le lundi matin."
    return ("%d évaluations dans %d cours. La plus lourde : %s. Rien de neuf ne commence "
            "ce lundi-là." % (len(dedans), n_cours, nom_lourde))


def conseil_du_jour(data, jour, actifs, bj):
    """Comment decouper concretement les blocs du jour entre les chantiers chauds."""
    if not bj or not actifs:
        return None
    chauds = [e for e in actifs if e["reste"] <= 2][:2]
    if not chauds:
        e = actifs[0]
        return ("Le bloc de %s sert a %s — %s. C'est de la prise d'avance, et c'est exactement "
                "ce qui évite le bourrage." % (h(bj[0]["debut"]), data["cours"][e["cours"]]["nom"], e["titre"]))
    if len(chauds) == 1:
        return "Le bloc du jour part en entier sur : %s. Rien d'autre." % chauds[0]["titre"]
    return ("Couper le bloc en deux : d'abord %s, ensuite %s. Dans cet ordre — le plus lourd "
            "quand la tête est encore fraîche." % (chauds[0]["titre"], chauds[1]["titre"]))


# --------------------------------------------------------------------------
def page(data, jour):
    sem = carte.semaine_de(data, jour)
    actifs = carte.chantiers(data, jour)
    tous = carte.chantiers_tous(data, jour)
    cj = carte.cours_du_jour(data, jour)
    bj = carte.blocs_du_jour(data, jour)
    L = []

    ses = data["session"]
    L.append("> 420.B0 Techniques de l'informatique — Cégep de Granby")
    L.append("> Du %s au %s · Semaine d'études : %s au %s"
             % (carte.court(d(ses["debut"])), carte.court(d(ses["fin"])),
                carte.court(d(ses["semaine_etudes"][0])), carte.court(d(ses["semaine_etudes"][1]))))
    entete = "**Nous sommes en semaine %d sur 15.**" % sem if sem else "**Hors session.**"
    L.append("> %s Page mise à jour le %s." % (entete, long_(jour)))
    L.append("---")

    # ---------------- aujourd'hui
    L.append("## ☀️ Aujourd'hui — %s" % long_(jour))
    L.append("**Mes cours**")
    if cj:
        for c in cj:
            co = data["cours"][c["cours"]]
            L.append("- %s `%s – %s` %s · %s" % (ICONE[c["cours"]], h(c["debut"]), h(c["fin"]),
                                                 co["nom"], c["local"]))
    else:
        L.append("- Aucun cours — journée de travail libre.")

    if actifs:
        p = actifs[0]
        L.append("> 🔴 **Ma priorité : %s** — %s, %s, %s"
                 % (p["titre"], data["cours"][p["cours"]]["nom"], poids_txt(p), carte.jx(p["reste"])))
        L.append("> Si je ne fais qu'une seule chose aujourd'hui, c'est celle-là.")

    L.append("**À cocher aujourd'hui**")
    for tag, t in carte.taches_du_jour(data, jour, actifs):
        L.append("- [ ] **%s** — %s" % (ETAPE_LISIBLE.get(tag, tag.capitalize()), t))

    L.append("**Mes blocs de travail**")
    if bj:
        for b in bj:
            L.append("- ⏱️ `%s – %s` %s" % (h(b["debut"]), h(b["fin"]), b["titre"]))
    else:
        L.append("- Journée libre — repos assumé, c'est prévu.")
    conseil = conseil_du_jour(data, jour, actifs, bj)
    if conseil:
        L.append("> 💡 %s" % conseil)
    L.append("---")

    # ---------------- sept prochains jours
    fin7 = jour + dt.timedelta(days=7)
    L.append("## ⚡ Mes sept prochains jours — %s au %s" % (carte.court(jour), carte.court(fin7)))
    for t in data["taches_admin"]:
        if t["pour"] == "recurrent":
            continue
        ech = d(t["pour"])
        if ech < jour and t.get("urgent"):
            L.append("- [ ] 🔴 %s — **en retard depuis le %s**" % (t["quoi"], carte.court(ech)))
        elif jour <= ech <= fin7:
            L.append("- [ ] %s %s — pour le %s" % ("🔴" if t.get("urgent") else "🔵",
                                                   t["quoi"], carte.court(ech)))
    for l in data["lectures"]:
        ech = d(l["pour"])
        if jour <= ech <= fin7:
            L.append("- [ ] %s %s — pour le %s" % (ICONE[l["cours"]], l["quoi"], carte.court(ech)))
    for e in tous:
        if e["reste"] <= 7:
            etape = ETAPE_LISIBLE.get(carte.etape(dict(e, reste=e["reste"])), "").lower()
            L.append("- [ ] %s %s — %s, %s (%s)"
                     % (ICONE[e["cours"]], e["titre"], data["cours"][e["cours"]]["court"],
                        carte.jx(e["reste"]), etape))
    L.append("---")

    # ---------------- semaines rouges
    rouges = semaines_rouges(data, jour)
    L.append("## 🔴 Mes semaines rouges — %d encore devant moi" % len(rouges))
    lignes = []
    for num, debut, fin, dedans, total in rouges:
        quoi = ", ".join("%s %s %s" % (ICONE[e["cours"]], e["titre"],
                                       ("%d %%" % e["poids"]) if e["poids"] else "formatif")
                         for e in sorted(dedans, key=lambda e: d(e["date"])))
        lignes.append(["**%d**" % num, "%s – %s" % (carte.court(debut), carte.court(fin)),
                       quoi, regle_semaine(num, dedans, total, data)])
    L.append(tableau(["Semaine", "Dates", "Ce qui tombe", "La règle"], lignes))
    L.append("---")

    # ---------------- toutes les echeances
    L.append("## 📅 Toutes mes échéances")
    L.append("> 💡 Sélectionne ce tableau → **Transformer en base de données** pour filtrer par cours "
             "et trier par date.")
    lignes = []
    for ev in sorted(data["evaluations"], key=lambda e: (d(e["date"]), -e["poids"])):
        ech = d(ev["date"])
        reste = (ech - jour).days
        if ev.get("fait") or reste < 0:
            marque, compte = "✅", "✅ fait"
        else:
            marque, compte = pastille(reste), carte.jx(reste)
        co = data["cours"][ev["cours"]]
        lignes.append([marque, long_(ech), "%s %s" % (ICONE[ev["cours"]], co["court"]),
                       titre_ev(data, ev), poids_txt(ev), compte])
    L.append(tableau(["", "Date", "Cours", "Évaluation", "Poids", "Compte à rebours"], lignes))
    L.append("---")

    # ---------------- semaine type
    total_min = 0
    lignes = []
    for b in data["blocs_travail"]:
        deb = dt.datetime.strptime(b["debut"], "%H:%M")
        f = dt.datetime.strptime(b["fin"], "%H:%M")
        mins = int((f - deb).total_seconds() // 60)
        total_min += mins
        duree = "%d h %02d" % (mins // 60, mins % 60) if mins % 60 else "%d h" % (mins // 60)
        gras = mins >= 180
        quand = "%s %s – %s" % (JOURS[b["jour"] - 1].capitalize(), h(b["debut"]), h(b["fin"]))
        icones = "".join(ICONE.get(c, "🔁") for c in b["focus"])
        lignes.append([("**%s**" % quand) if gras else quand,
                       ("**%s**" % duree) if gras else duree,
                       "%s %s" % (icones, b["titre"])])
    L.append("## 🗓️ Ma semaine type — %d h %02d de travail" % (total_min // 60, total_min % 60))
    L.append(tableau(["Quand", "Durée", "Ce que je fais"], lignes))
    L.append("> ⚠️ Vendredi soir, samedi après-midi et dimanche matin restent volontairement vides. "
             "**Ne pas les remplir** : c'est ce qui rend le reste tenable, semaine après semaine.")
    L.append("---")

    # ---------------- methodes
    L.append("## 🧠 Mes méthodes, cours par cours")
    dur = max(c["difficulte"] for c in data["cours"].values())
    for cle, texte in METHODES:
        co = data["cours"][cle]
        L.append("### %s %s" % (ICONE[cle], co["nom"]))
        if co["difficulte"] >= dur:
            L.append("*Cours où je me sens le plus fragile — c'est là que va le temps en priorité.*")
        L.append(texte)
    L.append("---")

    # ---------------- rattrapage
    L.append("## 🔁 Si je prends du retard")
    L.append("> Le dimanche 16 h – 18 h ne sert **qu'à ça** : reprendre ce qui a sauté dans la semaine "
             "et refaire le plan des sept jours suivants. Rien d'autre ne s'y planifie.")
    for r in RATTRAPAGE:
        L.append("- %s" % r)
    L.append("---")

    # ---------------- a confirmer
    L.append("## ✅ À faire confirmer auprès des profs")
    for t in data["taches_admin"]:
        if t["pour"] == "recurrent":
            L.append("- [ ] 🔁 %s" % t["quoi"])
            continue
        ech = d(t["pour"])
        if ech < jour and t.get("urgent"):
            L.append("- [ ] 🔴 %s — **en retard depuis le %s**" % (t["quoi"], carte.court(ech)))
        else:
            L.append("- [ ] %s %s — pour le %s" % ("🔴" if t.get("urgent") else "🔵",
                                                   t["quoi"], carte.court(ech)))
    L.append("---")

    # ---------------- avancement
    L.append("## 📊 Mon avancement")
    av = carte.avancement(data, jour)
    lignes = [["%s %s" % (ICONE[cle], data["cours"][cle]["court"]), "%d %%" % pct]
              for cle, (nom, pct) in av.items()]
    L.append(tableau(["Cours", "Part de la note déjà jouée"], lignes))
    moy = sum(p for _, p in av.values()) / len(av)
    reste_j = (d(ses["fin"]) - jour).days
    L.append("> **%d %%** de la session est joué en moyenne. Il reste %d jours avant le %s"
             % (round(moy), reste_j, carte.court(d(ses["fin"]))))
    L.append("---")
    L.append("*Page régénérée par **`notion.py`** à partir de **`donnees-session.json`**. "
             "La carte du jour arrive chaque matin dans Slack.*")
    return "\n".join(L)


def main():
    args = sys.argv[1:]
    jour = d(args[0]) if args else dt.date.today()
    print(page(carte.charger(), jour))


if __name__ == "__main__":
    main()

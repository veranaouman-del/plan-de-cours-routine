# -*- coding: utf-8 -*-
"""Tableau de bord Notion — Automne 2026.

Régénère le contenu de la page Notion « Ma session — Automne 2026 » à partir de
donnees-session.json. Le script écrit du Markdown sur la sortie standard ; c'est
ce texte qui est passé à l'outil Notion (commande replace_content) pour remplacer
la page en entier.

    python3 notion.py                 -> la page d'aujourd'hui
    python3 notion.py 2026-10-07      -> la page telle qu'elle serait ce jour-là
    python3 notion.py --sortie p.md   -> écrit dans un fichier au lieu de stdout

Complémentaire à carte.py : carte.py répond « quoi faire aujourd'hui »,
notion.py garde la vue d'ensemble de la session. Les deux lisent le même JSON,
donc une échéance qui bouge se change à un seul endroit.
"""
import os
import sys
import datetime as dt

import carte
from carte import (JOURS, MOIS, charger, d, court, jx, semaine_de,
                   en_semaine_etudes, cours_du_jour, blocs_du_jour,
                   chantiers, chantiers_tous, taches_du_jour, avancement)

BASE = os.path.dirname(os.path.abspath(__file__))

# Une semaine est « rouge » si elle pèse lourd ou si elle empile les remises.
SEUIL_POIDS = 30
SEUIL_NOMBRE = 3


def heure(h):
    """08:55 -> « 8 h 55 », 18:00 -> « 18 h ». Comme on l'écrit en français."""
    hh, mm = h.split(":")
    return "%d h" % int(hh) if mm == "00" else "%d h %s" % (int(hh), mm)


def long(j):
    return "%s %d %s" % (JOURS[j.weekday()], j.day, MOIS[j.month - 1])


def emo(data, cle):
    return data["cours"][cle].get("emoji", "•")


def libelle(data, e):
    """Titre d'une évaluation, avec la mention « à confirmer » s'il y a lieu."""
    t = e["titre"]
    if e.get("a_confirmer"):
        t += " *(date à confirmer)*"
    return t


def poids_texte(e):
    if not e["poids"]:
        return "formatif"
    p = "%d %%" % e["poids"]
    if e["poids"] >= 20:
        p = "**%s**" % p
    if e.get("poids_approx"):
        p += " *(à confirmer)*"
    return p


def etat_admin(data, t, jour):
    """Pastille + échéance d'une tâche administrative, écrites une seule fois."""
    echeance = d(t["pour"])
    if echeance < jour:
        etat = "**en retard**"
    elif t.get("note"):
        # la note dit pourquoi ça traîne : « en retard depuis la semaine 3 »
        etat = "**%s**" % t["note"].rstrip(".").lower()
    else:
        etat = "pour le %s" % court(echeance)
    reste = (echeance - jour).days
    if reste < 0 or t.get("urgent"):
        pastille = "\U0001f534"
    elif reste <= 14:
        pastille = "\U0001f7e0"
    else:
        pastille = "\U0001f535"
    return pastille, etat


def bornes_semaine(data, num):
    debut = d(data["session"]["semaines"][str(num)])
    return debut, debut + dt.timedelta(days=6)


def semaines_rouges(data, jour):
    """Les semaines où tout tombe en même temps. Calculées, jamais écrites à la main."""
    out = []
    for num in sorted((int(n) for n in data["session"]["semaines"]), key=int):
        debut, fin = bornes_semaine(data, num)
        dedans = [e for e in data["evaluations"]
                  if not e.get("fait") and debut <= d(e["date"]) <= fin]
        total = sum(e["poids"] for e in dedans)
        if not dedans or (total < SEUIL_POIDS and len(dedans) < SEUIL_NOMBRE):
            continue
        regle = data.get("regles_semaines", {}).get(str(num))
        if not regle:
            regle = ("%d %% de la session en une semaine. Rien ne commence ce lundi-là."
                     % total)
        out.append((num, debut, fin, sorted(dedans, key=lambda e: d(e["date"])), regle, fin >= jour))
    return out


def table(lignes):
    """Tableau Notion : en-tête, puis les lignes."""
    L = ['<table header-row="true">']
    for ligne in lignes:
        L.append("<tr>")
        for cellule in ligne:
            L.append("<td>%s</td>" % cellule)
        L.append("</tr>")
    L.append("</table>")
    return L


# --------------------------------------------------------------------------
# Les sections
# --------------------------------------------------------------------------
def entete(data, jour):
    sem = semaine_de(data, jour)
    a, b = data["session"]["semaine_etudes"]
    if en_semaine_etudes(data, jour):
        situation = "**Nous sommes dans la semaine d'études.**"
    elif sem:
        situation = "**Nous sommes en semaine %d sur 15.**" % sem
    else:
        situation = "**La session est terminée.**"
    return [
        "> %s" % data["programme"].replace("- Cegep de Granby", "— Cégep de Granby"),
        "> Du %s au %s · Semaine d'études : %s au %s"
        % (court(d(data["session"]["debut"])), court(d(data["session"]["fin"])),
           court(d(a)), court(d(b))),
        "> %s Page mise à jour le %s." % (situation, long(jour)),
        "---",
    ]


def section_aujourdhui(data, jour):
    """Le bloc qui répond en dix secondes : qu'est-ce que je fais maintenant ?"""
    actifs = chantiers(data, jour)
    L = ["## ☀️ Aujourd'hui — %s" % long(jour)]

    cj = cours_du_jour(data, jour)
    if cj:
        L.append("**Mes cours**")
        for c in cj:
            co = data["cours"][c["cours"]]
            L.append("- %s `%s – %s` %s — %s"
                     % (co.get("emoji", "•"), heure(c["debut"]), heure(c["fin"]),
                        co["nom"], c["local"]))
    else:
        L.append("**Aucun cours aujourd'hui.**")

    if actifs:
        p = actifs[0]
        L.append("> 🔴 **Ma priorité : %s** — %s, %s, %s"
                 % (p["titre"], data["cours"][p["cours"]]["nom"],
                    poids_texte(p).replace("**", ""), jx(p["reste"])))
        L.append("> Si je ne fais qu'une seule chose aujourd'hui, c'est celle-là.")

    L.append("**À cocher aujourd'hui**")
    for tag, t in taches_du_jour(data, jour, actifs):
        marque = "🔴 " if tag in ("RETARD", "REMISE") else ""
        L.append("- [ ] %s**%s** — %s" % (marque, tag.capitalize(), t))

    bj = blocs_du_jour(data, jour)
    if bj:
        L.append("**Mes blocs de travail**")
        for b in bj:
            L.append("- ⏱️ `%s – %s` %s" % (heure(b["debut"]), heure(b["fin"]), b["titre"]))
    else:
        L.append("> ☕ Aucun bloc de travail prévu. Repos assumé — c'est ce qui rend le reste tenable.")

    L.append("---")
    return L


def section_sept_jours(data, jour):
    fin = jour + dt.timedelta(days=7)
    L = ["## ⚡ Mes sept prochains jours — %s au %s" % (court(jour), court(fin))]

    for t in data["taches_admin"]:
        if t["pour"] == "recurrent":
            continue
        if d(t["pour"]) > fin:
            continue
        pastille, etat = etat_admin(data, t, jour)
        L.append("- [ ] %s %s — %s" % (pastille, t["quoi"], etat))

    for l in data["lectures"]:
        if jour <= d(l["pour"]) <= fin:
            L.append("- [ ] %s %s — pour le %s"
                     % (emo(data, l["cours"]), l["quoi"], court(d(l["pour"]))))

    for e in chantiers(data, jour):
        if e["reste"] <= 7:
            L.append("- [ ] %s %s — %s, %s (%s)"
                     % (emo(data, e["cours"]), e["titre"],
                        data["cours"][e["cours"]]["court"], jx(e["reste"]),
                        carte.etape(e).lower()))
    L.append("---")
    return L


def section_semaines_rouges(data, jour):
    rouges = semaines_rouges(data, jour)
    devant = [r for r in rouges if r[5]]
    L = ["## 🔴 Mes semaines rouges — %d encore devant moi" % len(devant)]
    lignes = [["Semaine", "Dates", "Ce qui tombe", "La règle"]]
    for num, debut, fin, dedans, regle, a_venir in rouges:
        if not a_venir:
            continue
        quoi = ", ".join("%s %s %s" % (emo(data, e["cours"]), e["titre"],
                                       ("%d %%" % e["poids"]) if e["poids"] else "formatif")
                         for e in dedans)
        lignes.append(["**%d**" % num,
                       "%s – %s" % (court(debut), court(fin)),
                       quoi, regle])
    L += table(lignes)
    L.append("---")
    return L


def section_echeances(data, jour):
    L = ["## 📅 Toutes mes échéances",
         "> 💡 Sélectionne ce tableau → **Transformer en base de données** "
         "pour filtrer par cours et trier par date."]
    lignes = [["", "Date", "Cours", "Évaluation", "Poids", "Compte à rebours"]]

    passees = sorted((e for e in data["evaluations"]
                      if e.get("fait") or d(e["date"]) < jour), key=lambda e: d(e["date"]))
    for e in passees:
        co = data["cours"][e["cours"]]
        lignes.append(["✅", long(d(e["date"])), "%s %s" % (co.get("emoji", "•"), co["court"]),
                       e["titre"], "%d %%" % e["poids"], "✅ fait"])

    for e in chantiers_tous(data, jour):
        co = data["cours"][e["cours"]]
        pastille = "🔴" if e["reste"] <= 7 else ("🟠" if e["reste"] <= 21 else "🔵")
        lignes.append([pastille, long(d(e["date"])), "%s %s" % (co.get("emoji", "•"), co["court"]),
                       libelle(data, e), poids_texte(e), jx(e["reste"])])

    L += table(lignes)
    L.append("---")
    return L


def section_semaine_type(data):
    total = 0.0
    lignes = [["Quand", "Durée", "Ce que je fais"]]
    for b in sorted(data["blocs_travail"], key=lambda b: (b["jour"], b["debut"])):
        h1 = dt.datetime.strptime(b["debut"], "%H:%M")
        h2 = dt.datetime.strptime(b["fin"], "%H:%M")
        heures = (h2 - h1).seconds / 3600.0
        total += heures
        duree = "%d h" % heures if heures == int(heures) else "%d h %02d" % (int(heures), round((heures % 1) * 60))
        gros = b["titre"].startswith("GROS BLOC") or heures >= 3
        quand = "%s %s – %s" % (JOURS[b["jour"] - 1].capitalize(), heure(b["debut"]), heure(b["fin"]))
        focus = " ".join(emo(data, f) for f in b["focus"] if f in data["cours"]) or "🔁"
        titre = "%s %s" % (focus, b["titre"])
        lignes.append(["**%s**" % quand if gros else quand,
                       "**%s**" % duree if gros else duree,
                       "**%s**" % titre if gros else titre])

    entier = "%d h %02d" % (int(total), round((total % 1) * 60)) if total % 1 else "%d h" % total
    L = ["## 🗓️ Ma semaine type — %s de travail" % entier]
    L += table(lignes)
    L.append("> ⚠️ Vendredi soir, samedi après-midi et dimanche matin restent **vides**. "
             "Ce n'est pas du temps perdu : c'est ce qui rend les %s restantes tenables "
             "semaine après semaine." % entier)
    L.append("---")
    return L


def section_methodes(data):
    L = ["## 🧠 Mes méthodes, cours par cours"]
    ordre = sorted(data["cours"].items(), key=lambda kv: -kv[1].get("difficulte", 3))
    for cle, co in ordre:
        methode = data.get("methodes", {}).get(cle)
        if not methode:
            continue
        L.append("### %s %s" % (co.get("emoji", "•"), co["nom"]))
        if co.get("difficulte", 3) >= 4:
            L.append("*Cours où je me sens le plus fragile — c'est là que va le temps en priorité.*")
        L.append(methode)
    L.append("---")
    return L


def section_profs(data, jour):
    L = ["## ✅ À faire confirmer auprès des profs"]
    for t in data["taches_admin"]:
        if t["pour"] == "recurrent":
            L.append("- [ ] 🔁 %s" % t["quoi"])
            continue
        pastille, etat = etat_admin(data, t, jour)
        L.append("- [ ] %s %s — %s" % (pastille, t["quoi"], etat))
    L.append("---")
    return L


def section_avancement(data, jour):
    L = ["## 📊 Mon avancement"]
    lignes = [["Cours", "Part de la note déjà jouée"]]
    total = 0
    for cle, (nom, pct) in avancement(data, jour).items():
        total += pct
        lignes.append(["%s %s" % (emo(data, cle), nom), "%d %%" % pct])
    L += table(lignes)
    restants = (d(data["session"]["fin"]) - jour).days
    fini = restants <= 0
    L.append("> **%d %%** de la session est joué en moyenne. %s"
             % (round(total / max(len(data["cours"]), 1)),
                "La session est terminée." if fini else
                ("Il reste %d jours avant le %s"
                 % (restants, court(d(data["session"]["fin"])).rstrip("."))) + "."))
    L.append("---")
    return L


# --------------------------------------------------------------------------
def page(data, jour):
    L = []
    L += entete(data, jour)
    L += section_aujourdhui(data, jour)
    L += section_sept_jours(data, jour)
    L += section_semaines_rouges(data, jour)
    L += section_echeances(data, jour)
    L += section_semaine_type(data)
    L += section_methodes(data)
    L += section_profs(data, jour)
    L += section_avancement(data, jour)
    L.append("*Page regénérée par `notion.py` à partir de `donnees-session.json`. "
             "La carte du jour arrive chaque matin dans Slack.*")
    return "\n".join(L)


def main():
    args = sys.argv[1:]
    sortie = None
    if "--sortie" in args:
        i = args.index("--sortie")
        sortie = args[i + 1]
        args = args[:i] + args[i + 2:]
    jour = d(args[0]) if args else dt.date.today()

    texte = page(charger(), jour)
    if sortie:
        with open(sortie, "w", encoding="utf-8") as fh:
            fh.write(texte)
        print(sortie)
    else:
        print(texte)


if __name__ == "__main__":
    main()

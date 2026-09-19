# -*- coding: utf-8 -*-
"""Page Notion « Ma session » — Automne 2026.

Régénère le tableau de bord Notion à partir de donnees-session.json, au format
Markdown enrichi de Notion (tableaux <table>, cases à cocher, citations).

    python3 notion.py                 -> la page d'aujourd'hui sur la sortie standard
    python3 notion.py 2026-10-07      -> la page telle qu'elle serait ce jour-là
    python3 notion.py --sortie p.md   -> écrit dans un fichier

Le texte produit se colle tel quel dans notion-update-page (commande
« replace_content ») sur la page 3df73824-e620-811e-9e6c-d07440cb6ec7.

Rien n'est codé en dur ici : pour changer une échéance, éditer donnees-session.json.
"""
import sys
import datetime as dt

import carte
from carte import (d, court, jx, charger, semaine_de, en_semaine_etudes,
                   cours_du_jour, blocs_du_jour, chantiers, chantiers_tous,
                   taches_du_jour, etape, avancement, JOURS, MOIS)

PAGE_ID = "3df73824-e620-811e-9e6c-d07440cb6ec7"

# Une semaine est « rouge » quand au moins deux évaluations NOTÉES y tombent et
# qu'elles pèsent ensemble 20 % ou plus : au-delà, la semaine ne se rattrape plus,
# elle se prépare la semaine d'avant. Un atelier formatif ne rougit pas une semaine.
SEUIL_ROUGE_POIDS = 20
SEUIL_ROUGE_NOMBRE = 2

ETIQUETTES = {"REMISE": "Remise", "FINIR": "Finir", "AVANCER": "Avancer",
              "RELIRE": "Relire", "TEST BLANC": "Test blanc", "FICHES": "Fiches",
              "NOTES": "Notes", "ADMIN": "Admin", "RETARD": "En retard",
              "LECTURE": "Lecture"}


def emo(data, cle):
    return data["cours"][cle].get("emoji", "•")


def nom(data, cle):
    return data["cours"][cle]["nom"]


def poids_txt(e):
    if not e["poids"]:
        return "formatif"
    txt = "%d %%" % e["poids"]
    if e["poids"] >= 20:
        txt = "**%s**" % txt
    if e.get("poids_approx"):
        txt += " *(à confirmer)*"
    return txt


def long(j):
    return "%s %d %s" % (JOURS[j.weekday()], j.day, MOIS[j.month - 1])


def heure(h):
    hh, mm = h.split(":")
    return "%d h" % int(hh) if mm == "00" else "%d h %s" % (int(hh), mm)


def tableau(entetes, lignes):
    out = ['<table header-row="true">', "<tr>"]
    out += ["<td>%s</td>" % c for c in entetes]
    out.append("</tr>")
    for ligne in lignes:
        out.append("<tr>")
        out += ["<td>%s</td>" % c for c in ligne]
        out.append("</tr>")
    out.append("</table>")
    return "\n".join(out)


# --------------------------------------------------------------------------
# Semaines rouges
# --------------------------------------------------------------------------
def semaines_rouges(data, jour):
    out = []
    for num, debut in sorted(((int(n), d(x)) for n, x in data["session"]["semaines"].items())):
        fin = debut + dt.timedelta(days=6)
        dedans = [e for e in data["evaluations"] if debut <= d(e["date"]) <= fin]
        total = sum(e["poids"] for e in dedans)
        notees = [e for e in dedans if e["poids"]]
        if len(notees) < SEUIL_ROUGE_NOMBRE or total < SEUIL_ROUGE_POIDS:
            continue
        regle = data.get("regles_semaines", {}).get(str(num))
        if not regle:
            regle = "%d %% de la session en une semaine. Rien ne commence ce lundi-là." % total
        out.append({"num": num, "debut": debut, "fin": fin, "evals": dedans,
                    "total": total, "regle": regle, "passee": fin < jour})
    return out


# --------------------------------------------------------------------------
# La page
# --------------------------------------------------------------------------
def page(data, jour):
    sem = semaine_de(data, jour)
    actifs = chantiers(data, jour)
    tous = chantiers_tous(data, jour)
    s = data["session"]
    L = []

    # En-tête ------------------------------------------------------------
    L.append("> %s" % data["programme"].replace(" - ", " — "))
    L.append("> Du %s au %s · Semaine d'études : %s au %s"
             % (court(d(s["debut"])), court(d(s["fin"])),
                court(d(s["semaine_etudes"][0])), court(d(s["semaine_etudes"][1]))))
    if sem:
        L.append("> **Nous sommes en semaine %d sur 15.** Page mise à jour le %s." % (sem, long(jour)))
    L.append("---")

    # Aujourd'hui --------------------------------------------------------
    L.append("## ☀️ Aujourd'hui — %s" % long(jour))
    L.append("**Mes cours**")
    cj = cours_du_jour(data, jour)
    if cj:
        for c in cj:
            L.append("- %s `%s – %s` %s — %s"
                     % (emo(data, c["cours"]), heure(c["debut"]), heure(c["fin"]),
                        nom(data, c["cours"]), c["local"]))
    elif en_semaine_etudes(data, jour):
        L.append("- 🌴 Semaine d'études et d'encadrement — aucun cours")
    else:
        L.append("- 🏠 Aucun cours aujourd'hui")

    if actifs:
        p = actifs[0]
        L.append("> 🔴 **Ma priorité : %s** — %s, %d %%, %s"
                 % (p["titre"], nom(data, p["cours"]), p["poids"], jx(p["reste"])))
        L.append("> Si je ne fais qu'une seule chose aujourd'hui, c'est celle-là.")

    L.append("**À cocher aujourd'hui**")
    for tag, t in taches_du_jour(data, jour, actifs):
        L.append("- [ ] **%s** — %s" % (ETIQUETTES.get(tag, tag.title()), t))

    L.append("**Mes blocs de travail**")
    bj = blocs_du_jour(data, jour)
    if bj:
        for b in bj:
            L.append("- ⏱️ `%s – %s` %s" % (heure(b["debut"]), heure(b["fin"]), b["titre"]))
    else:
        L.append("- 🌙 Journée libre — repos assumé, et c'est prévu comme ça")
    L.append("---")

    # Sept prochains jours ------------------------------------------------
    fin7 = jour + dt.timedelta(days=7)
    L.append("## ⚡ Mes sept prochains jours — %s au %s" % (court(jour), court(fin7)))
    for t in data["taches_admin"]:
        if t["pour"] == "recurrent" or t.get("fait"):
            continue
        echeance = d(t["pour"])
        if echeance <= fin7:
            suffixe = ("**en retard depuis le %s**" % court(echeance)) if echeance < jour \
                else ("pour le %s" % court(echeance))
            L.append("- [ ] %s %s — %s" % ("🔴" if t.get("urgent") else "🟠", t["quoi"], suffixe))
    for l in data["lectures"]:
        reste = (d(l["pour"]) - jour).days
        if 0 <= reste <= 7:
            L.append("- [ ] %s %s — pour le %s" % (emo(data, l["cours"]), l["quoi"], court(d(l["pour"]))))
    for e in tous:
        if e["reste"] <= 7:
            L.append("- [ ] %s %s — %s, %s (%s)"
                     % (emo(data, e["cours"]), e["titre"], data["cours"][e["cours"]]["court"],
                        jx(e["reste"]), ETIQUETTES.get(etape(dict(e, reste=e["reste"])), "").lower()))
    L.append("---")

    # Semaines rouges ------------------------------------------------------
    rouges = semaines_rouges(data, jour)
    devant = [r for r in rouges if not r["passee"]]
    L.append("## 🔴 Mes semaines rouges — %d encore devant moi" % len(devant))
    lignes = []
    for r in devant:
        quoi = ", ".join("%s %s %s" % (emo(data, e["cours"]), e["titre"],
                                       ("%d %%" % e["poids"]) if e["poids"] else "formatif")
                         for e in sorted(r["evals"], key=lambda e: e["date"]))
        lignes.append(["**%d**" % r["num"], "%s – %s" % (court(r["debut"]), court(r["fin"])),
                       quoi, r["regle"]])
    L.append(tableau(["Semaine", "Dates", "Ce qui tombe", "La règle"], lignes))
    L.append("---")

    # Toutes les échéances -------------------------------------------------
    L.append("## 📅 Toutes mes échéances")
    L.append("> 💡 Sélectionne ce tableau → **Transformer en base de données** "
             "pour filtrer par cours et trier par date.")
    lignes = []
    for e in sorted(data["evaluations"], key=lambda e: (e["date"], -e["poids"])):
        echeance = d(e["date"])
        reste = (echeance - jour).days
        if e.get("fait") or reste < 0:
            pastille, compte = "✅", "✅ fait"
        elif reste <= 7:
            pastille, compte = "🔴", jx(reste)
        elif reste <= 21:
            pastille, compte = "🟠", jx(reste)
        else:
            pastille, compte = "🔵", jx(reste)
        titre = e["titre"] + (" *(date à confirmer)*" if e.get("a_confirmer") else "")
        lignes.append([pastille, long(echeance),
                       "%s %s" % (emo(data, e["cours"]), data["cours"][e["cours"]]["court"]),
                       titre, poids_txt(e), compte])
    L.append(tableau(["", "Date", "Cours", "Évaluation", "Poids", "Compte à rebours"], lignes))
    L.append("---")

    # Semaine type ---------------------------------------------------------
    total_h = 0.0
    lignes = []
    for b in sorted(data["blocs_travail"], key=lambda b: (b["jour"], b["debut"])):
        h1 = dt.datetime.strptime(b["debut"], "%H:%M")
        h2 = dt.datetime.strptime(b["fin"], "%H:%M")
        heures = (h2 - h1).seconds / 3600.0
        total_h += heures
        duree = "%d h" % heures if heures == int(heures) else "%d h %02d" % (int(heures), (heures % 1) * 60)
        quand = "%s %s – %s" % (JOURS[b["jour"] - 1].capitalize(), heure(b["debut"]), heure(b["fin"]))
        icones = " ".join(emo(data, f) for f in b["focus"] if f in data["cours"]) or "🔁"
        gros = "GROS BLOC" in b["titre"]
        lignes.append(["**%s**" % quand if gros else quand,
                       "**%s**" % duree if gros else duree,
                       "**%s %s**" % (icones, b["titre"]) if gros else "%s %s" % (icones, b["titre"])])
    total_txt = "%d h" % total_h if total_h == int(total_h) else "%d h %02d" % (int(total_h), (total_h % 1) * 60)
    L.append("## 🗓️ Ma semaine type — %s de travail" % total_txt)
    L.append(tableau(["Quand", "Durée", "Ce que je fais"], lignes))
    L.append("> ⚠️ Vendredi soir, samedi après-midi et dimanche matin restent **vides**. "
             "Ce n'est pas du temps perdu : c'est ce qui rend les %s restantes tenables "
             "semaine après semaine." % total_txt)
    L.append("---")

    # Méthodes --------------------------------------------------------------
    L.append("## 🧠 Mes méthodes, cours par cours")
    ordre = sorted(data["cours"], key=lambda c: -data["cours"][c]["difficulte"])
    for cle in ordre:
        c = data["cours"][cle]
        L.append("### %s %s" % (emo(data, cle), c["nom"]))
        if c["difficulte"] >= 4:
            L.append("*Cours où je me sens le plus fragile — c'est là que va le temps en priorité.*")
        L.append(data.get("methodes", {}).get(cle, ""))
    L.append("---")

    # Rattrapage ------------------------------------------------------------
    L.append("## 🔁 Si je prends du retard")
    L.append("> Le dimanche 16 h – 18 h ne sert **qu'à ça** : reprendre ce qui a sauté dans la "
             "semaine et refaire le plan des sept jours suivants. Rien d'autre ne s'y planifie.")
    L.append("- **Une journée sautée** → elle se reprend dans le bloc du dimanche, pas en "
             "empilant sur le lendemain.")
    L.append("- **Une semaine sautée** → je laisse tomber la prise d'avance du jeudi et je "
             "protège les deux gros blocs (mardi, mercredi).")
    L.append("- **Deux semaines de retard** → j'écris au prof concerné avant l'échéance, "
             "jamais après. Une remise négociée vaut mieux qu'une remise ratée.")
    L.append("---")

    # À confirmer -----------------------------------------------------------
    L.append("## ✅ À faire confirmer auprès des profs")
    for t in data["taches_admin"]:
        if t.get("fait"):
            continue
        if t["pour"] == "recurrent":
            L.append("- [ ] 🔁 %s" % t["quoi"])
            continue
        echeance = d(t["pour"])
        pastille = "🔴" if t.get("urgent") else ("🟠" if (echeance - jour).days <= 14 else "🔵")
        suffixe = ("**en retard depuis le %s**" % court(echeance)) if echeance < jour \
            else ("pour le %s" % court(echeance))
        L.append("- [ ] %s %s — %s" % (pastille, t["quoi"], suffixe))
    L.append("---")

    # Avancement ------------------------------------------------------------
    L.append("## 📊 Mon avancement")
    lignes, cumul = [], []
    for cle, (nom_c, pct) in avancement(data, jour).items():
        lignes.append(["%s %s" % (emo(data, cle), nom_c), "%d %%" % pct])
        cumul.append(pct)
    L.append(tableau(["Cours", "Part de la note déjà jouée"], lignes))
    reste_j = (d(s["fin"]) - jour).days
    L.append("> **%d %%** de la session est joué en moyenne. Il reste %d jours avant le %s"
             % (sum(cumul) / len(cumul), reste_j, court(d(s["fin"]))))
    L.append("---")
    L.append("*Page regénérée par **`notion.py`** à partir de **`donnees-session.json`**. "
             "La carte du jour arrive chaque matin dans Slack.*")
    return "\n".join(L)


def main():
    args = [a for a in sys.argv[1:]]
    sortie = None
    if "--sortie" in args:
        i = args.index("--sortie")
        sortie = args[i + 1]
        del args[i:i + 2]
    jour = d(args[0]) if args else dt.date.today()
    txt = page(charger(), jour)
    if sortie:
        with open(sortie, "w", encoding="utf-8") as fh:
            fh.write(txt)
        print("Écrit dans %s (%d caractères)" % (sortie, len(txt)))
    else:
        print(txt)


if __name__ == "__main__":
    main()

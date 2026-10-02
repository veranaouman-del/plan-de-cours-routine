# -*- coding: utf-8 -*-
"""Tableau de bord Notion — Automne 2026.

Génère le contenu complet de la page Notion « Ma session — Automne 2026 »
à partir de donnees-session.json. Même moteur que carte.py : une échéance
qui bouge se change à un seul endroit.

    python3 notion.py                 -> la page pour aujourd'hui, sur stdout
    python3 notion.py 2026-10-07      -> pour une date précise

Le texte produit est du Markdown enrichi Notion (blocs <table>). Il se passe
tel quel à notion-update-page, commande replace_content.
"""
import sys
import datetime as dt

import carte
from carte import (charger, d, semaine_de, en_semaine_etudes, chantiers,
                   chantiers_tous, cours_du_jour, blocs_du_jour, avancement,
                   etape, jx, JOURS, MOIS)

JOURS_ABREV = ["lun.", "mar.", "mer.", "jeu.", "ven.", "sam.", "dim."]
SEUIL_ROUGE = 30          # une semaine à 30 % ou plus se joue, elle ne se subit pas


# --------------------------------------------------------------------------
# Dates en français
# --------------------------------------------------------------------------
def jour_num(j):
    return "1er" if j.day == 1 else str(j.day)


def longue(j):
    return "%s %s %s" % (JOURS[j.weekday()], jour_num(j), MOIS[j.month - 1])


def brieve(j):
    return "%s %s %s" % (JOURS_ABREV[j.weekday()], jour_num(j), carte.ABREV[j.month - 1])


def hhmm(t):
    h, m = t.split(":")
    return "%d h" % int(h) if m == "00" else "%d h %s" % (int(h), m)


def nom(data, cle):
    c = data["cours"][cle]
    return "%s %s" % (c["emoji"], c["nom"])


def court_nom(data, cle):
    c = data["cours"][cle]
    return "%s %s" % (c["emoji"], c.get("court", c["nom"]))


def pct(poids):
    return "**%d %%**" % poids if poids >= 20 else ("%d %%" % poids if poids else "formatif")


def table(entetes, lignes):
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
# Lecture des données
# --------------------------------------------------------------------------
def span_semaine(data, num):
    debut = d(data["session"]["semaines"][str(num)])
    return debut, debut + dt.timedelta(days=6)


def semaines_rouges(data):
    """Toute semaine de session où il se joue SEUIL_ROUGE % ou plus, tous cours confondus."""
    out = []
    for num in sorted(int(n) for n in data["session"]["semaines"]):
        debut, fin = span_semaine(data, num)
        dedans = [e for e in data["evaluations"] if debut <= d(e["date"]) <= fin and e["poids"]]
        total = sum(e["poids"] for e in dedans)
        if total >= SEUIL_ROUGE:
            out.append((num, debut, fin, sorted(dedans, key=lambda e: -e["poids"]), total))
    return out


def en_retard(data, jour):
    """Évaluations passées encore marquées « non faites » : l'avancement reste une hypothèse."""
    out = []
    for e in data["evaluations"]:
        if e.get("fait") or not e["poids"]:
            continue
        echeance = d(e["date"])
        if echeance < jour:
            out.append((e, (jour - echeance).days))
    return sorted(out, key=lambda p: -p[1])


def admin(data, jour):
    urgents, suivants, recurrents = [], [], []
    for t in data["taches_admin"]:
        if t["pour"] == "recurrent":
            recurrents.append(t)
            continue
        reste = (d(t["pour"]) - jour).days
        if reste < 0:
            urgents.append((t, -reste))
        elif reste <= 14:
            suivants.append((t, reste))
    urgents.sort(key=lambda p: -p[1])
    suivants.sort(key=lambda p: p[1])
    return urgents, suivants, recurrents


# --------------------------------------------------------------------------
# La page
# --------------------------------------------------------------------------
def page(data, jour):
    sem = semaine_de(data, jour)
    actifs = chantiers(data, jour)
    aven = chantiers_tous(data, jour)
    L = []

    a, b = data["session"]["semaine_etudes"]
    L.append("# 🎓 Ma session — Automne 2026")
    L.append("> Cégep de Granby · Techniques de l'informatique (420.B0) · 24 août → 11 décembre")
    etiquette = ("**Semaine d'études**" if en_semaine_etudes(data, jour)
                 else ("**Semaine %d sur 15**" % sem if sem else "**Hors session**"))
    L.append("> %s · Semaine d'études : %s au %s %s"
             % (etiquette, d(a).day, d(b).day, MOIS[d(b).month - 1]))
    L.append("---")

    # ---- aujourd'hui
    L.append("## 📍 Aujourd'hui — %s" % longue(jour))
    cj, bj = cours_du_jour(data, jour), blocs_du_jour(data, jour)
    for c in cj:
        L.append("- %s · %s – %s · %s" % (nom(data, c["cours"]), hhmm(c["debut"]),
                                          hhmm(c["fin"]), c["local"]))
    for bl in bj:
        L.append("- 🎯 **%s** · %s – %s" % (bl["titre"], hhmm(bl["debut"]), hhmm(bl["fin"])))
    if not cj and not bj:
        L.append("- Journée libre — repos assumé, c'est prévu.")
    if actifs:
        p = actifs[0]
        L.append("> 🔥 **Priorité du jour :** %s — %s (%d %%), **%s**."
                 % (nom(data, p["cours"]), p["titre"], p["poids"], jx(p["reste"]).lower()))
    L.append("---")

    # ---- à faire aujourd'hui, avec l'étape de préparation
    L.append("## ✅ À faire aujourd'hui")
    for tag, t in carte.taches_du_jour(data, jour, actifs):
        puce = "🔴" if tag in ("RETARD", "REMISE") else ("🟠" if tag in ("FINIR", "TEST BLANC", "ADMIN") else "🔵")
        L.append("- [ ] %s **%s** — %s" % (puce, tag, t))
    L.append("---")

    # ---- les 7 prochains jours
    L.append("## 🗓️ Les 7 prochains jours")
    lignes = []
    for i in range(7):
        j = jour + dt.timedelta(days=i)
        libelle = "**%s**" % brieve(j) + (" ← *aujourd'hui*" if i == 0 else "")
        colonne = [court_nom(data, c["cours"]) for c in cours_du_jour(data, j)]
        colonne += ["%s – %s" % (hhmm(x["debut"]), hhmm(x["fin"])) for x in blocs_du_jour(data, j)]
        act = chantiers(data, j)
        dus = [e for e in act if e["reste"] == 0]
        if dus:
            e = max(dus, key=lambda x: x["poids"])
            quoi = "🔥 **%s — %s**" % (court_nom(data, e["cours"]), e["titre"])
        elif act:
            e = act[0]
            quoi = "%s — %s *(%s)*" % (court_nom(data, e["cours"]), e["titre"], etape(e).lower())
        else:
            quoi = "—"
        lignes.append([libelle, "<br>".join(colonne) or "—", quoi])
    L.append(table(["Jour", "Cours et blocs", "Ce que je fais"], lignes))
    L.append("---")

    # ---- remises passées jamais cochées
    retards = en_retard(data, jour)
    if retards:
        L.append("## 🔴 À confirmer — remises passées jamais cochées")
        L.append("> Ces évaluations sont passées et toujours marquées « non faites » dans `donnees-session.json`. "
                 "Tant qu'elles y sont, mon avancement est une hypothèse, pas un fait.")
        L.append(table(["Évaluation", "Cours", "Poids", "Était dû le", "Retard"],
                       [[e["titre"], court_nom(data, e["cours"]), pct(e["poids"]),
                         brieve(d(e["date"])), "%d jour%s" % (n, "s" if n > 1 else "")]
                        for e, n in retards]))
        L.append("- [ ] Cocher celles qui sont remises → l'avancement redevient exact")
        L.append("- [ ] Écrire au prof **le jour même** pour celles qui ne le sont pas")
        L.append("---")

    # ---- admin
    urgents, suivants, recurrents = admin(data, jour)
    if urgents or suivants or recurrents:
        L.append("## 📌 À régler tout de suite")
        for t, n in urgents:
            L.append("- [ ] 🔴 **%s** — *%d jour%s de retard*"
                     % (t["quoi"], n, "s" if n > 1 else ""))
        for t, n in suivants:
            L.append("- [ ] 🟠 %s — *%s*" % (t["quoi"], jx(n).lower()))
        for t in recurrents:
            L.append("- [ ] 🔁 %s" % t["quoi"])
        L.append("---")

    # ---- échéances
    L.append("## 📅 Toutes mes échéances à venir")
    L.append("> 💡 Sélectionne ce tableau → **Transformer en base de données** pour filtrer par cours "
             "et cocher au fur et à mesure.")
    lignes = []
    for e in aven:
        pastille = "🔴" if e["reste"] <= 4 else ("🟠" if e["reste"] <= 12 else "🔵")
        lignes.append([pastille, brieve(d(e["date"])), court_nom(data, e["cours"]),
                       e["titre"], pct(e["poids"]), jx(e["reste"])])
    L.append(table(["", "Date", "Cours", "Évaluation", "Poids", "Compte à rebours"], lignes))
    L.append("---")

    # ---- lectures
    futures = [l for l in data["lectures"] if d(l["pour"]) >= jour]
    if futures:
        L.append("## 📖 Mes lectures")
        L.append(table(["Pour le", "Cours", "À lire"],
                       [[brieve(d(l["pour"])), court_nom(data, l["cours"]), l["quoi"]]
                        for l in sorted(futures, key=lambda x: x["pour"])]))
        L.append("---")

    # ---- semaines rouges
    L.append("## 🔴 Mes semaines rouges")
    L.append("> Toute semaine de session où il se joue **%d %% ou plus** de points, tous cours confondus. "
             "C'est là que se gagne ou se perd la session." % SEUIL_ROUGE)
    lignes = []
    for num, debut, fin, evs, total in semaines_rouges(data):
        ici = " ← *ici*" if sem == num else ""
        quoi = " · ".join("%s %s %d %%" % (data["cours"][e["cours"]]["emoji"], e["titre"], e["poids"])
                          for e in evs)
        lignes.append(["**%d**%s" % (num, ici),
                       "%s – %s" % (jour_num(debut) + " " + carte.ABREV[debut.month - 1],
                                    jour_num(fin) + " " + carte.ABREV[fin.month - 1]),
                       quoi, "**%d %%**" % total])
    L.append(table(["Semaine", "Dates", "Ce qui tombe", "Poids total"], lignes))
    L.append("---")

    # ---- semaine type
    L.append("## 🗓️ Ma semaine type")
    lignes = []
    for bl in sorted(data["blocs_travail"], key=lambda x: (x["jour"], x["debut"])):
        h1 = dt.datetime.strptime(bl["debut"], "%H:%M")
        h2 = dt.datetime.strptime(bl["fin"], "%H:%M")
        mins = int((h2 - h1).total_seconds() // 60)
        duree = "%d h%s" % (mins // 60, (" %02d" % (mins % 60)) if mins % 60 else "")
        gros = bl["titre"].startswith("GROS BLOC") or "RATTRAPAGE" in bl["titre"]
        emos = "".join(data["cours"][f]["emoji"] for f in bl["focus"] if f in data["cours"]) or "🔁"
        quand = "%s %s – %s" % (JOURS[bl["jour"] - 1].capitalize(), hhmm(bl["debut"]), hhmm(bl["fin"]))
        titre = "%s %s" % (emos, bl["titre"])
        lignes.append(["**%s**" % quand if gros else quand, "**%s**" % duree if gros else duree,
                       "**%s**" % titre if gros else titre])
    L.append(table(["Quand", "Durée", "Ce que je fais"], lignes))
    L.append("> ⚠️ Vendredi soir, samedi après-midi et dimanche matin restent **vides**. "
             "Ce n'est pas du temps perdu : c'est ce qui rend le reste tenable semaine après semaine.")
    L.append("---")

    # ---- méthodes : classées par difficulté déclarée, le plus dur d'abord
    L.append("## 🧠 Mes méthodes, cours par cours")
    ordre = sorted(data["cours"].items(), key=lambda p: -p[1]["difficulte"])
    for cle, c in ordre:
        dur = " — *ma matière la plus difficile*" if c["difficulte"] >= 4 else ""
        L.append("### %s %s%s" % (c["emoji"], c["nom"], dur))
        L.append(METHODES[cle])
    L.append("---")

    L.append("## 🔁 Quand je prends du retard")
    L.append("Le bloc du dimanche 16 h – 18 h existe pour ça. L'ordre est toujours le même : "
             "**ce qui est noté le plus lourd et qui tombe le plus tôt d'abord.** "
             "Une lecture en retard se rattrape ; une remise manquée, non.")
    L.append("Si deux semaines de suite débordent, ce n'est pas un problème d'effort : c'est que le plan "
             "est trop chargé. On retire quelque chose plutôt que d'accumuler.")
    L.append("---")

    # ---- avancement
    L.append("## 📊 Mon avancement")
    av = sorted(avancement(data, jour).items(), key=lambda p: -p[1][1])
    L.append(table(["Cours", "Part de la note déjà jouée"],
                   [[nom(data, cle), "%d %%" % p] for cle, (_, p) in av]))
    total_joue = sum(p for _, (_, p) in av) / len(av) if av else 0
    L.append("> **%d %%** de la session est joué en moyenne, tous cours confondus." % round(total_joue))
    L.append("---")
    L.append("*Mis à jour automatiquement le %s · source : `donnees-session.json` · généré par `notion.py`*"
             % longue(jour))
    return "\n".join(L)


METHODES = {
    "anglais": "Tout se joue en classe. Remplir le journal Odyssey **le jour même** (5 % garantis). "
               "Les évaluations orales valent **45 %** du cours : elles se préparent **à voix haute**, "
               "pas par écrit. Enregistrer deux minutes au téléphone et se réécouter.",
    "philo":   "Droit aux notes de cours à **toutes** les évaluations. La vraie préparation, c'est donc de "
               "**construire de bonnes notes**, pas de mémoriser. Un tableau par penseur : thèse, critère "
               "du juste, objection principale, exemple concret. C'est ce tableau qu'on apporte à l'examen.",
    "litt":    "Annoter **pendant** la lecture, jamais après. Un carnet de citations classées par thème. "
               "Garder 10 minutes de relecture linguistique en fin de rédaction — la langue vaut **25 %** "
               "de chaque dissertation.",
    "devlog":  "Le code se retient par les doigts. Refaire les exercices dirigés **sans la correction**, "
               "puis comparer. S'entraîner à écrire du code **sur papier** — c'est ce qui est demandé "
               "à l'examen.",
    "web":     "Chaque TP s'appuie sur le précédent. Un TP bâclé se paie deux fois. Après chaque remise, "
               "noter en trois lignes **ce qui a bloqué** : c'est exactement ce qui tombera à l'Évaluation #1.",
}


def main():
    args = sys.argv[1:]
    jour = d(args[0]) if args else dt.date.today()
    print(page(charger(), jour))


if __name__ == "__main__":
    main()

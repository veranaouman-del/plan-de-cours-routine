# -*- coding: utf-8 -*-
"""Tableau de bord Notion — Automne 2026.

Régénère le corps complet de la page Notion « Ma session » à partir de
donnees-session.json. Sort du Markdown Notion prêt à coller / à pousser
par le connecteur.

    python3 notion.py                 -> la page d'aujourd'hui
    python3 notion.py 2026-10-05      -> la page telle qu'elle serait ce jour-là
    python3 notion.py 2026-10-05 /tmp/page.md

Même source de vérité que carte.py : une échéance se corrige à un seul
endroit, dans donnees-session.json, et les deux sorties suivent.
"""
import os
import sys
import datetime as dt

import carte

BASE = os.path.dirname(os.path.abspath(__file__))

EMOJI = {"devlog": "💻", "web": "🌐", "litt": "📕", "anglais": "🗣️", "philo": "⚖️"}
ETIQUETTE = {"RETARD": "En retard", "ADMIN": "Admin", "LECTURE": "Lecture",
             "REMISE": "Remise", "FINIR": "Finir", "AVANCER": "Avancer",
             "RELIRE": "Relire", "TEST BLANC": "Test blanc", "FICHES": "Fiches",
             "NOTES": "Notes"}


def long(j):
    return "%s %d %s" % (carte.JOURS[j.weekday()], j.day, carte.MOIS[j.month - 1])


def moyen(j):
    return "%d %s" % (j.day, carte.ABREV[j.month - 1])


def hm(t):
    return t.replace(":", " h ")


def ligne(cells):
    return "<tr>\n%s\n</tr>" % "\n".join("<td>%s</td>" % c for c in cells)


def tableau(entetes, lignes):
    corps = "\n".join([ligne(entetes)] + [ligne(l) for l in lignes])
    return '<table header-row="true">\n%s\n</table>' % corps


def nom(data, cle, court=False):
    c = data["cours"][cle]
    return "%s %s" % (EMOJI[cle], c["court"] if court else c["nom"])


def poids_txt(ev):
    if not ev["poids"]:
        return "formatif"
    t = "%d %%" % ev["poids"]
    if ev["poids"] >= 20:
        t = "**%s**" % t
    return t + (" *(à confirmer)*" if ev.get("poids_approx") else "")


# --------------------------------------------------------------------------
# Semaines : une semaine est « rouge » dès qu'elle porte 2 évaluations ou 20 %
# --------------------------------------------------------------------------
def semaines_chargees(data, jour):
    out = []
    for num, debut in sorted(data["session"]["semaines"].items(), key=lambda p: int(p[0])):
        d0 = carte.d(debut)
        d1 = d0 + dt.timedelta(days=6)
        evs = [e for e in data["evaluations"] if d0 <= carte.d(e["date"]) <= d1]
        if not evs:
            continue
        total = sum(e["poids"] for e in evs)
        if total < 20:          # sous 20 %, ce n'est pas une semaine rouge
            continue
        out.append((int(num), d0, d1, sorted(evs, key=lambda e: carte.d(e["date"])), total))
    return out


def bouclee(evs, jour):
    return all(e.get("fait") or carte.d(e["date"]) < jour for e in evs)


def regle(data, d0, evs, total, passee, pire):
    if passee:
        return "✅ Semaine bouclée : les %d évaluations sont derrière moi." % len(evs)
    lourde = max(evs, key=lambda e: e["poids"])
    phrase = "%d évaluations dans %d cours. La plus lourde : %s %d %% en %s." % (
        len(evs), len({e["cours"] for e in evs}), lourde["titre"], lourde["poids"],
        data["cours"][lourde["cours"]]["court"])
    # Au-dela de 60 points, la semaine ne se travaille plus pendant : elle se prepare avant.
    # Attention : ces poids portent sur des cours differents, leur somme n'est donc pas
    # un pourcentage. D'ou "points de note", et non "%".
    if total >= 60:
        cours_n = len({e["cours"] for e in evs})
        tete = ("**La semaine la plus lourde de la session : %d points de note sur %d cours.**"
                % (total, cours_n) if pire
                else "**Semaine à %d points de note sur %d cours.**" % (total, cours_n))
        phrase = ("%s Tout doit être prêt le %s au soir, avant que la semaine commence ; "
                  "les jours suivants ne servent qu'à repasser."
                  % (tete, moyen(d0 - dt.timedelta(days=1))))
    return phrase


# --------------------------------------------------------------------------
def page(data, jour):
    sem = carte.semaine_de(data, jour)
    actifs = carte.chantiers(data, jour)
    tous = carte.chantiers_tous(data, jour)
    fin = carte.d(data["session"]["fin"])
    L = []

    a, b = data["session"]["semaine_etudes"]
    L.append("> %s" % data["programme"].replace(" - ", " — "))
    L.append("> Du %s au %s · Semaine d'études : %s au %s" % (
        moyen(carte.d(data["session"]["debut"])), moyen(fin), moyen(carte.d(a)), moyen(carte.d(b))))
    L.append("> **Nous sommes en semaine %s sur 15.** Page mise à jour le %s." % (
        sem or "—", long(jour)))
    L.append("---")

    # ---- Aujourd'hui ----
    L.append("## ☀️ Aujourd'hui — %s" % long(jour))
    L.append("**Mes cours**")
    cj = carte.cours_du_jour(data, jour)
    if cj:
        for c in cj:
            L.append("- ⏱️ `%s – %s` %s — local %s" % (
                hm(c["debut"]), hm(c["fin"]), nom(data, c["cours"]), c["local"]))
    else:
        L.append("- Aucun cours — journée de travail libre.")

    if actifs:
        p = actifs[0]
        L.append("> 🔴 **Ma priorité : %s** — %s, %d %%, %s" % (
            p["titre"], data["cours"][p["cours"]]["court"], p["poids"], carte.jx(p["reste"])))
        L.append("> Si je ne fais qu'une seule chose aujourd'hui, c'est celle-là.")

    L.append("**À cocher aujourd'hui**")
    for tag, t in carte.taches_du_jour(data, jour, actifs):
        L.append("- [ ] **%s** — %s" % (ETIQUETTE.get(tag, tag.capitalize()), t))

    L.append("**Mes blocs de travail**")
    bj = carte.blocs_du_jour(data, jour)
    if bj:
        for bl in bj:
            L.append("- ⏱️ `%s – %s` %s" % (hm(bl["debut"]), hm(bl["fin"]), bl["titre"]))
    else:
        L.append("- Journée libre — repos assumé, c'est prévu au plan.")
    L.append("---")

    # ---- Sept prochains jours ----
    L.append("## ⚡ Mes sept prochains jours — %s au %s" % (
        moyen(jour), moyen(jour + dt.timedelta(days=7))))
    sept = []
    for t in data["taches_admin"]:
        if t["pour"] == "recurrent":
            continue
        ech = carte.d(t["pour"])
        if ech < jour and t.get("urgent"):
            sept.append("- [ ] 🔴 %s — **en retard depuis le %s**" % (t["quoi"], moyen(ech)))
        elif 0 <= (ech - jour).days <= 7:
            sept.append("- [ ] 🔵 %s — pour le %s" % (t["quoi"], moyen(ech)))
    for l in data["lectures"]:
        reste = (carte.d(l["pour"]) - jour).days
        if 0 <= reste <= 7:
            sept.append("- [ ] %s %s — pour le %s" % (
                EMOJI[l["cours"]], l["quoi"], moyen(carte.d(l["pour"]))))
    for e in tous:
        if e["reste"] <= 7:
            sept.append("- [ ] %s %s — %s, %s (%s)" % (
                EMOJI[e["cours"]], e["titre"], data["cours"][e["cours"]]["court"],
                carte.jx(e["reste"]), carte.etape(e).lower()))
    L.extend(sept or ["- Rien d'imposé cette semaine. C'est le moment de prendre de l'avance."])
    L.append("---")

    # ---- Semaines chargées ----
    chargees = semaines_chargees(data, jour)
    devant = [s for s in chargees if not bouclee(s[3], jour)]
    pire_total = max((s[4] for s in chargees), default=0)
    L.append("## 🔴 Mes semaines rouges — %d encore devant moi" % len(devant))
    lignes = []
    for num, d0, d1, evs, total in chargees:
        passee = bouclee(evs, jour)
        etiq = "~~%d~~" % num if passee else str(num)
        quoi = " · ".join("%s %s %s" % (EMOJI[e["cours"]], e["titre"],
                                        "%d %%" % e["poids"] if e["poids"] else "formatif")
                          for e in evs)
        lignes.append([etiq, "%s – %s" % (moyen(d0), moyen(d1)), quoi,
                       regle(data, d0, evs, total, passee, total == pire_total)])
    L.append(tableau(["Semaine", "Dates", "Ce qui tombe", "La règle"], lignes))
    L.append("---")

    # ---- Toutes les échéances ----
    L.append("## 📅 Toutes mes échéances")
    L.append("> 💡 Sélectionne ce tableau → **Transformer en base de données** "
             "pour filtrer par cours et trier par date.")
    lignes = []
    for e in sorted(data["evaluations"], key=lambda e: (carte.d(e["date"]), -e["poids"])):
        ech = carte.d(e["date"])
        reste = (ech - jour).days
        if e.get("fait") or reste < 0:
            pastille, compte = "✅", "✅ fait"
        else:
            pastille = "🔴" if reste <= 4 else ("🟠" if reste <= 12 else "🔵")
            compte = carte.jx(reste)
        titre = e["titre"] + (" *(date à confirmer)*" if e.get("a_confirmer") else "")
        lignes.append([pastille, long(ech), nom(data, e["cours"], court=True),
                       titre, poids_txt(e), compte])
    L.append(tableau(["", "Date", "Cours", "Évaluation", "Poids", "Compte à rebours"], lignes))
    L.append("---")

    # ---- Semaine type ----
    heures = 0.0
    lignes = []
    for bl in data["blocs_travail"]:
        h0 = dt.datetime.strptime(bl["debut"], "%H:%M")
        h1 = dt.datetime.strptime(bl["fin"], "%H:%M")
        duree = (h1 - h0).seconds / 3600
        heures += duree
        d_txt = "%d h" % duree if duree == int(duree) else "%d h %02d" % (int(duree), (duree % 1) * 60)
        gros = bl["titre"].startswith("GROS BLOC")
        quand = "%s %s – %s" % (carte.JOURS[bl["jour"] - 1].capitalize(), hm(bl["debut"]), hm(bl["fin"]))
        icones = "".join(EMOJI[f] for f in bl["focus"] if f in EMOJI) or "🔁"
        lignes.append(["**%s**" % quand if gros else quand,
                       "**%s**" % d_txt if gros else d_txt,
                       "%s %s" % (icones, bl["titre"])])
    total_txt = "%d h" % heures if heures == int(heures) else "%d h %02d" % (int(heures), (heures % 1) * 60)
    L.append("## 🗓️ Ma semaine type — %s de travail hors cours" % total_txt)
    L.append(tableau(["Quand", "Durée", "Ce que je fais"], lignes))
    L.append("> ⚠️ Vendredi soir, samedi après-midi et dimanche matin restent volontairement "
             "vides. **Ne pas les remplir** : c'est ce qui rend le reste tenable, semaine "
             "après semaine.")
    L.append("---")

    # ---- Méthodes ----
    L.append("## 🧠 Mes méthodes, cours par cours")
    dur = max(c["difficulte"] for c in data["cours"].values())
    for cle in sorted(data["cours"], key=lambda k: -data["cours"][k]["difficulte"]):
        L.append("### %s" % nom(data, cle))
        if data["cours"][cle]["difficulte"] >= dur:
            L.append("*Cours où je me sens le plus fragile — c'est là que va le temps en priorité.*")
        L.append(METHODES[cle])
    L.append("---")

    # ---- Rattrapage ----
    L.append("## 🔁 Si je prends du retard")
    L.append("> Le dimanche 16 h – 18 h ne sert **qu'à ça** : reprendre ce qui a sauté dans la "
             "semaine et refaire le plan des sept jours suivants. Rien d'autre ne s'y planifie.")
    L.append("- Une journée sautée → elle se reprend dans le bloc du dimanche, pas en empilant "
             "sur le lendemain.")
    L.append("- Une semaine sautée → je laisse tomber la prise d'avance du jeudi et je protège "
             "les deux gros blocs (mardi, mercredi).")
    L.append("- Deux semaines de retard → j'écris au prof concerné AVANT l'échéance, jamais "
             "après. Une remise négociée vaut mieux qu'une remise ratée.")
    if carte.d(b) >= jour:
        L.append("- Coussin suivant : la **semaine d'études, du %s au %s**" % (moyen(carte.d(a)), moyen(carte.d(b))))
    L.append("---")

    # ---- Profs ----
    L.append("## ✅ À faire confirmer auprès des profs")
    for t in data["taches_admin"]:
        if t["pour"] == "recurrent":
            L.append("- [ ] 🔁 %s" % t["quoi"])
            continue
        ech = carte.d(t["pour"])
        if ech < jour and t.get("urgent"):
            L.append("- [ ] 🔴 %s — **en retard depuis le %s**" % (t["quoi"], moyen(ech)))
        else:
            L.append("- [ ] 🔵 %s — pour le %s" % (t["quoi"], moyen(ech)))
    L.append("---")

    # ---- Avancement ----
    L.append("## 📊 Mon avancement")
    av = carte.avancement(data, jour)
    lignes = [[nom(data, cle, court=True), "%d %%" % pct] for cle, (_, pct) in av.items()]
    L.append(tableau(["Cours", "Part de la note déjà jouée"], lignes))
    moyenne = sum(p for _, p in av.values()) / len(av)
    L.append("> **%d %%** de la session est joué en moyenne, et il reste %d jours avant le %s"
             % (round(moyenne), (fin - jour).days, moyen(fin)))
    quinzaine = [e for e in tous if e["reste"] <= 15]
    if quinzaine:
        lourde = max(quinzaine, key=lambda e: e["poids"])
        L.append("> Les quinze prochains jours comptent **%d évaluations** dans %d cours ; "
                 "la plus lourde est %s (%d %%, %s)." % (
                     len(quinzaine), len({e["cours"] for e in quinzaine}),
                     lourde["titre"], lourde["poids"], carte.jx(lourde["reste"])))
    L.append("---")
    L.append("*Page régénérée par **`notion.py`** à partir de **`donnees-session.json`**. "
             "La carte du jour arrive chaque matin dans Slack.*")
    return "\n".join(L)


METHODES = {
    "litt": "Annoter PENDANT la lecture, jamais après. Un carnet de citations classées par "
            "thème. Garder 10 minutes de relecture linguistique en fin de rédaction : la "
            "langue vaut 25 % de chaque dissertation.",
    "philo": "Droit aux notes de cours à TOUTES les évaluations — donc la vraie préparation, "
             "c'est de construire de bonnes notes. Un tableau par penseur : thèse, critère du "
             "juste, objection, exemple.",
    "anglais": "Tout se joue en classe. Remplir le journal Odyssey le jour même (5 % garantis). "
               "Les évaluations orales valent 45 % du cours : elles se préparent à voix haute, "
               "pas par écrit.",
    "devlog": "Le code se retient par les doigts. Refaire les exercices dirigés SANS la "
              "correction, puis comparer. S'entraîner à écrire du code sur papier : c'est ce "
              "qui est demandé à l'examen.",
    "web": "Chaque TP s'appuie sur le précédent ; un TP bâclé se paie deux fois. Après chaque "
           "remise, noter en trois lignes ce qui a bloqué : c'est exactement ce qui tombera à "
           "l'Évaluation #1.",
}


def main():
    args = sys.argv[1:]
    jour = carte.d(args[0]) if args else dt.date.today()
    texte = page(carte.charger(), jour)
    if len(args) > 1:
        with open(args[1], "w", encoding="utf-8") as fh:
            fh.write(texte)
        print(args[1])
    else:
        print(texte)


if __name__ == "__main__":
    main()

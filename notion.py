# -*- coding: utf-8 -*-
"""Tableau de bord Notion — Automne 2026.

Génère, à partir de donnees-session.json, le contenu complet de la page Notion
« 🎓 Ma session — Automne 2026 » (page 3df73824-e620-811e-9e6c-d07440cb6ec7).

    python3 notion.py                 -> la page d'aujourd'hui sur la sortie standard
    python3 notion.py 2026-10-07      -> la page telle qu'elle serait ce jour-là
    python3 notion.py --sortie p.md   -> écrit dans un fichier

Le moteur (quelles évaluations sont en préparation, à quelle étape, quelles
tâches tombent aujourd'hui) est celui de carte.py : un seul endroit à corriger.
Le résultat se colle dans Notion avec update-page / replace_content.
"""
import io
import os
import sys
import datetime as dt

import carte
from carte import d, jx, court, JOURS, MOIS, ABREV

BASE = os.path.dirname(os.path.abspath(__file__))

# Couleur de l'échéance selon ce qu'il reste de temps.
def pastille(reste):
    if reste <= 4:
        return "🔴"
    if reste <= 12:
        return "🟠"
    return "🔵"


def emo(data, cle):
    return data["cours"][cle].get("emoji", "•")


def nom(data, cle):
    return "%s %s" % (emo(data, cle), data["cours"][cle]["nom"])


def long_date(j):
    return "%s %d %s" % (JOURS[j.weekday()], j.day, MOIS[j.month - 1])


def court_jour(j):
    jour = JOURS[j.weekday()][:3] + "."
    d_ = "1er" if j.day == 1 else str(j.day)
    return "%s %s %s" % (jour, d_, ABREV[j.month - 1])


def poids_txt(p):
    if not p:
        return "formatif"
    return ("**%d %%**" % p) if p >= 20 else ("%d %%" % p)


def heure(h):
    return h.replace(":", " h ")


# --------------------------------------------------------------------------
# Les sections
# --------------------------------------------------------------------------
def section_aujourdhui(data, jour, actifs, L):
    L.append("## 📍 Aujourd'hui — %s" % long_date(jour))
    cj = carte.cours_du_jour(data, jour)
    if cj:
        for c in cj:
            L.append("- %s · **%s – %s** · local %s"
                     % (nom(data, c["cours"]), heure(c["debut"]), heure(c["fin"]), c["local"]))
    elif carte.en_semaine_etudes(data, jour):
        L.append("- *Semaine d'études et d'encadrement — aucun cours*")
    else:
        L.append("- *Aucun cours aujourd'hui*")
    for b in carte.blocs_du_jour(data, jour):
        L.append("- 🎯 **%s** · %s – %s" % (b["titre"], heure(b["debut"]), heure(b["fin"])))
    if not carte.blocs_du_jour(data, jour):
        L.append("- 🌙 *Journée libre — repos assumé, c'est prévu au plan.*")
    if actifs:
        p = actifs[0]
        L.append("")
        L.append("> 🔥 **Priorité du jour :** %s — %s (%s), **%s**."
                 % (nom(data, p["cours"]), p["titre"], poids_txt(p["poids"]).replace("**", ""),
                    jx(p["reste"])))
    L.append("")
    L.append("---")


def section_a_faire(data, jour, actifs, L):
    L.append("## ✅ À faire aujourd'hui")
    taches = carte.taches_du_jour(data, jour, actifs)
    if not taches:
        L.append("- [ ] *Rien d'imposé. Prends de l'avance ou repose-toi.*")
    for tag, t in taches:
        rond = "🔴" if tag in ("RETARD", "REMISE") else ("🟠" if tag in ("FINIR", "TEST BLANC", "ADMIN") else "🔵")
        L.append("- [ ] %s **%s** — %s" % (rond, tag, t))
    L.append("")
    L.append("---")


def section_sept_jours(data, jour, L):
    L.append("## 🗓️ Les 7 prochains jours")
    L.append('<table header-row="true">')
    L.append("<tr>\n<td>Jour</td>\n<td>Cours et blocs</td>\n<td>Ce que je fais</td>\n</tr>")
    for i in range(7):
        j = jour + dt.timedelta(days=i)
        etiquette = "**%s**" % court_jour(j)
        if i == 0:
            etiquette += " ← *aujourd'hui*"
        colonne = ["%s" % emo(data, c["cours"]) + " " + data["cours"][c["cours"]].get("court", "")
                   for c in carte.cours_du_jour(data, j)]
        colonne += ["%s – %s" % (heure(b["debut"]), heure(b["fin"])) for b in carte.blocs_du_jour(data, j)]
        if carte.en_semaine_etudes(data, j):
            colonne.insert(0, "*semaine d'études*")

        act = carte.chantiers(data, j)
        dus = [e for e in act if e["reste"] == 0]
        if dus:
            quoi = " · ".join("🔥 **%s — %s**" % (nom(data, e["cours"]), e["titre"]) for e in dus)
        else:
            # vue d'ensemble : ce qui presse le plus d'abord, peu importe le bloc du jour
            quoi = " · ".join("%s — %s *(%s)*" % (nom(data, e["cours"]), e["titre"], carte.etape(e).lower())
                             for e in act[:2]) or "—"
        L.append("<tr>\n<td>%s</td>\n<td>%s</td>\n<td>%s</td>\n</tr>"
                 % (etiquette, "<br>".join(colonne) or "—", quoi))
    L.append("</table>")
    L.append("")
    L.append("---")


def section_remises_en_retard(data, jour, L):
    """Les remises passées jamais cochées : tant qu'elles sont là, l'avancement est une hypothèse."""
    oubliees = [e for e in data["evaluations"]
                if not e.get("fait") and d(e["date"]) < jour and e["type"] in ("tp", "remise")]
    if not oubliees:
        return
    L.append("## 🔴 À confirmer — remises passées jamais cochées")
    L.append("> Ces remises sont passées et toujours marquées « non faites » dans `donnees-session.json`. "
             "Tant qu'elles y sont, mon avancement est une hypothèse, pas un fait.")
    L.append('<table header-row="true">')
    L.append("<tr>\n<td>Évaluation</td>\n<td>Cours</td>\n<td>Poids</td>\n<td>Était dû le</td>\n<td>Retard</td>\n</tr>")
    for e in sorted(oubliees, key=lambda x: x["date"]):
        retard = (jour - d(e["date"])).days
        L.append("<tr>\n<td>%s</td>\n<td>%s</td>\n<td>%d %%</td>\n<td>%s</td>\n<td>%d jours</td>\n</tr>"
                 % (e["titre"], nom(data, e["cours"]), e["poids"], court_jour(d(e["date"])), retard))
    L.append("</table>")
    L.append("- [ ] Cocher celles qui sont remises → l'avancement redevient exact")
    L.append("- [ ] Écrire au prof **le jour même** pour celles qui ne le sont pas")
    L.append("")
    L.append("---")


def section_admin(data, jour, L):
    L.append("## 📌 À régler tout de suite")
    for t in data["taches_admin"]:
        if t["pour"] == "recurrent":
            L.append("- [ ] 🔁 %s" % t["quoi"])
            continue
        reste = (d(t["pour"]) - jour).days
        if reste < 0:
            L.append("- [ ] 🔴 **%s** — *%d jours de retard*" % (t["quoi"], -reste))
        elif reste <= 10:
            L.append("- [ ] 🟠 %s — *%s*" % (t["quoi"], jx(reste)))
        else:
            L.append("- [ ] 🔵 %s — *pour le %s*" % (t["quoi"], court_jour(d(t["pour"]))))
    L.append("")
    L.append("---")


def section_echeances(data, jour, L):
    L.append("## 📅 Toutes mes échéances à venir")
    L.append("> 💡 Sélectionne ce tableau → **Transformer en base de données** pour filtrer par cours "
             "et cocher au fur et à mesure.")
    L.append('<table header-row="true">')
    L.append("<tr>\n<td></td>\n<td>Date</td>\n<td>Cours</td>\n<td>Évaluation</td>\n<td>Poids</td>\n<td>Compte à rebours</td>\n</tr>")
    for e in carte.chantiers_tous(data, jour):
        L.append("<tr>\n<td>%s</td>\n<td>%s</td>\n<td>%s</td>\n<td>%s</td>\n<td>%s</td>\n<td>%s</td>\n</tr>"
                 % (pastille(e["reste"]), court_jour(d(e["date"])), nom(data, e["cours"]),
                    e["titre"], poids_txt(e["poids"]), jx(e["reste"])))
    L.append("</table>")
    L.append("")
    L.append("---")


def section_lectures(data, jour, L):
    a_venir = [l for l in data["lectures"] if d(l["pour"]) >= jour]
    if not a_venir:
        return
    L.append("## 📖 Mes lectures")
    L.append('<table header-row="true">')
    L.append("<tr>\n<td>Pour le</td>\n<td>Cours</td>\n<td>À lire</td>\n</tr>")
    for l in sorted(a_venir, key=lambda x: x["pour"]):
        L.append("<tr>\n<td>%s</td>\n<td>%s</td>\n<td>%s</td>\n</tr>"
                 % (court_jour(d(l["pour"])), nom(data, l["cours"]), l["quoi"]))
    L.append("</table>")
    L.append("")
    L.append("---")


def semaines_rouges(data, seuil=30):
    """Toute semaine de session où il se joue seuil % ou plus, tous cours confondus."""
    paires = sorted(((int(n), d(deb)) for n, deb in data["session"]["semaines"].items()),
                    key=lambda p: p[1])
    out = []
    for num, debut in paires:
        fin = debut + dt.timedelta(days=6)
        dedans = [e for e in data["evaluations"] if debut <= d(e["date"]) <= fin]
        total = sum(e["poids"] for e in dedans)
        if total >= seuil:
            out.append((num, debut, fin, sorted(dedans, key=lambda e: -e["poids"]), total))
    return out


def section_semaines_rouges(data, jour, L):
    sem_courante = carte.semaine_de(data, jour)
    L.append("## 🔴 Mes semaines rouges")
    L.append("> Toute semaine de session où il se joue **30 % ou plus** de points, tous cours confondus. "
             "C'est là que se gagne ou se perd la session.")
    L.append('<table header-row="true">')
    L.append("<tr>\n<td>Semaine</td>\n<td>Dates</td>\n<td>Ce qui tombe</td>\n<td>Poids total</td>\n</tr>")
    for num, debut, fin, evs, total in semaines_rouges(data):
        etiquette = "**%d**" % num + (" ← *ici*" if num == sem_courante else "")
        quoi = " · ".join("%s %s %d %%" % (emo(data, e["cours"]), e["titre"], e["poids"]) for e in evs)
        L.append("<tr>\n<td>%s</td>\n<td>%s – %s</td>\n<td>%s</td>\n<td>**%d %%**</td>\n</tr>"
                 % (etiquette, court(debut), court(fin), quoi, total))
    L.append("</table>")
    L.append("")
    L.append("---")


def section_semaine_type(data, L):
    L.append("## 🗓️ Ma semaine type")
    L.append('<table header-row="true">')
    L.append("<tr>\n<td>Quand</td>\n<td>Durée</td>\n<td>Ce que je fais</td>\n</tr>")
    for b in sorted(data["blocs_travail"], key=lambda x: (x["jour"], x["debut"])):
        h1 = dt.datetime.strptime(b["debut"], "%H:%M")
        h2 = dt.datetime.strptime(b["fin"], "%H:%M")
        mins = int((h2 - h1).total_seconds() // 60)
        duree = ("%d h %02d" % (mins // 60, mins % 60)) if mins % 60 else "%d h" % (mins // 60)
        # on met en gras ce qui porte la semaine : les gros blocs et le rattrapage
        gros = "GROS BLOC" in b["titre"] or "rattrapage" in b["focus"]
        quand = "%s %s – %s" % (JOURS[b["jour"] - 1].capitalize(), heure(b["debut"]), heure(b["fin"]))
        icones = "".join(emo(data, f) for f in b["focus"] if f in data["cours"]) or "🔁"
        titre = "%s %s" % (icones, b["titre"])
        if gros:
            quand, duree, titre = "**%s**" % quand, "**%s**" % duree, "**%s**" % titre
        L.append("<tr>\n<td>%s</td>\n<td>%s</td>\n<td>%s</td>\n</tr>" % (quand, duree, titre))
    L.append("</table>")
    L.append("> ⚠️ Vendredi soir, samedi après-midi et dimanche matin restent **vides**. Ce n'est pas du "
             "temps perdu : c'est ce qui rend le reste tenable semaine après semaine.")
    L.append("")
    L.append("---")


def section_methodes(data, L):
    methodes = data.get("methodes", {})
    if not methodes:
        return
    L.append("## 🧠 Mes méthodes, cours par cours")
    ordre = sorted(methodes, key=lambda c: -data["cours"][c].get("difficulte", 0))
    for cle in ordre:
        dur = data["cours"][cle].get("difficulte", 0) >= 4
        L.append("### %s%s" % (nom(data, cle), " — *ma matière la plus difficile*" if dur else ""))
        L.append(methodes[cle])
    L.append("")
    L.append("---")


def section_avancement(data, jour, L):
    av = carte.avancement(data, jour)
    L.append("## 📊 Mon avancement")
    L.append('<table header-row="true">')
    L.append("<tr>\n<td>Cours</td>\n<td>Part de la note déjà jouée</td>\n<td></td>\n</tr>")
    rangs = sorted(av.items(), key=lambda kv: -kv[1][1])
    for cle, (n, pct) in rangs:
        barre = "▰" * int(round(pct / 10.0)) + "▱" * (10 - int(round(pct / 10.0)))
        L.append("<tr>\n<td>%s</td>\n<td>%d %%</td>\n<td>`%s`</td>\n</tr>" % (nom(data, cle), pct, barre))
    L.append("</table>")
    moy = sum(p for _, (_, p) in rangs) / float(len(rangs))
    L.append("> **%d %%** de la session est joué en moyenne, tous cours confondus." % int(moy))
    L.append("")
    L.append("---")


# --------------------------------------------------------------------------
def page(data, jour):
    sem = carte.semaine_de(data, jour)
    s = data["session"]
    a, b = s["semaine_etudes"]
    L = []
    L.append("# 🎓 Ma session — %s" % s["nom"])
    L.append("> Cégep de Granby · Techniques de l'informatique (420.B0) · %s → %s"
             % (court(d(s["debut"])).replace(".", ""), court(d(s["fin"])).replace(".", "")))
    entete = "**Semaine d'études**" if carte.en_semaine_etudes(data, jour) else \
             ("**Semaine %d sur 15**" % sem if sem else "**Hors session**")
    L.append("> %s · Semaine d'études : %s au %s" % (entete, court(d(a)), court(d(b))))
    L.append("")
    L.append("---")

    actifs = carte.chantiers(data, jour)
    section_aujourdhui(data, jour, actifs, L)
    section_a_faire(data, jour, actifs, L)
    section_sept_jours(data, jour, L)
    section_remises_en_retard(data, jour, L)
    section_admin(data, jour, L)
    section_echeances(data, jour, L)
    section_lectures(data, jour, L)
    section_semaines_rouges(data, jour, L)
    section_semaine_type(data, L)
    section_methodes(data, L)
    section_avancement(data, jour, L)

    L.append("*Mis à jour automatiquement le %s · source : `donnees-session.json` · généré par `notion.py`*"
             % long_date(jour))
    return "\n".join(L)


def main():
    args = sys.argv[1:]
    sortie = None
    if "--sortie" in args:
        i = args.index("--sortie")
        sortie = args[i + 1]
        args = args[:i] + args[i + 2:]
    jour = d(args[0]) if args else dt.date.today()

    data = carte.charger()
    txt = page(data, jour)
    if sortie:
        io.open(sortie, "w", encoding="utf-8").write(txt)
        print(sortie)
    else:
        print(txt)


if __name__ == "__main__":
    main()

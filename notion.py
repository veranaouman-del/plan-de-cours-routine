# -*- coding: utf-8 -*-
"""Page Notion « Ma session » — Automne 2026.

Génère le contenu Markdown enrichi du tableau de bord Notion à partir de
donnees-session.json, en réutilisant le moteur de carte.py.

    python3 notion.py                 -> aujourd'hui, sur la sortie standard
    python3 notion.py 2026-10-09      -> une date précise

Le texte produit est à passer tel quel à notion-update-page (replace_content).
Rien n'est codé en dur ici sauf les méthodes par cours : pour changer une
échéance, éditer donnees-session.json.
"""
import sys
import datetime as dt

import carte as C

JOURS_C = ["lun.", "mar.", "mer.", "jeu.", "ven.", "sam.", "dim."]


def em(data, cle):
    return data["cours"][cle].get("emoji", "")


def nom(data, cle):
    return "%s %s" % (em(data, cle), data["cours"][cle]["nom"])


def court_nom(data, cle):
    return "%s %s" % (em(data, cle), data["cours"][cle]["court"])


def dlong(j):
    jour = "1er" if j.day == 1 else str(j.day)
    return "%s %s %s" % (C.JOURS[j.weekday()], jour, C.MOIS[j.month - 1])


def dcourt(j):
    jour = "1er" if j.day == 1 else str(j.day)
    return "%s %s %s" % (JOURS_C[j.weekday()], jour, C.ABREV[j.month - 1])


def hh(t):
    return t.replace(":", " h ")


def poids_txt(p):
    if not p:
        return "formatif"
    return "**%d %%**" % p if p >= 20 else "%d %%" % p


def puce(reste):
    if reste <= 1:
        return "🔴"
    if reste <= 7:
        return "🟠"
    return "🔵"


# --------------------------------------------------------------------------
# Sections
# --------------------------------------------------------------------------
def entete(data, jour):
    sem = C.semaine_de(data, jour)
    a, b = data["session"]["semaine_etudes"]
    L = ["# 🎓 Ma session — %s" % data["session"]["nom"],
         "> Cégep de Granby · Techniques de l'informatique (420.B0) · 24 août → 11 déc"]
    if C.en_semaine_etudes(data, jour):
        L.append("> **Semaine d'études** · aucun cours · reprise le %s"
                 % dcourt(C.d(b) + dt.timedelta(days=3)))
    else:
        L.append("> **Semaine %s sur 15** · Semaine d'études : %s au %s"
                 % (sem, dcourt(C.d(a)), dcourt(C.d(b))))
    return L


def aujourdhui(data, jour, actifs):
    L = ["## 📍 Aujourd'hui — %s" % dlong(jour)]
    cj = C.cours_du_jour(data, jour)
    bj = C.blocs_du_jour(data, jour)
    if not cj and not bj:
        L.append("- 🌿 Aucun cours, aucun bloc — journée libre, repos assumé")
    for c in cj:
        L.append("- %s · **%s – %s** · local %s"
                 % (court_nom(data, c["cours"]), hh(c["debut"]), hh(c["fin"]), c["local"]))
    for b in bj:
        L.append("- 🎯 **%s** · %s – %s" % (b["titre"], hh(b["debut"]), hh(b["fin"])))
    if actifs:
        p = actifs[0]
        L.append("> 🔥 **Priorité du jour :** %s — %s (%s), **%s**."
                 % (nom(data, p["cours"]), p["titre"], poids_txt(p["poids"]).replace("**", ""),
                    C.jx(p["reste"])))
    suite = apres(data, jour, actifs)
    if suite:
        L.append("> ⏭️ **Ensuite :** %s" % suite)
    return L


def apres(data, jour, actifs):
    """Ce qui vient juste après aujourd'hui : la semaine d'études si elle ouvre, sinon
    la prochaine échéance. C'est la ligne qui évite de ne voir que la journée en cours."""
    debut_etudes = C.d(data["session"]["semaine_etudes"][0])
    jusqua = (debut_etudes - jour).days
    apres_demain = [e for e in C.chantiers_tous(data, jour) if e["reste"] > 0]
    if 0 < jusqua <= 3 and apres_demain:
        c = apres_demain[0]
        quand = "demain" if jusqua == 1 else "dans %d jours" % jusqua
        return ("la **semaine d'études** s'ouvre %s — aucun cours, et la plus grosse "
                "échéance qui suit est %s %s (%s) le %s C'est la semaine pour "
                "la prendre d'avance, pas pour la reporter."
                % (quand, em(data, c["cours"]), c["titre"],
                   poids_txt(c["poids"]).replace("**", ""), dcourt(C.d(c["date"]))))
    if apres_demain:
        c = apres_demain[0]
        return ("%s %s (%s) — %s, le %s"
                % (em(data, c["cours"]), c["titre"], poids_txt(c["poids"]).replace("**", ""),
                   C.jx(c["reste"]), dcourt(C.d(c["date"]))))
    return ""


def a_confirmer(data, jour):
    """Remises passées jamais cochées : tant qu'elles traînent, l'avancement est une hypothèse."""
    en_jeu = [e for e in data["evaluations"]
              if not e.get("fait")
              and e["type"] in ("tp", "remise", "redaction")
              and C.d(e["date"]) < jour]
    if not en_jeu:
        return []
    en_jeu.sort(key=lambda e: C.d(e["date"]))
    total = sum(e["poids"] for e in en_jeu)
    L = ["## 🔴 À confirmer — remises passées jamais cochées",
         "> Ces remises sont passées et toujours marquées « non faites ». "
         "Tant qu'elles y sont, mon avancement est une hypothèse, pas un fait.",
         '<table header-row="true">',
         "<tr><td>Évaluation</td><td>Cours</td><td>Poids</td><td>Était dû le</td><td>Retard</td></tr>"]
    for e in en_jeu:
        retard = (jour - C.d(e["date"])).days
        L.append("<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%d jours</td></tr>"
                 % (e["titre"], nom(data, e["cours"]), poids_txt(e["poids"]),
                    dcourt(C.d(e["date"])), retard))
    L.append("</table>")
    L.append("- [ ] Cocher sur LÉA celles qui sont bien déposées → l'avancement redevient exact")
    L.append("- [ ] Écrire au prof **le jour même** pour celles qui ne le sont pas — "
             "**%d %%** de points au statut incertain" % total)
    return L


def a_faire(data, jour, actifs):
    niveau = {"RETARD": "🔴", "REMISE": "🔴", "ADMIN": "🟠", "RELIRE": "🟠",
              "LECTURE": "📖", "TEST BLANC": "🟠", "FINIR": "🟠",
              "FICHES": "🔵", "NOTES": "🔵", "AVANCER": "🔵"}
    L = ["## ✅ À faire aujourd'hui"]
    for tag, t in C.taches_du_jour(data, jour, actifs):
        L.append("- [ ] %s **%s** — %s" % (niveau.get(tag, "🔵"), tag, t))
    if len(L) == 1:
        L.append("- [ ] 🌿 Rien d'imposé aujourd'hui — prendre de l'avance ou se reposer")
    return L


def sept_jours(data, jour):
    """Les 7 prochains jours : cours, blocs, et ce qui se joue — en emoji + titre court."""
    L = ["## 🗓️ Les 7 prochains jours",
         '<table header-row="true">',
         "<tr><td>Jour</td><td>Cours et blocs</td><td>Ce que je fais</td></tr>"]
    for i in range(7):
        j = jour + dt.timedelta(days=i)
        gauche = [court_nom(data, c["cours"]) for c in C.cours_du_jour(data, j)]
        if C.en_semaine_etudes(data, j):
            gauche.append("*semaine d'études*")
        gauche += ["%s – %s" % (hh(b["debut"]), hh(b["fin"])) for b in C.blocs_du_jour(data, j)]

        focus = set()
        for b in C.blocs_du_jour(data, j):
            focus.update(b["focus"])
        actifs = C.chantiers(data, j)
        if "rattrapage" in focus or not focus:
            liste = actifs
        else:
            liste = ([e for e in actifs if e["cours"] in focus]
                     + [e for e in actifs if e["cours"] not in focus])

        droite = []
        for e in liste[:3]:
            tag = C.etape(e)
            libelle = "%s %s" % (em(data, e["cours"]), e["titre"])
            if tag in ("REMISE", "RELIRE"):
                droite.append("🔥 **%s**" % libelle)
            else:
                droite.append("%s — *%s*" % (libelle, tag.lower()))

        etiquette = "**%s**" % dcourt(j)
        if i == 0:
            etiquette += " ← *aujourd'hui*"
        L.append("<tr><td>%s</td><td>%s</td><td>%s</td></tr>"
                 % (etiquette, "<br>".join(gauche) or "—", " · ".join(droite) or "—"))
    L.append("</table>")
    return L


def admin(data, jour):
    L = ["## 📌 À régler tout de suite"]
    rec, dates = [], []
    for t in data["taches_admin"]:
        if t["pour"] == "recurrent":
            rec.append("- [ ] 🔁 %s" % t["quoi"])
            continue
        dates.append(t)
    dates.sort(key=lambda t: C.d(t["pour"]))
    for t in dates:
        reste = (C.d(t["pour"]) - jour).days
        if reste < 0:
            L.append("- [ ] 🔴 **%s** — *%d jours de retard*" % (t["quoi"], -reste))
        else:
            L.append("- [ ] %s %s — *pour le %s*" % (puce(reste), t["quoi"], dcourt(C.d(t["pour"]))))
    return L + rec


def echeances(data, jour):
    L = ["## 📅 Toutes mes échéances à venir",
         "> 💡 Sélectionne ce tableau → **Transformer en base de données** "
         "pour filtrer par cours et cocher au fur et à mesure.",
         '<table header-row="true">',
         "<tr><td></td><td>Date</td><td>Cours</td><td>Évaluation</td>"
         "<td>Poids</td><td>Compte à rebours</td></tr>"]
    for e in C.chantiers_tous(data, jour):
        L.append("<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>"
                 % (puce(e["reste"]), dcourt(C.d(e["date"])), nom(data, e["cours"]),
                    e["titre"], poids_txt(e["poids"]), C.jx(e["reste"])))
    L.append("</table>")
    return L


def lectures(data, jour):
    a_venir = [l for l in data["lectures"] if C.d(l["pour"]) >= jour]
    if not a_venir:
        return []
    a_venir.sort(key=lambda l: C.d(l["pour"]))
    L = ["## 📖 Mes lectures",
         '<table header-row="true">',
         "<tr><td>Pour le</td><td>Cours</td><td>À lire</td></tr>"]
    for l in a_venir:
        L.append("<tr><td>%s</td><td>%s</td><td>%s</td></tr>"
                 % (dcourt(C.d(l["pour"])), nom(data, l["cours"]), l["quoi"]))
    L.append("</table>")
    return L


def semaines_rouges(data, jour):
    """Toute semaine de session où il se joue 30 % ou plus, tous cours confondus."""
    paires = sorted(((int(n), C.d(x)) for n, x in data["session"]["semaines"].items()),
                    key=lambda p: p[1])
    L = ["## 🔴 Mes semaines rouges",
         "> Toute semaine de session où il se joue **30 % ou plus** de points, "
         "tous cours confondus. C'est là que se gagne ou se perd la session.",
         '<table header-row="true">',
         "<tr><td>Semaine</td><td>Dates</td><td>Ce qui tombe</td><td>Poids total</td></tr>"]
    vide = True
    for num, debut in paires:
        fin = debut + dt.timedelta(days=6)
        dedans = [e for e in data["evaluations"] if debut <= C.d(e["date"]) <= fin]
        total = sum(e["poids"] for e in dedans)
        if total < 30:
            continue
        vide = False
        dedans.sort(key=lambda e: -e["poids"])
        quoi = " · ".join("%s %s %d %%" % (em(data, e["cours"]), e["titre"], e["poids"])
                          for e in dedans if e["poids"])
        etiquette = "**%d**" % num
        if debut <= jour <= fin:
            etiquette += " ← *ici*"
        L.append("<tr><td>%s</td><td>%s – %s</td><td>%s</td><td>**%d %%**</td></tr>"
                 % (etiquette, dcourt(debut), dcourt(fin), quoi, total))
    L.append("</table>")
    return [] if vide else L


def semaine_type(data):
    L = ["## 🗓️ Ma semaine type",
         '<table header-row="true">',
         "<tr><td>Quand</td><td>Durée</td><td>Ce que je fais</td></tr>"]
    for b in sorted(data["blocs_travail"], key=lambda b: (b["jour"], b["debut"])):
        h1 = dt.datetime.strptime(b["debut"], "%H:%M")
        h2 = dt.datetime.strptime(b["fin"], "%H:%M")
        mins = int((h2 - h1).total_seconds() // 60)
        duree = "%d h%s" % (mins // 60, (" %02d" % (mins % 60)) if mins % 60 else "")
        gros = mins >= 180
        ems = "".join(em(data, f) for f in b["focus"] if f in data["cours"]) or "🔁"
        quand = "%s %s – %s" % (C.JOURS[b["jour"] - 1].capitalize(), hh(b["debut"]), hh(b["fin"]))
        g = (lambda s: "**%s**" % s) if gros else (lambda s: s)
        L.append("<tr><td>%s</td><td>%s</td><td>%s</td></tr>"
                 % (g(quand), g(duree), g("%s %s" % (ems, b["titre"]))))
    L.append("</table>")
    L.append("> ⚠️ Vendredi soir, samedi après-midi et dimanche matin restent **vides**. "
             "Ce n'est pas du temps perdu : c'est ce qui rend le reste tenable "
             "semaine après semaine.")
    return L


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
           "aux évaluations.",
}


def methodes(data):
    L = ["## 🧠 Mes méthodes, cours par cours"]
    ordre = sorted(data["cours"], key=lambda c: -data["cours"][c]["difficulte"])
    dur = max(data["cours"][c]["difficulte"] for c in ordre)
    for cle in ordre:
        if cle not in METHODES:
            continue
        titre = "### %s" % nom(data, cle)
        if data["cours"][cle]["difficulte"] == dur:
            titre += " — *ma matière la plus difficile*"
        L.append(titre)
        L.append(METHODES[cle])
    return L


def progression(data, jour):
    av = C.avancement(data, jour)
    lignes = sorted(av.items(), key=lambda kv: -kv[1][1])
    L = ["## 📊 Mon avancement",
         '<table header-row="true">',
         "<tr><td>Cours</td><td>Part de la note déjà jouée</td><td></td></tr>"]
    for cle, (_, pct) in lignes:
        pleins = int(round(pct / 10.0))
        L.append("<tr><td>%s</td><td>%d %%</td><td>`%s`</td></tr>"
                 % (nom(data, cle), pct, "▰" * pleins + "▱" * (10 - pleins)))
    L.append("</table>")
    moy = sum(v[1] for v in av.values()) / float(len(av))
    L.append("> **%d %%** de la session est joué en moyenne, tous cours confondus." % round(moy))
    return L


# --------------------------------------------------------------------------
def page(data, jour):
    actifs = C.chantiers(data, jour)
    blocs = [entete(data, jour),
             aujourdhui(data, jour, actifs),
             a_confirmer(data, jour),
             a_faire(data, jour, actifs),
             sept_jours(data, jour),
             admin(data, jour),
             echeances(data, jour),
             lectures(data, jour),
             semaines_rouges(data, jour),
             semaine_type(data),
             methodes(data),
             progression(data, jour)]
    corps = "\n---\n".join("\n".join(b) for b in blocs if b)
    pied = ("*Mis à jour automatiquement le %s · source : **`donnees-session.json`** · "
            "généré par **`notion.py`***" % dlong(jour))
    return corps + "\n---\n" + pied


def main():
    data = C.charger()
    jour = C.d(sys.argv[1]) if len(sys.argv) > 1 else dt.date.today()
    sys.stdout.write(page(data, jour) + "\n")


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""Page Notion « Ma session » — Automne 2026.

Régénère tout le contenu de la page de tableau de bord à partir de
donnees-session.json, en Markdown Notion (callouts, tables, cases à cocher).

    python3 notion.py                 -> aujourd'hui, sortie ./notion-page.md
    python3 notion.py 2026-10-22      -> une date précise
    python3 notion.py 2026-10-22 /tmp/page.md

Le fichier produit est à passer tel quel à l'outil Notion `update-page`,
commande `replace_content`, sur la page 3df73824-e620-811e-9e6c-d07440cb6ec7.

S'il existe un fichier `note-du-jour.md` à la racine, son contenu est inséré
en encadré sous la priorité : c'est là qu'on écrit le découpage d'une journée
particulière (un oral le matin, un bloc redirigé, une remise le lendemain).

Rien n'est codé en dur ici sauf les méthodes de travail : tout le reste vient
de donnees-session.json, comme pour carte.py.
"""
import datetime as dt
import os
import sys

import carte

BASE = os.path.dirname(os.path.abspath(__file__))
NOTE = os.path.join(BASE, "note-du-jour.md")

JOURS_COURT = ["lun.", "mar.", "mer.", "jeu.", "ven.", "sam.", "dim."]

# Les seules lignes rédigées à la main : elles ne changent pas d'un jour à l'autre.
METHODES = {
    "litt": "Annoter PENDANT la lecture, jamais après. Un carnet de citations classées par "
            "thème — c'est lui qui sauve quand le sujet tombe. Garder 10 minutes de relecture "
            "linguistique en fin de rédaction : la langue vaut 25 % de chaque dissertation.",
    "philo": "Droit aux notes de cours à TOUTES les évaluations : la vraie préparation, c'est de "
             "construire de bonnes notes, pas de mémoriser. Un tableau par penseur — thèse, "
             "critère du juste, objection, exemple. Lire les extraits AVANT le cours du vendredi. "
             "Chaque faute de français retranche 0,5 % de la note globale, jusqu'à 10 %.",
    "anglais": "Tout se joue en classe, rien ne se rattrape. Remplir le journal Odyssey le jour "
               "même (5 % garantis). Les oraux valent 45 % du cours : ils se préparent À VOIX "
               "HAUTE. S'enregistrer deux minutes au téléphone et se réécouter.",
    "devlog": "Le code se retient par les doigts. Refaire les exercices dirigés sans la "
              "correction, puis comparer. S'entraîner à écrire du code SUR PAPIER, sans "
              "autocomplétion — c'est ce qui est demandé à l'examen.",
    "web": "Chaque TP s'appuie sur le précédent (VueJS → Router → WebAPI → EF Core → fetch) : "
           "un TP bâclé se paie deux fois. Après chaque remise, noter en trois lignes ce qui a "
           "bloqué — c'est exactement ce qui tombera aux évaluations.",
}


# --------------------------------------------------------------------------
# Petits formateurs
# --------------------------------------------------------------------------
def jour_court(j):
    """« jeu. 22 oct. », avec le 1er du mois écrit correctement."""
    num = "1er" if j.day == 1 else str(j.day)
    return "%s %s %s" % (JOURS_COURT[j.weekday()], num, carte.ABREV[j.month - 1])


def jour_long(j):
    return "%s %d %s" % (carte.JOURS[j.weekday()], j.day, carte.MOIS[j.month - 1])


def heure(h):
    return h.replace(":", " h ")


def poids_txt(ev):
    if not ev["poids"]:
        return "formatif"
    t = "%d %%" % ev["poids"]
    if ev["poids"] >= 20:
        t = "<b>%s</b>" % t
    if ev.get("poids_approx"):
        t += " <i>(estimé)</i>"
    return t


def pastille(reste):
    return "🔴" if reste <= 2 else ("🟠" if reste <= 7 else "🔵")


def nom_cours(data, cle):
    c = data["cours"][cle]
    return "%s %s" % (c.get("emoji", ""), c["nom"])


def table(entetes, lignes):
    """Table Notion. Chaque cellule part dans sa propre ligne, comme Notion les rend."""
    out = ['<table fit-page-width="true" header-row="true">']
    for rang in [entetes] + lignes:
        out.append("<tr>")
        for cell in rang:
            out.append("<td></td>" if cell == "" else "<td>\n%s<br />\n</td>" % cell)
        out.append("</tr>")
    out.append("</table>")
    return "\n".join(out)


# --------------------------------------------------------------------------
# Les sections
# --------------------------------------------------------------------------
def section_aujourdhui(data, jour, L):
    L.append("## 📍 Aujourd'hui — %s" % jour_long(jour))
    L.append("")
    cj = carte.cours_du_jour(data, jour)
    for c in cj:
        L.append("- %s <b>%s – %s</b> · %s · %s" % (
            data["cours"][c["cours"]].get("emoji", ""), heure(c["debut"]), heure(c["fin"]),
            data["cours"][c["cours"]]["nom"], c["local"]))
    if not cj:
        L.append("- 🏠 Aucun cours aujourd'hui")
    for b in carte.blocs_du_jour(data, jour):
        L.append("- 🎯 <b>%s – %s</b> · %s" % (heure(b["debut"]), heure(b["fin"]), b["titre"]))
    L.append("")


def section_restant(data, jour, L):
    restant = sum(e["poids"] for e in carte.chantiers_tous(data, jour))
    derniere = max(carte.d(e["date"]) for e in data["evaluations"])
    L.append('<callout icon="🎯" color="blue_bg">')
    L.append("<b>%d %% de points restent à jouer d'ici la fin de la session.</b> "
             "Tout se décide entre aujourd'hui et le %s" % (restant, jour_court(derniere)))
    L.append("</callout>")
    L.append("")


def section_priorite(data, jour, actifs, L):
    if actifs:
        p = actifs[0]
        L.append("> 🔥 <b>Priorité du jour :</b> %s — %s (%s), %s. Étape : <b>%s</b>." % (
            nom_cours(data, p["cours"]), p["titre"], poids_txt(p).replace("<b>", "").replace("</b>", ""),
            carte.jx(p["reste"]), carte.etape(p).lower()))
        L.append("")
    prochaines = carte.chantiers_tous(data, jour)
    if actifs:
        prochaines = [e for e in prochaines
                      if (e["titre"], e["cours"]) != (actifs[0]["titre"], actifs[0]["cours"])]
    if prochaines:
        e = prochaines[0]
        L.append("> ⏭️ <b>Prochaine échéance :</b> %s — %s (%s), le %s, <b>%s</b>." % (
            nom_cours(data, e["cours"]), e["titre"],
            poids_txt(e).replace("<b>", "").replace("</b>", ""),
            jour_court(carte.d(e["date"])), carte.jx(e["reste"])))
        L.append("")
    if os.path.exists(NOTE):
        note = open(NOTE, encoding="utf-8").read().strip()
        if note:
            L.append(note)
            L.append("")


def section_lea(data, jour, L):
    a_verifier = [e for e in data["evaluations"]
                  if e.get("a_verifier_lea") and not e.get("fait")]
    if not a_verifier:
        return
    total = sum(e["poids"] for e in a_verifier)
    L.append("## 🔴 À confirmer — points au statut incertain")
    L.append("")
    L.append("> Ces évaluations sont passées, mais rien ne confirme qu'elles ont bien été "
             "déposées, ou même tenues. Tant qu'elles sont là, mon avancement est une "
             "hypothèse, pas un fait.")
    L.append("")
    L.append(table(["Évaluation", "Cours", "Poids", "Était prévu le"],
                   [[e["titre"], nom_cours(data, e["cours"]), poids_txt(e),
                     jour_court(carte.d(e["date"]))] for e in a_verifier]))
    L.append("")
    L.append("- [ ] Vérifier sur LÉA ou par MIO celles qui sont réglées → l'avancement redevient exact")
    L.append("- [ ] Écrire au prof <b>le jour même</b> pour chaque ligne qui reste — "
             "<b>%d %%</b> de points au statut incertain" % total)
    L.append("- [ ] Une fois vérifié : retirer <code>a_verifier_lea</code> dans "
             "<code>donnees-session.json</code>")
    L.append("")
    L.append("---")
    L.append("")


PUCES = {"RETARD": "🔴 <b>RETARD</b>", "REMISE": "🔴 <b>REMISE</b>", "ADMIN": "🟠 <b>ADMIN</b>",
         "LECTURE": "📖 <b>LECTURE</b>", "FINIR": "🟠 <b>FINIR</b>",
         "TEST BLANC": "🟠 <b>TEST BLANC</b>", "RELIRE": "🟠 <b>RELIRE</b>",
         "FICHES": "🔵 <b>FICHES</b>", "AVANCER": "🔵 <b>AVANCER</b>", "NOTES": "🔵 <b>NOTES</b>"}


def section_a_faire(data, jour, actifs, L):
    L.append("## ✅ À faire aujourd'hui")
    L.append("")
    for tag, t in carte.taches_du_jour(data, jour, actifs):
        L.append("- [ ] %s — %s" % (PUCES.get(tag, "🔵 <b>%s</b>" % tag), t))
    L.append("")
    L.append("---")
    L.append("")


def section_7_jours(data, jour, L):
    L.append("## 🗓️ Les 7 prochains jours")
    L.append("")
    lignes = []
    for i in range(7):
        j = jour + dt.timedelta(days=i)
        bouts = []
        for c in carte.cours_du_jour(data, j):
            bouts.append("%s %s – %s · %s" % (data["cours"][c["cours"]].get("emoji", ""),
                                              heure(c["debut"]), heure(c["fin"]), c["local"]))
        for b in carte.blocs_du_jour(data, j):
            cible = ""
            pour_bloc = [e for e in carte.chantiers(data, j) if e["cours"] in b["focus"]]
            if pour_bloc:
                e = pour_bloc[0]
                cible = " — %s : %s <i>(%s)</i>" % (data["cours"][e["cours"]].get("emoji", ""),
                                                    e["titre"], carte.etape(e).lower())
            bouts.append("<b>%s – %s</b> %s%s" % (heure(b["debut"]), heure(b["fin"]),
                                                  b["titre"], cible))
        for e in data["evaluations"]:
            if e["date"] == j.isoformat() and not e.get("fait"):
                bouts.append("⚠️ <b>%s</b> — %s <i>(%s)</i>" % (
                    e["titre"], nom_cours(data, e["cours"]),
                    poids_txt(e).replace("<b>", "").replace("</b>", "")))
        if not bouts:
            bouts.append("<i>rien de prévu — repos assumé</i>")
        libelle = "<b>%s</b>" % jour_court(j)
        if i == 0:
            libelle += " ← <i>aujourd'hui</i>"
        lignes.append([libelle, "<br />".join(bouts)])
    L.append(table(["Jour", "Ce que je fais"], lignes))
    L.append("")
    L.append("---")
    L.append("")


def section_a_regler(data, jour, L):
    L.append("## 📌 À régler")
    L.append("")
    retards, a_venir, recurrents = [], [], []
    for t in data["taches_admin"]:
        if t["pour"] == "recurrent":
            recurrents.append("- [ ] 🔁 %s" % t["quoi"])
            continue
        e = carte.d(t["pour"])
        note = " · %s" % t["note"] if t.get("note") else ""
        if e < jour:
            retards.append((-(e - jour).days,
                            "- [ ] %s <b>%s</b> — <i>%d jours de retard</i>%s" % (
                                "🔴" if t.get("urgent") else "🟠", t["quoi"],
                                (jour - e).days, note)))
        else:
            a_venir.append(((e - jour).days,
                            "- [ ] 🔵 %s — <i>pour le %s</i>%s" % (
                                t["quoi"], jour_court(e), note)))
    for _, ligne in sorted(retards, key=lambda x: -x[0]):
        L.append(ligne)
    for _, ligne in sorted(a_venir):
        L.append(ligne)
    L.extend(recurrents)
    L.append("")
    L.append("---")
    L.append("")


def section_echeances(data, jour, L):
    L.append("## 📅 Toutes mes échéances à venir")
    L.append("")
    L.append("> 💡 Sélectionne ce tableau → <b>Transformer en base de données</b> pour filtrer "
             "par cours et cocher au fur et à mesure.")
    L.append("")
    lignes = []
    for e in carte.chantiers_tous(data, jour):
        titre = e["titre"] + (" ⚠️" if e.get("a_confirmer") else "")
        lignes.append([pastille(e["reste"]), jour_court(carte.d(e["date"])),
                       nom_cours(data, e["cours"]), titre, poids_txt(e), carte.jx(e["reste"])])
    L.append(table(["", "Date", "Cours", "Évaluation", "Poids", "Compte à rebours"], lignes))
    L.append("")
    L.append("> ⚠️ = date ou pondération encore à confirmer auprès du prof. Être prêt une "
             "semaine trop tôt ne coûte rien ; l'inverse, oui.")
    L.append("")
    L.append("---")
    L.append("")


def section_lectures(data, jour, L):
    prochaines = sorted((l for l in data["lectures"] if carte.d(l["pour"]) >= jour),
                        key=lambda l: l["pour"])
    if not prochaines:
        return
    L.append("## 📖 Mes lectures")
    L.append("")
    L.append(table(["Pour le", "Cours", "À lire"],
                   [[jour_court(carte.d(l["pour"])), nom_cours(data, l["cours"]), l["quoi"]]
                    for l in prochaines]))
    L.append("")
    L.append("---")
    L.append("")


def section_semaines_rouges(data, jour, L):
    """Toute semaine de session où il se joue 30 % ou plus, tous cours confondus."""
    paires = sorted(((int(n), carte.d(deb)) for n, deb in data["session"]["semaines"].items()),
                    key=lambda p: p[0])
    lignes = []
    for i, (num, debut) in enumerate(paires):
        if i + 1 < len(paires):
            # la semaine d'etudes creuse un trou de 14 jours entre deux numeros : on borne a 7
            fin = min(paires[i + 1][1] - dt.timedelta(days=1), debut + dt.timedelta(days=6))
        else:
            fin = debut + dt.timedelta(days=13)   # la 15e absorbe la periode d'examens
        dedans = [e for e in data["evaluations"] if debut <= carte.d(e["date"]) <= fin]
        total = sum(e["poids"] for e in dedans)
        if total < 30:
            continue
        quoi = " · ".join("%s %s %s" % (data["cours"][e["cours"]].get("emoji", ""), e["titre"],
                                        poids_txt(e).replace("<b>", "").replace("</b>", ""))
                          for e in sorted(dedans, key=lambda e: -e["poids"]))
        statut = "✅ passée" if fin < jour else ("🔥 EN COURS" if debut <= jour <= fin else "⏳ à venir")
        lignes.append(["<b>%d</b>" % num, "%s – %s" % (jour_court(debut), jour_court(fin)),
                       quoi, "<b>%d %%</b>" % total, statut])
    L.append("## 🔴 Mes semaines rouges")
    L.append("")
    L.append("> Toute semaine où il se joue <b>30 % ou plus</b> de points, tous cours confondus. "
             "C'est là que se gagne ou se perd la session.")
    L.append("")
    L.append(table(["Semaine", "Dates", "Ce qui tombe", "Poids total", "Statut"], lignes))
    L.append("")
    L.append("---")
    L.append("")


def section_semaine_type(data, L):
    L.append("## 🗓️ Ma semaine type")
    L.append("")
    lignes = []
    for b in sorted(data["blocs_travail"], key=lambda b: (b["jour"], b["debut"])):
        h1 = dt.datetime.strptime(b["debut"], "%H:%M")
        h2 = dt.datetime.strptime(b["fin"], "%H:%M")
        mins = int((h2 - h1).total_seconds() // 60)
        duree = "%d h%s" % (mins // 60, (" %02d" % (mins % 60)) if mins % 60 else "")
        gros = b["titre"].startswith("GROS BLOC") or "RATTRAPAGE" in b["titre"]
        emojis = "".join(data["cours"][f].get("emoji", "") for f in b["focus"] if f in data["cours"]) \
            or "🔁"
        quand = "%s %s – %s" % (carte.JOURS[b["jour"] - 1].capitalize(), heure(b["debut"]), heure(b["fin"]))
        ligne = [quand, duree, "%s %s" % (emojis, b["titre"])]
        if gros:
            ligne = ["<b>%s</b>" % c for c in ligne]
        lignes.append(ligne)
    L.append(table(["Quand", "Durée", "Ce que je fais"], lignes))
    L.append("")
    L.append("> ⚠️ Vendredi soir, samedi après-midi et dimanche matin restent <b>vides</b>. "
             "Ce n'est pas du temps perdu : c'est ce qui rend le reste tenable, semaine après semaine.")
    L.append("")
    L.append("---")
    L.append("")


def section_methodes(data, L):
    L.append("## 🧠 Mes méthodes, cours par cours")
    L.append("")
    ordre = sorted(data["cours"].items(), key=lambda kv: -kv[1].get("difficulte", 3))
    for cle, c in ordre:
        dur = " — <i>ma matière la plus difficile</i>" if c.get("difficulte", 3) >= 4 else ""
        L.append("### %s %s%s" % (c.get("emoji", ""), c["nom"], dur))
        L.append("")
        L.append(METHODES.get(cle, ""))
        L.append("")
    L.append("---")
    L.append("")


def section_avancement(data, jour, L):
    L.append("## 📊 Mon avancement")
    L.append("")
    incertain = {}
    for e in data["evaluations"]:
        if e.get("a_verifier_lea") and not e.get("fait"):
            incertain[e["cours"]] = incertain.get(e["cours"], 0) + e["poids"]
    av = carte.avancement(data, jour)
    lignes = []
    for cle, (nom, pct) in sorted(av.items(), key=lambda kv: -kv[1][1]):
        txt = "%d %%" % pct
        if incertain.get(cle):
            txt += " <i>(dont %d %% à confirmer)</i>" % incertain[cle]
        plein = round(pct / 10)
        lignes.append(["%s %s" % (data["cours"][cle].get("emoji", ""), nom), txt,
                       "<code>%s%s</code>" % ("▰" * plein, "▱" * (10 - plein))])
    L.append(table(["Cours", "Part de la note déjà jouée", ""], lignes))
    L.append("")
    moyenne = round(sum(p for _, p in av.values()) / len(av))   # meme arrondi que la carte Canva
    total_incertain = sum(incertain.values())
    phrase = "> <b>%d %%</b> de la session est joué en moyenne, tous cours confondus." % moyenne
    if total_incertain:
        phrase += (" Mais <b>%d %%</b> de points restent au statut incertain tant que les "
                   "évaluations ci-dessus ne sont pas confirmées." % total_incertain)
    L.append(phrase)
    L.append("")
    L.append("---")
    L.append("")


# --------------------------------------------------------------------------
def page(data, jour):
    sem = carte.semaine_de(data, jour)
    L = []
    L.append("> %s · Cégep de Granby · 24 août → 11 décembre<br /><b>Semaine %s sur 15</b>"
             % (data["programme"].replace(" - Cegep de Granby", ""), sem or "—"))
    L.append("")
    L.append("---")
    L.append("")
    actifs = carte.chantiers(data, jour)
    section_aujourdhui(data, jour, L)
    section_restant(data, jour, L)
    section_priorite(data, jour, actifs, L)
    section_lea(data, jour, L)
    section_a_faire(data, jour, actifs, L)
    section_7_jours(data, jour, L)
    section_a_regler(data, jour, L)
    section_echeances(data, jour, L)
    section_lectures(data, jour, L)
    section_semaines_rouges(data, jour, L)
    section_semaine_type(data, L)
    section_methodes(data, L)
    section_avancement(data, jour, L)
    L.append("<i>Mis à jour le %s · source : </i><i><code>donnees-session.json</code></i>"
             "<i> · généré par </i><i><code>notion.py</code></i>" % jour_long(jour))
    return "\n".join(L)


def main():
    args = sys.argv[1:]
    jour = carte.d(args[0]) if args else dt.date.today()
    sortie = args[1] if len(args) > 1 else os.path.join(BASE, "notion-page.md")
    with open(sortie, "w", encoding="utf-8") as fh:
        fh.write(page(carte.charger(), jour))
    print(sortie)


if __name__ == "__main__":
    main()

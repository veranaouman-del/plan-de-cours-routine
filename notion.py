# -*- coding: utf-8 -*-
"""Page Notion « Ma session » — Automne 2026.

Génère le contenu complet du tableau de bord Notion à partir de
donnees-session.json, en Notion-flavored Markdown.

    python3 notion.py                      -> aujourd'hui, sur stdout
    python3 notion.py 2026-11-03           -> une date précise
    python3 notion.py --mot plan-jour.md   -> insère un encadré écrit à la main

Le texte produit se colle tel quel dans la commande `replace_content` du
connecteur Notion. Rien n'est codé en dur : tout vient du JSON, sauf
l'encadré `--mot`, qui est le jugement du jour.

Page Notion : 3df73824-e620-811e-9e6c-d07440cb6ec7
"""
import io
import os
import sys
import datetime as dt

import carte

d = carte.d
JOURS = carte.JOURS
MOIS = carte.MOIS

EMOJI = {"devlog": "💻", "web": "🌐", "litt": "📕", "anglais": "🗣️", "philo": "⚖️"}

# Combien de points restent à jouer avant qu'une semaine devienne « rouge ».
SEUIL_ROUGE = 30


# --------------------------------------------------------------------------
# Petits formateurs
# --------------------------------------------------------------------------
def h(s):
    return s.replace(":", " h ")


def jour_court(j):
    """« mar. 27 oct. », avec le 1er qui s'écrit comme il se dit."""
    n = "1er" if j.day == 1 else str(j.day)
    return "%s. %s %s" % (JOURS[j.weekday()][:3], n, carte.ABREV[j.month - 1])


def jour_long(j):
    n = "1er" if j.day == 1 else str(j.day)
    return "%s %s %s" % (JOURS[j.weekday()], n, MOIS[j.month - 1])


def compte(reste):
    if reste == 0:
        return "AUJOURD'HUI"
    if reste == 1:
        return "DEMAIN"
    return "J-%d" % reste


def poids(ev):
    if ev["poids"] == 0:
        return "formatif"
    txt = "%d %%" % ev["poids"]
    if ev["poids"] >= 20:
        txt = "<b>%s</b>" % txt
    if ev.get("poids_approx"):
        txt += " <i>(estimé)</i>"
    return txt


def nom(data, cle):
    return "%s %s" % (EMOJI[cle], data["cours"][cle]["nom"])


def table(entetes, lignes):
    """Un tableau Notion. Les cellules acceptent du HTML inline."""
    out = ['<table fit-page-width="true" header-row="true">']
    for rang in [entetes] + lignes:
        out.append("<tr>")
        for cell in rang:
            out.append("<td>" if cell == "" else "<td>\n%s<br />\n</td>" % cell)
            if cell == "":
                out[-1] = "<td></td>"
        out.append("</tr>")
    out.append("</table>")
    return "\n".join(out)


# --------------------------------------------------------------------------
# Les sections
# --------------------------------------------------------------------------
def section_aujourdhui(data, jour, actifs):
    L = ["## 📍 Aujourd'hui — %s" % jour_long(jour), ""]

    cj = carte.cours_du_jour(data, jour)
    bj = carte.blocs_du_jour(data, jour)
    if not cj and not bj:
        L.append("- 🌿 Journée libre — repos assumé. C'est elle qui rend le reste tenable.")
    for c in cj:
        L.append("- %s <b>%s – %s</b> · %s · %s"
                 % (EMOJI[c["cours"]], h(c["debut"]), h(c["fin"]),
                    data["cours"][c["cours"]]["nom"], c["local"]))
    for b in bj:
        L.append("- 🎯 <b>%s – %s</b> · %s" % (h(b["debut"]), h(b["fin"]), b["titre"]))
    L.append("")

    restant = points_restants(data, jour)
    derniere = max(d(e["date"]) for e in data["evaluations"])
    L.append('<callout icon="🎯" color="blue_bg">')
    L.append("<b>%d %% de points restent à jouer d'ici la fin de la session.</b> "
             "Tout se décide entre aujourd'hui et le %s" % (restant, jour_court(derniere)))
    L.append("</callout>")
    L.append("")

    if actifs:
        p = actifs[0]
        L.append("> 🔥 <b>Priorité du jour :</b> %s — %s (%s), %s. Étape : <b>%s</b>."
                 % (nom(data, p["cours"]), p["titre"], poids(p).replace("<b>", "").replace("</b>", ""),
                    compte(p["reste"]), carte.etape(p).lower()))
        L.append("")
        suivante = min((e for e in actifs if e["reste"] > p["reste"]),
                       key=lambda e: e["reste"], default=None)
        if suivante:
            L.append("> ⏭️ <b>Prochaine échéance :</b> %s — %s (%s), le %s, <b>%s</b>."
                     % (nom(data, suivante["cours"]), suivante["titre"],
                        poids(suivante).replace("<b>", "").replace("</b>", ""),
                        jour_court(d(suivante["date"])), compte(suivante["reste"])))
            L.append("")
    return L


def points_restants(data, jour):
    return sum(e["poids"] for e in data["evaluations"]
               if not e.get("fait") and d(e["date"]) >= jour)


def section_a_confirmer(data, jour):
    douteux = [e for e in data["evaluations"]
               if e.get("a_verifier_lea") and not e.get("fait")]
    if not douteux:
        return []
    total = sum(e["poids"] for e in douteux)
    L = ["## 🔴 À confirmer — points au statut incertain", ""]
    L.append("> Ces évaluations sont passées, mais rien ne confirme qu'elles ont bien "
             "été déposées, ou même tenues. Tant qu'elles sont là, mon avancement est "
             "une hypothèse, pas un fait.")
    L.append("")
    L.append(table(["Évaluation", "Cours", "Poids", "Était prévu le"],
                   [[e["titre"], nom(data, e["cours"]), poids(e), jour_court(d(e["date"]))]
                    for e in sorted(douteux, key=lambda e: e["date"])]))
    L.append("")
    L.append("- [ ] Vérifier sur LÉA ou par MIO celles qui sont réglées → l'avancement redevient exact")
    L.append("- [ ] Écrire au prof <b>le jour même</b> pour chaque ligne qui reste — <b>%d %%</b> "
             "de points au statut incertain" % total)
    L.append("- [ ] Une fois vérifié : retirer <code>a_verifier_lea</code> dans <code>donnees-session.json</code>")
    L.append("")
    return L


PUCE = {"RETARD": "🔴 <b>RETARD</b> — ", "ADMIN": "🟠 <b>ADMIN</b> — ",
        "LECTURE": "📖 <b>LECTURE</b> — "}


def section_a_faire(data, jour, actifs):
    L = ["## ✅ À faire aujourd'hui", ""]
    for tag, t in carte.taches_du_jour(data, jour, actifs):
        L.append("- [ ] %s%s" % (PUCE.get(tag, "🔵 <b>%s</b> — " % tag), t))
    L.append("")
    return L


def section_semaine(data, jour):
    """Les sept prochains jours, pour voir venir au lieu de subir."""
    lignes = []
    for i in range(7):
        j = jour + dt.timedelta(days=i)
        bouts = []
        for c in carte.cours_du_jour(data, j):
            bouts.append("%s %s – %s · %s" % (EMOJI[c["cours"]], h(c["debut"]), h(c["fin"]), c["local"]))
        for b in carte.blocs_du_jour(data, j):
            chantiers_j = carte.chantiers(data, j)
            cible = next((e for e in chantiers_j if e["cours"] in b["focus"]), None)
            txt = "<b>%s – %s</b> %s" % (h(b["debut"]), h(b["fin"]), b["titre"])
            if cible:
                txt += " — %s : %s <i>(%s)</i>" % (EMOJI[cible["cours"]], cible["titre"],
                                                   carte.etape(cible).lower())
            elif "rattrapage" not in b["focus"]:
                # Aucune échéance ouverte sur ce bloc : c'est du temps à prendre
                # d'avance, pas du temps vide.
                txt += " — <i>aucune échéance ouverte : prise d'avance ou rattrapage</i>"
            bouts.append(txt)
        for e in data["evaluations"]:
            if d(e["date"]) == j and not e.get("fait"):
                bouts.append("⚠️ <b>%s</b> — %s <i>(%s)</i>"
                             % (e["titre"], nom(data, e["cours"]),
                                poids(e).replace("<b>", "").replace("</b>", "")))
        for l in data["lectures"]:
            if d(l["pour"]) == j:
                bouts.append("📖 %s" % l["quoi"])
        if not bouts:
            bouts.append("<i>rien de prévu — journée de repos</i>")
        etiquette = "<b>%s</b>" % jour_court(j)
        if i == 0:
            etiquette += " ← <i>aujourd'hui</i>"
        lignes.append([etiquette, "<br />".join(bouts)])
    return ["## 🗓️ Les 7 prochains jours", "",
            table(["Jour", "Ce que je fais"], lignes), ""]


def section_a_regler(data, jour):
    L = ["## 📌 À régler", ""]
    for t in data["taches_admin"]:
        if t["pour"] == "recurrent":
            L.append("- [ ] 🔁 %s" % t["quoi"])
            continue
        echeance = d(t["pour"])
        reste = (echeance - jour).days
        if reste < 0:
            tete = "- [ ] 🔴 <b>%s</b> — <i>%d jour%s de retard</i>" % (
                t["quoi"], -reste, "s" if reste < -1 else "")
        else:
            tete = "- [ ] 🔵 %s — <i>pour le %s</i>" % (t["quoi"], jour_court(echeance))
        if t.get("note"):
            tete += " · %s" % t["note"]
        L.append(tete)
    L.append("")
    return L


def section_echeances(data, jour):
    a_venir = sorted((e for e in data["evaluations"]
                      if not e.get("fait") and d(e["date"]) >= jour),
                     key=lambda e: e["date"])
    lignes = []
    for e in a_venir:
        reste = (d(e["date"]) - jour).days
        pastille = "🔴" if reste <= 2 else ("🟠" if reste <= 10 else "🔵")
        titre = e["titre"] + (" ⚠️" if e.get("a_confirmer") else "")
        lignes.append([pastille, jour_court(d(e["date"])), nom(data, e["cours"]),
                       titre, poids(e), compte(reste)])
    return ["## 📅 Toutes mes échéances à venir", "",
            "> 💡 Sélectionne ce tableau → <b>Transformer en base de données</b> "
            "pour filtrer par cours et cocher au fur et à mesure.", "",
            table(["", "Date", "Cours", "Évaluation", "Poids", "Compte à rebours"], lignes), "",
            "> ⚠️ = date ou pondération encore à confirmer auprès du prof. "
            "Être prêt une semaine trop tôt ne coûte rien ; l'inverse, oui.", ""]


def section_lectures(data, jour):
    a_venir = sorted((l for l in data["lectures"] if d(l["pour"]) >= jour),
                     key=lambda l: l["pour"])
    if not a_venir:
        return []
    return ["## 📖 Mes lectures", "",
            table(["Pour le", "Cours", "À lire"],
                  [[jour_court(d(l["pour"])), nom(data, l["cours"]), l["quoi"]] for l in a_venir]), ""]


def section_rouges(data, jour):
    """Toute semaine où il se joue SEUIL_ROUGE % ou plus, tous cours confondus."""
    paires = sorted(((int(n), d(deb)) for n, deb in data["session"]["semaines"].items()),
                    key=lambda p: p[1])
    lignes = []
    for idx, (num, debut) in enumerate(paires):
        fin = (paires[idx + 1][1] - dt.timedelta(days=1)) if idx + 1 < len(paires) \
            else debut + dt.timedelta(days=13)
        # La semaine d'études s'intercale entre deux semaines de cours : elle
        # n'appartient à aucune des deux.
        pause = d(data["session"]["semaine_etudes"][0])
        if debut < pause <= fin:
            fin = pause - dt.timedelta(days=1)
        dedans = [e for e in data["evaluations"] if debut <= d(e["date"]) <= fin]
        total = sum(e["poids"] for e in dedans)
        if total < SEUIL_ROUGE:
            continue
        quoi = " · ".join("%s %s %s" % (EMOJI[e["cours"]], e["titre"],
                                        poids(e).replace("<b>", "").replace("</b>", ""))
                          for e in sorted(dedans, key=lambda e: -e["poids"]))
        statut = "✅ passée" if fin < jour else ("🔥 en cours" if debut <= jour else "⏳ à venir")
        lignes.append(["<b>%d</b>" % num,
                       "%s – %s" % (jour_court(debut), jour_court(fin)),
                       quoi, "<b>%d %%</b>" % total, statut])
    return ["## 🔴 Mes semaines rouges", "",
            "> Toute semaine où il se joue <b>%d %% ou plus</b> de points, tous cours "
            "confondus. C'est là que se gagne ou se perd la session." % SEUIL_ROUGE, "",
            table(["Semaine", "Dates", "Ce qui tombe", "Poids total", "Statut"], lignes), ""]


def section_semaine_type(data):
    lignes = []
    for b in sorted(data["blocs_travail"], key=lambda b: (b["jour"], b["debut"])):
        deb = dt.datetime.strptime(b["debut"], "%H:%M")
        fin = dt.datetime.strptime(b["fin"], "%H:%M")
        mn = int((fin - deb).total_seconds() // 60)
        duree = ("%d h %02d" % (mn // 60, mn % 60)) if mn % 60 else "%d h" % (mn // 60)
        quand = "%s %s – %s" % (JOURS[b["jour"] - 1].capitalize(), h(b["debut"]), h(b["fin"]))
        quoi = "%s %s" % ("".join(EMOJI[f] for f in b["focus"] if f in EMOJI) or "🔁", b["titre"])
        if mn >= 120:
            quand, duree, quoi = "<b>%s</b>" % quand, "<b>%s</b>" % duree, "<b>%s</b>" % quoi
        lignes.append([quand, duree, quoi])
    return ["## 🗓️ Ma semaine type", "",
            table(["Quand", "Durée", "Ce que je fais"], lignes), "",
            "> ⚠️ Vendredi soir, samedi après-midi et dimanche matin restent <b>vides</b>. "
            "Ce n'est pas du temps perdu : c'est ce qui rend le reste tenable, "
            "semaine après semaine.", ""]


def section_methodes(data):
    if not data.get("methodes"):
        return []
    L = ["## 🧠 Mes méthodes, cours par cours", ""]
    dur = max(c["difficulte"] for c in data["cours"].values())
    for cle in sorted(data["methodes"], key=lambda k: -data["cours"][k]["difficulte"]):
        titre = "### %s" % nom(data, cle)
        if data["cours"][cle]["difficulte"] == dur:
            titre += " — <i>ma matière la plus difficile</i>"
        L += [titre, "", data["methodes"][cle], ""]
    return L


def section_avancement(data, jour):
    av = carte.avancement(data, jour)
    douteux = {}
    for e in data["evaluations"]:
        if e.get("a_verifier_lea") and not e.get("fait"):
            douteux[e["cours"]] = douteux.get(e["cours"], 0) + e["poids"]
    lignes = []
    for cle, (_, fait) in sorted(av.items(), key=lambda kv: -kv[1][1]):
        txt = "%d %%" % fait
        if douteux.get(cle):
            txt += " <i>(dont %d %% à confirmer)</i>" % douteux[cle]
        plein = max(0, min(10, round(fait / 10.0)))
        lignes.append([nom(data, cle), txt,
                       "<code>%s%s</code>" % ("▰" * plein, "▱" * (10 - plein))])
    moyenne = sum(f for _, f in av.values()) // len(av)
    L = ["## 📊 Mon avancement", "",
         table(["Cours", "Part de la note déjà jouée", ""], lignes), ""]
    pied = "> <b>%d %%</b> de la session est joué en moyenne, tous cours confondus." % moyenne
    if douteux:
        pied += (" Mais <b>%d %%</b> de points restent au statut incertain tant que les "
                 "évaluations ci-dessus ne sont pas confirmées." % sum(douteux.values()))
    return L + [pied, ""]


# --------------------------------------------------------------------------
# Assemblage
# --------------------------------------------------------------------------
def page(data, jour, mot=None):
    sem = carte.semaine_de(data, jour)
    entete = ("> 420.B0 Techniques de l'informatique · Cégep de Granby · "
              "24 août → 11 décembre<br /><b>Semaine %s sur 15</b>" % (sem or "—"))
    if carte.en_semaine_etudes(data, jour):
        entete += "<br /><i>Semaine d'études et d'encadrement — aucun cours</i>"

    actifs = carte.chantiers(data, jour)
    blocs = [[entete, ""], ["---", ""]]
    blocs.append(section_aujourdhui(data, jour, actifs))
    if mot:
        blocs.append([mot, ""])
    for s in (section_a_confirmer(data, jour), section_a_faire(data, jour, actifs),
              section_semaine(data, jour), section_a_regler(data, jour),
              section_echeances(data, jour), section_lectures(data, jour),
              section_rouges(data, jour), section_semaine_type(data),
              section_methodes(data), section_avancement(data, jour)):
        if s:
            blocs.append(["---", ""])
            blocs.append(s)

    corps = []
    for b in blocs:
        corps += b
    corps.append("<i>Mis à jour le %s · source : </i><i><code>donnees-session.json</code></i>"
                 "<i> · généré par </i><i><code>notion.py</code></i>" % jour_long(jour))
    return "\n".join(corps)


def main():
    args = [a for a in sys.argv[1:]]
    mot = None
    if "--mot" in args:
        i = args.index("--mot")
        mot = io.open(args[i + 1], encoding="utf-8").read().strip()
        del args[i:i + 2]
    jour = d(args[0]) if args else dt.date.today()
    data = carte.charger()
    sys.stdout.write(page(data, jour, mot) + "\n")


if __name__ == "__main__":
    main()

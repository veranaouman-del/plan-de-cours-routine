# -*- coding: utf-8 -*-
"""Tableau de bord Notion — Automne 2026.

Produit la page Notion complete a partir de donnees-session.json, en Markdown
Notion (tables <table>, cases a cocher, callouts). La sortie se colle telle quelle
dans update-page / replace_content.

    python3 notion.py                 -> la page d'aujourd'hui, sur stdout
    python3 notion.py 2026-10-11      -> la page d'une date precise
    python3 notion.py 2026-10-11 x.md -> ecrite dans un fichier

Le contenu vient entierement de donnees-session.json et des fonctions de carte.py :
les deux sorties (image du jour, page Notion) disent donc toujours la meme chose.
"""
import io
import os
import sys
import datetime as dt

import carte
from carte import d, court, ABREV, JOURS, MOIS

EMOJI = {"devlog": "💻", "web": "🌐", "litt": "📕", "anglais": "🗣️", "philo": "⚖️"}
JOURS_COURT = ["lun.", "mar.", "mer.", "jeu.", "ven.", "sam.", "dim."]
SEUIL_ROUGE = 30          # une semaine est "rouge" des 30 % de points, tous cours confondus


# --------------------------------------------------------------------------
# Petits utilitaires de mise en forme
# --------------------------------------------------------------------------
def _quantieme(j):
    return "1er" if j.day == 1 else str(j.day)


def jour_long(j):
    return "%s %s %s" % (JOURS[j.weekday()], _quantieme(j), MOIS[j.month - 1])


def jour_court(j):
    return "%s %s %s" % (JOURS_COURT[j.weekday()], _quantieme(j), ABREV[j.month - 1])


def heure(h):
    return h.replace(":", " h ")


def nom(data, cle):
    return "%s %s" % (EMOJI[cle], data["cours"][cle]["nom"])


def poids_txt(ev):
    if not ev["poids"]:
        return "formatif"
    return "**%d %%**" % ev["poids"] if ev["poids"] >= 20 else "%d %%" % ev["poids"]


def pastille(reste):
    return "🔴" if reste <= 4 else ("🟠" if reste <= 12 else "🔵")


def barre(pct):
    plein = int(round(pct / 10.0))
    return "`" + "▰" * plein + "▱" * (10 - plein) + "`"


def table(entetes, lignes):
    """Une table Notion. Les cellules ne portent que du rich text."""
    out = ['<table fit-page-width="true" header-row="true">', "\t<tr>"]
    out += ["\t\t<td>%s</td>" % e for e in entetes]
    out.append("\t</tr>")
    for ligne in lignes:
        out.append("\t<tr>")
        out += ["\t\t<td>%s</td>" % c for c in ligne]
        out.append("\t</tr>")
    out.append("</table>")
    return "\n".join(out)


# --------------------------------------------------------------------------
# Sections
# --------------------------------------------------------------------------
def section_aujourdhui(data, jour):
    """Ce qui se passe aujourd'hui, et la phrase qui dit ou on va ensuite."""
    L = ["## 📍 Aujourd'hui — %s" % jour_long(jour)]

    for c in carte.cours_du_jour(data, jour):
        L.append("- 🎓 **%s** · %s – %s · %s"
                 % (data["cours"][c["cours"]]["nom"], heure(c["debut"]), heure(c["fin"]), c["local"]))
    for b in carte.blocs_du_jour(data, jour):
        L.append("- 🎯 **%s** · %s – %s" % (b["titre"], heure(b["debut"]), heure(b["fin"])))
    if not carte.cours_du_jour(data, jour) and not carte.blocs_du_jour(data, jour):
        L.append("- 😮‍💨 **Journée libre** — repos assumé, c'est prévu au plan.")

    actifs = carte.chantiers(data, jour)
    if actifs:
        p = actifs[0]
        L.append("> 🔥 **Priorité du jour :** %s — %s (%s), **%s**."
                 % (nom(data, p["cours"]), p["titre"], poids_txt(p).replace("**", ""),
                    carte.jx(p["reste"])))

    suite = [e for e in carte.chantiers_tous(data, jour) if e["reste"] > 0]
    if suite:
        n = suite[0]
        L.append("> ⏭️ **Ensuite :** la prochaine échéance est %s — %s (%s), le %s."
                 % (nom(data, n["cours"]), n["titre"], poids_txt(n).replace("**", ""),
                    jour_court(d(n["date"])).rstrip(".")))
    return "\n".join(L)


def section_confirmer(data, jour):
    conf = carte.a_confirmer(data, jour)
    if not conf:
        return None
    pts = sum(e["poids"] for e in conf)
    L = ["## 🔴 À confirmer sur LÉA — remises passées au statut inconnu",
         "> Ces remises sont passées et leur dépôt n'est pas confirmé. Tant qu'elles sont là, "
         "mon avancement est une hypothèse, pas un fait."]
    L.append(table(["Évaluation", "Cours", "Poids", "Était dû le", "Retard"],
                   [[e["titre"], nom(data, e["cours"]), poids_txt(e), jour_court(d(e["date"])),
                     "%d jours" % (jour - d(e["date"])).days] for e in conf]))
    L.append("- [ ] Vérifier sur LÉA celles qui sont bien déposées → l'avancement redevient exact")
    L.append("- [ ] Écrire au prof **le jour même** pour celles qui ne le sont pas — **%d %%** "
             "de points au statut incertain" % pts)
    return "\n".join(L)


def section_a_faire(data, jour):
    puce = {"RETARD": "🔴", "CONFIRMER": "🔴", "REMISE": "🔴", "ADMIN": "🟠",
            "FINIR": "🟠", "TEST BLANC": "🟠", "LECTURE": "📖"}
    actifs = carte.chantiers(data, jour)
    L = ["## ✅ À faire aujourd'hui"]
    for tag, t in carte.taches_du_jour(data, jour, actifs):
        L.append("- [ ] %s **%s** — %s" % (puce.get(tag, "🔵"), tag, t))
    return "\n".join(L)


def section_sept_jours(data, jour):
    """L'horizon utile : assez loin pour anticiper, assez court pour rester lisible."""
    lignes = []
    for i in range(7):
        j = jour + dt.timedelta(days=i)
        quand = []
        for c in carte.cours_du_jour(data, j):
            quand.append("%s %s" % (EMOJI[c["cours"]], heure(c["debut"])))
        for b in carte.blocs_du_jour(data, j):
            quand.append("%s – %s" % (heure(b["debut"]), heure(b["fin"])))

        quoi = [b["titre"] for b in carte.blocs_du_jour(data, j)]
        for e in carte.chantiers_tous(data, j):
            if e["reste"] == 0:
                quoi.insert(0, "⚠️ **REMISE : %s** (%s)" % (e["titre"], poids_txt(e).replace("**", "")))

        etiquette = "**%s**" % jour_court(j)
        if i == 0:
            etiquette += " ← *aujourd'hui*"
        if carte.en_semaine_etudes(data, j):
            quand.insert(0, "*semaine d'études*")
        lignes.append([etiquette, "<br>".join(quand) or "—", "<br>".join(quoi) or "*libre*"])
    return "## 🗓️ Les 7 prochains jours\n" + table(["Jour", "Quand", "Ce que je fais"], lignes)


def section_admin(data, jour):
    L = ["## 📌 À régler tout de suite"]
    # le plus en retard d'abord, puis par echeance : la liste se lit de haut en bas
    ordre = sorted(data["taches_admin"],
                   key=lambda t: (t["pour"] == "recurrent", t.get("pour", "")))
    for t in ordre:
        if t["pour"] == "recurrent":
            L.append("- [ ] 🔁 %s" % t["quoi"])
            continue
        ech = d(t["pour"])
        reste = (ech - jour).days
        if reste < 0:
            L.append("- [ ] 🔴 **%s** — *%d jours de retard*" % (t["quoi"], -reste))
        else:
            L.append("- [ ] %s %s — *pour le %s*"
                     % ("🟠" if t.get("urgent") else "🔵", t["quoi"], jour_court(ech)))
    return "\n".join(L)


def section_echeances(data, jour):
    lignes = [[pastille(e["reste"]), jour_court(d(e["date"])), nom(data, e["cours"]),
               e["titre"], poids_txt(e), carte.jx(e["reste"])]
              for e in carte.chantiers_tous(data, jour)]
    return ("## 📅 Toutes mes échéances à venir\n"
            "> 💡 Sélectionne ce tableau → **Transformer en base de données** pour filtrer par cours "
            "et cocher au fur et à mesure.\n"
            + table(["", "Date", "Cours", "Évaluation", "Poids", "Compte à rebours"], lignes))


def section_lectures(data, jour):
    lignes = [[jour_court(d(l["pour"])), nom(data, l["cours"]), l["quoi"]]
              for l in sorted(data["lectures"], key=lambda l: l["pour"])
              if d(l["pour"]) >= jour]
    if not lignes:
        return None
    return "## 📖 Mes lectures\n" + table(["Pour le", "Cours", "À lire"], lignes)


def semaines_rouges(data, jour):
    """Une semaine rouge, c'est 30 % de points ou plus en cinq jours, tous cours confondus.

    Calcule, jamais saisi a la main : si une date bouge, la liste bouge avec elle.
    """
    bornes = sorted(((int(n), d(deb)) for n, deb in data["session"]["semaines"].items()),
                    key=lambda p: p[1])
    paquets = {}
    for ev in data["evaluations"]:
        e = d(ev["date"])
        num = None
        for n, deb in bornes:
            if e >= deb:
                num = n
        if num:
            paquets.setdefault(num, []).append(ev)

    lignes = []
    for num, deb in bornes:
        evs = paquets.get(num, [])
        total = sum(e["poids"] for e in evs)
        if total < SEUIL_ROUGE:
            continue
        courante = " ← *ici*" if deb <= jour <= deb + dt.timedelta(days=6) else ""
        passee = all(d(e["date"]) < jour for e in evs)
        quoi = " · ".join("%s %s %s" % (EMOJI[e["cours"]], e["titre"],
                                        ("%d %%" % e["poids"]) if e["poids"] else "formatif")
                          for e in sorted(evs, key=lambda e: -e["poids"]))
        fin = max(d(e["date"]) for e in evs)
        fin = max(fin, deb + dt.timedelta(days=6))
        lignes.append(["**%d**%s" % (num, courante),
                       "%s – %s" % (jour_court(deb), jour_court(fin)),
                       quoi, "**%d %%**" % total, "✅ passée" if passee else "⏳ à venir"])
    return ("## 🔴 Mes semaines rouges\n"
            "> Toute semaine où il se joue **%d %% ou plus** de points, tous cours confondus. "
            "C'est là que se gagne ou se perd la session.\n" % SEUIL_ROUGE
            + table(["Semaine", "Dates", "Ce qui tombe", "Poids total", "Statut"], lignes))


def section_semaine_type(data):
    lignes = []
    for b in sorted(data["blocs_travail"], key=lambda b: (b["jour"], b["debut"])):
        h1 = dt.datetime.strptime(b["debut"], "%H:%M")
        h2 = dt.datetime.strptime(b["fin"], "%H:%M")
        mins = int((h2 - h1).total_seconds() // 60)
        duree = "%d h%s" % (mins // 60, (" %02d" % (mins % 60)) if mins % 60 else "")
        gros = b["titre"].startswith("GROS BLOC")
        quand = "%s %s – %s" % (JOURS[b["jour"] - 1].capitalize(), heure(b["debut"]), heure(b["fin"]))
        icones = "".join(EMOJI.get(f, "🔁") for f in b["focus"])
        lignes.append(["**%s**" % quand if gros else quand,
                       "**%s**" % duree if gros else duree,
                       "**%s %s**" % (icones, b["titre"]) if gros else "%s %s" % (icones, b["titre"])])
    return ("## 🗓️ Ma semaine type\n" + table(["Quand", "Durée", "Ce que je fais"], lignes)
            + "\n> ⚠️ Vendredi soir, samedi après-midi et dimanche matin restent **vides**. "
              "Ce n'est pas du temps perdu : c'est ce qui rend le reste tenable, semaine après semaine.")


def section_methodes(data):
    L = ["## 🧠 Mes méthodes, cours par cours"]
    dur = max(c["difficulte"] for c in data["cours"].values())
    for cle, c in sorted(data["cours"].items(), key=lambda kv: -kv[1]["difficulte"]):
        titre = "### %s" % nom(data, cle)
        if c["difficulte"] == dur:
            titre += " — *ma matière la plus difficile*"
        L += [titre, c["methode"]]
    return "\n".join(L)


def section_avancement(data, jour):
    av = carte.avancement(data, jour)
    lignes = [[nom(data, cle), "%d %%" % pct, barre(pct)]
              for cle, (_, pct) in sorted(av.items(), key=lambda kv: -kv[1][1])]
    moyenne = sum(p for _, (_, p) in av.items()) / float(len(av))
    note = ("## 📊 Mon avancement\n" + table(["Cours", "Part de la note déjà jouée", ""], lignes)
            + "\n> **%d %%** de la session est joué en moyenne, tous cours confondus." % round(moyenne))
    conf = carte.a_confirmer(data, jour)
    if conf:
        note += (" Mais **%d %%** de points restent au statut incertain tant que les remises "
                 "ci-dessus ne sont pas confirmées sur LÉA." % sum(e["poids"] for e in conf))
    return note


# --------------------------------------------------------------------------
def page(data, jour):
    sem = carte.semaine_de(data, jour)
    a, b = data["session"]["semaine_etudes"]
    entete = ["> Cégep de Granby · Techniques de l'informatique (420.B0) · 24 août → 11 décembre<br>"
              + ("**Semaine d'études** — aucun cours" if carte.en_semaine_etudes(data, jour)
                 else "**Semaine %s sur 15**" % (sem or "—"))
              + " · Semaine d'études : %s au %s" % (jour_court(d(a)), jour_court(d(b)))]

    blocs = [
        "\n".join(entete),
        section_aujourdhui(data, jour),
        section_confirmer(data, jour),
        section_a_faire(data, jour),
        section_sept_jours(data, jour),
        section_admin(data, jour),
        section_echeances(data, jour),
        section_lectures(data, jour),
        semaines_rouges(data, jour),
        section_semaine_type(data),
        section_methodes(data),
        section_avancement(data, jour),
        "*Mis à jour le %s · source : `donnees-session.json` · généré par `notion.py`*" % jour_long(jour),
    ]
    return "\n\n---\n\n".join(b for b in blocs if b)


def main():
    args = sys.argv[1:]
    jour = d(args[0]) if args else dt.date.today()
    texte = page(carte.charger(), jour)
    if len(args) > 1:
        io.open(args[1], "w", encoding="utf-8").write(texte)
        print(args[1])
    else:
        sys.stdout.write(texte + "\n")


if __name__ == "__main__":
    main()

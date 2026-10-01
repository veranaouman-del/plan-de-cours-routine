# -*- coding: utf-8 -*-
"""Page Notion « Ma session » — Automne 2026.

Génère le Markdown enrichi de la page de tableau de bord à partir de
donnees-session.json, exactement comme carte.py génère la carte du jour.

    python3 notion.py              -> aujourd'hui, sur la sortie standard
    python3 notion.py 2026-10-07   -> une date précise

Le résultat se pousse dans Notion avec le connecteur (commande replace_content)
sur la page « Ma session — Automne 2026 ».

Rien n'est codé en dur : pour changer une échéance, éditer donnees-session.json.
"""
import sys
import datetime as dt

import carte

EMOJI = {"devlog": "💻", "web": "🌐", "litt": "📕", "anglais": "🗣️", "philo": "⚖️"}
JOURS_COURTS = ["lun.", "mar.", "mer.", "jeu.", "ven.", "sam.", "dim."]


def jour_court(j):
    n = "1er" if j.day == 1 else str(j.day)
    return "%s %s %s" % (JOURS_COURTS[j.weekday()], n, carte.ABREV[j.month - 1])


def jour_long(j):
    n = "1er" if j.day == 1 else str(j.day)
    return "%s %s %s" % (carte.JOURS[j.weekday()], n, carte.MOIS[j.month - 1])


def heure(h):
    hh, mm = h.split(":")
    return "%d h" % int(hh) if mm == "00" else "%d h %s" % (int(hh), mm)


def plage(a, b):
    return "%s – %s" % (heure(a), heure(b))


def em(data, cle):
    return "%s %s" % (EMOJI.get(cle, "•"), data["cours"][cle].get("court", data["cours"][cle]["nom"]))


def table(lignes):
    out = ['<table header-row="true">']
    for ligne in lignes:
        out.append("<tr>")
        for cell in ligne:
            out.append("<td>%s</td>" % cell)
        out.append("</tr>")
    out.append("</table>")
    return "\n".join(out)


def pastille(reste):
    return "🔴" if reste <= 2 else ("🟠" if reste <= 9 else "🔵")


def gras_si(txt, lourd):
    return "**%s**" % txt if lourd else txt


# ---------------------------------------------------------------------------
def page(data, jour):
    sem = carte.semaine_de(data, jour)
    actifs = carte.chantiers(data, jour)
    L = []

    L.append("# 🎓 Ma session — Automne 2026")
    L.append("> Cégep de Granby · Techniques de l'informatique (420.B0) · 24 août → 11 décembre")
    L.append("> **Semaine %s sur 15** · Semaine d'études : 12 au 16 octobre" % (sem or "—"))
    L.append("---")

    # ---- aujourd'hui
    L.append("## 📍 Aujourd'hui — %s" % jour_long(jour))
    for c in carte.cours_du_jour(data, jour):
        L.append("- %s **%s** · %s · %s" % (
            EMOJI.get(c["cours"], "•"), data["cours"][c["cours"]]["nom"],
            plage(c["debut"], c["fin"]), c["local"]))
    for b in carte.blocs_du_jour(data, jour):
        L.append("- 🎯 **%s** · %s" % (b["titre"], plage(b["debut"], b["fin"])))
    if actifs:
        p = actifs[0]
        L.append("> 🔥 **Priorité du jour :** %s — %s (%d %%), **%s**." % (
            em(data, p["cours"]), p["titre"], p["poids"], carte.jx(p["reste"]).lower()))
    L.append("---")

    # ---- 7 prochains jours
    L.append("## 🗓️ Les 7 prochains jours")
    lignes = [["Jour", "Cours", "Ce que je fais"]]
    for i in range(7):
        j = jour + dt.timedelta(days=i)
        libelle = "**%s**%s" % (jour_court(j), " ← *aujourd'hui*" if i == 0 else "")
        cours = "<br>".join(em(data, c["cours"]) for c in carte.cours_du_jour(data, j)) or "—"
        blocs = carte.blocs_du_jour(data, j)
        if blocs:
            cours += "<br>%s" % plage(blocs[0]["debut"], blocs[0]["fin"])
        taches = carte.taches_du_jour(data, j, carte.chantiers(data, j))
        quoi = "—"
        for tag, t in taches:
            if tag in ("RETARD", "ADMIN"):
                continue
            # "Nom complet du cours — Titre" -> emoji + nom court + titre
            titre = t.split(" — ", 1)[-1]
            cle = next((k for k, c in data["cours"].items() if t.startswith(c["nom"])), None)
            etiquette = "%s — %s" % (em(data, cle), titre) if cle else t
            quoi = ("🔥 **%s**" % etiquette) if tag in ("REMISE", "RELIRE") \
                else "%s *(%s)*" % (etiquette, tag.lower())
            break
        lignes.append([libelle, cours, quoi])
    L.append(table(lignes))
    L.append("---")

    # ---- remises passees jamais cochees
    passees = carte.passees_non_reglees(data, jour)
    if passees:
        L.append("## 🔴 À confirmer — remises passées jamais cochées")
        L.append("> Ces évaluations sont passées et toujours marquées « non faites » dans "
                 "`donnees-session.json`. Tant qu'elles y sont, mon avancement est une "
                 "hypothèse, pas un fait.")
        lignes = [["Évaluation", "Cours", "Poids", "Était dû le", "Retard"]]
        for e in passees:
            lignes.append([e["titre"], em(data, e["cours"]), "**%d %%**" % e["poids"],
                           jour_court(carte.d(e["date"])), "%d jours" % e["depuis"]])
        L.append(table(lignes))
        L.append("- [ ] Cocher celles qui sont remises → l'avancement redevient exact")
        L.append("- [ ] Écrire au prof **le jour même** pour celles qui ne le sont pas")
        L.append("---")

    # ---- admin
    L.append("## ✅ À régler tout de suite")
    for t in data["taches_admin"]:
        if t["pour"] == "recurrent":
            L.append("- [ ] 🔁 %s" % t["quoi"])
            continue
        reste = (carte.d(t["pour"]) - jour).days
        if reste < 0:
            L.append("- [ ] 🔴 **%s** — *%d jours de retard*" % (t["quoi"], -reste))
        elif reste <= 7:
            L.append("- [ ] 🟠 %s — *%s*" % (t["quoi"], "aujourd'hui" if reste == 0 else
                                             "dans %d jour%s" % (reste, "s" if reste > 1 else "")))
    L.append("---")

    # ---- echeances
    L.append("## 📅 Toutes mes échéances à venir")
    L.append("> 💡 Sélectionne ce tableau → **Transformer en base de données** pour filtrer "
             "par cours et cocher au fur et à mesure.")
    lignes = [["", "Date", "Cours", "Évaluation", "Poids", "Compte à rebours"]]
    for e in carte.chantiers_tous(data, jour):
        poids = "**%d %%**" % e["poids"] if e["poids"] >= 20 else (
            "%d %%" % e["poids"] if e["poids"] else "formatif")
        lignes.append([pastille(e["reste"]), jour_court(carte.d(e["date"])), em(data, e["cours"]),
                       e["titre"], poids, carte.jx(e["reste"])])
    L.append(table(lignes))
    L.append("---")

    # ---- lectures
    L.append("## 📖 Mes lectures")
    lignes = [["Pour le", "Cours", "À lire"]]
    for l in sorted(data["lectures"], key=lambda x: x["pour"]):
        if carte.d(l["pour"]) < jour:
            continue
        lignes.append([jour_court(carte.d(l["pour"])), em(data, l["cours"]), l["quoi"]])
    L.append(table(lignes))
    L.append("---")

    # ---- semaines rouges, calculees et non plus figees
    L.append("## 🔴 Mes semaines rouges")
    L.append("> Toute semaine de session où il se joue **30 % ou plus** de points, tous cours "
             "confondus. C'est là que se gagne ou se perd la session.")
    paires = sorted(((int(n), carte.d(deb)) for n, deb in data["session"]["semaines"].items()),
                    key=lambda p: p[1])
    lignes = [["Semaine", "Dates", "Ce qui tombe", "Poids total"]]
    for num, debut in paires:
        fin = debut + dt.timedelta(days=6)
        dedans = [e for e in data["evaluations"]
                  if debut <= carte.d(e["date"]) <= fin and e["poids"]]
        total = sum(e["poids"] for e in dedans)
        if total < 30:
            continue
        ici = debut <= jour <= fin
        quoi = " · ".join("%s %s %d %%" % (EMOJI.get(e["cours"], "•"), e["titre"], e["poids"])
                          for e in sorted(dedans, key=lambda x: -x["poids"]))
        lignes.append(["**%d**%s" % (num, " ← *ici*" if ici else ""),
                       "%s – %s" % (jour_court(debut), jour_court(fin)),
                       quoi, "**%d %%**" % total])
    L.append(table(lignes))
    L.append("---")

    # ---- semaine type
    L.append("## 🗓️ Ma semaine type")
    lignes = [["Quand", "Durée", "Ce que je fais"]]
    for b in data["blocs_travail"]:
        h1 = dt.datetime.strptime(b["debut"], "%H:%M")
        h2 = dt.datetime.strptime(b["fin"], "%H:%M")
        mins = int((h2 - h1).total_seconds() // 60)
        duree = "%d h%s" % (mins // 60, " %02d" % (mins % 60) if mins % 60 else "")
        quand = "%s %s" % (carte.JOURS[b["jour"] - 1].capitalize(), plage(b["debut"], b["fin"]))
        icones = "".join(EMOJI.get(f, "🔁") for f in b["focus"])
        gros = b["titre"].startswith("GROS") or "RATTRAPAGE" in b["titre"]
        lignes.append([gras_si(quand, gros), gras_si(duree, gros),
                       "%s %s" % (icones, gras_si(b["titre"], gros))])
    L.append(table(lignes))
    L.append("> ⚠️ Vendredi soir, samedi après-midi et dimanche matin restent **vides**. "
             "Ce n'est pas du temps perdu : c'est ce qui rend le reste tenable semaine après semaine.")
    L.append("---")

    # ---- methodes (texte stable, pas genere)
    L.append("""## 🧠 Mes méthodes, cours par cours
### 🗣️ Anglais
Tout se joue en classe. Remplir le journal Odyssey **le jour même** (5 % garantis). Les évaluations orales valent **45 %** du cours : elles se préparent **à voix haute**, pas par écrit.
### 💻 Développement de logiciels
Le code se retient par les doigts. Refaire les exercices dirigés **sans la correction**, puis comparer. S'entraîner à écrire du code **sur papier** — c'est ce qui est demandé à l'examen.
### 🌐 Programmation Web I
Chaque TP s'appuie sur le précédent. Un TP bâclé se paie deux fois. Après chaque remise, noter en trois lignes **ce qui a bloqué** : c'est exactement ce qui tombera à l'Évaluation #1.
### ⚖️ Éthique et politique
Droit aux notes de cours à **toutes** les évaluations. La vraie préparation, c'est donc de **construire de bonnes notes**, pas de mémoriser. Un tableau par penseur : thèse, critère du juste, objection principale, exemple concret. C'est ce tableau qu'on apporte à l'examen.
### 📕 Littérature et imaginaire
Annoter **pendant** la lecture, jamais après. Un carnet de citations classées par thème. Garder 10 minutes de relecture linguistique en fin de rédaction — la langue vaut **25 %** de chaque dissertation.
---
## 🔁 Quand je prends du retard
Le bloc du dimanche 16 h – 18 h existe pour ça. L'ordre est toujours le même : **ce qui est noté le plus lourd et qui tombe le plus tôt d'abord.** Une lecture en retard se rattrape ; une remise manquée, non.
Si deux semaines de suite débordent, ce n'est pas un problème d'effort : c'est que le plan est trop chargé. On retire quelque chose plutôt que d'accumuler.
---""")

    # ---- avancement
    L.append("## 📊 Mon avancement")
    lignes = [["Cours", "Part de la note déjà jouée"]]
    av = carte.avancement(data, jour)
    for cle, (nom, pct) in sorted(av.items(), key=lambda kv: -kv[1][1]):
        lignes.append(["%s %s" % (EMOJI.get(cle, "•"), nom), "%d %%" % pct])
    L.append(table(lignes))
    total = sum(p for _, p in av.values()) / len(av)
    L.append("> **%d %%** de la session est joué, tous cours confondus." % round(total))
    L.append("---")
    L.append("*Mis à jour automatiquement le %s · source : **`donnees-session.json`** · "
             "généré par **`notion.py`***" % jour_long(jour))

    return "\n".join(L)


if __name__ == "__main__":
    args = sys.argv[1:]
    j = carte.d(args[0]) if args else dt.date.today()
    print(page(carte.charger(), j))

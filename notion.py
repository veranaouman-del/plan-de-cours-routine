# -*- coding: utf-8 -*-
"""Page Notion « Ma session » — Automne 2026.

Regénère le contenu complet de la page de vue d'ensemble à partir de
donnees-session.json. Rien n'est écrit en dur : les compteurs J-x, les semaines
rouges, l'avancement et les cases à cocher se recalculent à la date demandée.

    python3 notion.py                 -> la page à la date du jour
    python3 notion.py 2026-09-20      -> la page telle qu'elle sera ce dimanche
    python3 notion.py --semaine       -> juste le bloc « Cette semaine »

Prévu pour tourner le dimanche soir, pas tous les matins : Slack porte la carte
du jour, cette page porte la vue d'ensemble.
"""
import sys
import datetime as dt

import carte
from carte import d, court, MOIS, JOURS

# Une semaine est « rouge » au-delà de ce poids cumulé, ou de ce nombre
# d'évaluations. Les deux seuils attrapent deux problèmes différents : une
# grosse note isolée, et l'empilement de petites remises la même semaine.
SEUIL_POIDS = 25
SEUIL_NOMBRE = 3


# --------------------------------------------------------------------------
# Découpage en semaines de session
# --------------------------------------------------------------------------
def semaines(data):
    """[(numéro, lundi, dimanche)] pour les 15 semaines de la session."""
    out = []
    for num, debut in sorted(data["session"]["semaines"].items(), key=lambda p: int(p[0])):
        lundi = d(debut)
        out.append((int(num), lundi, lundi + dt.timedelta(days=6)))
    return out


def semaine_contenant(data, jour):
    for num, lundi, dimanche in semaines(data):
        if lundi <= jour <= dimanche:
            return num, lundi, dimanche
    return None, None, None


def evaluations_de_semaine(data, lundi, dimanche):
    return [e for e in data["evaluations"] if lundi <= d(e["date"]) <= dimanche]


def semaines_rouges(data):
    """Les semaines à surveiller, calculées et non listées à la main."""
    out = []
    for num, lundi, dimanche in semaines(data):
        evs = evaluations_de_semaine(data, lundi, dimanche)
        poids = sum(e["poids"] for e in evs)
        if poids >= SEUIL_POIDS or len(evs) >= SEUIL_NOMBRE:
            out.append((num, lundi, dimanche, evs, poids))
    return out


def rouge_passee(evs, jour):
    """Une semaine rouge est derrière moi quand sa dernière évaluation l'est —
    pas quand le dimanche est atteint. Le dimanche d'une semaine dont l'examen
    tombait le mardi, tout est déjà joué."""
    return max(d(e["date"]) for e in evs) < jour


# --------------------------------------------------------------------------
# Mise en forme
# --------------------------------------------------------------------------
def jx(ev, jour):
    """Le compte à rebours, ou une coche si c'est derrière moi."""
    reste = (d(ev["date"]) - jour).days
    if ev.get("fait") or reste < 0:
        return "✅ fait"
    if reste == 0:
        return "**AUJOURD'HUI**"
    if reste == 1:
        return "**DEMAIN**"
    return "J-%d" % reste


def pastille(ev, jour):
    reste = (d(ev["date"]) - jour).days
    if ev.get("fait") or reste < 0:
        return "✅"
    if reste <= 7:
        return "🔴"
    if reste <= 21:
        return "🟠"
    return "🔵"


def poids_affiche(ev):
    if ev["poids"] == 0:
        return "formatif"
    texte = "%d %%" % ev["poids"]
    if ev["poids"] >= 20:
        texte = "**%s**" % texte
    if ev.get("poids_approx"):
        texte += " *(à confirmer)*"
    return texte


def date_longue(jour):
    return "%s %d %s" % (JOURS[jour.weekday()], jour.day, MOIS[jour.month - 1])


def heure(hhmm):
    """08:55 -> « 8 h 55 », 18:00 -> « 18 h »."""
    h, m = (int(x) for x in hhmm.split(":"))
    return "%d h %02d" % (h, m) if m else "%d h" % h


def intervalle(lundi, dimanche):
    """« 21 – 27 sept. », mais « 28 sept. – 4 oct. » à cheval sur deux mois."""
    if lundi.month == dimanche.month:
        return "%d – %d %s" % (lundi.day, dimanche.day, carte.ABREV[dimanche.month - 1])
    return "%s – %s" % (court(lundi), court(dimanche))


def nom(data, ev):
    c = data["cours"][ev["cours"]]
    return "%s %s" % (c["emoji"], c["court"])


# --------------------------------------------------------------------------
# Les sections
# --------------------------------------------------------------------------
HORIZON = 7      # jours couverts par la liste à cocher
PLAFOND = 8      # au-delà, la liste cesse d'être une liste et devient un mur


def bloc_semaine(data, jour):
    """Les cases à cocher des sept prochains jours, tirées du même moteur que la
    carte du jour mais étalées sur la semaine au lieu d'une seule journée.

    Fenêtre glissante et non « du lundi au dimanche » : la page se regénère le
    dimanche soir, et ce qui compte ce soir-là, c'est la semaine qui commence."""
    fin = jour + dt.timedelta(days=HORIZON)
    retards, courant = [], []

    for t in data["taches_admin"]:
        if t["pour"] == "recurrent":
            continue
        echeance = d(t["pour"])
        if echeance < jour and t.get("urgent"):
            retards.append("- [ ] 🔴 %s — **en retard**" % t["quoi"])
        elif jour <= echeance <= fin:
            courant.append("- [ ] ✉️ %s — pour le %s" % (t["quoi"], court(echeance)))

    for l in data["lectures"]:
        echeance = d(l["pour"])
        if jour <= echeance <= fin:
            c = data["cours"][l["cours"]]
            courant.append("- [ ] %s %s — pour le %s" % (c["emoji"], l["quoi"], court(echeance)))

    # Les chantiers sont déjà triés par urgence. On ne garde que ceux qui
    # tombent dans la fenêtre : préparer un travail dû dans deux mois n'a rien
    # à faire dans la liste de la semaine, même si sa fenêtre de prép est ouverte.
    for e in carte.chantiers(data, jour):
        if d(e["date"]) > fin:
            continue
        c = data["cours"][e["cours"]]
        courant.append("- [ ] %s %s — %s, %s (%s)" % (
            c["emoji"], e["titre"], c["court"], jx(e, jour), carte.etape(e).lower()))

    L = retards + courant[:PLAFOND - len(retards)]
    reste = len(retards) + len(courant) - len(L)
    if reste > 0:
        L.append("- [ ] *…et %d autre%s point%s, dans le tableau des échéances ci-dessous.*"
                 % (reste, "s" if reste > 1 else "", "s" if reste > 1 else ""))
    return L or ["- [ ] Rien ne presse d'ici sept jours. En profiter pour prendre de l'avance."]


def bloc_rouges(data, jour):
    L = ["| Semaine | Dates | Ce qui tombe | La règle |", "| --- | --- | --- | --- |"]
    for num, lundi, dimanche, evs, poids in semaines_rouges(data):
        passee = rouge_passee(evs, jour)
        etiquette = "~~**%d**~~" % num if passee else "**%d**" % num
        dates = intervalle(lundi, dimanche)
        contenu = ", ".join(
            "%s %s %s" % (data["cours"][e["cours"]]["emoji"], e["titre"],
                          "formatif" if e["poids"] == 0 else "%d %%" % e["poids"])
            for e in sorted(evs, key=lambda e: e["date"]))
        regle = data.get("consignes_semaines", {}).get(str(num))
        if not regle:
            regle = "%d %% de la session en une semaine. Rien ne commence ce lundi-là." % poids
        if passee:
            regle = "*Derrière moi.*"
        L.append("| %s | %s | %s | %s |" % (etiquette, dates, contenu, regle))
    return L


def bloc_echeances(data, jour):
    L = ["| | Date | Cours | Évaluation | Poids | Compte à rebours |",
         "| --- | --- | --- | --- | --- | --- |"]
    for e in sorted(data["evaluations"], key=lambda e: e["date"]):
        echeance = d(e["date"])
        titre = e["titre"]
        if e.get("a_confirmer"):
            titre += " *(date à confirmer)*"
        L.append("| %s | %s | %s | %s | %s | %s |" % (
            pastille(e, jour), date_longue(echeance), nom(data, e),
            titre, poids_affiche(e), jx(e, jour)))
    return L


def bloc_semaine_type(data):
    L = ["| Quand | Durée | Ce que je fais |", "| --- | --- | --- |"]
    total = dt.timedelta()
    for b in sorted(data["blocs_travail"], key=lambda b: (b["jour"], b["debut"])):
        h1, m1 = (int(x) for x in b["debut"].split(":"))
        h2, m2 = (int(x) for x in b["fin"].split(":"))
        duree = dt.timedelta(hours=h2 - h1, minutes=m2 - m1)
        total += duree
        heures, minutes = divmod(int(duree.total_seconds() // 60), 60)
        duree_txt = "%d h %02d" % (heures, minutes) if minutes else "%d h" % heures
        emojis = "".join(data["cours"][f]["emoji"] for f in b["focus"] if f in data["cours"]) or "🔁"
        quand = "%s %s – %s" % (JOURS[b["jour"] - 1].capitalize(),
                                heure(b["debut"]), heure(b["fin"]))
        # Les blocs de 3 h et plus sont la colonne vertébrale de la semaine : en gras.
        if duree >= dt.timedelta(hours=3):
            L.append("| **%s** | **%s** | %s **%s** |" % (quand, duree_txt, emojis, b["titre"]))
        else:
            L.append("| %s | %s | %s %s |" % (quand, duree_txt, emojis, b["titre"]))
    return L, total.total_seconds() / 3600


def bloc_avancement(data, jour):
    L = ["| Cours | Part de la note déjà jouée |", "| --- | --- |"]
    total_fait = 0
    for cle, (nom_cours, fait) in carte.avancement(data, jour).items():
        total_fait += fait
        L.append("| %s %s | %d %% |" % (data["cours"][cle]["emoji"], nom_cours, fait))
    return L, total_fait / len(data["cours"])


def bloc_profs(data, jour):
    L = []
    for t in sorted(data["taches_admin"], key=lambda t: (t["pour"] == "recurrent", t["pour"])):
        if t["pour"] == "recurrent":
            L.append("- [ ] 🔁 %s" % t["quoi"])
            continue
        echeance = d(t["pour"])
        reste = (echeance - jour).days
        if reste < 0 and t.get("urgent"):
            L.append("- [ ] 🔴 %s — **en retard**" % t["quoi"])
        elif reste < 0:
            L.append("- [ ] ⬜ %s — échéance passée le %s" % (t["quoi"], court(echeance)))
        else:
            puce = "🔴" if t.get("urgent") else ("🟠" if reste <= 14 else "🔵")
            L.append("- [ ] %s %s — pour le %s" % (puce, t["quoi"], court(echeance)))
    return L


# --------------------------------------------------------------------------
# La page
# --------------------------------------------------------------------------
def page(data, jour):
    num, lundi, dimanche = semaine_contenant(data, jour)
    s = data["session"]
    debut, fin = d(s["debut"]), d(s["fin"])
    etudes_a, etudes_b = (d(x) for x in s["semaine_etudes"])

    L = []
    L.append("> %s · %s" % (data["programme"], s["nom"]))
    L.append("> Du %s au %s · Semaine d'études : %s au %s"
             % (court(debut), court(fin), court(etudes_a), court(etudes_b)))
    L.append("> **Nous sommes en semaine %d sur 15.** Page mise à jour le %s."
             % (num or 15, date_longue(jour)))
    L.append("")
    L.append("---")
    L.append("")

    fin_horizon = jour + dt.timedelta(days=HORIZON)
    L.append("## ⚡ Mes sept prochains jours — %s au %s"
             % (court(jour), court(fin_horizon)))
    L.append("")
    L += bloc_semaine(data, jour)
    L.append("")
    L.append("---")
    L.append("")

    rouges = [r for r in semaines_rouges(data) if not rouge_passee(r[3], jour)]
    L.append("## 🔴 Mes semaines rouges — %d encore devant moi" % len(rouges))
    L.append("")
    L += bloc_rouges(data, jour)
    L.append("")
    L.append("---")
    L.append("")

    L.append("## 📅 Toutes mes échéances")
    L.append("")
    L.append("> 💡 Sélectionne ce tableau → **Transformer en base de données** pour filtrer par cours et trier par date.")
    L.append("")
    L += bloc_echeances(data, jour)
    L.append("")
    L.append("---")
    L.append("")

    lignes, heures = bloc_semaine_type(data)
    h, m = divmod(int(round(heures * 60)), 60)
    total_txt = "%d h %02d" % (h, m) if m else "%d h" % h
    L.append("## 🗓️ Ma semaine type — %s de travail" % total_txt)
    L.append("")
    L += lignes
    L.append("")
    L.append("> ⚠️ Vendredi soir, samedi après-midi et dimanche matin restent **vides**. "
             "Ce n'est pas du temps perdu : c'est ce qui rend les %s restantes tenables "
             "semaine après semaine." % total_txt)
    L.append("")
    L.append("---")
    L.append("")

    L.append("## 🧠 Mes méthodes, cours par cours")
    L.append("")
    for cle, c in sorted(data["cours"].items(), key=lambda p: -p[1]["difficulte"]):
        L.append("### %s %s" % (c["emoji"], c["nom"]))
        if c["difficulte"] >= 4:
            L.append("*Cours où je me sens le plus fragile — c'est là que va le temps en priorité.*")
        L.append(c["methode"])
        L.append("")
    L.append("---")
    L.append("")

    L.append("## ✅ À faire confirmer auprès des profs")
    L.append("")
    L += bloc_profs(data, jour)
    L.append("")
    L.append("---")
    L.append("")

    lignes, moyenne = bloc_avancement(data, jour)
    L.append("## 📊 Mon avancement")
    L.append("")
    L += lignes
    L.append("")
    reste_jours = (fin - jour).days
    L.append("> **%.0f %%** de la session est joué en moyenne. "
             "Il reste %d jours avant le %d %s." % (moyenne, reste_jours, fin.day, MOIS[fin.month - 1]))
    L.append("")
    L.append("---")
    L.append("")
    L.append("*Page regénérée par `notion.py` à partir de `donnees-session.json`. "
             "La carte du jour arrive chaque matin dans Slack.*")

    return "\n".join(L)


def main():
    args = [a for a in sys.argv[1:]]
    seulement_semaine = "--semaine" in args
    args = [a for a in args if a != "--semaine"]
    jour = d(args[0]) if args else dt.date.today()

    data = carte.charger()
    if seulement_semaine:
        print("\n".join(bloc_semaine(data, jour)))
    else:
        print(page(data, jour))


if __name__ == "__main__":
    main()

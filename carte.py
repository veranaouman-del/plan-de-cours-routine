# -*- coding: utf-8 -*-
"""Carte du jour — Automne 2026.

Génère l'image du tableau de bord quotidien à partir de donnees-session.json.

    python3 carte.py                  -> aujourd'hui, sortie ./ma_journee.png
    python3 carte.py 2026-10-07       -> une date précise
    python3 carte.py 2026-10-07 /tmp/x.png
    python3 carte.py --texte          -> la même carte en texte (pour Slack)

Rien n'est codé en dur ici : pour changer une échéance, éditer donnees-session.json.
"""
import json
import os
import sys
import datetime as dt

BASE = os.path.dirname(os.path.abspath(__file__))
DONNEES = os.path.join(BASE, "donnees-session.json")

JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
ABREV = ["janv.", "févr.", "mars", "avril", "mai", "juin", "juil.",
         "août", "sept.", "oct.", "nov.", "déc."]
MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet",
        "août", "septembre", "octobre", "novembre", "décembre"]


# --------------------------------------------------------------------------
# Données
# --------------------------------------------------------------------------
def charger():
    with open(DONNEES, encoding="utf-8") as fh:
        return json.load(fh)


def d(s):
    return dt.date.fromisoformat(s)


def semaine_de(data, jour):
    """Numéro de semaine de session (1-15), ou None hors session."""
    paires = sorted(((int(n), d(debut)) for n, debut in data["session"]["semaines"].items()),
                    key=lambda p: p[1])
    courante = None
    for num, debut in paires:
        if jour >= debut:
            courante = num
    if courante and jour > d(data["session"]["semaines"]["15"]) + dt.timedelta(days=6):
        return None
    return courante


def en_semaine_etudes(data, jour):
    a, b = data["session"]["semaine_etudes"]
    return d(a) <= jour <= d(b)


# --------------------------------------------------------------------------
# Moteur : qu'est-ce qui est actif aujourd'hui ?
# --------------------------------------------------------------------------
def urgence(ev, jour):
    """Plus le score est haut, plus ça presse. Le poids compte, le temps restant aussi."""
    reste = max((d(ev["date"]) - jour).days, 0)
    return (ev["poids"] + 4) / (reste + 1.5)


def chantiers(data, jour):
    """Évaluations dont la fenêtre de préparation est ouverte aujourd'hui."""
    actifs = []
    for ev in data["evaluations"]:
        if ev.get("fait"):
            continue
        echeance = d(ev["date"])
        if echeance < jour:
            continue
        debut_prep = echeance - dt.timedelta(days=ev.get("prep_jours", 7))
        if jour >= debut_prep:
            e = dict(ev)
            e["reste"] = (echeance - jour).days
            e["score"] = urgence(ev, jour)
            actifs.append(e)
    return sorted(actifs, key=lambda e: -e["score"])


def cours_du_jour(data, jour):
    if jour.isoweekday() > 5 or en_semaine_etudes(data, jour):
        return []
    return [c for c in data["horaire"] if c["jour"] == jour.isoweekday()]


def blocs_du_jour(data, jour):
    return [b for b in data["blocs_travail"] if b["jour"] == jour.isoweekday()]


def taches_du_jour(data, jour, actifs):
    """Construit la liste de tâches : admin urgent, lectures qui arrivent, puis
    les chantiers qui correspondent aux blocs de travail de la journée."""
    taches = []

    # Les retards remontent en haut, mais jamais plus de deux : sinon ils mangent
    # la journée. Une fois la tâche réglée, la retirer de donnees-session.json.
    retards = []
    for t in data["taches_admin"]:
        if t["pour"] == "recurrent":
            continue
        echeance = d(t["pour"])
        if echeance < jour and t.get("urgent"):
            retards.append(("RETARD", t["quoi"]))
        elif 0 <= (echeance - jour).days <= 3:
            taches.append(("ADMIN", t["quoi"]))
    taches = retards[:2] + taches

    for l in data["lectures"]:
        reste = (d(l["pour"]) - jour).days
        if 0 <= reste <= 6:
            taches.append(("LECTURE", "%s  (pour le %s)" % (l["quoi"], court(d(l["pour"])))))

    focus = set()
    for b in blocs_du_jour(data, jour):
        focus.update(b["focus"])
    if not focus:
        focus = {"rattrapage"}

    prioritaires = [e for e in actifs if e["cours"] in focus]
    autres = [e for e in actifs if e["cours"] not in focus]
    # un jour de rattrapage (ou de week-end) attaque ce qui presse le plus, peu importe le cours
    liste = (prioritaires + autres) if "rattrapage" not in focus else actifs

    for e in liste[:4]:
        taches.append((etape(e), "%s — %s" % (data["cours"][e["cours"]]["nom"], e["titre"])))

    return taches[:7]


def etape(e):
    """Où en est la préparation : c'est ça qui évite le bourrage de dernière minute."""
    total = e.get("prep_jours", 7)
    reste = e["reste"]
    if e["type"] in ("tp", "remise"):
        if reste <= 1:
            return "REMISE"
        if reste <= total * 0.35:
            return "FINIR"
        return "AVANCER"
    if reste <= 1:
        return "RELIRE"
    if reste <= total * 0.3:
        return "TEST BLANC"
    if reste <= total * 0.65:
        return "FICHES"
    return "NOTES"


def court(j):
    return "%d %s" % (j.day, ABREV[j.month - 1])


def avancement(data, jour):
    """Part de la note déjà jouée, par cours."""
    out = {}
    for cle, c in data["cours"].items():
        fait = sum(e["poids"] for e in data["evaluations"]
                   if e["cours"] == cle and (e.get("fait") or d(e["date"]) < jour))
        out[cle] = (c["nom"], fait)
    return out


# --------------------------------------------------------------------------
# Sortie texte (Slack : pas de tableaux Markdown, titres en MAJUSCULES)
# --------------------------------------------------------------------------
def texte(data, jour):
    sem = semaine_de(data, jour)
    actifs = chantiers(data, jour)
    L = []
    L.append("MA JOURNÉE — %s %d %s" % (JOURS[jour.weekday()], jour.day, MOIS[jour.month - 1]))
    if en_semaine_etudes(data, jour):
        L.append("Semaine d'études et d'encadrement — aucun cours")
    elif sem:
        L.append("Semaine %d sur 15" % sem)
    L.append("")

    L.append("MES COURS AUJOURD'HUI")
    cj = cours_du_jour(data, jour)
    if cj:
        for c in cj:
            L.append("• %s – %s  %s  (%s)" % (c["debut"].replace(":", " h "), c["fin"].replace(":", " h "),
                                              data["cours"][c["cours"]]["nom"], c["local"]))
    else:
        L.append("• Aucun cours")
    L.append("")

    if actifs:
        p = actifs[0]
        L.append("PRIORITÉ DU JOUR")
        L.append("• %s — %s (%d %%), %s" % (data["cours"][p["cours"]]["nom"], p["titre"],
                                            p["poids"], jx(p["reste"])))
        L.append("")

    L.append("À FAIRE AUJOURD'HUI")
    for tag, t in taches_du_jour(data, jour, actifs):
        L.append("• [%s] %s" % (tag, t))
    L.append("")

    L.append("MES BLOCS DE TRAVAIL")
    bj = blocs_du_jour(data, jour)
    if bj:
        for b in bj:
            L.append("• %s – %s  %s" % (b["debut"].replace(":", " h "), b["fin"].replace(":", " h "), b["titre"]))
    else:
        L.append("• Journée libre — repos assumé")
    L.append("")

    L.append("ÉCHÉANCES QUI APPROCHENT")
    prochaines = [e for e in chantiers_tous(data, jour) if e["reste"] <= 28][:7]
    for e in prochaines:
        poids = "%d %%" % e["poids"] if e["poids"] else "formatif"
        L.append("• %s — %s — %s — %s, %s" % (e["titre"], data["cours"][e["cours"]]["nom"],
                                              poids, court(d(e["date"])), jx(e["reste"])))
    L.append("")

    L.append("MON AVANCEMENT — PART DE LA NOTE DÉJÀ JOUÉE")
    for _, (nom, pct) in avancement(data, jour).items():
        L.append("• %s : %d %%" % (nom, pct))
    return "\n".join(L)


def chantiers_tous(data, jour):
    """Toutes les échéances à venir, pas seulement celles en préparation."""
    out = []
    for ev in data["evaluations"]:
        if ev.get("fait"):
            continue
        reste = (d(ev["date"]) - jour).days
        if reste < 0:
            continue
        e = dict(ev)
        e["reste"] = reste
        out.append(e)
    return sorted(out, key=lambda e: (e["reste"], -e["poids"]))


def jx(reste):
    if reste == 0:
        return "AUJOURD'HUI"
    if reste == 1:
        return "DEMAIN"
    return "J-%d" % reste


# --------------------------------------------------------------------------
# Sortie image
# --------------------------------------------------------------------------
def image(data, jour, sortie):
    from PIL import Image, ImageDraw, ImageFont

    W, H = 900, 1900   # canevas généreux, rogné à la fin sur la hauteur réelle
    BG, RED, ORANGE = "#f9fafb", "#e63946", "#f4a261"
    DARK, GREY, WHITE, LIGHT = "#2b2b2b", "#6b7280", "#ffffff", "#e5e7eb"
    FD = "/usr/share/fonts/truetype/dejavu/"

    def f(sz, b=False):
        return ImageFont.truetype(FD + ("DejaVuSans-Bold.ttf" if b else "DejaVuSans.ttf"), sz)

    img = Image.new("RGB", (W, H), BG)
    dr = ImageDraw.Draw(img)

    def tronque(txt, font, largeur):
        while dr.textlength(txt, font=font) > largeur and len(txt) > 4:
            txt = txt[:-2]
        return txt

    sem = semaine_de(data, jour)
    actifs = chantiers(data, jour)

    # en-tête
    dr.rectangle([0, 0, W, 168], fill=RED)
    dr.text((40, 30), "MA JOURNÉE", font=f(50, True), fill=WHITE)
    soustitre = "%s %d %s" % (JOURS[jour.weekday()].capitalize(), jour.day, MOIS[jour.month - 1])
    if en_semaine_etudes(data, jour):
        soustitre += "  ·  Semaine d'études"
    elif sem:
        soustitre += "  ·  Semaine %d sur 15" % sem
    dr.text((42, 100), soustitre, font=f(22), fill="#ffe3e5")

    y = 200

    def section(titre, y):
        dr.text((40, y), titre, font=f(22, True), fill=RED)
        dr.line([(40, y + 32), (W - 40, y + 32)], fill=LIGHT, width=2)
        return y + 50

    # cours
    y = section("MES COURS AUJOURD'HUI", y)
    cj = cours_du_jour(data, jour)
    if cj:
        for c in cj:
            co = data["cours"][c["cours"]]
            dr.rounded_rectangle([40, y, W - 40, y + 54], radius=10, fill=WHITE, outline=LIGHT, width=2)
            dr.rectangle([40, y + 9, 46, y + 45], fill=co["couleur"])
            dr.text((66, y + 8), "%s – %s" % (c["debut"].replace(":", " h "), c["fin"].replace(":", " h ")),
                    font=f(19, True), fill=DARK)
            dr.text((300, y + 8), tronque(co["nom"], f(19), 480), font=f(19), fill=DARK)
            dr.text((W - 105, y + 8), c["local"], font=f(18), fill=GREY)
            y += 64
    else:
        dr.rounded_rectangle([40, y, W - 40, y + 54], radius=10, fill=WHITE, outline=LIGHT, width=2)
        dr.text((66, y + 12), "Aucun cours — journée de travail libre", font=f(19), fill=GREY)
        y += 64

    # priorité
    y += 10
    if actifs:
        p = actifs[0]
        dr.rounded_rectangle([40, y, W - 40, y + 102], radius=12, fill=ORANGE)
        dr.text((66, y + 14), "PRIORITÉ DU JOUR", font=f(18, True), fill="#7c3d07")
        libelle = "%s — %s" % (p["titre"], jx(p["reste"]))
        dr.text((66, y + 44), tronque(libelle, f(22, True), 640), font=f(22, True), fill="#1f2937")
        dr.text((66, y + 74), tronque(data["cours"][p["cours"]]["nom"], f(17), 640), font=f(17), fill="#7c3d07")
        if p["poids"]:
            dr.text((W - 146, y + 34), "%d %%" % p["poids"], font=f(36, True), fill="#1f2937")
        y += 128

    # à faire
    y = section("À FAIRE AUJOURD'HUI", y)
    for tag, t in taches_du_jour(data, jour, actifs):
        couleur = RED if tag in ("RETARD", "REMISE") else (ORANGE if tag in ("FINIR", "TEST BLANC", "ADMIN") else GREY)
        dr.rounded_rectangle([44, y + 2, 66, y + 24], radius=5, outline=GREY, width=2)
        dr.rounded_rectangle([80, y, 80 + 110, y + 26], radius=6, fill=couleur)
        dr.text((88, y + 4), tronque(tag, f(14, True), 96), font=f(14, True), fill=WHITE)
        dr.text((202, y + 1), tronque(t, f(19), W - 250), font=f(19), fill=DARK)
        y += 38

    # échéances
    y += 14
    y = section("ÉCHÉANCES QUI APPROCHENT", y)
    for e in [x for x in chantiers_tous(data, jour) if x["reste"] <= 28][:6]:
        co = data["cours"][e["cours"]]
        pastille = RED if e["reste"] <= 4 else (ORANGE if e["reste"] <= 12 else "#3b82f6")
        dr.ellipse([44, y + 6, 60, y + 22], fill=pastille)
        dr.text((76, y), tronque(e["titre"], f(19, True), 372), font=f(19, True), fill=DARK)
        dr.text((456, y + 1), tronque(co.get("court", co["nom"]), f(17), 150), font=f(17), fill=GREY)
        dr.text((614, y), ("%d %%" % e["poids"]) if e["poids"] else "—", font=f(19, True), fill=pastille)
        dr.text((684, y + 1), "%s · %s" % (court(d(e["date"])), jx(e["reste"])), font=f(17), fill=GREY)
        y += 36

    # blocs de travail
    y += 14
    y = section("MES BLOCS DE TRAVAIL", y)
    bj = blocs_du_jour(data, jour)
    if bj:
        for b in bj:
            dr.rounded_rectangle([40, y, W - 40, y + 44], radius=8, fill=WHITE, outline=LIGHT, width=2)
            dr.text((62, y + 11), "%s – %s" % (b["debut"].replace(":", " h "), b["fin"].replace(":", " h ")),
                    font=f(18, True), fill=DARK)
            dr.text((300, y + 11), tronque(b["titre"], f(18), 520), font=f(18), fill=GREY)
            y += 52
    else:
        dr.text((44, y), "Journée libre — repos assumé, c'est prévu.", font=f(18), fill=GREY)
        y += 52

    # avancement — collé sous le contenu, la carte est rognée juste après
    y += 8
    bas = y + 196
    dr.rectangle([0, y, W, bas], fill="#1f2937")
    dr.text((40, y + 18), "MON AVANCEMENT — PART DE LA NOTE DÉJÀ JOUÉE", font=f(16, True), fill="#9ca3af")
    yy = y + 50
    for cle, (nom, pct) in avancement(data, jour).items():
        dr.text((40, yy), tronque(nom, f(16), 250), font=f(16), fill=WHITE)
        dr.rounded_rectangle([300, yy + 3, 300 + 480, yy + 17], radius=7, fill="#374151")
        if pct:
            dr.rounded_rectangle([300, yy + 3, 300 + int(480 * pct / 100), yy + 17], radius=7,
                                 fill=data["cours"][cle]["couleur"])
        dr.text((W - 80, yy), "%d %%" % pct, font=f(16, True), fill=WHITE)
        yy += 28

    img = img.crop((0, 0, W, bas))
    img.save(sortie)
    return sortie


# --------------------------------------------------------------------------
def main():
    args = [a for a in sys.argv[1:]]
    mode_texte = "--texte" in args
    args = [a for a in args if a != "--texte"]
    jour = d(args[0]) if args else dt.date.today()
    sortie = args[1] if len(args) > 1 else os.path.join(BASE, "ma_journee.png")

    data = charger()
    if mode_texte:
        print(texte(data, jour))
    else:
        print(image(data, jour, sortie))


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
from PIL import Image, ImageDraw, ImageFont

W, H = 900, 1124
BG="#f9fafb"; RED="#e63946"; ORANGE="#f4a261"; DARK="#2b2b2b"; GREY="#6b7280"; WHITE="#ffffff"
FD="/usr/share/fonts/truetype/dejavu/"
def f(sz, b=False): return ImageFont.truetype(FD+("DejaVuSans-Bold.ttf" if b else "DejaVuSans.ttf"), sz)

img = Image.new("RGB",(W,H),BG); d = ImageDraw.Draw(img)

# ---- header
d.rectangle([0,0,W,168], fill=RED)
d.text((40,34), "MA JOURNÉE", font=f(50,True), fill=WHITE)
d.text((42,104), "Vendredi 18 septembre  ·  Semaine 4 sur 15", font=f(22), fill="#ffe3e5")

y = 208
def section(title, y):
    d.text((40,y), title, font=f(23,True), fill=RED)
    d.line([(40,y+34),(W-40,y+34)], fill="#e5e7eb", width=2)
    return y+52

# ---- cours
y = section("MES COURS AUJOURD'HUI", y)
for heure, cours, local in [("8 h 55 – 11 h 35","Philosophie (Éthique et politique)","E204"),
                            ("13 h 30 – 16 h 10","Programmation Web I","A307")]:
    d.rounded_rectangle([40,y,W-40,y+56], radius=10, fill="#ffffff", outline="#e5e7eb", width=2)
    d.rectangle([40,y+10,46,y+46], fill=RED)
    d.text((66,y+9),  heure, font=f(20,True), fill=DARK)
    d.text((306,y+9), cours, font=f(20), fill=DARK)
    d.text((W-110,y+9), local, font=f(19), fill=GREY)
    y += 68

# ---- priorite
y += 12
d.rounded_rectangle([40,y,W-40,y+104], radius=12, fill=ORANGE)
d.text((66,y+16), "PRIORITÉ DU JOUR", font=f(19,True), fill="#7c3d07")
d.text((66,y+48), "Plan de dissertation — examen mardi 22 sept.", font=f(23,True), fill="#1f2937")
d.text((W-148,y+36), "20 %", font=f(38,True), fill="#1f2937")
y += 132

# ---- a faire
y = section("À FAIRE AUJOURD'HUI", y)
for t in ["Finir La vie devant soi p. 176-223",
          "Faire un plan de dissertation type",
          "Avancer le TP1 VueJS",
          "Réviser Kant, Bentham et Mill"]:
    d.rounded_rectangle([44,y+2,68,y+26], radius=5, outline=GREY, width=2)
    d.text((84,y), t, font=f(22), fill=DARK)
    y += 42

# ---- echeances
y += 16
y = section("ÉCHÉANCES QUI APPROCHENT", y)
for dot, quoi, cours, pct, quand in [
    (RED,     "Dissertation développement", "Français",       "20 %", "mardi 22 sept.  ·  J-4"),
    (ORANGE,  "Remise TP1 VueJS",           "Prog. Web I",    "—",    "semaine du 21 sept."),
    (ORANGE,  "TP2",                        "Dév. logiciels", "10 %", "semaine du 21 sept."),
    (ORANGE,  "Test utilitarisme / déonto.", "Éthique",       "10 %", "vendredi 25 sept.  ·  J-7"),
    ("#3b82f6","Examen théories éthiques",  "Éthique",        "25 %", "vendredi 2 oct.  ·  J-14"),
]:
    d.ellipse([44,y+7,60,y+23], fill=dot)
    d.text((76,y),  quoi,  font=f(20,True), fill=DARK)
    d.text((408,y), cours, font=f(19), fill=GREY)
    d.text((610,y), pct,   font=f(20,True), fill=dot)
    d.text((672,y), quand, font=f(18), fill=GREY)
    y += 38

# ---- footer
y = H-92
d.rectangle([0,y,W,H], fill="#1f2937")
d.text((40,y+16), "DÉJÀ ÉVALUÉ À CE JOUR", font=f(17,True), fill="#9ca3af")
d.text((40,y+46), "Prog. Web I 0 %   ·   Dév. logiciels 10 %   ·   Littérature 10 %   ·   Anglais 0 %   ·   Éthique 0 %",
       font=f(18), fill=WHITE)

img.save("/tmp/claude-0/-home-user/228885a6-0db1-5f3c-9f02-613f6e7e6774/scratchpad/ma_journee.png")
print("OK")

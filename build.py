#!/usr/bin/env python3
"""
build.py — Generator pagini portofoliu pentru tractariautobraila.ro
===================================================================
Citește data/prestatii.csv (sau un Google Sheets publicat ca CSV)
și generează:
  - portofoliu/<slug>.html  pentru fiecare rând
  - portofoliu.html          (lista de carduri, regenerat complet)

UTILIZARE:
  python build.py

GOOGLE SHEETS (opțional):
  Publică sheet-ul: File → Share → Publish to web → CSV → copiază URL
  Dezcommentează linia SHEETS_CSV_URL de mai jos și pune URL-ul tău.
"""

import csv
import os
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

# ── Configurare ────────────────────────────────────────────────────────────────

# Sursa de date: CSV local (implicit) sau Google Sheets publicat
LOCAL_CSV   = "data/prestatii.csv"
SHEETS_CSV_URL = "https://docs.google.com/spreadsheets/d/1WtZeFDG46sM0xeKjvOjx23kMjIAjpu01HfF6IuHL1eY/export?format=csv&gid=0"   # ← Google Sheets export direct (sheet setat Anyone with link can view/edit)

# Folderul cu imaginile de portofoliu (relativ față de rădăcina proiectului)
IMAGES_DIR  = "assets/img/portfolio"

# Telefon afișat pe pagini
TELEFON     = "0736 390 565"
TELEFON_URL = "tel:+40736390565"

# ── GTM / cookie snippet (copiat din paginile existente) ──────────────────────
GTM_HEAD = """<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){ dataLayer.push(arguments); }
  gtag('consent', 'default', {
    'ad_storage': 'denied','analytics_storage': 'denied',
    'ad_user_data': 'denied','ad_personalization': 'denied'
  });
  try {
    if (localStorage.getItem('cookieConsent') === 'granted') {
      gtag('consent', 'update', {
        'ad_storage': 'granted','analytics_storage': 'granted',
        'ad_user_data': 'granted','ad_personalization': 'granted'
      });
      dataLayer.push({event: 'consent_already_granted'});
    }
  } catch(e) {}
</script>
<!-- Google Tag Manager -->
<script>(function(w,d,s,l,i){w[l]=w[l]||[];w[l].push({'gtm.start':
new Date().getTime(),event:'gtm.js'});var f=d.getElementsByTagName(s)[0],
j=d.createElement(s),dl=l!='dataLayer'?'&l='+l:'';j.async=true;j.src=
'https://www.googletagmanager.com/gtm.js?id='+i+dl;f.parentNode.insertBefore(j,f);
})(window,document,'script','dataLayer','GTM-T3JBRMFG');</script>
<!-- End Google Tag Manager -->"""

GTM_BODY = """<!-- Google Tag Manager (noscript) -->
<noscript><iframe src="https://www.googletagmanager.com/ns.html?id=GTM-T3JBRMFG"
height="0" width="0" style="display:none;visibility:hidden"></iframe></noscript>
<!-- End Google Tag Manager (noscript) -->"""

COOKIE_BANNER = """<div id="cookie-banner" class="cookie-banner" role="dialog" aria-live="polite" aria-label="Consimțământ cookie">
  <span>Folosim cookie-uri (ex. Google Analytics) pentru a îmbunătăți experiența. Prin accept, ne permiți măsurarea traficului.</span>
  <div class="cookie-actions">
    <button id="cookie-accept" class="btn-accept">Accept</button>
    <button id="cookie-close" class="btn-close" aria-label="Închide">Mai târziu</button>
  </div>
</div>
<script>
(function(){
  const banner = document.getElementById('cookie-banner');
  const btnAccept = document.getElementById('cookie-accept');
  const btnClose = document.getElementById('cookie-close');
  try {
    if (localStorage.getItem('cookieConsent') === 'granted' || localStorage.getItem('cookieConsent') === 'dismissed') {
      banner.style.display = 'none';
    }
  } catch(e){}
  btnAccept?.addEventListener('click', function(){
    try { localStorage.setItem('cookieConsent','granted'); } catch(e){}
    if (typeof gtag === 'function') {
      gtag('consent', 'update', {'ad_storage':'granted','analytics_storage':'granted','ad_user_data':'granted','ad_personalization':'granted'});
      dataLayer.push({event:'consent_granted'});
    }
    banner.style.display = 'none';
  });
  btnClose?.addEventListener('click', function(){
    try { localStorage.setItem('cookieConsent','dismissed'); } catch(e){}
    dataLayer.push({event:'consent_dismissed'});
    banner.style.display = 'none';
  });
})();
</script>"""

# ── Funcții helpers ────────────────────────────────────────────────────────────

def load_rows():
    """Încarcă rândurile din CSV local sau Google Sheets."""
    if SHEETS_CSV_URL:
        print(f"  📥 Fetch Google Sheets: {SHEETS_CSV_URL[:60]}...")
        try:
            with urllib.request.urlopen(SHEETS_CSV_URL) as r:
                content = r.read().decode("utf-8-sig").replace('\x00', '')
            rows = list(csv.DictReader(content.splitlines()))
            print(f"  ✓ {len(rows)} rânduri din Google Sheets")
            if not rows:
                raise ValueError("Google Sheets a returnat 0 rânduri — folosesc CSV local.")
            # Actualizează și CSV-ul local ca backup
            with open(LOCAL_CSV, "w", encoding="utf-8-sig", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows(rows)
            return rows
        except Exception as e:
            print(f"  ⚠ Nu pot accesa Google Sheets ({e}), folosesc CSV local.")

    with open(LOCAL_CSV, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(line.replace('\x00', '') for line in f))
    print(f"  ✓ {len(rows)} rânduri din {LOCAL_CSV}")
    return rows


def images_for_row(row):
    """Returnează lista completă de imagini (cover + extra)."""
    folder  = row.get("folder", "").strip()
    cover   = row.get("cover", "").strip()
    extra   = [x.strip() for x in row.get("imagini_extra", "").split("|") if x.strip()]
    all_imgs = []
    if cover:
        all_imgs.append((folder, cover))
    for img in extra:
        all_imgs.append((folder, img))
    return all_imgs   # list of (folder, filename)


def img_src(folder, filename):
    """URL relativ la rădăcina site-ului pentru o imagine."""
    if folder:
        return f"/assets/img/portfolio/{folder}/{filename}"
    return f"/assets/img/portfolio/{filename}"


# ── Generator pagini individuale ──────────────────────────────────────────────

def build_page(row):
    slug        = row["slug"].strip()
    data_iso    = row["data_iso"].strip()
    data_disp   = row["data_display"].strip()
    datetime_at = row["datetime_attr"].strip()
    titlu       = row["titlu"].strip()
    titlu_seo   = row["titlu_seo"].strip()
    serviciu    = row["serviciu"].strip()
    locatie     = row["locatie"].strip()
    desc_pagina = row["descriere_pagina"].strip()
    meta_desc   = row["meta_desc"].strip()
    folder      = row.get("folder", "").strip()
    imgs        = images_for_row(row)

    canonical = f"https://tractariautobraila.ro/portofoliu/{slug}.html"

    # ── Schema BreadcrumbList ────────────────────────────────────────────────
    schema_breadcrumb = f"""{{
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    "itemListElement": [
      {{"@type":"ListItem","position":1,"name":"Acasă","item":"https://tractariautobraila.ro/"}},
      {{"@type":"ListItem","position":2,"name":"Portofoliu","item":"https://tractariautobraila.ro/portofoliu.html"}},
      {{"@type":"ListItem","position":3,"name":"{titlu}","item":"{canonical}"}}
    ]
  }}"""

    # ── Galerie imagini ──────────────────────────────────────────────────────
    gallery_html = ""
    for i, (fld, fname) in enumerate(imgs):
        src  = img_src(fld, fname)
        alt  = f"{titlu} — fotografie {i+1}"
        load = "eager" if i == 0 else "lazy"
        gallery_html += f'  <img src="{src}" alt="{alt}" loading="{load}" width="1200" height="900">\n'

    # ── HTML complet ─────────────────────────────────────────────────────────
    html = f"""<!doctype html>
<html lang="ro">
<head>
{GTM_HEAD}
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>{titlu_seo}</title>
  <meta name="description" content="{meta_desc}">
  <link rel="canonical" href="{canonical}">
  <link rel="stylesheet" href="/assets/css/styles.css">
  <link rel="icon" type="image/png" sizes="32x32" href="/favicon/favicon.png">
  <script defer src="/assets/js/main.js"></script>
  <script type="application/ld+json">
  {schema_breadcrumb}
  </script>
</head>
<body>
{GTM_BODY}
  <div id="header-placeholder" data-active="portofoliu"></div>

  <main class="container">

    <!-- Breadcrumbs -->
    <nav aria-label="Breadcrumb">
      <ol class="breadcrumb">
        <li><a href="/">Acasă</a></li>
        <li><a href="/portofoliu.html">Portofoliu</a></li>
        <li>{titlu}</li>
      </ol>
    </nav>

    <div class="prestatie-header">
      <h1>{titlu}</h1>
      <div class="prestatie-meta">
        <span class="chip">
          <time datetime="{datetime_at}">{data_disp}</time>
        </span>
        <span class="chip">{serviciu}</span>
        <span class="chip">{locatie}</span>
      </div>
    </div>

    <!-- Galerie foto -->
    <div class="prestatie-gallery">
{gallery_html}    </div>

    <!-- Descriere -->
    <p class="prestatie-desc">{desc_pagina}</p>

    <!-- CTA -->
    <div class="prestatie-cta">
      <a class="btn btn-primary" href="{TELEFON_URL}">📞 Sună acum — {TELEFON}</a>
      <a class="btn btn-outline" href="/portofoliu.html">← Înapoi la portofoliu</a>
    </div>

  </main>

  <div id="footer-placeholder"></div>
  {COOKIE_BANNER}
</body>
</html>
"""
    out_path = Path("portofoliu") / f"{slug}.html"
    out_path.write_text(html, encoding="utf-8")
    print(f"  ✓ portofoliu/{slug}.html")


# ── Generator portofoliu.html ─────────────────────────────────────────────────

def build_index(rows):
    """Regenerează portofoliu.html cu toate cardurile, sortate descrescător după dată."""
    sorted_rows = sorted(rows, key=lambda r: r.get("data_iso",""), reverse=True)

    cards_html = ""
    for row in sorted_rows:
        if not row.get("slug", "").strip():
            continue
        slug        = row["slug"].strip()
        datetime_at = row["datetime_attr"].strip()
        data_disp   = row["data_display"].strip()
        titlu       = row["titlu"].strip()
        serviciu    = row["serviciu"].strip()
        locatie     = row["locatie"].strip()
        desc_card   = row["descriere_card"].strip()
        folder      = row.get("folder","").strip()
        cover       = row.get("cover","").strip()
        src         = img_src(folder, cover) if cover else "/assets/img/portfolio/caz-01.jpg"
        href        = f"/portofoliu/{slug}.html"
        alt         = f"{data_disp} – {titlu}"

        cards_html += f"""
      <article class="card">
        <a class="card__media" href="{href}">
          <img
            src="{src}"
            alt="{alt}"
            loading="lazy"
            width="1200"
            height="900"
          >
        </a>
        <div class="card__body">
          <p class="card__label">
            <time datetime="{datetime_at}">{data_disp}</time> – {titlu}
          </p>
          <p class="card__desc">{desc_card}</p>
          <ul class="card__chips">
            <li>{serviciu}</li>
            <li>{locatie}</li>
          </ul>
        </div>
      </article>"""

    html = f"""<!doctype html>
<html lang="ro">
<head>
{GTM_HEAD}
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Portofoliu Prestații — Tractări Auto Brăila</title>
  <meta name="description" content="Galerie de intervenții reale: tractări auto, platformă și asistență rutieră în Brăila și Galați. Actualizat periodic.">
  <link rel="canonical" href="https://tractariautobraila.ro/portofoliu.html" />
  <link rel="stylesheet" href="/assets/css/styles.css">
  <link rel="icon" type="image/png" sizes="32x32" href="/favicon/favicon.png">
  <script defer src="/assets/js/main.js"></script>
  <script type="application/ld+json">
  {{
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    "itemListElement": [
      {{"@type":"ListItem","position":1,"name":"Acasă","item":"https://tractariautobraila.ro/"}},
      {{"@type":"ListItem","position":2,"name":"Portofoliu","item":"https://tractariautobraila.ro/portofoliu.html"}}
    ]
  }}
  </script>
</head>
<body>
{GTM_BODY}
  <div id="header-placeholder" data-active="portofoliu"></div>

  <main class="container">

    <!-- Breadcrumbs -->
    <nav aria-label="Breadcrumb">
      <ol class="breadcrumb">
        <li><a href="/">Acasă</a></li>
        <li>Portofoliu</li>
      </ol>
    </nav>

    <h1>Portofoliu prestații</h1>
    <p class="muted">Intervenții documentate din teren — actualizat periodic.</p>

    <section class="portfolio wall" aria-label="Intervenții documentate">
{cards_html}
    </section>

  </main>

  <div id="footer-placeholder"></div>
  {COOKIE_BANNER}
</body>
</html>
"""
    Path("portofoliu.html").write_text(html, encoding="utf-8")
    print("  ✓ portofoliu.html (regenerat)")


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    # Schimbă directorul de lucru la rădăcina proiectului
    script_dir = Path(__file__).parent
    os.chdir(script_dir)

    print("\n🚀 Build tractariautobraila.ro — portofoliu\n")

    rows = load_rows()
    if not rows:
        print("⚠ Nu am găsit rânduri în CSV. Verifică data/prestatii.csv")
        sys.exit(1)

    print("\n📄 Generez paginile individuale...")
    Path("portofoliu").mkdir(exist_ok=True)
    for row in rows:
        if row.get("slug","").strip():
            build_page(row)

    print("\n🗂 Regenerez portofoliu.html...")
    build_index(rows)

    print(f"\n✅ Gata! {len(rows)} prestații procesate.")
    print("   Urmează: commit + push în GitHub Desktop.\n")


if __name__ == "__main__":
    main()

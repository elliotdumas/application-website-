#!/usr/bin/env python3
"""Récupère les offres des pages carrières publiques, les filtre selon profil.json,
les classe et écrit data/jobs.json.

Sources :
  - scripts/sources.json : pages carrières (Ashby, Lever, Greenhouse, Recruitee, Workable)
  - data/extra.json      : offres trouvées à la main ou par recherche web
                           (LinkedIn, Welcome to the Jungle, Indeed, cabinets de conseil…)

Usage : python3 scripts/fetch_jobs.py
"""
import concurrent.futures as cf
import hashlib
import html
import json
import re
import sys
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROFIL = json.loads((ROOT / "profil.json").read_text())
SOURCES = json.loads((ROOT / "scripts/sources.json").read_text())["boards"]
DATA = ROOT / "data"
NOW = datetime.now(timezone.utc)
MAX_AGE_DAYS = 45

# ---------------------------------------------------------------- réseau

def get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "radar-carriere/1.0", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def strip_html(s):
    s = html.unescape(s or "")
    s = re.sub(r"<(br|/p|/li|/h\d)[^>]*>", "\n", s, flags=re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    s = html.unescape(s)
    s = re.sub(r"[ \t\xa0]+", " ", s)
    s = re.sub(r"\n\s*\n+", "\n", s)
    return s.strip()


def parse_date(v):
    if v in (None, ""):
        return None
    if isinstance(v, (int, float)):
        return datetime.fromtimestamp(v / 1000 if v > 1e11 else v, timezone.utc)
    try:
        d = datetime.fromisoformat(str(v).replace("Z", "+00:00").replace(" UTC", "+00:00"))
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except ValueError:
        try:
            return datetime.strptime(str(v)[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            return None

# ---------------------------------------------------------------- lecteurs par outil

def read_ashby(slug, company):
    d = get_json(f"https://api.ashbyhq.com/posting-api/job-board/{slug}?includeCompensation=true")
    for j in d.get("jobs", []):
        if j.get("isListed") is False:
            continue
        locs = [j.get("location") or ""] + [x.get("location", "") for x in j.get("secondaryLocations") or []]
        addr = ((j.get("address") or {}).get("postalAddress") or {})
        yield dict(
            titre=j.get("title"), entreprise=company, lieu=" · ".join(l for l in locs if l),
            pays=addr.get("addressCountry") or "", remote=bool(j.get("isRemote")) or j.get("workplaceType") == "Remote",
            contrat=j.get("employmentType") or "", publie=j.get("publishedAt"),
            url=j.get("jobUrl"), postuler=j.get("applyUrl") or j.get("jobUrl"),
            description=j.get("descriptionPlain") or strip_html(j.get("descriptionHtml")),
            salaire=((j.get("compensation") or {}).get("compensationTierSummary") or ""),
            outil="Ashby",
        )


def read_lever(slug, company):
    d = get_json(f"https://api.lever.co/v0/postings/{slug}?mode=json")
    for j in d:
        c = j.get("categories") or {}
        locs = c.get("allLocations") or [c.get("location") or ""]
        yield dict(
            titre=j.get("text"), entreprise=company, lieu=" · ".join(l for l in locs if l),
            pays=j.get("country") or "", remote=j.get("workplaceType") == "remote",
            contrat=c.get("commitment") or "", publie=j.get("createdAt"),
            url=j.get("hostedUrl"), postuler=j.get("applyUrl") or j.get("hostedUrl"),
            description=j.get("descriptionPlain") or strip_html(j.get("description")),
            salaire="", outil="Lever",
        )


def read_greenhouse(slug, company):
    d = get_json(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true")
    for j in d.get("jobs", []):
        yield dict(
            titre=j.get("title"), entreprise=company, lieu=(j.get("location") or {}).get("name") or "",
            pays="", remote="remote" in ((j.get("location") or {}).get("name") or "").lower(),
            contrat="", publie=j.get("first_published") or j.get("updated_at"),
            url=j.get("absolute_url"), postuler=j.get("absolute_url"),
            description=strip_html(j.get("content")), salaire="", outil="Greenhouse",
        )


def read_recruitee(slug, company):
    d = get_json(f"https://{slug}.recruitee.com/api/offers/")
    for j in d.get("offers", []):
        yield dict(
            titre=j.get("title"), entreprise=company,
            lieu=", ".join(x for x in [j.get("city"), j.get("country")] if x) or j.get("location") or "",
            pays=j.get("country_code") or "", remote=bool(j.get("remote")),
            contrat=j.get("employment_type_code") or "", publie=j.get("published_at") or j.get("created_at"),
            url=j.get("careers_url"), postuler=j.get("careers_apply_url") or j.get("careers_url"),
            description=strip_html(j.get("description")), salaire="", outil="Recruitee",
        )


def read_workable(slug, company):
    d = get_json(f"https://apply.workable.com/api/v1/widget/accounts/{slug}?details=true")
    for j in d.get("jobs", []):
        yield dict(
            titre=j.get("title"), entreprise=company,
            lieu=", ".join(x for x in [j.get("city"), j.get("country")] if x),
            pays=j.get("country") or "", remote=bool(j.get("telecommuting")),
            contrat=j.get("employment_type") or "", publie=j.get("published_on") or j.get("created_at"),
            url=j.get("url") or j.get("shortlink"), postuler=j.get("application_url") or j.get("url"),
            description=strip_html(j.get("description")), salaire="", outil="Workable",
        )


READERS = dict(ashby=read_ashby, lever=read_lever, greenhouse=read_greenhouse,
               recruitee=read_recruitee, workable=read_workable)

# ---------------------------------------------------------------- géographie

PARIS = ["paris", "île-de-france", "ile-de-france", "idf", "boulogne", "levallois", "neuilly", "la défense", "la defense", "issy", "saint-ouen", "montreuil", "clichy", "puteaux", "courbevoie"]
FRANCE = ["france", "lyon", "marseille", "lille", "bordeaux", "nantes", "toulouse", "nice", "montpellier", "rennes", "strasbourg", "grenoble", "sophia"]
AFRIQUE = ["africa", "afrique", "dakar", "senegal", "sénégal", "abidjan", "côte d'ivoire", "cote d'ivoire", "ivory coast", "casablanca", "rabat", "morocco", "maroc", "tunis", "tunisia", "tunisie", "algiers", "alger", "algeria", "cairo", "egypt", "lagos", "nigeria", "nairobi", "kenya", "accra", "ghana", "kigali", "rwanda", "douala", "cameroon", "cameroun", "kinshasa", "johannesburg", "cape town", "south africa", "kampala", "uganda", "dar es salaam", "tanzania", "lomé", "lome", "togo", "cotonou", "benin", "bénin", "bamako", "mali", "ouagadougou", "libreville", "gabon", "madagascar", "antananarivo", "mauritius", "maurice", "addis", "ethiopia"]
EUROPE = ["london", "united kingdom", " uk", "uk ", "england", "berlin", "munich", "münchen", "hamburg", "frankfurt", "cologne", "germany", "deutschland", "amsterdam", "rotterdam", "netherlands", "madrid", "barcelona", "spain", "españa", "lisbon", "lisboa", "porto", "portugal", "milan", "milano", "rome", "italy", "brussels", "bruxelles", "belgium", "belgique", "geneva", "genève", "zurich", "zürich", "lausanne", "switzerland", "suisse", "luxembourg", "dublin", "ireland", "stockholm", "sweden", "copenhagen", "denmark", "oslo", "norway", "helsinki", "finland", "vienna", "austria", "warsaw", "poland", "prague", "czech", "athens", "greece", "europe", "emea", "eu ", "monaco", "tallinn", "estonia", "budapest", "bucharest", "riga", "vilnius"]
AMERIQUE = ["new york", "nyc", "san francisco", "los angeles", "boston", "chicago", "miami", "austin", "seattle", "washington", "united states", "usa", " us", "us ", "u.s.", "montreal", "montréal", "quebec", "québec", "toronto", "canada"]
PAYS_ZONE = {"FR": "Paris", "GB": "Europe", "DE": "Europe", "NL": "Europe", "ES": "Europe", "PT": "Europe", "IT": "Europe", "BE": "Europe", "CH": "Europe", "LU": "Europe", "IE": "Europe", "SE": "Europe", "DK": "Europe", "NO": "Europe", "FI": "Europe", "AT": "Europe", "PL": "Europe", "SN": "Afrique", "CI": "Afrique", "MA": "Afrique", "TN": "Afrique", "NG": "Afrique", "KE": "Afrique", "GH": "Afrique", "EG": "Afrique", "ZA": "Afrique", "RW": "Afrique", "CM": "Afrique", "US": "Amérique du Nord", "CA": "Amérique du Nord"}


def has(text, words):
    return any(w in text for w in words)


def zone_of(lieu, pays, remote):
    t = f" {lieu} {pays} ".lower()
    if has(t, PARIS):
        return "Paris"
    if has(t, FRANCE):
        return "France"
    if has(t, AFRIQUE):
        return "Afrique"
    if has(t, EUROPE):
        return "Europe"
    if has(t, AMERIQUE):
        return "Amérique du Nord"
    if pays and pays.upper() in PAYS_ZONE:
        return PAYS_ZONE[pays.upper()]
    if remote or "remote" in t or "télétravail" in t:
        return "Télétravail"
    return None

# ---------------------------------------------------------------- classement

T = PROFIL["titres"]
FRENCH_WORDS = re.compile(r"\b(nous|vous|avec|pour|les|des|une|est|sont|votre|notre|équipe|poste|missions?)\b", re.I)


def norm(s):
    return " " + re.sub(r"\s+", " ", (s or "").lower().replace("’", "'")) + " "


def word_hit(text, kw):
    return re.search(r"(?<![a-z])" + re.escape(kw.strip()) + r"(?![a-z])", text) is not None


def speaks_french(job):
    d = (job.get("description") or "")[:4000]
    if re.search(r"\b(french|français|francais|francophone)\b", d, re.I):
        return True
    return len(FRENCH_WORDS.findall(d)) >= 25


def score(job):
    titre = norm(job["titre"])
    raisons = []
    if any(word_hit(titre, k) for k in T["exclus"]) and not any(word_hit(titre, k) for k in T["forts"]):
        return None
    fort = next((k for k in T["forts"] if word_hit(titre, k)), None)
    moyen = next((k for k in T["moyens"] if word_hit(titre, k)), None)
    if fort:
        s = 46
        raisons.append("Intitulé au cœur de ta cible")
    elif moyen:
        s = 30 if moyen in ("associate", "strategy", "stratégie", "strategic", "investment", "venture", "m&a", "general manager", "country manager", "chargé de mission", "chargée de mission") else 22
        raisons.append(f"Intitulé proche ({moyen.strip()})")
    else:
        return None

    zone = job["zone"]
    s += {"Paris": 25, "France": 17, "Afrique": 21, "Europe": 15, "Télétravail": 13, "Amérique du Nord": 10}[zone]
    raisons.append({"Paris": "Basé à Paris", "France": "En France", "Afrique": "En Afrique", "Europe": "En Europe",
                    "Télétravail": "En télétravail", "Amérique du Nord": "Amérique du Nord, poste francophone"}[zone])

    fr = job.get("francais")
    if fr:
        s += 4
        if zone != "Paris":
            raisons.append("Français demandé ou annonce en français")

    if job.get("type") == "Startup":
        s += 8
        raisons.append("Startup / scale-up")
    elif job.get("type") in ("Conseil", "Fonds"):
        s += 7
        raisons.append("Cabinet de conseil" if job["type"] == "Conseil" else "Fonds d'investissement")

    jours = job["age_jours"]
    if jours is not None:
        s += 12 if jours <= 1 else 9 if jours <= 3 else 6 if jours <= 7 else 3 if jours <= 14 else 0
        if jours <= 3:
            raisons.append("Publié très récemment")

    if job["stage"]:
        s -= 22
        raisons.append("Stage ou alternance")
    if any(word_hit(titre, k) for k in PROFIL["trop_senior"]) and not fort:
        s -= 10
        raisons.append("Poste peut-être très senior")
    return max(1, min(99, s)), raisons


def contrat_of(job, titre):
    if any(word_hit(titre, k) for k in PROFIL["stages"]):
        return "Stage / alternance", True
    c = (job.get("contrat") or "").lower()
    if "intern" in c:
        return "Stage / alternance", True
    if "contract" in c or "temporary" in c or "cdd" in c or "freelance" in c:
        return "CDD / freelance", False
    return "CDI", False

# ---------------------------------------------------------------- assemblage

def fetch_board(entry):
    tool, slug, company = entry
    try:
        return company, list(READERS[tool](slug, company)), None
    except Exception as e:  # une source en panne ne bloque pas les autres
        return company, [], f"{company} ({tool}/{slug}) : {e}"


def make_id(job):
    return hashlib.sha1((job.get("url") or f"{job['entreprise']}|{job['titre']}").encode()).hexdigest()[:12]


def finalize(job, seen, default_type):
    job["id"] = job.get("id") or make_id(job)
    titre = norm(job["titre"])
    job["zone"] = job.get("zone") or zone_of(job.get("lieu", ""), job.get("pays", ""), job.get("remote"))
    if not job["zone"]:
        return None
    job["francais"] = job.get("francais", speaks_french(job))
    if job["zone"] == "Amérique du Nord" and not job["francais"]:
        return None
    job["contrat"], job["stage"] = contrat_of(job, titre) if not job.get("stage") else (job.get("contrat") or "Stage / alternance", True)
    job["type"] = job.get("type") or default_type
    first_seen = seen.get(job["id"]) or NOW.isoformat(timespec="seconds")
    seen[job["id"]] = first_seen
    pub = parse_date(job.get("publie")) or parse_date(first_seen)
    job["publie"] = pub.isoformat(timespec="seconds")
    job["vu_le"] = first_seen
    job["age_jours"] = max(0, (NOW - pub).days)
    if job["age_jours"] > MAX_AGE_DAYS:
        return None
    if job.get("score") is None:
        res = score(job)
        if res is None:
            return None
        job["score"], job["raisons"] = res
    desc = re.sub(r"\s+", " ", job.get("description") or "").strip()
    job["extrait"] = job.get("extrait") or (desc[:700] + ("…" if len(desc) > 700 else ""))
    job.pop("description", None)
    job.pop("pays", None)
    return job


def main():
    DATA.mkdir(exist_ok=True)
    seen_path = DATA / "seen.json"
    seen = json.loads(seen_path.read_text()) if seen_path.exists() else {}

    jobs, erreurs, sources_ok = [], [], []
    with cf.ThreadPoolExecutor(16) as ex:
        for company, raw, err in ex.map(fetch_board, SOURCES):
            if err:
                erreurs.append(err)
                continue
            sources_ok.append(company)
            for j in raw:
                if not j.get("titre") or not j.get("url"):
                    continue
                f = finalize(j, seen, "Startup")
                if f:
                    jobs.append(f)

    extra_path = DATA / "extra.json"
    extra = json.loads(extra_path.read_text()).get("offres", []) if extra_path.exists() else []
    for j in extra:
        j = dict(j)
        j.setdefault("outil", j.get("source", "Recherche web"))
        f = finalize(j, seen, j.get("type") or "Startup")
        if f:
            jobs.append(f)

    uniq = {}
    for j in jobs:
        uniq.setdefault((j["entreprise"].lower(), norm(j["titre"]).strip(), j["zone"]), j)
    jobs = sorted(uniq.values(), key=lambda j: (-j["score"], j["age_jours"]))

    # on garde seen.json court : seulement les 120 derniers jours
    cutoff = (NOW - timedelta(days=120)).isoformat()
    seen = {k: v for k, v in seen.items() if v >= cutoff}
    seen_path.write_text(json.dumps(seen, indent=0, sort_keys=True))

    out = dict(
        mis_a_jour=NOW.isoformat(timespec="seconds"),
        nb_sources=len(sources_ok) + (1 if extra else 0),
        sources=sorted(sources_ok),
        erreurs=erreurs,
        offres=jobs,
    )
    (DATA / "jobs.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(f"{len(jobs)} offres retenues depuis {len(sources_ok)} pages carrières + {len(extra)} offres ajoutées à la main.")
    for e in erreurs:
        print("  source en échec :", e, file=sys.stderr)


if __name__ == "__main__":
    main()

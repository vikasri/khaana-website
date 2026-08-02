# Moving khaana.com from GitHub Pages to Cloudflare Pages

Everything in the repository is ready. What is left needs an account login, so
it is yours to do. It is about fifteen minutes of clicking and one wait.

## Where things stand today

| | |
|---|---|
| Registrar | GoDaddy |
| Nameservers | `ns09.domaincontrol.com`, `ns10.domaincontrol.com` (GoDaddy) |
| Apex `khaana.com` | four A records to GitHub Pages (185.199.108–111.153) |
| `www` | CNAME to `vikasri.github.io` |
| Mail | **none** (no MX records) |
| Other records | one TXT, `google-site-verification=sLusuinZWcjaFeKBhZ9JTE_Q8xh3QWdnmFiFwUkY2U4` |

No mail on the domain is the important part. Moving nameservers is normally
risky because it can silently break email; here there is no email to break.

## The one record you must not lose

```
TXT  @  google-site-verification=sLusuinZWcjaFeKBhZ9JTE_Q8xh3QWdnmFiFwUkY2U4
```

That is what keeps Search Console verified. Cloudflare's scan usually copies it
across automatically, but check it is there before you switch the nameservers.
If it goes missing the site keeps working and you quietly lose access to search
data.

## Steps

1. **Create the Cloudflare account** at dash.cloudflare.com, if you do not have
   one.

2. **Add the site.** *Add a site* → `khaana.com` → Free plan. Cloudflare scans
   the existing DNS and imports what it finds. **Stop and read the imported
   list.** Confirm the `google-site-verification` TXT is in it. Add it by hand
   if not.

3. **Create the project.** Cloudflare has moved new accounts to Workers and
   no longer offers Pages project creation in every account, so use the Workers
   route. *Workers & Pages* (or *Compute*) → **Create** → **Import a
   repository** → the `khaana-website` repo.

   Leave the build and deploy commands at their defaults. The repository now
   contains `wrangler.jsonc`, which is what that flow needs:

   ```jsonc
   { "name": "khaana-website", "compatibility_date": "2026-08-01",
     "assets": { "directory": "./" } }
   ```

   There is no `main` field because there is no server-side code. An
   assets-only Worker just serves the directory. Without this file the deploy
   fails with "error occurred while running deploy command", because
   `wrangler deploy` has nothing to act on.

   `_headers` and `_redirects` are read natively by Workers static assets, the
   same as they would be by Pages, so caching, security headers and the www
   redirect all still apply. `.assetsignore` keeps `tools/`, `api/` and the
   repository's own housekeeping files out of the deployed site: 1,815 files
   are served, including all 586 recipe pages and their JSON.

4. **Check the temporary `workers.dev` URL before touching DNS.** Load the home page, a
   cuisine page, a recipe, and the Cook page. The Cook page is the real test
   because it fetches JSON at runtime. Nothing is live for your visitors yet,
   so this is free to get wrong.

5. **Add the custom domains** in the project settings: `khaana.com` and
   `www.khaana.com`. Cloudflare will say it needs to manage DNS.

6. **Redirect www to the apex.** Workers accepts a `_redirects` file but only
   with relative URLs, so a cross-host redirect cannot go in one: the deploy
   fails with "Only relative URLs are allowed". It is a zone-level Redirect
   Rule instead, which is free and runs before the Worker.

   *khaana.com* → **Rules** → **Redirect Rules** → **Create rule**

   | Field | Value |
   |---|---|
   | Rule name | `www to apex` |
   | If: field | Hostname |
   | Operator | equals |
   | Value | `www.khaana.com` |
   | Then: type | Dynamic |
   | Expression | `concat("https://khaana.com", http.request.uri.path)` |
   | Status code | 301 |
   | Preserve query string | on |

   Dynamic rather than static so the path survives: a link to
   `www.khaana.com/goan.html` should land on `khaana.com/goan.html`, not on the
   home page.

7. **Switch the nameservers at GoDaddy** to the two Cloudflare gives you.
   Propagation is usually under an hour and can take up to 24. The site stays
   up throughout: GitHub Pages keeps serving until DNS moves, Cloudflare serves
   after.

8. **Turn off GitHub Pages** only once the live site is served by Cloudflare
   (`curl -sI https://khaana.com | grep -i server` should say `cloudflare`).
   Repo → Settings → Pages → set source to None. Leave the `CNAME` file alone;
   it does no harm and makes going back easy.

## Going back

If anything looks wrong, point the GoDaddy nameservers back at
`ns09/ns10.domaincontrol.com`. The GitHub Pages A records are still in the
GoDaddy zone and the site returns as it was. Nothing in this repository has to
change.

## What the move buys

- **Cache headers you control.** `_headers` in this repository. GitHub Pages
  sends a blanket `max-age=600` and gives no way to change it, which is what
  made browsers hold a stale stylesheet against new markup. HTML and the JSON
  data now revalidate on every request, while the hashed CSS and JS are cached
  for a year.
- **Security headers**, also in `_headers`: a strict Content-Security-Policy
  (the site has no inline scripts and loads nothing from a third party),
  nosniff, a referrer policy, and HSTS.
- **`www` redirects to the apex**, so search engines stop seeing two sites.
  Set up as a Redirect Rule, not a file. See below.
- **A path to a backend.** `api/suggest.js` was parked because GitHub Pages
  cannot run code. A Worker can, on the same free plan, and this project is
  already a Worker: adding a `main` script alongside the assets is all it
  takes. That is also what an email signup or saved pantries would need.
- **Commercial use is permitted on the free plan.** This matters for the LLC:
  Vercel's Hobby plan is "restricted to non-commercial personal use only" and
  counts advertising, affiliate links and donations as commercial use.

## Headroom on the free plan

| | Used | Limit |
|---|---|---|
| Files | 1,844 | 20,000 |
| Largest file | 3.4 MB (`data/recipes.json`) | 25 MiB |
| Builds | 1 per push | 500 / month |
| Bandwidth | — | unmetered |

## After the move

- Re-check Search Console. The property stays verified if the TXT record came
  across; resubmit the sitemap if it complains.
- Turn on Cloudflare Web Analytics if you want traffic numbers. It needs no
  cookie banner, which Google Analytics does.
- `tools/version-assets.py` still earns its place. The `immutable` caching in
  `_headers` depends on every reference carrying `?v=<hash>`, so keep running
  it last.

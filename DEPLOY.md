# How khaana.com is served

The site is static files in this repository, published by **GitHub Pages** from
the default branch. Push and it is live in about a minute. There is no build
step on the server: `tools/rebuild.py` runs here, and what it writes is what
ships.

This file used to describe a migration to Cloudflare Pages. That migration was
started and never finished, and the half-finished state is what caused the
problems recorded below. It is being undone rather than completed.

## What was actually true before this was written

The domain's nameservers had been moved to Cloudflare, and the Cloudflare
project was half-made: it existed and was connected to this repository, but it
never served khaana.com. Cloudflare sat in front as a proxy and GitHub Pages
served every request behind it. That is visible in any response:

```
x-github-request-id: ...
via: 1.1 varnish
cache-control: max-age=600
```

Three things this repository contained were therefore doing nothing at all:

| File | What it was for | What it did |
|---|---|---|
| `wrangler.jsonc` | telling `wrangler deploy` what to publish | nothing; nothing ran wrangler |
| `.assetsignore` | keeping `tools/` and `api/` out of a Cloudflare deploy | nothing; GitHub Pages serves the whole repository |
| `_headers` | CSP, HSTS, cache-control | nothing; GitHub Pages does not read it |
| `_redirects` | 301s for renamed pages | nothing; `/recipe.html` had been answering 404 for as long as the rule existed |

All four are deleted. Believing them was worse than not having them: a recipe
was renamed, a `_redirects` rule was added for the old URL, and the old URL
went on returning 404 with nothing to say otherwise.

## The deploy failures of 2026-08-06

Three deploys in a row failed after the DNS move, and the shape was always the
same: `build` succeeded in twelve seconds, `deploy` ran into its ten-minute
ceiling with `Timeout reached, aborting!`, and a re-triggered run then sat in
`queued` without starting. The site kept serving the previous build throughout,
which is why nothing looked wrong from outside.

It was not the DNS, the custom domain, the branch policy or the site's size:
the domain passed its DNS check, `main` was on the allowed list, there were no
approval rules, and 127 MB across 2,304 files is well inside the 1 GB limit.

It was the Cloudflare Git integration. The project was still connected to this
repository and creating its own deployments on every push — this repository had
four deployment environments, `github-pages` plus three of Cloudflare's — and
GitHub's publish step waited behind them until it gave up. Disconnecting the
repository in Cloudflare fixed it on the next push, in under a minute.

Worth knowing if a deploy ever hangs again: `deploy` timing out while `build`
passes means the publish handoff, not the site. Check
`/repos/OWNER/REPO/environments` for anything that is not `github-pages`.

## Redirects, on this host

GitHub Pages has no redirect configuration. A page that redirects itself is the
only mechanism available, and the site already used it:

```
south-indian.html          -> tamil-nadu.html
himachali.html             -> pahari.html
recipe.html                -> cook.html
recipes/mithila-machh-posto.html -> recipes/machhak-jhor.html
```

Each is a small file carrying `<link rel="canonical">` to the new address, a
`noindex, follow` robots tag and a `<meta http-equiv="refresh">`. Search engines
treat that combination as a move; it is weaker than a 301 and it is what there
is. `tools/build-seo.py` knows about the root-level stubs and keeps them out of
the sitemap, and `tools/build-recipe-pages.py` keeps its hands off the recipe
one, which it would otherwise delete on every build as a page no recipe owns.

Renaming a page means adding a stub. Deleting one without a stub throws away
whatever ranking the old URL had.

## Caching

GitHub Pages sends `max-age=600` on everything and offers no way to change it.
For ten minutes after a deploy a browser can hold the old stylesheet against
new markup, which once rendered the cuisines menu as a plain list three times
the height of the header.

`tools/version-assets.py` is the answer to that and must keep running last in
`rebuild.py`. It stamps `?v=<content hash>` onto every stylesheet and script
reference, so new markup can only ever be paired with the CSS it was built
against, and an unchanged file keeps its URL and stays cached.

## Cloudflare is not in front of this site

Done on 2026-08-06. Read the next section too: there *is* Cloudflare in the
picture again, but not here and not in the path of any page. The domain is delegated to `ns27.domaincontrol.com` and
`ns28.domaincontrol.com` at GoDaddy, and the zone is:

```
A      @      185.199.108.153, .109.153, .110.153, .111.153
AAAA   @      2606:50c0:8000::153 through :8003::153
CNAME  www    vikasri.github.io
TXT    @      google-site-verification=K9s30Is97phCshKSdYOm1_MVQ5T098-YxV3bTOnX52E
TXT    @      google-site-verification=sLusuinZWcjaFeKBhZ9JTE_Q8xh3QWdnmFiFwUkY2U4
TXT    @      v=spf1 -all
```

No MX. The Cloudflare Email Routing records forwarded nothing and are not
recreated; the SPF says no mail is ever sent from this domain, which makes it
harder to spoof.

Verified after the switch: all four public resolvers see the GoDaddy
nameservers, every one of the 31 top-level pages and a random sample of recipe
pages returns 200, the five runtime JSON files load, `www` and plain HTTP both
301 to `https://khaana.com/`, the Let's Encrypt certificate covers both names,
`robots.txt` is byte-for-byte the file in this repository with no injected
block, and the matching game loads its thumbnails.

### What that fixed, beyond removing a dependency

* `www` used to answer 200 with identical content. It redirects now, so the
  site has one address instead of two.
* `robots.txt` used to be rewritten in transit, with a managed block above the
  site's own rules disallowing GPTBot, ClaudeBot, CCBot and the rest — in a
  second `User-agent: *` group that most crawlers never reach, which meant the
  site's own `Disallow` lines were ignored as well. Both problems are gone.

### What is given up

Cloudflare's free plan would have bought real things: header control, actual
301s, and somewhere to run `api/suggest.js`, which is parked because GitHub
Pages cannot execute code. None were ever switched on, so leaving costs
nothing that works today. It also stops something working *against* the site,
which is the robots.txt rewrite.

## The leaderboard runs on a Cloudflare Worker

Added 2026-08-08, and the reason the heading above is worded the way it is.
The fun page's high-score boards are shared by everyone, which a static host
cannot do: GitHub Pages serves files and cannot take a write. So one endpoint
exists that can.

```
API      https://khaana-board.vikasri.workers.dev
routes   GET  /top?game=trivia|pair      the board
         POST /score                     one finished run
storage  Cloudflare D1, database "khaana-board"
source   ~/Documents/Claude_Work/KhaanaBoard  (its own repository)
caller   assets/js/leaderboard.js, on fun.html only
```

Four things to be clear about, because the last Cloudflare entanglement cost
three days of failed deploys:

* **It is not a Pages project and is not connected to this repository.** It is
  a standalone Worker, deployed by hand with `npx wrangler deploy` from its own
  directory. Nothing about it runs on push. The deployment-environment trap
  described above cannot recur through it.
* **It is not in front of any page.** No proxying, no DNS change; the zone is
  still delegated to GoDaddy and khaana.com still answers from GitHub Pages.
* **The site does not depend on it.** `leaderboard.js` treats every call as
  optional: no network, slow network or Worker down leaves both games playing
  exactly as they do and the board simply absent. Nothing waits on a fetch.
* **Its source is not in this repository**, deliberately — GitHub Pages serves
  the whole repository, and a Worker's `node_modules` has no business being
  published at khaana.com.

### Why it is on workers.dev and not api.khaana.com

Because a Worker custom domain requires the zone to be in the Cloudflare
account, and this domain's nameservers are at GoDaddy. Pointing
`api.khaana.com` at it would mean delegating khaana.com back to Cloudflare,
which is the thing the section above records undoing. The uglier hostname is
the cheaper price.

### Operating it

Season reset, and removing a row, are documented in that repository's README.
Both are single authenticated requests; neither needs this repository or a
site deploy.

If a backend is ever needed, the route is the one that was never finished: a
Cloudflare Workers project with an assets directory. The files are in this
repository's history rather than its working tree.

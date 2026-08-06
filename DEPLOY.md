# How khaana.com is served

The site is static files in this repository, published by **GitHub Pages** from
the default branch. Push and it is live in about a minute. There is no build
step on the server: `tools/rebuild.py` runs here, and what it writes is what
ships.

This file used to describe a migration to Cloudflare Pages. That migration was
started and never finished, and the half-finished state is what caused the
problems recorded below. It is being undone rather than completed.

## What was actually true before this was written

The domain's nameservers had been moved to Cloudflare, but no Cloudflare Pages
or Workers project was ever created. So Cloudflare sat in front as a proxy and
GitHub Pages served every request behind it. That is visible in any response:

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

## What Cloudflare is still doing

At the time of writing, the DNS is still Cloudflare's:

```
nameservers   watson.ns.cloudflare.com, samara.ns.cloudflare.com
khaana.com    A 104.21.73.236, 172.67.193.91   (Cloudflare's proxy IPs)
www           the same
MX            route1/2/3.mx.cloudflare.net     (Cloudflare Email Routing)
TXT           v=spf1 include:_spf.mx.cloudflare.net ~all
TXT           google-site-verification=... (two of them)
```

Two things there are load-bearing and one is a live bug:

* **Email routing is real.** Those MX records mean mail to the domain is being
  forwarded by Cloudflare. Moving the nameservers away turns that off. Whatever
  address is set up there stops working the moment the zone stops answering.
* **The Google Search Console verification** is a TXT record. It has to be
  recreated wherever the DNS ends up or search data access is lost.
* **`www` serves the site instead of redirecting to the apex.** Both hostnames
  answer 200 with identical content. Every page's `<link rel="canonical">`
  points at the apex, which is most of the protection, but it is still two
  addresses for one site.

## Leaving Cloudflare completely

This is account work and cannot be done from this repository.

1. **Deal with the email first.** Find out what Cloudflare Email Routing is
   forwarding and where. If it matters, arrange a replacement before anything
   else moves — an email address that silently stops accepting mail is a worse
   outcome than any of this is worth. If it forwards nothing, there is nothing
   to protect.
2. **Recreate the zone at the new DNS host** (GoDaddy is the registrar, so its
   own DNS is the obvious place). Before switching, have ready:

   | Type | Name | Value |
   |---|---|---|
   | A | `@` | `185.199.108.153` |
   | A | `@` | `185.199.109.153` |
   | A | `@` | `185.199.110.153` |
   | A | `@` | `185.199.111.153` |
   | CNAME | `www` | `vikasri.github.io` |
   | TXT | `@` | both `google-site-verification=` values |
   | MX | `@` | whatever step 1 decided |

   The four A records are GitHub's published Pages addresses. AAAA records
   exist too if IPv6 matters.
3. **Point the registrar's nameservers back**, away from Cloudflare. Allow up
   to 24 hours, though it is usually under one.
4. **In the repository settings**, Pages → Custom domain → `khaana.com`, and
   tick **Enforce HTTPS** once the certificate is issued. The `CNAME` file in
   this repository already says `khaana.com` and is what makes that stick.
   GitHub then redirects `www` to the apex on its own, which fixes the
   duplicate-hostname problem for free.
5. **Confirm** with `curl -sI https://khaana.com` — no `server: cloudflare`,
   and `x-github-request-id` still present — and re-check Search Console.

## What is given up, honestly

Cloudflare's free plan would have bought real things: header control, actual
301s, and a place to run `api/suggest.js`, which is parked because GitHub Pages
cannot execute code. None of them were ever switched on here, so leaving costs
nothing that is currently working — except the email routing, which is.

If any of those become necessary later, the route back is the one that was
never finished: a Cloudflare Workers project with an assets directory. The
files it needs are in this repository's history rather than its working tree.

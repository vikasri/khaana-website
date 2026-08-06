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

## What Cloudflare was doing, before stage one

The nameservers were Cloudflare's and the proxy was on, so every request went
through Cloudflare to reach GitHub Pages. Two things it did unasked, both now
gone with the proxy:

* **It rewrote `robots.txt` on the way out.** What a crawler fetched was not
  what is in this repository: Cloudflare injected a managed block above it that
  disallows GPTBot, ClaudeBot, CCBot, Google-Extended, Amazonbot,
  Applebot-Extended, Bytespider and meta-externalagent, and adds
  `Content-Signal: search=yes,ai-train=no,use=reference`. Ordinary search is
  explicitly allowed, so this does not touch Google; AI answer engines are shut
  out. It also leaves two `User-agent: *` groups in one file, and most crawlers
  read only the first, which was Cloudflare's — so the site's own
  `Disallow: /tools/` was ignored. Removing the proxy also un-blocks the AI
  crawlers, which is the intended outcome: an answer engine that cannot read
  the site cannot send anyone to it.
* **`www` answered 200 instead of redirecting.** Both hostnames served
  identical content. GitHub Pages 301s it to the apex on its own, which is what
  happens now.

The MX records point at Email Routing that was set up, never worked and
forwards nothing. There is no mailbox on this domain and the feedback form
posts to Google, so nothing depends on them.

## Leaving

Checked before deciding, by resolving past Cloudflare and talking to GitHub
Pages directly. All of it already works:

```
curl -sI https://khaana.com/     --resolve khaana.com:443:185.199.108.153
    HTTP/2 200, server: GitHub.com
curl -sI https://www.khaana.com/ --resolve www.khaana.com:443:185.199.108.153
    HTTP/2 301, location: https://khaana.com/
openssl s_client -servername khaana.com -connect 185.199.108.153:443
    subject CN=khaana.com, SAN khaana.com + www.khaana.com, Let's Encrypt
```

So GitHub already holds a valid certificate for both names, already redirects
`www` to the apex, and already serves every page. Nothing has to be built. The
only question left is which nameservers the world is asked.

### Stage one: take Cloudflare out of the request path — DONE

Verified after the change: apex and `www` both answer `server: GitHub.com`,
`www` 301s to the apex, `robots.txt` is byte-for-byte what is in this
repository, the Let's Encrypt certificate covers both names, all 21 cuisine
pages and a sample of recipe pages return 200, and the Cook page still fetches
its JSON and renders matches. What was set, in **Cloudflare → DNS**:

| Type | Name | Value | Proxy |
|---|---|---|---|
| A | `@` | `185.199.108.153` | **DNS only** |
| A | `@` | `185.199.109.153` | **DNS only** |
| A | `@` | `185.199.110.153` | **DNS only** |
| A | `@` | `185.199.111.153` | **DNS only** |
| CNAME | `www` | `vikasri.github.io` | **DNS only** |

Delete the Cloudflare AAAA records, or replace them with GitHub's
(`2606:50c0:8000::153` through `:8003::153`). Grey cloud, not orange, on every
one: proxied is what injects the robots.txt block and swallows the redirect.

The checks that confirmed it:

```
curl -sI https://khaana.com | grep -i server        # GitHub.com, not cloudflare
curl -sI https://www.khaana.com | grep -i location  # https://khaana.com/
curl -s  https://khaana.com/robots.txt | head -3    # no Cloudflare block
```

### Stage two: move the nameservers — remaining

The slow part, and by now it carries no unknowns: whichever nameserver a
resolver asks, the answer is already GitHub's addresses. This only changes who
is asked.

At **GoDaddy**, build the zone before switching anything to it: the four A
records above, the `www` CNAME, and **both** `google-site-verification` TXT
records — those are what keep Search Console. No MX, since nothing uses it. An
SPF record of `v=spf1 -all` is worth adding in their place: it says no mail is
ever sent from this domain, which makes it harder to spoof.

Then point the registrar's nameservers away from Cloudflare. Propagation is
usually under an hour and can take 24. The site stays up throughout, because
whichever nameserver a resolver asks, the answer is GitHub's addresses.

### Stage three: after

* **Repository → Settings → Pages**: confirm the custom domain still reads
  `khaana.com` and **Enforce HTTPS** is ticked. The `CNAME` file here is what
  makes it stick across deploys.
* **Search Console**: confirm the property is still verified and resubmit
  `sitemap.xml` if it complains.
* **Delete the Cloudflare zone** once `dig NS khaana.com` no longer mentions
  it. Nothing in this repository refers to Cloudflare any more.

## What is given up

Cloudflare's free plan would have bought real things: header control, actual
301s, and somewhere to run `api/suggest.js`, which is parked because GitHub
Pages cannot execute code. None were ever switched on, so leaving costs
nothing that works today. It also stops something working *against* the site,
which is the robots.txt rewrite.

If a backend is ever needed, the route is the one that was never finished: a
Cloudflare Workers project with an assets directory. The files are in this
repository's history rather than its working tree.

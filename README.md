# gianniaronestudio

Portfolio site for Gianni Arone: video work (Vimeo), websites, resume, plus the original art gallery and v1s1t0r mixes.

Static HTML in `public/`, served by Vercel with a few serverless functions in `api/` (used by the art gallery admin).

## Pages

| Path | What |
| --- | --- |
| `/` | Home: reel, selected video, websites, resume snapshot |
| `/video/` | Every video on vimeo.com/uaawtf, filterable by category |
| `/web/` | Websites designed and built |
| `/resume/` | Resume (print-friendly: use the Print / Save as PDF button) |
| `/art/` | Original studio gallery (password gate + admin panel, Vercel Blob) |
| `/v1s1t0r/mixes/` | Practice mixes |

Shared styles and behaviour live in `public/portfolio.css` and `public/portfolio.js`.

## Video data

`public/videos.json` is the source for the video pages. Refresh it after uploading to Vimeo:

```sh
npm run sync-vimeo
```

The script pulls the public Vimeo list, downloads any missing thumbnails into `public/img/video/`, and keeps the hand-set `category` (`reels`, `spots`, `entertainment`, `music`, `art`) and `featured` order for videos already in the file. Edit those fields directly in `videos.json`.

Only videos whose Vimeo privacy setting allows embedding **anywhere** play inline. Others link out to vimeo.com and show a "vimeo ↗" tag. To make a video play on-site: Vimeo → video settings → Privacy → *Where can this be embedded?* → Anywhere.

## Website cards

Screenshots are in `public/img/sites/` (1280×800 JPEG). Card copy is in `public/web/index.html` and the four featured cards in `public/index.html`. When Charlotte Square moves to its own domain, update the two links and remove the "custom domain soon" badge.

## Local preview

```sh
npm run dev   # http://localhost:3000
```

import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { mkdir, readdir, readFile, writeFile } from 'node:fs/promises'
import { createServer } from 'vite'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const projectRoot = path.resolve(__dirname, '..')
const distRoot = path.resolve(projectRoot, 'dist')
const distIndexPath = path.resolve(distRoot, 'index.html')
const songDataDir = path.resolve(projectRoot, 'src', 'data')
const siteOrigin = (process.env.SITE_ORIGIN || 'https://projectvocaleadsheets.com').replace(
  /\/+$/,
  '',
)
const siteLogoUrl = `${siteOrigin}/logo.png`
const homePageTitle = 'Project VocaLead Sheets | Vocaloid Lead Sheets & Sheet Music'
const homePageDescription =
  'Browse Vocaloid lead sheets and sheet music from producers of Hatsune Miku and more for musicians, performers, and fans.'

const vite = await createServer({
  root: projectRoot,
  configFile: path.resolve(projectRoot, 'vite.config.ts'),
  appType: 'custom',
  logLevel: 'error',
  server: {
    middlewareMode: true,
  },
})

const escapeHtml = (value) =>
  String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')

const injectDocumentMetadata = (template, title, description, options = {}) => {
  let result = template
    .replace(/<title>[\s\S]*?<\/title>/, `<title>${escapeHtml(title)}</title>`)
    .replace(
      /<meta\s+name="description"\s+content="[^"]*"\s*\/>/,
      `<meta name="description" content="${escapeHtml(description)}" />`,
    )

  // Add Open Graph tags for social sharing
  const ogTags = [
    `<meta property="og:title" content="${escapeHtml(title)}" />`,
    `<meta property="og:description" content="${escapeHtml(description)}" />`,
    options.canonicalUrl
      ? `<meta property="og:url" content="${escapeHtml(options.canonicalUrl)}" />`
      : '',
    `<meta property="og:type" content="website" />`,
    options.songImageUrl
      ? `<meta property="og:image" content="${escapeHtml(options.songImageUrl)}" />`
      : '',
    `<meta name="twitter:card" content="summary_large_image" />`,
  ]
    .filter(Boolean)
    .join('\n  ')

  return result.replace('</head>', `  ${ogTags}\n  </head>`)
}

// A song is indexable only when it is completed (or has no status as a fallback)
const isIndexableSong = (song) => {
  const status = typeof song?.status === 'string' ? song.status.toLowerCase() : ''
  return status === '' || status === 'completed'
}

// Add a robots noindex directive to under-review non-indexable songs
const injectRobotsNoindex = (template) => {
  const robotsTag = '<meta name="robots" content="noindex, follow" />'
  if (/<meta\s+name="robots"/i.test(template)) {
    return template.replace(/<meta\s+name="robots"[^>]*>/i, robotsTag)
  }
  return template.replace('</head>', `  ${robotsTag}\n  </head>`)
}

const injectCanonicalLink = (template, routePath) => {
  const canonicalPath = routePath.startsWith('/') ? routePath : `/${routePath}`
  const canonicalUrl = `${siteOrigin}${canonicalPath}`
  const canonicalTag = `<link rel="canonical" href="${escapeHtml(canonicalUrl)}" />`

  if (template.includes('rel="canonical"')) {
    return template.replace(/<link\s+rel="canonical"\s+href="[^"]*"\s*\/>/, canonicalTag)
  }

  return template.replace('</head>', `  ${canonicalTag}\n  </head>`)
}

const buildSongPageTitle = (song) => {
  const producerParts = [song.producer, ...(song.additionalProducers ?? [])].filter(Boolean)
  const singerParts = [song.singer, ...(song.additionalVoices ?? [])].filter(Boolean)
  return `${song.title} Lead Sheet - ${producerParts.join(' + ')} ft. ${singerParts.join(' + ')} | Project VocaLead Sheets`
}

const buildSongDescription = (song) => {
  const producerParts = [song.producer, ...(song.additionalProducers ?? [])].filter(Boolean)
  const singerParts = [song.singer, ...(song.additionalVoices ?? [])].filter(Boolean)
  const parts = [
    `${song.title} lead sheet by ${producerParts.join(' + ')} ft. ${singerParts.join(' + ')}`,
  ]

  if (song.alternativeNames?.length) {
    parts.push(`Also known as ${song.alternativeNames.join(', ')}`)
  }

  parts.push(homePageDescription)

  return parts.join('. ')
}

const generateSlug = (value) =>
  String(value || '')
    .toLowerCase()
    .replace(/['’]/g, '')
    .replace(/[^a-z0-9-]/g, (match, offset, stringValue) => {
      const before = offset > 0 ? stringValue[offset - 1] : ''
      const after = offset < stringValue.length - 1 ? stringValue[offset + 1] : ''
      const isBeforeWord = /[a-z0-9]/i.test(before)
      const isAfterWord = /[a-z0-9]/i.test(after)
      return isBeforeWord && isAfterWord ? '-' : ''
    })
    .replace(/-+/g, '-')
    .replace(/^-+|-+$/g, '')

const getSongRouteEntries = async () => {
  const entries = await readdir(songDataDir, { withFileTypes: true })
  const jsonFiles = entries
    .filter((entry) => entry.isFile() && entry.name.endsWith('.json'))
    .map((entry) => entry.name)
    .filter((name) => name !== 'generated-manifest.json')
    .sort()

  const routes = await Promise.all(
    jsonFiles.map(async (filename) => {
      const filePath = path.resolve(songDataDir, filename)
      const raw = await readFile(filePath, 'utf-8')
      const song = JSON.parse(raw)
      const routeSlug = generateSlug(song.title)

      return {
        routePath: `/view/${routeSlug}`,
        song,
      }
    }),
  )

  return routes
}

const writeFlatRouteHtml = async (routePath, html) => {
  if (routePath === '/') return

  const normalized = routePath.replace(/^\//, '').replace(/\/$/, '')
  const outputPath = path.resolve(distRoot, `${normalized}.html`)
  await mkdir(path.dirname(outputPath), { recursive: true })
  await writeFile(outputPath, html, 'utf-8')
}

/**
 * Convert a song timestamp into a W3C datetime (ISO 8601) string for <lastmod>.
 * Falls back through updatedAt -> syncedAt, returning undefined if none are valid.
 */
const toLastmod = (song) => {
  for (const value of [song?.updatedAt, song?.syncedAt]) {
    if (typeof value !== 'string' || value.length === 0) continue
    const parsed = new Date(value)
    if (!Number.isNaN(parsed.getTime())) return parsed.toISOString()
  }
  return undefined
}

/**
 * Generate sitemap.xml for Google Search Console
 * Uses flat structure URLs (no trailing slashes)
 */
const generateSitemap = async (songRoutes) => {
  const indexableRoutes = songRoutes.filter(({ song }) => isIndexableSong(song))

  const songLastmods = indexableRoutes
    .map(({ song }) => toLastmod(song))
    .filter(Boolean)
    .sort()
  const homeLastmod = songLastmods.length
    ? songLastmods[songLastmods.length - 1]
    : new Date().toISOString()

  const urls = [
    { path: '/', priority: '1.0', lastmod: homeLastmod },
    ...indexableRoutes.map(({ routePath, song }) => ({
      path: routePath,
      priority: '0.8',
      lastmod: toLastmod(song),
    })),
  ]

  const sitemapContent = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${urls
  .map(({ path: urlPath, priority, lastmod }) => {
    const fullUrl = `${siteOrigin}${urlPath}`
    const lastmodTag = lastmod ? `\n    <lastmod>${escapeHtml(lastmod)}</lastmod>` : ''
    return `  <url>
    <loc>${escapeHtml(fullUrl)}</loc>${lastmodTag}
    <priority>${priority}</priority>
  </url>`
  })
  .join('\n')}
</urlset>`

  const sitemapPath = path.resolve(distRoot, 'sitemap.xml')
  await writeFile(sitemapPath, sitemapContent, 'utf-8')

  return indexableRoutes.length
}

try {
  const { render } = await vite.ssrLoadModule('/src/entry-server.ts')
  const template = await readFile(distIndexPath, 'utf-8')
  const songRoutes = await getSongRouteEntries()
  const prerenderSongs = songRoutes.map(({ song }) => song)

  const homeRender = await render('/', { songs: prerenderSongs })
  const homeHtml = template.replace(
    '<div id="app"></div>',
    `<div id="app">${homeRender.appHtml}</div>`,
  )
  const homeCanonicalUrl = `${siteOrigin}/`
  const homeHtmlWithMeta = injectDocumentMetadata(homeHtml, homePageTitle, homePageDescription, {
    canonicalUrl: homeCanonicalUrl,
    songImageUrl: siteLogoUrl,
  })

  await writeFile(distIndexPath, injectCanonicalLink(homeHtmlWithMeta, '/'), 'utf-8')
  console.log('✓ Prerendered home page into dist/index.html')

  const claimedRoutes = new Map()

  for (const { routePath, song } of songRoutes) {
    if (claimedRoutes.has(routePath)) {
      console.warn(
        `⚠ Skipping duplicate canonical route ${routePath} for "${song.title}" (already claimed by "${claimedRoutes.get(routePath)}")`,
      )
      continue
    }

    try {
      const canonicalUrl = `${siteOrigin}${routePath}`
      const routeRender = await render(routePath, { songs: prerenderSongs })
      const baseHtml = template.replace(
        '<div id="app"></div>',
        `<div id="app">${routeRender.appHtml}</div>`,
      )
      const songHtml = injectDocumentMetadata(
        baseHtml,
        buildSongPageTitle(song),
        buildSongDescription(song),
        { canonicalUrl, songImageUrl: siteLogoUrl },
      )
      const songHtmlWithCanonical = injectCanonicalLink(songHtml, routePath)

      const finalSongHtml = isIndexableSong(song)
        ? songHtmlWithCanonical
        : injectRobotsNoindex(songHtmlWithCanonical)

      // Write only to flat structure (song-name.html)
      await writeFlatRouteHtml(routePath, finalSongHtml)
      claimedRoutes.set(routePath, song.title)
    } catch (err) {
      console.error(`✗ Failed to prerender "${song.title}" at ${routePath}:`, err.message)
      throw err
    }
  }

  // Generate sitemap.xml for search engines
  const indexedCount = await generateSitemap(songRoutes)
  const excludedCount = songRoutes.length - indexedCount
  console.log(
    `✓ Generated sitemap.xml with ${indexedCount} song routes` +
      (excludedCount > 0 ? ` (${excludedCount} non-public excluded, marked noindex)` : ''),
  )
  console.log(`✓ Prerendered ${songRoutes.length} song pages into dist/view/*.html`)
} catch (err) {
  console.error('✗ Prerender failed:', err)
  process.exit(1)
} finally {
  await vite.close()
}

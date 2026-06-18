import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { mkdir, readFile, writeFile } from 'node:fs/promises'
import { createServer } from 'vite'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const projectRoot = path.resolve(__dirname, '..')
const distRoot = path.resolve(projectRoot, 'dist')
const distIndexPath = path.resolve(distRoot, 'index.html')

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

const injectDocumentMetadata = (template, title, description) =>
  template
    .replace(/<title>[\s\S]*?<\/title>/, `<title>${escapeHtml(title)}</title>`)
    .replace(
      /<meta\s+name="description"\s+content="[^"]*"\s*\/>/,
      `<meta name="description" content="${escapeHtml(description)}" />`,
    )

const buildSongPageTitle = (song) => {
  const producerParts = [song.producer, ...(song.additionalProducers ?? [])].filter(Boolean)
  const singerParts = [song.singer, ...(song.additionalVoices ?? [])].filter(Boolean)
  return `${song.title} Lead Sheet - ${producerParts.join(' + ')} ft. ${singerParts.join(' + ')} | Project VocaLead Sheets`
}

const buildSongDescription = (song) => {
  const producerParts = [song.producer, ...(song.additionalProducers ?? [])].filter(Boolean)
  const singerParts = [song.singer, ...(song.additionalVoices ?? [])].filter(Boolean)
  const parts = [`${song.title} lead sheet by ${producerParts.join(' + ')} ft. ${singerParts.join(' + ')}`]

  if (song.alternativeNames?.length) {
    parts.push(`Also known as ${song.alternativeNames.join(', ')}`)
  }

  parts.push('Canonical static page for Google indexing and sharing')
  return parts.join('. ')
}

const writeRouteHtml = async (routePath, html) => {
  const normalized = routePath === '/' ? '' : routePath.replace(/^\//, '').replace(/\/$/, '')
  const outputPath = normalized ? path.resolve(distRoot, normalized, 'index.html') : distIndexPath
  await mkdir(path.dirname(outputPath), { recursive: true })
  await writeFile(outputPath, html, 'utf-8')
}

try {
  const { render } = await vite.ssrLoadModule('/src/entry-server.ts')
  const template = await readFile(distIndexPath, 'utf-8')
  const { appHtml } = await render('/')
  const prerenderedHtml = template.replace(
    '<div id="app"></div>',
    `<div id="app">${appHtml}</div>`,
  )

  await writeFile(distIndexPath, prerenderedHtml, 'utf-8')
  console.log('Prerendered home page into dist/index.html')
} finally {
  await vite.close()
}
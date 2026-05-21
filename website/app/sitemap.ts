import { MetadataRoute } from 'next'
 
export default function sitemap(): MetadataRoute.Sitemap {
  const baseUrl = 'https://nvus.dev/spb/'
  const routes = [
    '',
    'students/',
    'higher-ed/',
    'developers/',
    'professionals/',
    'writers/',
    'adhd/',
    'parents/',
    'entrepreneurs/',
  ]

  return routes.map((route) => ({
    url: `${baseUrl}${route}`,
    lastModified: new Date(),
    changeFrequency: 'monthly' as const,
    priority: route === '' ? 1 : 0.8,
  }))
}

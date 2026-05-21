import { MetadataRoute } from 'next'
 
export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: '*',
        allow: '/spb/',
        disallow: '/',
      },
    ],
    sitemap: 'https://nvus.dev/spb/sitemap.xml',
  }
}

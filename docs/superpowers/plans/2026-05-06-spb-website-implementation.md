# Simple Productivity Blocker Landing Page Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a high-end, empathetic, and futuristic dark-mode landing page for SPB using Next.js, Tailwind v4, and Framer Motion.

**Architecture:** A static-first hybrid architecture using Next.js App Router. The site will be optimized for fast loading on GitHub Pages and containerized for Google Cloud Run. Focus on 3D isometric visuals and empathetic SEO-driven copy.

**Tech Stack:** Next.js, TypeScript, Tailwind CSS v4, Framer Motion, Lucide React, Docker.

---

### Task 1: Project Initialization & Scaffold

**Files:**
- Create: `website/package.json`
- Create: `website/tsconfig.json`
- Create: `website/next.config.ts`
- Create: `website/app/layout.tsx`
- Create: `website/app/page.tsx`

- [ ] **Step 1: Initialize Next.js project**
Run: `npx create-next-app@latest website --typescript --tailwind --eslint --app --src-dir=false --import-alias="@/*" --use-npm`
Note: Use non-interactive mode if possible or follow default prompts.

- [ ] **Step 2: Install additional dependencies**
Run: `cd website && npm install framer-motion lucide-react clsx tailwind-merge`

- [ ] **Step 3: Configure Static Export**
Modify `website/next.config.ts`:
```typescript
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: 'export',
  images: {
    unoptimized: true,
  },
};

export default nextConfig;
```

- [ ] **Step 4: Verify dev server starts**
Run: `npm run dev`
Expected: Server starts on localhost:3000.

- [ ] **Step 5: Commit**
```bash
git add website/
git commit -m "chore: initialize next.js project for spb website"
```

---

### Task 2: Design System & Token Setup

**Files:**
- Modify: `website/app/globals.css`
- Create: `website/lib/utils.ts`

- [ ] **Step 1: Implement CSS Variables for Dark Mode**
Modify `website/app/globals.css`:
```css
@import "tailwindcss";

@theme {
  --color-background: var(--background);
  --color-foreground: var(--foreground);
  --color-accent: var(--accent);
}

:root {
  --background: #09090b; /* Zinc-950 */
  --foreground: #f4f4f5; /* Zinc-100 */
  --accent: #10b981;    /* Emerald-500 */
}

body {
  background-color: var(--background);
  color: var(--foreground);
  font-family: 'Outfit', sans-serif;
}
```

- [ ] **Step 2: Add Tailwind Merge Utility**
Create `website/lib/utils.ts`:
```typescript
import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
```

- [ ] **Step 3: Commit**
```bash
git add website/app/globals.css website/lib/utils.ts
git commit -m "style: set up design system tokens and utilities"
```

---

### Task 3: Hero Component with 3D Mockup

**Files:**
- Create: `website/components/Hero.tsx`
- Modify: `website/app/page.tsx`

- [ ] **Step 1: Create Hero component with Framer Motion**
Create `website/components/Hero.tsx` with a 3D tilt effect for the app mockup. Use a placeholder for the mockup image for now.
```tsx
"use client";
import { motion } from "framer-motion";
import { Download } from "lucide-react";

export default function Hero() {
  return (
    <section className="relative pt-20 pb-32 overflow-hidden">
      <div className="container mx-auto px-6 flex flex-col md:flex-row items-center">
        <div className="md:w-1/2 text-left z-10">
          <motion.h1 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-5xl md:text-7xl font-bold tracking-tight mb-6"
          >
            Secure Your <span className="text-emerald-500">Focus.</span>
          </motion.h1>
          <motion.p 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="text-xl text-zinc-400 mb-8 max-w-lg leading-relaxed"
          >
            They <strong>ask</strong> you to be strong every second. We provide the hardened support you need when willpower isn't enough.
          </motion.p>
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            className="bg-emerald-500 text-zinc-950 px-8 py-4 rounded-full font-bold flex items-center gap-2"
          >
            <Download size={20} /> Download for Windows
          </motion.button>
        </div>
        <div className="md:w-1/2 mt-12 md:mt-0 relative">
          {/* 3D Mockup Container */}
          <motion.div 
            initial={{ opacity: 0, rotateY: -20, scale: 0.9 }}
            animate={{ opacity: 1, rotateY: 0, scale: 1 }}
            transition={{ duration: 1 }}
            className="relative bg-zinc-900 border border-zinc-800 rounded-xl p-4 shadow-2xl"
            style={{ perspective: "1000px" }}
          >
             <div className="aspect-video bg-zinc-800 rounded-lg flex items-center justify-center">
                <span className="text-zinc-500 text-sm italic">High-Fidelity 3D Isometric Mockup</span>
             </div>
          </motion.div>
        </div>
      </div>
    </section>
  );
}
```

- [ ] **Step 2: Integrate into Home Page**
Update `website/app/page.tsx` to include the Hero component.

- [ ] **Step 3: Commit**
```bash
git add website/components/Hero.tsx website/app/page.tsx
git commit -m "feat: add hero section with 3d mockup placeholder"
```

---

### Task 4: Comparison Section (SEO Optimized)

**Files:**
- Create: `website/components/Comparison.tsx`

- [ ] **Step 1: Implement the "Supportive Shield" vs "Weak Blockers" table**
Use semantic HTML and high-intent keywords (e.g., "kernel-level enforcement," "system-level app blocker").

- [ ] **Step 2: Commit**
```bash
git add website/components/Comparison.tsx
git commit -m "feat: add seo-optimized comparison section"
```

---

### Task 5: Bento Grid: Solutions & Use Cases

**Files:**
- Create: `website/components/Solutions.tsx`

- [ ] **Step 1: Implement Bento Grid for target audiences**
Include cards for Schools, Parents, Professionals, and Personal use. Use Lucide icons for each.

- [ ] **Step 2: Commit**
```bash
git add website/components/Solutions.tsx
git commit -m "feat: add bento grid for target audience solutions"
```

---

### Task 6: Installation Timeline

**Files:**
- Create: `website/components/Installation.tsx`

- [ ] **Step 1: Implement the step-by-step guide**
Download -> Extract -> Run as Admin -> Configure.

- [ ] **Step 2: Commit**
```bash
git add website/components/Installation.tsx
git commit -m "feat: add installation timeline guide"
```

---

### Task 7: SEO & Metadata Implementation

**Files:**
- Modify: `website/app/layout.tsx`
- Create: `website/app/sitemap.ts`

- [ ] **Step 1: Add Comprehensive Metadata**
Update `website/app/layout.tsx` with title, description, and OpenGraph tags using keywords from README.

- [ ] **Step 2: Create Sitemap**
Implement `sitemap.ts` for search engines.

- [ ] **Step 3: Commit**
```bash
git add website/app/layout.tsx website/app/sitemap.ts
git commit -m "seo: implement metadata and sitemap"
```

---

### Task 8: Deployment Configuration (GitHub & Cloud Run)

**Files:**
- Create: `website/Dockerfile`
- Create: `website/.github/workflows/deploy.yml`

- [ ] **Step 1: Create Dockerfile for Nginx**
Serve the static files from `website/out`.

- [ ] **Step 2: Setup GitHub Action for Pages**
Automate the static export and deployment.

- [ ] **Step 3: Commit**
```bash
git add website/Dockerfile website/.github/workflows/deploy.yml
git commit -m "deploy: add docker and github actions config"
```

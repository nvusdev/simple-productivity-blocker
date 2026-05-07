# Design Spec: Simple Productivity Blocker Landing Page

Architecting an empathetic, high-end, and futuristic web presence for a kernel-level Windows focus tool.

## 1. Vision & Strategy

### 1.1 Goal
Create a supportive landing page that positions Simple Productivity Blocker (SPB) as a partner in focus rather than a digital cage. The site must "wow" users with high-fidelity 3D visuals while maintaining a clean, professional, and trustworthy aesthetic.

### 1.2 Target Audience
*   **Neurodivergent Individuals (ADHD/Autism):** Seeking structure without feeling punished.
*   **Students:** Needing deep work sessions for exam preparation.
*   **Parents:** Looking for robust but respectful controls for their children.
*   **Professionals:** Entrepreneurs and remote workers fighting "doomscrolling" and distraction.
*   **Privacy-Conscious Users:** Valuing open-source and local-first software.

### 1.3 Design Pillars
*   **Futuristic Google Dark Mode:** Clean, high-contrast, OLED-friendly, and emerald accents.
*   **Empathetic Partnership:** Use supportive language. Acknowledge that focus is hard.
*   **Hardened Reliability:** Emphasize the kernel-level "Triple-Lock" suite to build trust.
*   **Visual-First:** Load directly to an eye-catching 3D isometric mockup of the app.

---

## 2. Visual Identity & Design System

### 2.1 Color Palette
*   **Backdrop:** `Zinc-950` (#09090b) - Deep, "bottomless" black.
*   **Surface:** `Zinc-900` / `Zinc-800` with subtle glassmorphism.
*   **Accent:** `Emerald-500` (#10b981) - Signifying growth, focus, and "Go."
*   **Warning:** `Amber-400` - For high-risk configuration warnings.
*   **Text:** `Zinc-100` (Primary), `Zinc-400` (Secondary).

### 2.2 Typography
*   **Headlines:** `Outfit` (Bold, tight tracking, -0.02em).
*   **Body/UI:** `Geist` or `Inter` (Clean, highly legible).
*   **Code:** `Geist Mono`.

### 2.3 Interactive Elements
*   **3D Isometric Mockups:** Rendered with CSS/Framer Motion or high-quality static assets with parallax tilt.
*   **Double-Bezel Cards:** Inner 1px border (`Zinc-800`) inside an outer subtle glow or slightly lighter background.
*   **Micro-Animations:** Spring-based transitions for all hover states.

---

## 3. Page Structure

### 3.1 Hero: The Supportive Shield
*   **Headline:** "Secure Your Focus."
*   **Subtext:** "They **ask** you to be strong every second. We provide the hardened support you need when willpower isn't enough."
*   **Primary CTA:** "Download for Windows" (Downloads latest GitHub release .zip).
*   **Visual:** Interactive 3D isometric mockup of the SPB Dashboard, showing the "Triple-Lock" status.

### 3.2 Comparison: The Focus Reality
*   **Left Column (Competitors):** "Weak Surface Blockers" (Browser extensions, easy to bypass, "punishment" tone).
*   **Right Column (SPB):** "The Supportive Shield" (System-level enforcement, impossible to "accidentally" bypass, partner tone).

### 3.3 Bento Grid: Solutions for Everyone
*   **Card 1 (Schools/Edu):** Managing labs and exam environments.
*   **Card 2 (Parents):** Setting boundaries without "spying."
*   **Card 3 (Professionals):** Deep work for high-stakes projects.
*   **Card 4 (Personal):** Breaking the cycle of digital addiction.

### 3.4 Installation: The Path to Peace
A vertical timeline or step-grid:
1.  **Download:** Get the latest build from GitHub.
2.  **Extract:** Unzip to your preferred directory.
3.  **Deploy:** Run `main.py` (or compiled binary) as Administrator.
4.  **Secure:** Configure your blocks and activate the Triple-Lock.

### 3.5 About: Why SPB?
*   **Open Source:** Full transparency. No hidden telemetry.
*   **Local-First:** Your data never leaves your machine.
*   **Kernel-Hardened:** Using Windows registry and file-system locks to ensure focus stays focus.

---

## 4. Technical Architecture

### 4.1 Framework Stack
*   **Framework:** Next.js (App Router).
*   **Styling:** Tailwind CSS v4.
*   **Animations:** Framer Motion.
*   **Deployment:** GitHub Pages (Static export) + Google Cloud Run (Containerized).

### 4.2 Key Logic
*   **Dynamic Release Fetching:** Server-side or Build-time script to fetch the latest release URL from GitHub API.
*   **Mobile Responsiveness:** All asymmetric layouts must stack to single-column on viewports `< 768px`.
*   **SEO:** Metadata optimization for terms like "ADHD Productivity Tool," "Windows App Blocker," "Hardened Focus Software."

---

## 5. Constraints & Compliance
*   **No Em Dashes:** Use colons, periods, or commas instead.
*   **Unique Emojis:** Avoid standard 🚀/🔥. Use minimalist geometric symbols or refined icons (e.g., Lucide React).
*   **Empathetic Tone:** Strict audit of copy to ensure no "dehumanizing" or "punishing" language.

---

## 6. Verification Plan
*   **Automated:** `npm run build` validation, Lighthouse score > 95 across all categories.
*   **Manual:** Responsive test on iOS/Android, Link validation for GitHub releases.

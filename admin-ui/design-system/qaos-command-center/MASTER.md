# Design System Master File

> **LOGIC:** When building a specific page, first check `design-system/pages/[page-name].md`.
> If that file exists, its rules **override** this Master file.
> If not, strictly follow the rules below.

---

**Project:** QAOS Command Center
**Generated:** 2026-09-18 01:09:12
**Category:** Status Page / Incident Management
**Design Dials:** Variance 4/10 (Balanced / Modern) | Motion 3/10 (Subtle) | Density 8/10 (Dense / Dashboard)

---

## Global Rules

### Color Palette

| Role | Hex | CSS Variable |
|------|-----|--------------|
| Primary | `#16A34A` | `--color-primary` |
| On Primary | `#000000` | `--color-on-primary` |
| Secondary | `#22C55E` | `--color-secondary` |
| On Secondary | `#0F172A` | `--color-on-secondary` |
| Accent/CTA | `#DC2626` | `--color-accent` |
| On Accent/CTA | `#FFFFFF` | `--color-on-accent` |
| Background | `#0F172A` | `--color-background` |
| Foreground | `#F8FAFC` | `--color-foreground` |
| Card | `#111827` | `--color-card` |
| Card Foreground | `#F8FAFC` | `--color-card-foreground` |
| Muted | `#1E293B` | `--color-muted` |
| Muted Foreground | `#CBD5E1` | `--color-muted-foreground` |
| Border | `#334155` | `--color-border` |
| Destructive | `#DC2626` | `--color-destructive` |
| On Destructive | `#FFFFFF` | `--color-on-destructive` |
| Ring | `#16A34A` | `--color-ring` |

**Color Notes:** Operational green + incident red + maintenance amber

### Typography

- **Heading Font:** Fira Code
- **Body Font:** Fira Sans
- **Mood:** dashboard, data, analytics, code, technical, precise
- **Google Fonts:** [Fira Code + Fira Sans](https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;500;600;700&family=Fira+Sans:wght@300;400;500;600;700&display=swap)

**CSS Import:**
```css
@import url('https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;500;600;700&family=Fira+Sans:wght@300;400;500;600;700&display=swap');
```

### Spacing Variables

*Density: 8/10 — Dense / Dashboard*

| Token | Value | Usage |
|-------|-------|-------|
| `--space-xs` | `2px` / `0.125rem` | Tight gaps |
| `--space-sm` | `4px` / `0.25rem` | Icon gaps, inline spacing |
| `--space-md` | `8px` / `0.5rem` | Standard padding |
| `--space-lg` | `12px` / `0.75rem` | Section padding |
| `--space-xl` | `16px` / `1rem` | Large gaps |
| `--space-2xl` | `24px` / `1.5rem` | Section margins |
| `--space-3xl` | `32px` / `2rem` | Hero padding |

### Shadow Depths

| Level | Value | Usage |
|-------|-------|-------|
| `--shadow-sm` | `0 1px 2px rgba(0,0,0,0.05)` | Subtle lift |
| `--shadow-md` | `0 4px 6px rgba(0,0,0,0.1)` | Cards, buttons |
| `--shadow-lg` | `0 10px 15px rgba(0,0,0,0.1)` | Modals, dropdowns |
| `--shadow-xl` | `0 20px 25px rgba(0,0,0,0.15)` | Hero images, featured cards |

---

## Component Specs

### Buttons

```css
/* Primary Button */
.btn-primary {
  background: #DC2626;
  color: white;
  padding: 12px 24px;
  border-radius: 8px;
  font-weight: 600;
  transition: all 200ms ease;
  cursor: pointer;
}

.btn-primary:hover {
  opacity: 0.9;
  transform: translateY(-1px);
}

/* Secondary Button */
.btn-secondary {
  background: transparent;
  color: #16A34A;
  border: 2px solid #16A34A;
  padding: 12px 24px;
  border-radius: 8px;
  font-weight: 600;
  transition: all 200ms ease;
  cursor: pointer;
}
```

### Cards

```css
.card {
  background: #0F172A;
  border-radius: 12px;
  padding: 24px;
  box-shadow: var(--shadow-md);
  transition: all 200ms ease;
  cursor: pointer;
}

.card:hover {
  box-shadow: var(--shadow-lg);
  transform: translateY(-2px);
}
```

### Inputs

```css
.input {
  padding: 12px 16px;
  border: 1px solid #E2E8F0;
  border-radius: 8px;
  font-size: 16px;
  transition: border-color 200ms ease;
}

.input:focus {
  border-color: #16A34A;
  outline: none;
  box-shadow: 0 0 0 3px #16A34A20;
}
```

### Modals

```css
.modal-overlay {
  background: rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(4px);
}

.modal {
  background: white;
  border-radius: 16px;
  padding: 32px;
  box-shadow: var(--shadow-xl);
  max-width: 500px;
  width: 90%;
}
```

---

## Style Guidelines

**Style:** Dark Mode (OLED)

**Keywords:** Dark theme, low light, high contrast, deep black, midnight blue, eye-friendly, OLED, night mode, power efficient

**Best For:** Night-mode apps, coding platforms, entertainment, eye-strain prevention, OLED devices, low-light

**Key Effects:** Minimal glow (text-shadow: 0 0 10px), dark-to-light transitions, low white emission, high readability, visible focus

### Page Pattern

**Pattern Name:** Real-Time / Operations Landing

- **Conversion Strategy:** Offer a demo or sandbox and show trust signals. Label telemetry as live only when backed by a current source, with update time and stale state. Provide pause/hide or update-frequency controls for tickers and previews, stop offscreen/hidden work, support keyboard controls, and render a static final snapshot under reduced motion.
- **CTA Placement:** Primary CTA in nav + After metrics
- **Section Order:** Hero (product + live preview or status) > Key metrics/indicators > How it works > CTA (Start trial / Contact)

---

## Motion

**Scroll Reveal** (Subtle) — Trigger: scroll (viewport enter) | Duration: 300-400ms | Easing: `power1.out`

```js
gsap.from(el, { opacity: 0, y: 12, duration: 0.35, ease: 'power1.out', scrollTrigger: { trigger: el, start: 'top 90%', toggleActions: 'play none none reverse' } });
```

**Framework notes:** Requires the ScrollTrigger plugin registered once via gsap.registerPlugin(ScrollTrigger); Use matchMedia('(prefers-reduced-motion: reduce)') to skip non-essential motion and render the final state immediately

- ✅ Keep the y offset small (8-16px) so it reads as a fade, not a slide
- ❌ Don't reveal below-the-fold content needed for SEO/crawlers as invisible-by-default without a no-JS fallback
- ⚡ toggleActions 'play none none reverse' avoids re-triggering on every scroll direction change

---

## Anti-Patterns (Do NOT Use)

- ❌ Slow dashboards
- ❌ decorative charts
- ❌ hidden error states

### Additional Forbidden Patterns

- ❌ **Emojis as icons** — Use SVG icons (Heroicons, Lucide, Simple Icons)
- ❌ **Missing cursor:pointer** — All clickable elements must have cursor:pointer
- ❌ **Layout-shifting hovers** — Avoid scale transforms that shift layout
- ❌ **Low contrast text** — Maintain 4.5:1 minimum contrast ratio
- ❌ **Instant state changes** — Always use transitions (150-300ms)
- ❌ **Invisible focus states** — Focus states must be visible for a11y

---

## Pre-Delivery Checklist

Before delivering any UI code, verify:

- [ ] No emojis used as icons (use SVG instead)
- [ ] All icons from consistent icon set (Heroicons/Lucide)
- [ ] `cursor-pointer` on all clickable elements
- [ ] Hover states with smooth transitions (150-300ms)
- [ ] Light mode: text contrast 4.5:1 minimum
- [ ] Focus states visible for keyboard navigation
- [ ] `prefers-reduced-motion` respected
- [ ] Responsive: 375px, 768px, 1024px, 1440px
- [ ] No content hidden behind fixed navbars
- [ ] No horizontal scroll on mobile

---

## Adopted decisions for QAOS 指揮台（本專案採用版，覆蓋上方建議）

上方為 ui-ux-pro-max 依「內部 QA 營運指揮台、深色、資料密集」查詢產生的建議；以下是對照本專案實況後**實際採用**的決定。衝突時以本節為準。

### 為什麼不照抄建議的配色
建議把 **綠色當 Primary、紅色當 Accent**。本平台是狀態密集的監看介面，綠／黃／紅已經被 `done / waiting / failed`、`live / stalled / dead`、`已審 / 待審 / 退回` 佔用；若互動色也用綠色，「可以按的東西」和「已完成的狀態」會混在一起。因此：

- **互動主色維持藍色**（按鈕、連結、焦點環、目前階段），語意色專用於狀態，互不重疊。
- 採用建議的 **slate 基底**（比現況的近黑更能分出層次），與 **提亮的次要文字色**（修掉現況 3.0:1 的小字對比問題）。

### Tokens（取代 `frontend/src/styles/global.css` 的 :root）

| Role | 現況 | 採用 | 對 surface 對比 |
|---|---|---|---|
| bg | `#090c12` | `#0B1220` | — |
| bg-elev（側欄） | `#0e1219` | `#0F172A` | — |
| surface | `#121722` | `#111827` | — |
| surface-2 | `#171d2a` | `#1E293B` | — |
| surface-3 | `#1d2434` | `#273449` | — |
| border | `#1e2636` | `#293548` | — |
| border-strong | `#2b3549` | `#3B4A63` | ≥3:1 non-text |
| text | `#e6eaf2` | `#F1F5F9` | 15.6:1 |
| text-muted | `#8f9ab0` | `#CBD5E1` | 11.4:1 |
| text-faint（小字、標籤） | `#5d6880`（3.2:1 ✗） | `#94A3B8` | 6.4:1 ✓ |
| accent（互動） | `#6ea8ff` | `#7DA6FF` | 焦點環／主按鈕 |
| accent-ink | `#bcd4ff` | `#C7D8FF` | 標籤文字 |
| ok / warn / danger | 維持 | `#3FD598` / `#F4B64A` / `#FF6B7A` | 只給狀態 |
| violet / cyan | 維持 | 只給分類標籤（報告、產出檔案類型） | |

### 字型
- Body：**IBM Plex Sans + Noto Sans TC**（維持；建議的 Fira Sans 對繁中沒有加分）
- Mono：**JetBrains Mono**（取代 IBM Plex Mono；ID、時間、計數一律 mono 並開 `font-variant-numeric: tabular-nums`）
- 字級尺度：**12 / 13 / 14 / 16 / 20 / 24**。最小 12px（現況 10.5 / 11px 全部上調）。

### 密度與間距
採用 density 8 的尺度 `2 / 4 / 8 / 12 / 16 / 24 / 32`；卡片 padding 12px、列表列 8px、區塊間 16–24px。

### 動效
Subtle（motion 3）：只有「目前階段 pulse」與「面板滑入」兩種；全部包在 `@media (prefers-reduced-motion: no-preference)` 內。不引入 GSAP。

### 圖示
Phosphor Icons（`@phosphor-icons/react`，線性、1.5px stroke），取代所有字元圖示（`✋ ⇄ ▾ ▸ → ＋`）。

### 反模式（本專案版）
- 綠色只表示「完成／健康」，不當互動色
- 不用色彩單獨表達狀態：每個狀態標籤都有文字
- 不截斷 gate 名稱、ID；寬度不足時換行或橫向捲動並提示
- 不隱藏錯誤狀態（backend offline、SSE 斷線都要顯示）

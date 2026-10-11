import fs from 'node:fs'

// Official Figma vector paths (5 shapes, no background badge)
// ViewBox: 0 0 200 300
const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 300" width="200" height="300">
  <!-- Top-Left: Orange-Red -->
  <path id="Figma_TopLeft" fill="#F24E1E" d="M0 50C0 22.4 22.4 0 50 0h50v100H50C22.4 100 0 77.6 0 50z"/>
  <!-- Top-Right: Coral -->
  <path id="Figma_TopRight" fill="#FF7262" d="M100 0h50c27.6 0 50 22.4 50 50s-22.4 50-50 50h-50V0z"/>
  <!-- Mid-Left: Purple -->
  <path id="Figma_MidLeft" fill="#A259FF" d="M0 150c0-27.6 22.4-50 50-50h50v100H50c-27.6 0-50-22.4-50-50z"/>
  <!-- Mid-Right: Blue -->
  <path id="Figma_MidRight" fill="#1ABCFE" d="M200 150c0 27.6-22.4 50-50 50s-50-22.4-50-50 22.4-50 50-50 50 22.4 50 50z"/>
  <!-- Bottom-Left: Green -->
  <path id="Figma_BottomLeft" fill="#0ACF83" d="M50 300c27.6 0 50-22.4 50-50v-50H50c-27.6 0-50 22.4-50 50s22.4 50 50 50z"/>
</svg>`

fs.writeFileSync('public/figma_model.svg', svg)
console.log('Saved public/figma_model.svg (no background badge)')

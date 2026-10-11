import fs from 'node:fs'

const data = JSON.parse(fs.readFileSync('node_modules/@iconify-json/simple-icons/icons.json', 'utf8'))
const gsapPath = data.icons['gsap'].body.replace(/<path[^>]*d="([^"]*)"[^>]*>/, '$1')

// GSAP Wordmark Letters (no square badge)
// ViewBox: 0 0 24 24
const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="240" height="240">
  <path id="GSAP_Letters" fill="#FFFDE8" d="${gsapPath}" />
</svg>`

fs.writeFileSync('public/gsap_model.svg', svg)
console.log('Saved public/gsap_model.svg (GSAP letters only)')

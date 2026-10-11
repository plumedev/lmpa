import fs from 'node:fs'

const data = JSON.parse(fs.readFileSync('node_modules/@iconify-json/simple-icons/icons.json', 'utf8'))
const trianglePath = data.icons['threedotjs'].body.replace(/<path[^>]*d="([^"]*)"[^>]*>/, '$1')

// Triangle lattice mesh (no square badge, no lowercase 't')
// ViewBox: 0 0 24 24
const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="240" height="240">
  <path id="Three_Triangle" fill="#FFFFFF" d="${trianglePath}" />
</svg>`

fs.writeFileSync('public/three_model.svg', svg)
console.log('Saved public/three_model.svg (triangle lattice only)')

<script setup lang="ts">
import * as THREE from 'three'
import vertexShader from '~/shaders/dotGrid.vert?raw'
import fragmentShader from '~/shaders/dotGrid.frag?raw'

const containerRef = ref<HTMLDivElement | null>(null)
let cleanupFn: (() => void) | null = null

onMounted(() => {
  const container = containerRef.value
  if (!container || typeof window === 'undefined') {
    return
  }

  // 1. Scene, Camera & Renderer
  const scene = new THREE.Scene()
  const timer = new THREE.Timer()
  let width = container.clientWidth || window.innerWidth
  let height = container.clientHeight || window.innerHeight

  const camera = new THREE.OrthographicCamera(
    -width / 2,
    width / 2,
    height / 2,
    -height / 2,
    0.1,
    1000
  )
  camera.position.z = 10

  const renderer = new THREE.WebGLRenderer({
    antialias: true,
    alpha: true,
    powerPreference: 'high-performance'
  })
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.25))
  renderer.setSize(width, height)
  renderer.setClearColor(0x000000, 1)

  const domEl = renderer.domElement
  domEl.className = 'absolute inset-0 w-full h-full pointer-events-auto block max-w-full'
  container.appendChild(domEl)

  // Cached DOM Rect to eliminate synchronous layout reflows (getBoundingClientRect) on every mousemove
  let cachedDomRect = domEl.getBoundingClientRect()
  const refreshDomRect = () => {
    if (domEl) {
      cachedDomRect = domEl.getBoundingClientRect()
    }
  }
  window.addEventListener('scroll', refreshDomRect, { passive: true })
  window.addEventListener('resize', refreshDomRect, { passive: true })

  // 2. GUI Live Parameters
  const guiParams = {
    // Sensibilité Vitesse
    speedThreshold: 80,
    speedMax: 1150,

    // Zone Bateau (Capsule)
    hullLengthMin: 36,
    hullLengthMax: 64,
    hullRadiusMin: 14,
    hullRadiusMax: 36,
    hullPushMin: 4.5,
    hullPushMax: 9,
    hullBrightness: 0.9,

    // Sillon en V (Traits)
    lineWidthMin: 20,
    lineWidthMax: 25.5,
    lineAmpMin: 7.5,
    lineAmpMax: 15,
    vWaveSpeedMin: 60,
    vWaveSpeedMax: 150,
    lineBrightness: 1.7,

    // Canal Intérieur
    troughPushMin: 4.4,
    troughPushMax: 10,

    // Persistance & Limites
    maxAgeMin: 1.1,
    maxAgeMax: 2.45,
    corridorLimitMin: 83,
    corridorLimitMax: 154,
    maxDisplacement: 12,

    // Onde de Choc (Clic)
    shockSpeed: 520,
    shockAmp: 10.5,
    shockWidth: 42,
    shockDuration: 1.3,
    shockBrightness: 2.2,

    // Rendu Visuel
    pointBaseSize: 2.4,
    pointGrowSize: 4,
    ambientBreath: 0.15
  }

  // 3. Boat Wake & Shockwave Trailing State
  const MAX_WAKE = 32
  const wakePosArray = new Float32Array(MAX_WAKE * 4) // x, y, birthTime, speed
  const wakeVecArray = new Float32Array(MAX_WAKE * 4) // dirX, dirY, normX, normY
  let wakeHead = 0

  const MAX_SHOCKS = 8
  const shockwavesArray = new Float32Array(MAX_SHOCKS * 4) // x, y, birthTime, strength
  let shockHead = 0

  const triggerShockwave = (x: number, y: number, strength = 1.0) => {
    const now = timer.getElapsed()
    const idx = shockHead * 4
    shockwavesArray[idx] = x
    shockwavesArray[idx + 1] = y
    shockwavesArray[idx + 2] = now
    shockwavesArray[idx + 3] = strength
    shockHead = (shockHead + 1) % MAX_SHOCKS
  }

  const uniforms = {
    uTime: { value: 0 },
    uMouse: { value: new THREE.Vector2(-9999, -9999) },
    uMouseDir: { value: new THREE.Vector2(1, 0) },
    uMouseActive: { value: 0 },
    uMouseSpeed: { value: 0 },
    uWakePos: { value: wakePosArray },
    uWakeVec: { value: wakeVecArray },
    uShockwaves: { value: shockwavesArray },
    uShockParams: { value: new THREE.Vector4(guiParams.shockSpeed, guiParams.shockAmp, guiParams.shockWidth, guiParams.shockDuration) },
    uShockBrightness: { value: guiParams.shockBrightness },
    uPixelRatio: { value: renderer.getPixelRatio() },
    uSpeedTuning: { value: new THREE.Vector2(guiParams.speedThreshold, guiParams.speedMax) },
    uHullDim: { value: new THREE.Vector4(guiParams.hullLengthMin, guiParams.hullLengthMax, guiParams.hullRadiusMin, guiParams.hullRadiusMax) },
    uHullDyn: { value: new THREE.Vector4(guiParams.hullPushMin, guiParams.hullPushMax, guiParams.hullBrightness, 0) },
    uWakeLine: { value: new THREE.Vector4(guiParams.lineWidthMin, guiParams.lineWidthMax, guiParams.lineAmpMin, guiParams.lineAmpMax) },
    uWakeExp: { value: new THREE.Vector4(guiParams.vWaveSpeedMin, guiParams.vWaveSpeedMax, guiParams.lineBrightness, 0) },
    uChannel: { value: new THREE.Vector2(guiParams.troughPushMin, guiParams.troughPushMax) },
    uWakeLimits: { value: new THREE.Vector4(guiParams.maxAgeMin, guiParams.maxAgeMax, guiParams.corridorLimitMin, guiParams.corridorLimitMax) },
    uRenderParams: { value: new THREE.Vector4(guiParams.maxDisplacement, guiParams.pointBaseSize, guiParams.pointGrowSize, guiParams.ambientBreath) }
  }

  // 4. Custom GLSL Shader Material
  const material = new THREE.ShaderMaterial({
    vertexShader,
    fragmentShader,
    uniforms,
    transparent: true,
    depthTest: false
  })

  // 4. Dot Grid Construction
  let pointsMesh: THREE.Points | null = null
  const SPACING = 28 // 28px grid spacing matching the screenshot

  const buildGrid = (w: number, h: number) => {
    if (pointsMesh) {
      scene.remove(pointsMesh)
      pointsMesh.geometry.dispose()
      pointsMesh = null
    }

    const cols = Math.ceil(w / SPACING) + 4
    const rows = Math.ceil(h / SPACING) + 4
    const totalPoints = cols * rows

    const positions = new Float32Array(totalPoints * 3)
    const startX = -((cols - 1) * SPACING) / 2
    const startY = -((rows - 1) * SPACING) / 2

    let idx = 0
    for (let r = 0; r < rows; r++) {
      const y = startY + r * SPACING
      for (let c = 0; c < cols; c++) {
        const x = startX + c * SPACING
        positions[idx * 3] = x
        positions[idx * 3 + 1] = y
        positions[idx * 3 + 2] = 0
        idx++
      }
    }

    const geometry = new THREE.BufferGeometry()
    geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3))
    geometry.setAttribute('basePos', new THREE.BufferAttribute(positions.slice(), 3))

    pointsMesh = new THREE.Points(geometry, material)
    scene.add(pointsMesh)
  }

  buildGrid(width, height)

  // 5. Boat Wake Trailing Handlers
  let lastMouseX = 0
  let lastMouseY = 0
  let lastWakeTime = 0
  let smoothedDirX = 0
  let smoothedDirY = 0

  const addWakePoint = (worldX: number, worldY: number, dirX: number, dirY: number, speed: number, time: number) => {
    const offset = wakeHead * 4
    wakePosArray[offset] = worldX
    wakePosArray[offset + 1] = worldY
    wakePosArray[offset + 2] = time
    wakePosArray[offset + 3] = speed

    wakeVecArray[offset] = dirX
    wakeVecArray[offset + 1] = dirY
    wakeVecArray[offset + 2] = -dirY // lateral normal X (perpendicular)
    wakeVecArray[offset + 3] = dirX // lateral normal Y
    wakeHead = (wakeHead + 1) % MAX_WAKE
  }

  const onPointerMove = (e: PointerEvent) => {
    const px = e.clientX - cachedDomRect.left
    const py = e.clientY - cachedDomRect.top

    // Convert DOM pixel coordinates to Orthographic world coordinates
    const worldX = px - width / 2
    const worldY = height / 2 - py

    uniforms.uMouse.value.set(worldX, worldY)
    uniforms.uMouseActive.value = 1

    const now = timer.getElapsed()
    const dt = Math.max(0.001, now - lastWakeTime)
    const dx = worldX - lastMouseX
    const dy = worldY - lastMouseY
    const distMoved = Math.hypot(dx, dy)
    const rawSpeed = distMoved / dt
    smoothedSpeed = smoothedSpeed * 0.35 + rawSpeed * 0.65
    uniforms.uMouseSpeed.value = smoothedSpeed

    // Update mouse travel direction
    if (distMoved > 2) {
      const rawDirX = dx / distMoved
      const rawDirY = dy / distMoved
      smoothedDirX = smoothedDirX === 0 ? rawDirX : smoothedDirX * 0.25 + rawDirX * 0.75
      smoothedDirY = smoothedDirY === 0 ? rawDirY : smoothedDirY * 0.25 + rawDirY * 0.75
      const len = Math.hypot(smoothedDirX, smoothedDirY) || 1
      uniforms.uMouseDir.value.set(smoothedDirX / len, smoothedDirY / len)
    }

    // As the mouse travels, drop wake nodes along the trajectory path
    if (distMoved > 16) {
      const speed = Math.min(1800, rawSpeed)
      const len = Math.hypot(smoothedDirX, smoothedDirY) || 1
      const dirX = smoothedDirX / len
      const dirY = smoothedDirY / len

      addWakePoint(worldX, worldY, dirX, dirY, speed, now)

      lastMouseX = worldX
      lastMouseY = worldY
      lastWakeTime = now
    }
  }

  const onPointerDown = (e: PointerEvent) => {
    // Only respond to primary buttons (left click / touch)
    if (e.button !== undefined && e.button !== 0) {
      return
    }
    const px = e.clientX - cachedDomRect.left
    const py = e.clientY - cachedDomRect.top
    const worldX = px - width / 2
    const worldY = height / 2 - py
    // Trigger impactful shockwave expanding outwards
    triggerShockwave(worldX, worldY, 1.0)
  }

  const onPointerLeave = () => {
    smoothedSpeed = 0
    uniforms.uMouseSpeed.value = 0
    uniforms.uMouseActive.value = 0
    uniforms.uMouse.value.set(-9999, -9999)
  }

  domEl.addEventListener('pointermove', onPointerMove, { passive: true })
  domEl.addEventListener('pointerdown', onPointerDown, { passive: true })
  domEl.addEventListener('pointerleave', onPointerLeave, { passive: true })

  // 6. Responsive Resize Handling
  let resizePending = false
  const onResize = () => {
    if (!resizePending) {
      resizePending = true
      requestAnimationFrame(() => {
        if (!container) {
          return
        }
        width = container.clientWidth || window.innerWidth
        height = container.clientHeight || window.innerHeight

        camera.left = -width / 2
        camera.right = width / 2
        camera.top = height / 2
        camera.bottom = -height / 2
        camera.updateProjectionMatrix()

        renderer.setSize(width, height)
        uniforms.uPixelRatio.value = renderer.getPixelRatio()
        buildGrid(width, height)
        resizePending = false
      })
    }
  }
  window.addEventListener('resize', onResize, { passive: true })

  // 7. Intersection Hibernation (0% GPU/CPU when scrolled away)
  let isVisible = true
  let isTabActive = true

  const observer = new IntersectionObserver((entries) => {
    if (entries[0]) {
      isVisible = entries[0].isIntersecting
    }
  }, { threshold: 0.05 })
  observer.observe(container)

  const onVisibilityChange = () => {
    isTabActive = document.visibilityState === 'visible'
  }
  document.addEventListener('visibilitychange', onVisibilityChange)

  // 8. Ultra-Smooth 120Hz/165Hz Render Loop
  let animationId = 0
  let smoothedSpeed = 0

  const animate = (timestamp?: number) => {
    animationId = requestAnimationFrame(animate)

    timer.update(timestamp)
    const delta = timer.getDelta()
    if (!isVisible || !isTabActive) {
      return
    }

    // Natural decay of mouse speed when mouse slows down or stops
    smoothedSpeed *= Math.exp(-delta * 7.0)
    uniforms.uMouseSpeed.value = smoothedSpeed

    const elapsedTime = timer.getElapsed()
    uniforms.uTime.value = elapsedTime

    renderer.render(scene, camera)
  }

  // Start animation loop
  animate()

  // 10. Cleanup handler
  cleanupFn = () => {
    cancelAnimationFrame(animationId)
    observer.disconnect()
    document.removeEventListener('visibilitychange', onVisibilityChange)
    window.removeEventListener('resize', onResize)
    window.removeEventListener('scroll', refreshDomRect)
    window.removeEventListener('resize', refreshDomRect)
    domEl.removeEventListener('pointermove', onPointerMove)
    domEl.removeEventListener('pointerdown', onPointerDown)
    domEl.removeEventListener('pointerleave', onPointerLeave)

    if (pointsMesh) {
      scene.remove(pointsMesh)
      pointsMesh.geometry.dispose()
    }
    material.dispose()
    renderer.dispose()
    timer.dispose()

    if (domEl.parentNode) {
      domEl.parentNode.removeChild(domEl)
    }
  }
})

onUnmounted(() => {
  if (cleanupFn) {
    cleanupFn()
  }
})
</script>

<template>
  <section
    ref="containerRef"
    class="relative w-full min-h-screen bg-[#000000] text-white flex items-center justify-center overflow-hidden select-none"
  >
    <!-- Centered High-Impact Title matching the screenshot -->
    <div class="relative z-10 pointer-events-none text-left select-none px-6 md:px-12 max-w-5xl w-full flex justify-center">
      <h2 class="text-4xl sm:text-6xl md:text-7xl lg:text-[8vw] font-bold tracking-tight leading-[1.08] text-white">
        <div>Interactivity:</div>
        <div>user-driven</div>
      </h2>
    </div>
  </section>
</template>

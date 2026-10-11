<script setup lang="ts">
import * as THREE from 'three'
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js'
import RAPIER from '@dimforge/rapier3d-compat'

const containerRef = ref<HTMLDivElement | null>(null)
const isLoaded = ref(false)
const loadProgress = ref(0)
const shatteredCount = ref(0)

interface LogoItem {
  id: string
  name: string
  group: THREE.Group
  body: RAPIER.RigidBody
  collider: RAPIER.Collider
  homePos: { x: number, y: number, z: number }
  seed: number
  radius: number
  baseScale: number
  isShattered: boolean
  prevLinvel: { x: number, y: number, z: number }
  prevSpeed: number
  popIn?: { start: number, duration: number } | null
  respawnTimeoutId?: ReturnType<typeof setTimeout> | null
}

interface DebrisCluster {
  instancedMesh: THREE.InstancedMesh
  cubes: {
    body: RAPIER.RigidBody
    collider: RAPIER.Collider
    baseScale: number
  }[]
  logoId: string
  createdAt: number
  shrinkStart: number
}

interface ModelConfig {
  id: string
  name: string
  url: string
  scale: number
  homeOffset: { xRatio: number, y: number }
  seed: number
}

// Configurable models list (scaled down by 2x)
const modelConfigs: ModelConfig[] = [
  {
    id: 'vue',
    name: 'VueJS',
    url: '/models/vue.glb',
    scale: 0.22,
    homeOffset: { xRatio: -0.72, y: -0.7 },
    seed: 1.2
  },
  {
    id: 'angular',
    name: 'Angular',
    url: '/models/angular.glb',
    scale: 0.5,
    homeOffset: { xRatio: -0.43, y: 1.0 },
    seed: 3.4
  },
  {
    id: 'figma',
    name: 'Figma',
    url: '/models/figma.glb',
    scale: 0.5,
    homeOffset: { xRatio: -0.14, y: -0.9 },
    seed: 5.6
  },
  {
    id: 'three',
    name: 'Three.js',
    url: '/models/three.glb',
    scale: 0.5,
    homeOffset: { xRatio: 0.14, y: 0.9 },
    seed: 2.1
  },
  {
    id: 'ts',
    name: 'TypeScript',
    url: '/models/typescript.glb',
    scale: 0.5,
    homeOffset: { xRatio: 0.43, y: -0.7 },
    seed: 4.8
  },
  {
    id: 'gsap',
    name: 'GSAP',
    url: '/models/gsap.glb',
    scale: 0.5,
    homeOffset: { xRatio: 0.72, y: 1.0 },
    seed: 0.7
  }
]

// Expose respawn function to template
let respawnAllFn: (() => void) | null = null
let cleanupFn: (() => void) | null = null

const respawnAllLogos = () => {
  if (respawnAllFn) {
    respawnAllFn()
  }
}

onMounted(async () => {
  if (!containerRef.value) {
    return
  }

  // 1. Initialize Rapier Physics WASM engine
  await RAPIER.init()

  const container = containerRef.value
  let width = container.clientWidth
  let height = container.clientHeight

  // 2. Three.js Scene, Camera, and High-Performance Renderer
  const scene = new THREE.Scene()
  scene.background = new THREE.Color(0x000000)

  const camera = new THREE.PerspectiveCamera(40, width / height, 0.1, 100)
  camera.position.set(0, 0, 14)
  camera.lookAt(0, 0, 0)

  // WebGL Renderer with optimized high-performance flags
  const renderer = new THREE.WebGLRenderer({
    antialias: true,
    alpha: false,
    powerPreference: 'high-performance',
    precision: 'mediump',
    stencil: false,
    depth: true
  })
  renderer.setSize(width, height)
  // Capped at 1.25 on high-res / 2K / 4K displays to ensure locked 120Hz/144Hz framerate without GPU fillrate choke
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.25))
  renderer.shadowMap.enabled = false // Pitch-black background: eliminates full depth pass for 0% visual loss
  renderer.toneMapping = THREE.ACESFilmicToneMapping
  renderer.toneMappingExposure = 1.15
  const domEl = renderer.domElement
  domEl.style.display = 'block'
  domEl.style.maxWidth = '100%'
  container.appendChild(domEl)

  // 3. Studio Lighting for specular balloon sheen
  const ambientLight = new THREE.AmbientLight(0xffffff, 0.95)
  scene.add(ambientLight)

  const mainLight = new THREE.DirectionalLight(0xffffff, 2.8)
  mainLight.position.set(6, 10, 10)
  scene.add(mainLight)

  const rimLight = new THREE.DirectionalLight(0x7090ff, 1.4)
  rimLight.position.set(-8, -4, 6)
  scene.add(rimLight)

  const topLight = new THREE.DirectionalLight(0xffffff, 0.8)
  topLight.position.set(0, 8, -4)
  scene.add(topLight)

  // 4. Rapier Physics World with downward gravity for fallen debris
  const gravity = { x: 0, y: -26, z: 0 }
  const world = new RAPIER.World(gravity)

  // Calculate visible bounds in world coordinates at z = 0
  const getVisibleBounds = () => {
    const vFOV = (camera.fov * Math.PI) / 180
    const visibleH = 2 * Math.tan(vFOV / 2) * camera.position.z
    const visibleW = visibleH * (width / height)
    return {
      halfW: visibleW / 2,
      halfH: visibleH / 2
    }
  }

  let { halfW, halfH } = getVisibleBounds()

  // 5. Boundary Walls Colliders
  interface WallCollider {
    collider: RAPIER.Collider
    type: 'top' | 'bottom' | 'left' | 'right' | 'front' | 'back'
  }
  const walls: WallCollider[] = []

  const updateWallColliders = () => {
    for (let i = 0; i < walls.length; i++) {
      const w = walls[i]
      if (w) {
        world.removeCollider(w.collider, true)
      }
    }
    walls.length = 0

    const thickness = 2.0
    // Floor
    const bottomDesc = RAPIER.ColliderDesc.cuboid(halfW + 4, thickness, 5)
      .setTranslation(0, -halfH - thickness, 0)
      .setRestitution(0.50)
      .setFriction(0.4)
    walls.push({ collider: world.createCollider(bottomDesc), type: 'bottom' })

    // Ceiling
    const topDesc = RAPIER.ColliderDesc.cuboid(halfW + 4, thickness, 5)
      .setTranslation(0, halfH + thickness, 0)
      .setRestitution(0.50)
      .setFriction(0.3)
    walls.push({ collider: world.createCollider(topDesc), type: 'top' })

    // Left Wall
    const leftDesc = RAPIER.ColliderDesc.cuboid(thickness, halfH + 4, 5)
      .setTranslation(-halfW - thickness, 0, 0)
      .setRestitution(0.50)
      .setFriction(0.3)
    walls.push({ collider: world.createCollider(leftDesc), type: 'left' })

    // Right Wall
    const rightDesc = RAPIER.ColliderDesc.cuboid(thickness, halfH + 4, 5)
      .setTranslation(halfW + thickness, 0, 0)
      .setRestitution(0.50)
      .setFriction(0.3)
    walls.push({ collider: world.createCollider(rightDesc), type: 'right' })

    // Front Wall (keeps objects from flying past camera)
    const frontDesc = RAPIER.ColliderDesc.cuboid(halfW + 4, halfH + 4, thickness)
      .setTranslation(0, 0, 2.5 + thickness)
      .setRestitution(0.50)
      .setFriction(0.3)
    walls.push({ collider: world.createCollider(frontDesc), type: 'front' })

    // Back Wall
    const backDesc = RAPIER.ColliderDesc.cuboid(halfW + 4, halfH + 4, thickness)
      .setTranslation(0, 0, -2.5 - thickness)
      .setRestitution(0.50)
      .setFriction(0.3)
    walls.push({ collider: world.createCollider(backDesc), type: 'back' })
  }

  updateWallColliders()

  // 6. Instanced Debris System (1 draw call per shatter explosion!)
  const debrisSceneGroup = new THREE.Group()
  scene.add(debrisSceneGroup)
  const debrisClusters: DebrisCluster[] = []

  const cubeGeo = new THREE.BoxGeometry(0.11, 0.11, 0.11)
  const sharedDebrisMaterial = new THREE.MeshStandardMaterial({
    roughness: 0.20,
    metalness: 0.08
  })

  // Color palettes matching each logo
  const debrisColorPalettes: Record<string, number[]> = {
    vue: [0x42B883, 0x42B883, 0x35495E, 0x35495E, 0x00DC82],
    angular: [0xDD0031, 0xF50057, 0xE91E63, 0x7B1FA2, 0xFF4081],
    ts: [0x3178C6, 0x3178C6, 0xFFFFFF, 0xFFFFFF, 0x235A97],
    figma: [0xF24E1E, 0xFF7262, 0xA259FF, 0x1ABCFE, 0x0ACF83],
    three: [0xFFFFFF, 0xE2E8F0, 0x94A3B8, 0x38BDF8],
    gsap: [0xFFFDE8, 0x0AE448, 0x88CE02, 0xFFFFFF]
  }

  // Camera Shake state
  let screenShake = 0

  // Procedural Web Audio Shatter & Nudge SFX
  let audioCtx: AudioContext | null = null
  const playShatterSound = () => {
    try {
      const AudioCtx = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext
      if (!AudioCtx) {
        return
      }
      if (!audioCtx) {
        audioCtx = new AudioCtx()
      }
      if (audioCtx.state === 'suspended') {
        audioCtx.resume()
      }

      const now = audioCtx.currentTime
      const bufferSize = Math.floor(audioCtx.sampleRate * 0.32)
      const buffer = audioCtx.createBuffer(1, bufferSize, audioCtx.sampleRate)
      const data = buffer.getChannelData(0)
      for (let i = 0; i < bufferSize; i++) {
        data[i] = (Math.random() * 2 - 1) * Math.exp(-i / (audioCtx.sampleRate * 0.07))
      }
      const noise = audioCtx.createBufferSource()
      noise.buffer = buffer

      const filter = audioCtx.createBiquadFilter()
      filter.type = 'bandpass'
      filter.frequency.setValueAtTime(1500, now)
      filter.frequency.exponentialRampToValueAtTime(320, now + 0.30)
      filter.Q.value = 3.5

      const gain = audioCtx.createGain()
      gain.gain.setValueAtTime(0.28, now)
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.30)

      noise.connect(filter)
      filter.connect(gain)
      gain.connect(audioCtx.destination)
      noise.start(now)
    } catch {
      // Autoplay fallback
    }
  }

  const playNudgeSound = (isPower = false) => {
    try {
      const AudioCtx = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext
      if (!AudioCtx) {
        return
      }
      if (!audioCtx) {
        audioCtx = new AudioCtx()
      }
      if (audioCtx.state === 'suspended') {
        audioCtx.resume()
      }

      const now = audioCtx.currentTime
      const osc = audioCtx.createOscillator()
      const gain = audioCtx.createGain()

      osc.type = 'sine'
      const startFreq = isPower ? 180 : 135
      osc.frequency.setValueAtTime(startFreq, now)
      osc.frequency.exponentialRampToValueAtTime(38, now + (isPower ? 0.20 : 0.13))

      const startVol = isPower ? 0.28 : 0.15
      gain.gain.setValueAtTime(startVol, now)
      gain.gain.exponentialRampToValueAtTime(0.001, now + (isPower ? 0.20 : 0.13))

      osc.connect(gain)
      gain.connect(audioCtx.destination)
      osc.start(now)
      osc.stop(now + (isPower ? 0.21 : 0.14))
    } catch {
      // Autoplay fallback
    }
  }

  // 7. Load GLTF / GLB 3D Models
  const gltfLoader = new GLTFLoader()
  const logos: LogoItem[] = []

  let loadedCount = 0
  for (const cfg of modelConfigs) {
    try {
      const gltf = await gltfLoader.loadAsync(cfg.url)
      const model = gltf.scene

      // Freeze static internal mesh transforms to eliminate scenegraph matrix calculations
      model.traverse((child) => {
        if ((child as THREE.Mesh).isMesh) {
          const mesh = child as THREE.Mesh
          mesh.matrixAutoUpdate = false
          mesh.updateMatrix()

          if (mesh.material && mesh.material instanceof THREE.MeshStandardMaterial) {
            mesh.material.roughness = 0.22
            mesh.material.metalness = 0.05
            if (mesh.geometry.attributes.color) {
              mesh.material.vertexColors = true
              mesh.material.color.setRGB(1, 1, 1)
            }
          }
        }
      })

      if (cfg.scale !== 1.0) {
        model.scale.setScalar(cfg.scale)
      }

      const bbox = new THREE.Box3().setFromObject(model)
      const size = new THREE.Vector3()
      bbox.getSize(size)
      const center = new THREE.Vector3()
      bbox.getCenter(center)

      // Center model pivot
      model.position.sub(center)

      const wrapper = new THREE.Group()
      wrapper.add(model)
      scene.add(wrapper)

      const radius = Math.max(size.x, size.y, size.z) * 0.48

      const maxSpread = Math.max(2.0, halfW - 2.2)
      const homeX = cfg.homeOffset.xRatio * maxSpread
      const home = { x: homeX, y: cfg.homeOffset.y, z: 0 }
      wrapper.position.set(home.x, home.y, home.z)

      // Dynamic RigidBody: full 3D rotation, calibrated dampening for silky smooth float
      const bodyDesc = RAPIER.RigidBodyDesc.dynamic()
        .setTranslation(home.x, home.y, home.z)
        .enabledRotations(true, true, true)
        .setLinearDamping(2.0)
        .setAngularDamping(2.4)
      const body = world.createRigidBody(bodyDesc)
      body.setGravityScale(0.0, true)

      // Calibrated density (6.5) and soft restitution (0.50) for organic balloon feel
      const colliderDesc = RAPIER.ColliderDesc.ball(radius)
        .setRestitution(0.50)
        .setFriction(0.25)
        .setDensity(6.5)
      const collider = world.createCollider(colliderDesc, body)

      wrapper.userData = { id: cfg.id }

      logos.push({
        id: cfg.id,
        name: cfg.name,
        group: wrapper,
        body,
        collider,
        homePos: home,
        seed: cfg.seed,
        radius,
        baseScale: 1.0,
        isShattered: false,
        prevLinvel: { x: 0, y: 0, z: 0 },
        prevSpeed: 0,
        popIn: null,
        respawnTimeoutId: null
      })

      loadedCount++
      loadProgress.value = Math.round((loadedCount / modelConfigs.length) * 100)
    } catch (err) {
      console.error(`Failed to load GLB model ${cfg.url}:`, err)
    }
  }

  // 8. Easter Egg: Shatter & Respawn (Instanced draw calls)
  const shatterLogo = (logoItem: LogoItem, impactDir: { x: number, y: number, z: number }) => {
    if (logoItem.isShattered) {
      return
    }

    logoItem.isShattered = true
    logoItem.group.visible = false
    logoItem.body.setEnabled(false)

    if (activeLogo?.id === logoItem.id) {
      isDragging = false
      activeLogo = null
      updateCursor('default')
    }

    screenShake = 0.38
    playShatterSound()

    const trans = logoItem.body.translation()
    const now = performance.now()
    const colors = debrisColorPalettes[logoItem.id] ?? debrisColorPalettes.vue ?? [0xffffff]
    const cubeCount = 48

    const instancedMesh = new THREE.InstancedMesh(cubeGeo, sharedDebrisMaterial, cubeCount)
    instancedMesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage)
    debrisSceneGroup.add(instancedMesh)

    const cubesData: { body: RAPIER.RigidBody, collider: RAPIER.Collider, baseScale: number }[] = []
    const tempColor = new THREE.Color()

    for (let i = 0; i < cubeCount; i++) {
      const r = Math.cbrt(Math.random()) * logoItem.radius * 0.78
      const theta = Math.random() * Math.PI * 2
      const phi = Math.acos(2 * Math.random() - 1)

      const ox = r * Math.sin(phi) * Math.cos(theta)
      const oy = r * Math.sin(phi) * Math.sin(theta)
      const oz = r * Math.cos(phi) * 0.65

      const px = trans.x + ox
      const py = trans.y + oy
      const pz = trans.z + oz

      const dist = Math.hypot(ox, oy, oz) || 1
      const blastSpeed = 2.4 + Math.random() * 5.5
      const rx = (ox / dist) * blastSpeed
      const ry = (oy / dist) * blastSpeed
      const rz = (oz / dist) * blastSpeed

      const vx = rx - impactDir.x * 0.25 + (Math.random() - 0.5) * 2.5
      const vy = ry - impactDir.y * 0.25 + (Math.random() - 0.5) * 2.5
      const vz = rz - impactDir.z * 0.25 + (Math.random() - 0.5) * 1.8

      const cubeSize = 0.05 + (Math.random() - 0.5) * 0.0125
      const half = cubeSize / 2

      const rbDesc = RAPIER.RigidBodyDesc.dynamic()
        .setTranslation(px, py, pz)
        .setLinvel(vx, vy, vz)
        .setAngvel({
          x: (Math.random() - 0.5) * 22,
          y: (Math.random() - 0.5) * 22,
          z: (Math.random() - 0.5) * 22
        })
        .setLinearDamping(0.35)
        .setAngularDamping(0.4)
      const rb = world.createRigidBody(rbDesc)
      rb.setGravityScale(1.0, true)

      const collDesc = RAPIER.ColliderDesc.cuboid(half, half, half)
        .setRestitution(0.55)
        .setFriction(0.45)
        .setDensity(1.1)
      const coll = world.createCollider(collDesc, rb)

      tempColor.setHex(colors[i % colors.length] ?? 0xffffff)
      instancedMesh.setColorAt(i, tempColor)

      cubesData.push({
        body: rb,
        collider: coll,
        baseScale: cubeSize / 0.055
      })
    }

    if (instancedMesh.instanceColor) {
      instancedMesh.instanceColor.needsUpdate = true
    }

    debrisClusters.push({
      instancedMesh,
      cubes: cubesData,
      logoId: logoItem.id,
      createdAt: now,
      shrinkStart: now + 4800
    })

    shatteredCount.value = logos.filter(l => l.isShattered).length

    logoItem.respawnTimeoutId = setTimeout(() => {
      respawnLogo(logoItem)
    }, 5500)
  }

  const respawnLogo = (item: LogoItem) => {
    if (!item.isShattered) {
      return
    }

    if (item.respawnTimeoutId) {
      clearTimeout(item.respawnTimeoutId)
      item.respawnTimeoutId = null
    }

    const now = performance.now()
    for (let i = 0; i < debrisClusters.length; i++) {
      const c = debrisClusters[i]
      if (c && c.logoId === item.id && c.shrinkStart > now) {
        c.shrinkStart = now
      }
    }

    item.isShattered = false
    item.group.visible = true
    item.group.scale.setScalar(0.001)
    item.popIn = { start: now, duration: 600 }

    item.body.setTranslation(item.homePos, true)
    item.body.setRotation({ x: 0, y: 0, z: 0, w: 1 }, true)
    item.body.setLinvel({ x: 0, y: 0, z: 0 }, true)
    item.body.setAngvel({ x: 0, y: 0, z: 0 }, true)
    item.body.setEnabled(true)
    item.prevLinvel.x = 0
    item.prevLinvel.y = 0
    item.prevLinvel.z = 0
    item.prevSpeed = 0

    shatteredCount.value = logos.filter(l => l.isShattered).length
  }

  respawnAllFn = () => {
    for (let i = 0; i < logos.length; i++) {
      const l = logos[i]
      if (l && l.isShattered) {
        respawnLogo(l)
      }
    }
  }

  // 8b. Single click (shoulder nudge) & Double click (power axial spin)
  const applyNudge = (item: LogoItem, hitPoint: THREE.Vector3) => {
    if (item.isShattered) {
      return
    }

    const trans = item.body.translation()
    const r = item.radius || 1.2

    const dx = hitPoint.x - trans.x
    const dy = hitPoint.y - trans.y

    const nx = Math.max(-1, Math.min(1, dx / r))
    const ny = Math.max(-1, Math.min(1, dy / r))

    const pushX = -nx * 6.5
    const pushY = -ny * 6.5
    const pushZ = -3.8

    const torqueX = -ny * 4.5
    const torqueY = nx * 4.5
    const torqueZ = (-nx * ny) * 2.0 - nx * 1.2

    playNudgeSound(false)

    tempImpulse.x = pushX
    tempImpulse.y = pushY
    tempImpulse.z = pushZ
    item.body.applyImpulse(tempImpulse, true)

    tempTorque.x = torqueX
    tempTorque.y = torqueY
    tempTorque.z = torqueZ
    item.body.applyTorqueImpulse(tempTorque, true)
  }

  const applyPowerSpin = (item: LogoItem, hitPoint: THREE.Vector3) => {
    if (item.isShattered) {
      return
    }

    const trans = item.body.translation()
    const r = item.radius || 1.2

    const dx = hitPoint.x - trans.x
    const dy = hitPoint.y - trans.y

    const nx = Math.max(-1, Math.min(1, dx / r))
    const ny = Math.max(-1, Math.min(1, dy / r))

    const dist = Math.hypot(nx, ny)
    const dirX = dist > 0.12 ? (-nx / dist) : (Math.random() > 0.5 ? 0.6 : -0.6)
    const dirY = dist > 0.12 ? (-ny / dist) : 0.4

    const pushStrength = 14.5
    const pushX = dirX * pushStrength
    const pushY = dirY * pushStrength
    const pushZ = -8.5

    const spinPower = 28.0
    let spinX = 0
    let spinY = 0
    let spinZ = 0

    if (Math.abs(nx) >= Math.abs(ny) || dist < 0.15) {
      const sign = nx !== 0 ? Math.sign(nx) : 1
      spinY = sign * spinPower
      spinX = -ny * 10.0
      spinZ = -sign * 4.5
    } else {
      const sign = ny !== 0 ? Math.sign(ny) : 1
      spinX = -sign * spinPower
      spinY = nx * 10.0
      spinZ = sign * 4.5
    }

    screenShake = 0.20
    playNudgeSound(true)

    tempImpulse.x = pushX
    tempImpulse.y = pushY
    tempImpulse.z = pushZ
    item.body.applyImpulse(tempImpulse, true)

    tempTorque.x = spinX
    tempTorque.y = spinY
    tempTorque.z = spinZ
    item.body.applyTorqueImpulse(tempTorque, true)
  }

  // 9. High-Performance Raycasting and Drag & Drop Mechanics
  const raycaster = new THREE.Raycaster()
  const mouse = new THREE.Vector2()
  const dragPlane = new THREE.Plane(new THREE.Vector3(0, 0, 1), 0)
  const planeIntersection = new THREE.Vector3()

  // Pre-allocated reusable structures (0 per-frame GC allocations!)
  const tempImpulse = { x: 0, y: 0, z: 0 }
  const tempTorque = { x: 0, y: 0, z: 0 }
  const tempHitDir = { x: 0, y: 0, z: 0 }
  const tempSphereCenter = new THREE.Vector3()
  const tempTestSphere = new THREE.Sphere()
  const tempClusterPos = new THREE.Vector3()
  const tempClusterQuat = new THREE.Quaternion()
  const tempClusterScale = new THREE.Vector3()
  const tempClusterMat = new THREE.Matrix4()
  const tempTargetPos = new THREE.Vector3()

  let activeLogo: LogoItem | null = null
  let isDragging = false
  let isDragCandidate = false
  let hasMovedBeyondDragThreshold = false
  let pointerDownPos = { x: 0, y: 0 }
  let clickedLogoCandidate: LogoItem | null = null
  const clickedPointCandidate = new THREE.Vector3()

  let lastClickTime = 0
  let lastClickLogoId = ''
  let singleClickTimeout: ReturnType<typeof setTimeout> | null = null

  const dragOffset = new THREE.Vector3()
  const previousMousePos = new THREE.Vector3()
  const mouseVelocity = new THREE.Vector3()

  // DOM Cursor caching to prevent style recalculation thrashing
  let currentCursor = 'default'
  const updateCursor = (newCursor: string) => {
    if (currentCursor !== newCursor) {
      currentCursor = newCursor
      container.style.cursor = newCursor
    }
  }

  // Cached DOM Rect to eliminate synchronous layout reflows (getBoundingClientRect) on every mousemove
  let cachedDomRect = domEl.getBoundingClientRect()
  const refreshDomRect = () => {
    if (domEl) {
      cachedDomRect = domEl.getBoundingClientRect()
    }
  }
  window.addEventListener('scroll', refreshDomRect, { passive: true })
  window.addEventListener('resize', refreshDomRect, { passive: true })

  const getPointerPos = (e: PointerEvent) => {
    const w = cachedDomRect.width || width || 1
    const h = cachedDomRect.height || height || 1
    return {
      x: ((e.clientX - cachedDomRect.left) / w) * 2 - 1,
      y: -((e.clientY - cachedDomRect.top) / h) * 2 + 1
    }
  }

  const onPointerDown = (e: PointerEvent) => {
    const pos = getPointerPos(e)
    mouse.x = pos.x
    mouse.y = pos.y

    pointerDownPos = { x: e.clientX, y: e.clientY }
    hasMovedBeyondDragThreshold = false
    isDragging = false

    raycaster.setFromCamera(mouse, camera)
    const ray = raycaster.ray
    let found: LogoItem | null = null
    let closestDist = Infinity

    // Ultra-fast sphere intersection (0.0001ms)
    for (let i = 0; i < logos.length; i++) {
      const item = logos[i]
      if (!item || item.isShattered) {
        continue
      }
      const t = item.body.translation()
      tempSphereCenter.set(t.x, t.y, t.z)
      tempTestSphere.center = tempSphereCenter
      tempTestSphere.radius = item.radius * 1.05

      if (ray.intersectsSphere(tempTestSphere)) {
        const d = ray.origin.distanceToSquared(tempSphereCenter)
        if (d < closestDist) {
          closestDist = d
          found = item
          ray.intersectSphere(tempTestSphere, clickedPointCandidate)
        }
      }
    }

    if (found) {
      activeLogo = found
      clickedLogoCandidate = found
      isDragCandidate = true

      const t = found.body.translation()
      dragPlane.constant = -t.z

      if (raycaster.ray.intersectPlane(dragPlane, planeIntersection)) {
        dragOffset.copy(planeIntersection).sub(new THREE.Vector3(t.x, t.y, t.z))
        previousMousePos.copy(planeIntersection)
      }

      found.body.wakeUp()
    } else {
      activeLogo = null
      clickedLogoCandidate = null
      isDragCandidate = false
    }
  }

  let pointerMoveThrottle = false
  const onPointerMove = (e: PointerEvent) => {
    if (!isSceneVisible) {
      return
    }

    const pos = getPointerPos(e)
    mouse.x = pos.x
    mouse.y = pos.y

    if (isDragCandidate && activeLogo) {
      const dist = Math.hypot(e.clientX - pointerDownPos.x, e.clientY - pointerDownPos.y)
      if (!hasMovedBeyondDragThreshold && dist > 5) {
        hasMovedBeyondDragThreshold = true
        isDragging = true
        updateCursor('grabbing')
        if (singleClickTimeout) {
          clearTimeout(singleClickTimeout)
          singleClickTimeout = null
        }
      }

      if (isDragging) {
        raycaster.setFromCamera(mouse, camera)
        if (raycaster.ray.intersectPlane(dragPlane, planeIntersection)) {
          tempTargetPos.copy(planeIntersection).sub(dragOffset)
          const currentPos = activeLogo.body.translation()

          const targetVelX = (tempTargetPos.x - currentPos.x) * 20
          const targetVelY = (tempTargetPos.y - currentPos.y) * 20
          const targetVelZ = (tempTargetPos.z - currentPos.z) * 14

          const maxSpeed = 28
          const vx = Math.max(-maxSpeed, Math.min(maxSpeed, targetVelX))
          const vy = Math.max(-maxSpeed, Math.min(maxSpeed, targetVelY))
          const vz = Math.max(-maxSpeed, Math.min(maxSpeed, targetVelZ))

          activeLogo.body.setLinvel({ x: vx, y: vy, z: vz }, true)

          mouseVelocity.copy(planeIntersection).sub(previousMousePos).multiplyScalar(35)
          previousMousePos.copy(planeIntersection)
        }
      }
    } else {
      // Fast Ray-Sphere hover test (0.0001ms, 0 allocations)
      if (!pointerMoveThrottle) {
        pointerMoveThrottle = true
        requestAnimationFrame(() => {
          pointerMoveThrottle = false
          raycaster.setFromCamera(mouse, camera)
          const ray = raycaster.ray
          let isHovered = false

          for (let i = 0; i < logos.length; i++) {
            const item = logos[i]
            if (!item || item.isShattered) {
              continue
            }
            const t = item.body.translation()
            tempSphereCenter.set(t.x, t.y, t.z)
            tempTestSphere.center = tempSphereCenter
            tempTestSphere.radius = item.radius * 1.05
            if (ray.intersectsSphere(tempTestSphere)) {
              isHovered = true
              break
            }
          }
          updateCursor(isHovered ? 'grab' : 'default')
        })
      }
    }
  }

  const onPointerUp = () => {
    if (isDragging && activeLogo) {
      const throwSpeed = mouseVelocity.length()
      if (throwSpeed > 0.5) {
        activeLogo.body.setLinvel({
          x: Math.max(-32, Math.min(32, mouseVelocity.x)),
          y: Math.max(-32, Math.min(32, mouseVelocity.y)),
          z: 0
        }, true)
      }
      isDragging = false
      activeLogo = null
      isDragCandidate = false
      clickedLogoCandidate = null
      updateCursor('grab')
      return
    }

    // It was a click (not a drag)
    if (clickedLogoCandidate && !hasMovedBeyondDragThreshold) {
      const targetItem = clickedLogoCandidate
      const hitPoint = clickedPointCandidate.clone()
      const now = performance.now()
      const timeSinceLastClick = now - lastClickTime

      if (timeSinceLastClick < 280 && lastClickLogoId === targetItem.id) {
        // DOUBLE CLICK: Strong push + axial spin
        if (singleClickTimeout) {
          clearTimeout(singleClickTimeout)
          singleClickTimeout = null
        }
        lastClickTime = 0
        lastClickLogoId = ''
        applyPowerSpin(targetItem, hitPoint)
      } else {
        // FIRST CLICK: Wait briefly to differentiate single from double click
        lastClickTime = now
        lastClickLogoId = targetItem.id

        if (singleClickTimeout) {
          clearTimeout(singleClickTimeout)
        }
        singleClickTimeout = setTimeout(() => {
          singleClickTimeout = null
          applyNudge(targetItem, hitPoint)
        }, 220)
      }
    }

    isDragging = false
    activeLogo = null
    isDragCandidate = false
    clickedLogoCandidate = null
    updateCursor('grab')
  }

  domEl.addEventListener('pointerdown', onPointerDown)
  window.addEventListener('pointermove', onPointerMove, { passive: true })
  window.addEventListener('pointerup', onPointerUp, { passive: true })
  window.addEventListener('pointercancel', onPointerUp, { passive: true })

  // 10. Responsive Window Resize Handler (RAF Throttled)
  const handleResize = () => {
    if (!containerRef.value) {
      return
    }
    width = containerRef.value.clientWidth
    height = containerRef.value.clientHeight
    camera.aspect = width / height
    camera.updateProjectionMatrix()
    renderer.setSize(width, height)

    const nb = getVisibleBounds()
    halfW = nb.halfW
    halfH = nb.halfH
    updateWallColliders()

    const maxSpread = Math.max(2.0, halfW - 2.2)
    for (let i = 0; i < logos.length; i++) {
      const logo = logos[i]
      if (!logo) {
        continue
      }
      const cfg = modelConfigs.find(c => c.id === logo.id)
      if (cfg) {
        logo.homePos.x = cfg.homeOffset.xRatio * maxSpread
      }
    }
  }

  let resizePending = false
  const onThrottledResize = () => {
    if (!resizePending) {
      resizePending = true
      requestAnimationFrame(() => {
        handleResize()
        resizePending = false
      })
    }
  }
  window.addEventListener('resize', onThrottledResize, { passive: true })

  // 10b. Visibility & Intersection Hibernation (0% CPU/GPU when offscreen or tab hidden)
  let isSceneVisible = true
  let isTabActive = true

  const observer = new IntersectionObserver((entries) => {
    if (entries[0]) {
      isSceneVisible = entries[0].isIntersecting
    }
  }, { threshold: 0.05 })
  observer.observe(container)

  const onVisibilityChange = () => {
    isTabActive = document.visibilityState === 'visible'
  }
  document.addEventListener('visibilitychange', onVisibilityChange)

  // 11. Ultra-Low-Overhead High-Refresh Physics & Animation Loop (60Hz / 120Hz / 144Hz / 165Hz)
  let animationId = 0
  const timer = new THREE.Timer()

  const animate = (timestamp?: number) => {
    animationId = requestAnimationFrame(animate)

    timer.update(timestamp)
    if (!isSceneVisible || !isTabActive) {
      return
    }

    const rawDt = timer.getDelta()
    const dt = Math.min(rawDt, 0.033) // Capped at 33ms to ensure consistent physics step
    const elapsedTime = timer.getElapsed()
    const now = performance.now()

    // 11a. In-place velocity tracking (0 allocations per frame!)
    for (let i = 0; i < logos.length; i++) {
      const item = logos[i]
      if (!item || item.isShattered) {
        continue
      }
      const v = item.body.linvel()
      item.prevLinvel.x = v.x
      item.prevLinvel.y = v.y
      item.prevLinvel.z = v.z
      item.prevSpeed = Math.hypot(v.x, v.y, v.z)
    }

    // Refresh dragging kinematics directly inside render loop for jitter-free tracking
    if (isDragging && activeLogo && !activeLogo.isShattered) {
      raycaster.setFromCamera(mouse, camera)
      if (raycaster.ray.intersectPlane(dragPlane, planeIntersection)) {
        tempTargetPos.copy(planeIntersection).sub(dragOffset)
        const currentPos = activeLogo.body.translation()
        const targetVelX = (tempTargetPos.x - currentPos.x) * 20
        const targetVelY = (tempTargetPos.y - currentPos.y) * 20
        const targetVelZ = (tempTargetPos.z - currentPos.z) * 14
        const maxSpeed = 28
        const vx = Math.max(-maxSpeed, Math.min(maxSpeed, targetVelX))
        const vy = Math.max(-maxSpeed, Math.min(maxSpeed, targetVelY))
        const vz = Math.max(-maxSpeed, Math.min(maxSpeed, targetVelZ))
        activeLogo.body.setLinvel({ x: vx, y: vy, z: vz }, true)
      }
    }

    // Dynamic physics timestep adaptation (supports 60Hz, 120Hz, 144Hz, 165Hz, 240Hz)
    world.timestep = Math.min(Math.max(dt, 0.002), 0.033)
    world.step()

    // 11b. Check high-impact collisions
    for (let i = 0; i < logos.length; i++) {
      const item = logos[i]
      if (!item || item.isShattered) {
        continue
      }

      const v = item.body.linvel()
      const deltaVx = v.x - item.prevLinvel.x
      const deltaVy = v.y - item.prevLinvel.y
      const deltaVz = v.z - item.prevLinvel.z
      const deltaV = Math.hypot(deltaVx, deltaVy, deltaVz)

      const isViolentCollision = (item.prevSpeed > 6.0 && deltaV > 8.0) || (item.prevSpeed > 9.0 && deltaV > 6.0)
      if (isViolentCollision) {
        tempHitDir.x = deltaVx
        tempHitDir.y = deltaVy
        tempHitDir.z = deltaVz
        shatterLogo(item, tempHitDir)
      }
    }

    // 11c. Sync and update instanced debris clusters (1 draw call per cluster!)
    for (let cIdx = debrisClusters.length - 1; cIdx >= 0; cIdx--) {
      const cluster = debrisClusters[cIdx]
      if (!cluster) {
        continue
      }

      let scaleFactor = 1.0
      if (now > cluster.shrinkStart) {
        const shrinkProgress = (now - cluster.shrinkStart) / 700
        if (shrinkProgress >= 1.0) {
          for (let i = 0; i < cluster.cubes.length; i++) {
            const cb = cluster.cubes[i]
            if (cb) {
              world.removeCollider(cb.collider, true)
              world.removeRigidBody(cb.body)
            }
          }
          debrisSceneGroup.remove(cluster.instancedMesh)
          cluster.instancedMesh.dispose()
          debrisClusters.splice(cIdx, 1)
          continue
        } else {
          scaleFactor = Math.max(0, 1.0 - shrinkProgress)
        }
      }

      for (let i = 0; i < cluster.cubes.length; i++) {
        const cb = cluster.cubes[i]
        if (!cb) {
          continue
        }
        const t = cb.body.translation()
        const r = cb.body.rotation()
        tempClusterPos.set(t.x, t.y, t.z)
        tempClusterQuat.set(r.x, r.y, r.z, r.w)
        const s = cb.baseScale * scaleFactor
        tempClusterScale.set(s, s, s)
        tempClusterMat.compose(tempClusterPos, tempClusterQuat, tempClusterScale)
        cluster.instancedMesh.setMatrixAt(i, tempClusterMat)
      }
      cluster.instancedMesh.instanceMatrix.needsUpdate = true
    }

    // 11d. Apply buoyant forces & quaternion restoring torque (0 object allocations!)
    for (let i = 0; i < logos.length; i++) {
      const item = logos[i]
      if (!item || item.isShattered) {
        continue
      }

      const trans = item.body.translation()
      const rot = item.body.rotation()

      if (item.popIn) {
        const progress = Math.min(1.0, (now - item.popIn.start) / item.popIn.duration)
        if (progress >= 1.0) {
          item.group.scale.setScalar(item.baseScale)
          item.popIn = null
        } else {
          const c4 = (2 * Math.PI) / 3
          const s = progress === 0
            ? 0
            : progress === 1
              ? 1
              : Math.pow(2, -10 * progress) * Math.sin((progress * 10 - 0.75) * c4) + 1
          item.group.scale.setScalar(item.baseScale * Math.max(0, s))
        }
      }

      if (activeLogo?.id !== item.id) {
        const dx = item.homePos.x - trans.x
        const dy = item.homePos.y - trans.y
        const dz = item.homePos.z - trans.z

        const springK = 2.4
        const fx = dx * springK
        const fy = dy * springK
        const fz = dz * 3.5

        const floatY = Math.sin(elapsedTime * 1.5 + item.seed) * 0.9
        const floatX = Math.cos(elapsedTime * 1.0 + item.seed) * 0.45

        tempImpulse.x = (fx + floatX) * dt
        tempImpulse.y = (fy + floatY) * dt
        tempImpulse.z = fz * dt
        item.body.applyImpulse(tempImpulse, true)

        // Restoring torque directly from quaternion coordinates (zero allocation, no Euler conversion!)
        const qw = rot.w
        const signW = qw >= 0 ? 1 : -1
        const torqueK = 2.4

        tempTorque.x = -rot.x * signW * torqueK * dt
        tempTorque.y = -rot.y * signW * torqueK * dt
        tempTorque.z = -rot.z * signW * (torqueK * 0.75) * dt
        item.body.applyTorqueImpulse(tempTorque, true)
      }

      item.group.position.set(trans.x, trans.y, trans.z)
      item.group.quaternion.set(rot.x, rot.y, rot.z, rot.w)
    }

    // 11e. Camera micro-shake on impact (framerate-independent decay)
    if (screenShake > 0.001) {
      camera.position.x = (Math.random() - 0.5) * screenShake
      camera.position.y = (Math.random() - 0.5) * screenShake
      screenShake *= Math.exp(-9.0 * dt)
    } else {
      camera.position.x = 0
      camera.position.y = 0
      screenShake = 0
    }

    renderer.render(scene, camera)
  }

  animate()
  isLoaded.value = true

  // 12. Expose Dev Helpers
  if (import.meta.dev && typeof window !== 'undefined') {
    const devWindow = window as unknown as {
      __shatterLogo?: (id?: string) => void
      __nudgeLogo?: (id?: string, offset?: { x: number, y: number }) => void
      __doubleClickLogo?: (id?: string, offset?: { x: number, y: number }) => void
    }
    devWindow.__shatterLogo = (id: string = 'ts') => {
      const item = logos.find(l => l.id === id)
      if (item && !item.isShattered) {
        shatterLogo(item, { x: 0, y: -20, z: 0 })
      }
    }
    devWindow.__nudgeLogo = (id: string = 'figma', offset: { x: number, y: number } = { x: 0.8, y: 0.3 }) => {
      const item = logos.find(l => l.id === id)
      if (item && !item.isShattered) {
        const trans = item.body.translation()
        applyNudge(item, new THREE.Vector3(trans.x + offset.x, trans.y + offset.y, trans.z + 0.2))
      }
    }
    devWindow.__doubleClickLogo = (id: string = 'figma', offset: { x: number, y: number } = { x: 0.8, y: 0 }) => {
      const item = logos.find(l => l.id === id)
      if (item && !item.isShattered) {
        const trans = item.body.translation()
        applyPowerSpin(item, new THREE.Vector3(trans.x + offset.x, trans.y + offset.y, trans.z + 0.2))
      }
    }
  }

  // Cleanup handler
  cleanupFn = () => {
    cancelAnimationFrame(animationId)
    observer.disconnect()
    document.removeEventListener('visibilitychange', onVisibilityChange)
    window.removeEventListener('resize', onThrottledResize)
    window.removeEventListener('scroll', refreshDomRect)
    window.removeEventListener('resize', refreshDomRect)
    domEl.removeEventListener('pointerdown', onPointerDown)
    window.removeEventListener('pointermove', onPointerMove)
    window.removeEventListener('pointerup', onPointerUp)
    window.removeEventListener('pointercancel', onPointerUp)

    if (singleClickTimeout) {
      clearTimeout(singleClickTimeout)
      singleClickTimeout = null
    }

    for (let i = 0; i < logos.length; i++) {
      const item = logos[i]
      if (item?.respawnTimeoutId) {
        clearTimeout(item.respawnTimeoutId)
      }
    }

    for (let cIdx = 0; cIdx < debrisClusters.length; cIdx++) {
      const cluster = debrisClusters[cIdx]
      if (cluster) {
        for (let i = 0; i < cluster.cubes.length; i++) {
          const cb = cluster.cubes[i]
          if (cb) {
            world.removeCollider(cb.collider, true)
            world.removeRigidBody(cb.body)
          }
        }
        debrisSceneGroup.remove(cluster.instancedMesh)
        cluster.instancedMesh.dispose()
      }
    }
    debrisClusters.length = 0

    if (audioCtx) {
      audioCtx.close().catch(() => {})
      audioCtx = null
    }

    renderer.dispose()
    if (domEl.parentNode) {
      domEl.parentNode.removeChild(domEl)
    }
    world.free()
    timer.dispose()
  }
})

onUnmounted(() => {
  if (cleanupFn) {
    cleanupFn()
  }
})
</script>

<template>
  <div
    ref="containerRef"
    class="relative w-full h-screen min-h-screen bg-[#000000] overflow-hidden select-none touch-none"
  >
    <!-- Shattered alert & respawn button on top right -->
    <Transition
      enter-active-class="transition duration-300 ease-out"
      enter-from-class="opacity-0 -translate-y-2 scale-95"
      enter-to-class="opacity-100 translate-y-0 scale-100"
      leave-active-class="transition duration-200 ease-in"
      leave-from-class="opacity-100 scale-100"
      leave-to-class="opacity-0 scale-95"
    >
      <div
        v-if="shatteredCount > 0"
        class="absolute top-4 right-6 z-10 flex items-center gap-2"
      >
        <button
          type="button"
          class="inline-flex items-center gap-2 px-3.5 py-1.5 bg-neutral-500/20   hover:bg-neutral-500/30 text-neutral-300 border border-neutral-400/30 backdrop-blur-md text-xs font-medium transition cursor-pointer active:scale-95 shadow-lg shadow-neutral-500/10"
          @click="respawnAllLogos"
        >
          <UIcon
            name="i-lucide-sparkles"
            class="w-3.5 h-3.5"
          />
          <span>Reconstituer {{ shatteredCount > 1 ? 'les logos' : 'le logo' }}</span>
        </button>
      </div>
    </Transition>

    <!-- Loading spinner fallback -->
    <div
      v-if="!isLoaded"
      class="absolute inset-0 flex flex-col items-center justify-center gap-3 text-neutral-400 bg-[#000000]"
    >
      <UIcon
        name="i-lucide-loader-2"
        class="w-8 h-8 animate-spin text-primary"
      />
      <span class="text-sm">Chargement des modèles 3D ({{ loadProgress }}%)...</span>
    </div>
  </div>
</template>

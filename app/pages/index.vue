<script setup lang="ts">
useSeoMeta({
  title: 'Logos 3D Interactifs & GSAP - Nuxt 4',
  description: 'Animation de texte scroll-driven GSAP, grille de points interactive WebGL et logos 3D en lévitation'
})
</script>

<template>
  <main class="w-full max-w-full bg-[#000000] text-white overflow-x-hidden">
    <!-- Section 1: GSAP Scroll-driven text reveal -->
    <ClientOnly>
      <ScrollTextSection />
    </ClientOnly>

    <!-- Section 2: Interactive Dot Grid Waves with Title -->
    <ClientOnly>
      <DotGridWaveSection />
    </ClientOnly>

    <!-- Section 3: Interactive 3D Floating Logos -->
    <section class="relative w-full h-screen min-h-screen overflow-hidden bg-[#000000]">
      <ClientOnly>
        <FloatingLogos />
      </ClientOnly>
    </section>

    <!-- Section 4: Asymmetric Bento Grid Showcase -->
    <BentoSection />
  </main>
</template>

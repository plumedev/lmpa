<script setup lang="ts">
import gsap from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'

const triggerRef = ref<HTMLElement | null>(null)
const p1Ref = ref<HTMLElement | null>(null)
const p2Ref = ref<HTMLElement | null>(null)
const scrollHintRef = ref<HTMLElement | null>(null)

const paragraph1Text = 'I love creating high-end interactive, accessible and efficient experiences and products'
const paragraph2Text = 'My profound aspiration is to delicately balance interface, user experience, and aesthetics.'

const paragraph1Words = paragraph1Text.split(' ')
const paragraph2Words = paragraph2Text.split(' ')

let ctx: gsap.Context | null = null

onMounted(() => {
  if (typeof window === 'undefined') {
    return
  }

  gsap.registerPlugin(ScrollTrigger)

  ctx = gsap.context(() => {
    const paragraph1Elements = p1Ref.value?.querySelectorAll('span')
    const paragraph2Elements = p2Ref.value?.querySelectorAll('span')

    if (!triggerRef.value || !paragraph1Elements || !paragraph2Elements) {
      return
    }

    const tl = gsap.timeline({
      scrollTrigger: {
        trigger: triggerRef.value,
        start: 'top top',
        end: '+=200%',
        pin: true,
        scrub: 0.8,
        anticipatePin: 1
      }
    })

    if (scrollHintRef.value) {
      tl.to(scrollHintRef.value, {
        opacity: 0,
        y: -10,
        duration: 0.1,
        ease: 'power1.out'
      }, 0)
    }

    tl.to(paragraph1Elements, {
      color: '#ffffff',
      opacity: 1,
      duration: 0.5,
      stagger: 0.25,
      ease: 'none'
    }, 0.05)

    tl.to(paragraph2Elements, {
      color: '#00DC82',
      opacity: 1,
      duration: 0.5,
      stagger: 0.25,
      ease: 'none'
    }, '+=0.1')

    tl.to({}, { duration: 0.4 })
  }, triggerRef.value || undefined)
})

onUnmounted(() => {
  if (ctx) {
    ctx.revert()
    ctx = null
  }
})
</script>

<template>
  <section
    ref="triggerRef"
    class="relative w-full min-h-screen text-white flex flex-col justify-center items-center overflow-hidden px-6 md:px-16 lg:px-24 select-none"
  >
    <div class="w-full max-w-4xl mx-auto flex flex-col justify-center">
      <p
        ref="p1Ref"
        class="text-3xl sm:text-4xl md:text-5xl lg:text-[54px] font-normal leading-[1.26] tracking-tight"
      >
        <span
          v-for="(word, index) in paragraph1Words"
          :key="'p1-' + index"
          class="inline-block mr-[0.28em] text-[#333336] opacity-30 will-change-[color,opacity]"
        >
          {{ word }}
        </span>
      </p>

      <p
        ref="p2Ref"
        class="text-3xl sm:text-4xl md:text-5xl lg:text-[54px] font-normal leading-[1.26] tracking-tight mt-8 md:mt-12"
      >
        <span
          v-for="(word, index) in paragraph2Words"
          :key="'p2-' + index"
          class="inline-block mr-[0.28em] text-[#333336] opacity-30 will-change-[color,opacity]"
        >
          {{ word }}
        </span>
      </p>
    </div>

    <div
      id="scroll-hint"
      ref="scrollHintRef"
      class="absolute bottom-8 left-1/2 -translate-x-1/2 flex flex-col items-center gap-1.5 text-neutral-500 text-[11px] tracking-widest uppercase transition-opacity"
    >
      <span>Scroll</span>
      <UIcon
        name="i-lucide-chevron-down"
        class="w-4 h-4 animate-bounce text-neutral-400"
      />
    </div>
  </section>
</template>

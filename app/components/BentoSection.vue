<script setup lang="ts">
interface BentoItem {
  id: string
  title: string
  subtitle: string
  image: string
}

// Configuration simple: chaque carte a un titre, un sous-titre et son image de fond
const bentoItems: Record<string, BentoItem> = {
  ecommerce: {
    id: 'ecommerce',
    title: 'E-commerce expertises',
    subtitle: 'Integrations &\nFront-End developments',
    image: '/images/bento/groupe_ldlc_dark.svg'
  },
  algorigin: {
    id: 'algorigin',
    title: 'From big and small companies',
    subtitle: 'WordPress E-commerce developments for Algorigin CH',
    image: '/images/bento/algorigin_illustration.png'
  },
  nemeio: {
    id: 'nemeio',
    title: 'User interface & experiences',
    subtitle: 'VueJS & TypeScript developments for\nthe fully customisable Keyboard Nemeio app',
    image: '/images/bento/nemeio_illustration.png'
  },
  lightsaber: {
    id: 'lightsaber',
    title: 'Design and tools serving beautiful stories',
    subtitle: 'Ionic & Angular iOS/Android mobile developments\nfor realistic connected lightsaber',
    image: '/images/bento/solaari_illustration.png'
  }
}
</script>

<template>
  <section class="relative w-full bg-[#000000] text-white pt-0 pb-16 md:pb-24 px-4 sm:px-6 md:px-12 lg:px-16 overflow-hidden">
    <div class="max-w-[1320px] mx-auto">
      <!-- Asymmetric Bento Grid matching screenshot layout -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-5 lg:gap-6 items-stretch">
        <!-- ================= LEFT COLUMN ================= -->
        <div class="flex flex-col gap-5 lg:gap-6 justify-between">
          <!-- Top Row: Spacer (left) + Card 1 (right) -->
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-5 lg:gap-6">
            <!-- Empty Spacer keeping top-left breathable as in screenshot -->
            <div class="hidden sm:block pointer-events-none" />

            <!-- CARD 1: E-COMMERCE EXPERTISES -->
            <div class="relative h-[320px] rounded-lg bg-[#121214] overflow-hidden flex flex-col p-6 sm:p-7">
              <!-- Card Header -->
              <div>
                <h3 class="text-xl sm:text-[22px] font-semibold text-white tracking-tight leading-snug">
                  {{ bentoItems.ecommerce?.title }}
                </h3>
                <p class="text-xs sm:text-[13px] text-neutral-400 mt-1.5 whitespace-pre-line leading-relaxed font-normal">
                  {{ bentoItems.ecommerce?.subtitle }}
                </p>
              </div>

              <!-- Logo centered on X and Y, 2/3 width -->
              <div class="flex-1 min-h-0 flex items-center justify-center py-2">
                <img
                  :src="bentoItems.ecommerce?.image"
                  :alt="bentoItems.ecommerce?.title"
                  class="w-2/3 max-h-full object-contain"
                >
              </div>
            </div>
          </div>

          <!-- CARD 2: FROM BIG AND SMALL COMPANIES -->
          <div class="relative h-[560px] sm:h-[600px] lg:h-[620px] rounded-lg bg-[#121214] overflow-hidden flex flex-col justify-between p-7 sm:p-9">
            <!-- Background Image -->
            <img
              :src="bentoItems.algorigin?.image"
              :alt="bentoItems.algorigin?.title"
              class="absolute inset-0 w-full h-full object-cover"
            >
            <!-- Gradient Overlay for contrast -->
            <div class="absolute inset-0 pointer-events-none" />

            <!-- Card Header -->
            <div class="relative z-10">
              <h3 class="text-2xl sm:text-[26px] font-semibold text-white tracking-tight leading-snug">
                {{ bentoItems.algorigin?.title }}
              </h3>
              <p class="text-xs sm:text-[13px]  mt-1.5 leading-relaxed font-normal">
                {{ bentoItems.algorigin?.subtitle }}
              </p>
            </div>
          </div>
        </div>

        <!-- ================= RIGHT COLUMN ================= -->
        <div class="flex flex-col gap-5 lg:gap-6 justify-between">
          <!-- CARD 3: USER INTERFACE & EXPERIENCES -->
          <div class="relative h-[560px] sm:h-[600px] lg:h-[620px] rounded-lg bg-[#121214] overflow-hidden flex flex-col p-7 sm:p-9 pb-0">
            <!-- Card Header -->
            <div>
              <h3 class="text-2xl sm:text-[26px] font-semibold text-white tracking-tight leading-snug">
                {{ bentoItems.nemeio?.title }}
              </h3>
              <p class="text-xs sm:text-[13px] text-neutral-400 mt-1.5 whitespace-pre-line leading-relaxed font-normal">
                {{ bentoItems.nemeio?.subtitle }}
              </p>
            </div>

            <!-- Image placed below the title -->
            <div class="flex-1 min-h-0 flex items-center justify-center mt-4 sm:mt-6 overflow-hidden">
              <img
                :src="bentoItems.nemeio?.image"
                :alt="bentoItems.nemeio?.title"
                class="w-full h-full object-contain object-bottom"
              >
            </div>
          </div>

          <!-- CARD 4: DESIGN AND TOOLS -->
          <div class="relative h-[320px] rounded-lg bg-[#121214] overflow-hidden flex flex-col justify-between p-6 sm:p-7">
            <!-- Background Image -->
            <img
              :src="bentoItems.lightsaber?.image"
              :alt="bentoItems.lightsaber?.title"
              class="absolute inset-0 w-full h-full object-cover"
            >
            <!-- Gradient Overlay for contrast -->
            <div class="absolute inset-0 pointer-events-none" />

            <!-- Card Header -->
            <div class="relative z-10">
              <h3 class="text-xl sm:text-[22px] font-semibold text-white tracking-tight leading-snug">
                {{ bentoItems.lightsaber?.title }}
              </h3>
              <p class="text-xs sm:text-[13px]  mt-1.5 whitespace-pre-line leading-relaxed font-normal">
                {{ bentoItems.lightsaber?.subtitle }}
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

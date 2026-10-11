uniform float uTime;
uniform vec2 uMouse;
uniform vec2 uMouseDir;
uniform float uMouseActive;
uniform float uMouseSpeed;
uniform vec4 uWakePos[32]; // x, y, birthTime, speed
uniform vec4 uWakeVec[32]; // dirX, dirY, normX, normY
uniform vec4 uShockwaves[8]; // x, y, birthTime, strength
uniform vec4 uShockParams;   // speed, amp, width, duration
uniform float uShockBrightness;
uniform float uPixelRatio;

uniform vec2 uSpeedTuning;
uniform vec4 uHullDim;
uniform vec4 uHullDyn;
uniform vec4 uWakeLine;
uniform vec4 uWakeExp;
uniform vec2 uChannel;
uniform vec4 uWakeLimits;
uniform vec4 uRenderParams;

attribute vec3 basePos;
varying float vBrightness;

void main() {
  vec3 pos = basePos;
  vec2 totalDisplacement = vec2(0.0);
  float totalBrightness = 0.0;

  // Normalisation de la vitesse globale (avec limite stricte)
  float cursorSpeedNorm = clamp((uMouseSpeed - uSpeedTuning.x) / max(1.0, uSpeedTuning.y - uSpeedTuning.x), 0.0, 1.0);

  // 1. ZONE "BATEAU" (capsule blanche orientée : curseur à la proue, coque vers l'arrière)
  if (uMouseActive > 0.5) {
    vec2 mDir = length(uMouseDir) > 0.01 ? normalize(uMouseDir) : vec2(1.0, 0.0);

    // Dimensions de la coque du bateau adaptées à la vitesse
    float hullLength = mix(uHullDim.x, uHullDim.y, cursorSpeedNorm); // Longueur de la zone bateau
    float hullRadius = mix(uHullDim.z, uHullDim.w, cursorSpeedNorm); // Demi-largeur de la coque

    // Axe de la capsule : proue au niveau de la souris, poupe vers l'arrière
    vec2 bowP = uMouse + mDir * 4.0;
    vec2 sternP = uMouse - mDir * hullLength;
    vec2 segAxis = sternP - bowP;
    float segLen2 = dot(segAxis, segAxis);

    // Projection sur l'axe du bateau
    float tSeg = clamp(dot(basePos.xy - bowP, segAxis) / max(0.001, segLen2), 0.0, 1.0);
    vec2 closestOnHull = bowP + tSeg * segAxis;

    float distToHull = distance(basePos.xy, closestOnHull);
    float hullInfluenceRadius = hullRadius + 14.0;

    if (distToHull < hullInfluenceRadius && distToHull > 0.001) {
      float hullFactor = 1.0 - (distToHull / hullInfluenceRadius);
      float smoothHull = hullFactor * hullFactor * (3.0 - 2.0 * hullFactor);
      vec2 hullPushDir = normalize(basePos.xy - closestOnHull);

      float hullPushAmp = mix(uHullDyn.x, uHullDyn.y, cursorSpeedNorm);
      totalDisplacement += hullPushDir * (smoothHull * hullPushAmp);
      totalBrightness += smoothHull * mix(0.65, uHullDyn.z, cursorSpeedNorm);
    }
  }

  // 2. LE SILLON EN V (les deux traits rouges du schéma partant des flancs de la coque)
  for (int i = 0; i < 32; i++) {
    float birthTime = uWakePos[i].z;
    if (birthTime <= 0.0) continue;

    float speed = uWakePos[i].w;
    // Vitesse normalisée du nœud avec plafond strict
    float speedNorm = clamp((speed - uSpeedTuning.x) / max(1.0, uSpeedTuning.y - uSpeedTuning.x), 0.0, 1.0);

    // Durée de vie du sillage
    float maxAge = mix(uWakeLimits.x, uWakeLimits.y, speedNorm);
    float age = uTime - birthTime;
    if (age < 0.0 || age > maxAge) continue;

    vec2 wakeP = uWakePos[i].xy;
    vec2 fwdDir = uWakeVec[i].xy;
    vec2 latNorm = uWakeVec[i].zw; // perpendicular to trajectory

    vec2 delta = basePos.xy - wakeP;

    // Projection le long de la trajectoire
    float dForward = dot(delta, fwdDir);
    
    // Fenêtre longitudinale par nœud (s'ajuste avec la vitesse pour assurer la continuité)
    float segHalf = mix(24.0, 38.0, speedNorm);
    if (abs(dForward) > segHalf) continue;

    // Profil amorti en cloche le long du segment
    float longProfile = cos((dForward / segHalf) * 1.570796);

    // Projection latérale (gauche / droite de la trajectoire)
    float dLateral = dot(delta, latNorm);
    float absLateral = abs(dLateral);

    // Position latérale des DEUX TRAITS DU V :
    // Ils partent des flancs du bateau et s'écartent vers l'arrière à la vitesse d'onde
    float hullHalfWidth = mix(uHullDim.z, uHullDim.w, speedNorm);
    float vWaveSpeed = mix(uWakeExp.x, uWakeExp.y, speedNorm); // Vitesse d'écartement de l'angle en V
    float lineCenter = hullHalfWidth + age * vWaveSpeed;

    // LIMITE STRICTE DU SILLON
    float corridorLimit = mix(uWakeLimits.z, uWakeLimits.w, speedNorm);
    if (lineCenter > corridorLimit + 10.0) continue;
    if (absLateral > corridorLimit + 18.0) continue;

    // Dissipation temporelle douce
    float ageNorm = age / maxAge;
    float timeDecay = (1.0 - ageNorm) * exp(-age * mix(2.4, 1.5, speedNorm));

    // Sens d'écartement : pousse vers la droite à droite, vers la gauche à gauche
    float side = dLateral >= 0.0 ? 1.0 : -1.0;
    vec2 outwardPush = latNorm * side;

    // PROFIL DU TRAIT DE SILLON (les deux lignes du V)
    float lineWidth = mix(uWakeLine.x, uWakeLine.y, speedNorm);
    float distToLine = abs(absLateral - lineCenter);
    float lineProfile = exp(-pow(distToLine / lineWidth, 2.0));

    // Poussée le long du trait de sillon (écarte les points le long des 2 lignes en V)
    float lineAmp = mix(uWakeLine.z, uWakeLine.w, speedNorm);
    vec2 linePush = outwardPush * (lineProfile * longProfile * timeDecay * lineAmp);

    // Léger canal central intérieur (l'eau calme entre les deux traits du V)
    float innerTrough = smoothstep(lineCenter, 0.0, absLateral) * exp(-pow(absLateral / hullHalfWidth, 2.0));
    float troughAmp = mix(uChannel.x, uChannel.y, speedNorm);
    vec2 troughPush = outwardPush * (innerTrough * longProfile * timeDecay * troughAmp);

    totalDisplacement += linePush + troughPush;

    // Éclairage contrasté : les deux lignes du V ressortent nettement (lumineuses)
    float lineLight = (lineProfile * 0.95 + innerTrough * 0.25) * longProfile * timeDecay * mix(0.75, uWakeExp.z, speedNorm);
    totalBrightness += lineLight;
  }

  // 3. ONDE DE CHOC AU CLIC (front d'onde radial explosif avec crête lumineuse)
  for (int i = 0; i < 8; i++) {
    float sBirth = uShockwaves[i].z;
    if (sBirth <= 0.0) continue;

    float sAge = uTime - sBirth;
    float sDuration = uShockParams.w;
    if (sAge < 0.0 || sAge > sDuration) continue;

    vec2 sPos = uShockwaves[i].xy;
    float sStrength = uShockwaves[i].w;
    float distToShock = distance(basePos.xy, sPos);

    float waveRadius = sAge * uShockParams.x; // Expansion radiale du front d'onde
    float distDiff = distToShock - waveRadius; // Distance par rapport à la crête
    float halfWidth = uShockParams.z;

    if (abs(distDiff) < halfWidth * 2.2 && distToShock > 0.01) {
      // Profil en cloche du front de choc
      float normDist = distDiff / halfWidth;
      float shockEnvelope = exp(-normDist * normDist);

      // Poussée radiale vers l'extérieur au passage du front avec détente élastique
      float shockPulse = shockEnvelope - 0.28 * exp(-pow((distDiff + halfWidth * 0.95) / (halfWidth * 0.75), 2.0));

      // Dissipation naturelle dans le temps et l'espace
      float sAgeNorm = sAge / sDuration;
      float timeDecay = (1.0 - sAgeNorm) * exp(-sAge * 1.5);
      float spaceDecay = 1.0 / sqrt(1.0 + waveRadius * 0.008);
      float totalWeight = timeDecay * spaceDecay * sStrength;

      vec2 shockDir = (basePos.xy - sPos) / distToShock;
      totalDisplacement += shockDir * (shockPulse * uShockParams.y * totalWeight);

      // Anneau lumineux intense marquant le passage de l'onde de choc
      float crestLight = shockEnvelope * totalWeight * uShockBrightness;
      totalBrightness += crestLight;
    }
  }

  // 4. Respiration ambiante subtile
  float ambient = sin(uTime * 1.2 + basePos.x * 0.006 + basePos.y * 0.006) * uRenderParams.w;
  totalBrightness += max(0.0, ambient);

  // 5. GARANTIE MATHÉMATIQUE STRICTE : Plafonnement anti-chaos
  float dispLength = length(totalDisplacement);
  float maxDisplacement = uRenderParams.x;
  if (dispLength > maxDisplacement) {
    totalDisplacement = (totalDisplacement / dispLength) * maxDisplacement;
  }

  pos.xy += totalDisplacement;
  vBrightness = clamp(totalBrightness, 0.0, 1.0);

  vec4 mvPosition = modelViewMatrix * vec4(pos, 1.0);
  gl_Position = projectionMatrix * mvPosition;

  gl_PointSize = (uRenderParams.y + vBrightness * uRenderParams.z) * uPixelRatio;
}

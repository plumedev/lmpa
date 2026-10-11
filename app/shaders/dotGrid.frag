varying float vBrightness;

void main() {
  // Draw smooth antialiased circular dot
  vec2 coord = gl_PointCoord - vec2(0.5);
  float dist = length(coord);
  if (dist > 0.5) discard;

  float alpha = smoothstep(0.5, 0.36, dist);

  // Base dot color: crisp, elegant subtle slate/silver matching screenshot
  vec3 baseColor = vec3(0.38, 0.38, 0.42);
  // Active wave crest: pure bright white
  vec3 activeColor = vec3(1.0, 1.0, 1.0);
  // Subtle peak emerald hue (#00DC82)
  vec3 crestColor = vec3(0.0, 0.86, 0.51);

  vec3 color = mix(baseColor, activeColor, vBrightness);
  if (vBrightness > 0.6) {
    color = mix(color, crestColor, (vBrightness - 0.6) * 0.5);
  }

  float opacity = mix(0.48, 1.0, vBrightness);
  gl_FragColor = vec4(color, alpha * opacity);
}

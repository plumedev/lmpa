import bpy
import mathutils
import math

print("=== Building TypeScript 3D Logo ===")

# 1. Clean scene
bpy.ops.wm.read_factory_settings(use_empty=True)

# 2. Import SVG
svg_path = 'public/ts_2020_test.svg'
bpy.ops.import_curve.svg(filepath=svg_path)

objs = list(bpy.data.objects)
badge_obj = next(o for o in objs if o.dimensions.x > 0.05)
t_obj = next(o for o in objs if 0.025 < o.dimensions.x < 0.05)
s_obj = next(o for o in objs if o.dimensions.x < 0.025)

badge_obj.name = "TS_Badge"
t_obj.name = "TS_Letter_T"
s_obj.name = "TS_Letter_S"

print("Identified objects:", badge_obj.name, t_obj.name, s_obj.name)

# 3. Curve extrusion & bevel settings
# Badge: rounded squircle tile
badge_obj.data.dimensions = '2D'
badge_obj.data.fill_mode = 'BOTH'
badge_obj.data.extrude = 0.0036  # half-depth
badge_obj.data.bevel_depth = 0.0016
badge_obj.data.bevel_resolution = 4

# Letters T & S
for o in [t_obj, s_obj]:
    o.data.dimensions = '2D'
    o.data.fill_mode = 'BOTH'
    o.data.extrude = 0.0018  # half-depth
    o.data.bevel_depth = 0.0006
    o.data.bevel_resolution = 3

# 4. Convert all to MESH
for o in [badge_obj, t_obj, s_obj]:
    bpy.context.view_layer.objects.active = o
    o.select_set(True)
    bpy.ops.object.convert(target='MESH')
    o.select_set(False)

# 5. Measure badge bounds before transforms
badge_xs = [v.co.x for v in badge_obj.data.vertices]
badge_ys = [v.co.y for v in badge_obj.data.vertices]
badge_zs = [v.co.z for v in badge_obj.data.vertices]

min_x, max_x = min(badge_xs), max(badge_xs)
min_y, max_y = min(badge_ys), max(badge_ys)
min_z, max_z = min(badge_zs), max(badge_zs)

cx = (min_x + max_x) / 2.0
cy = (min_y + max_y) / 2.0
cz = (min_z + max_z) / 2.0

badge_width = max_x - min_x
target_width = 2.40
scale_factor = target_width / badge_width

print(f"Badge raw bounds: X=[{min_x:.4f}, {max_x:.4f}], Y=[{min_y:.4f}, {max_y:.4f}], Z=[{min_z:.4f}, {max_z:.4f}]")
print(f"Center XY: ({cx:.4f}, {cy:.4f}), Scale factor: {scale_factor:.3f}")

# 6. Adjust vertex coordinates directly
# For letters:
# badge front face is at Z = max_z (+0.0052).
# letter raw Z is [-0.0024, +0.0024].
# We shift letters so their back face starts at max_z - 0.0006 = 0.0046 (slightly embedded into badge front).
# shift_z = 0.0046 - (-0.0024) = +0.0070.
letter_shift_z = (max_z - 0.0006) - (-0.0024)

for o in [t_obj, s_obj]:
    for v in o.data.vertices:
        v.co.z += letter_shift_z

# Now transform all objects:
# Center XY at (0, 0), keep Z
# Then rotate 90 deg around X so it stands upright in Blender (Z is UP, -Y is FRONT)
# Then scale by scale_factor
#
# Math for rotate 90 deg around X:
# x' = (x - cx) * scale_factor
# y' = -z * scale_factor
# z' = (y - cy) * scale_factor
for o in [badge_obj, t_obj, s_obj]:
    for v in o.data.vertices:
        orig_x = v.co.x
        orig_y = v.co.y
        orig_z = v.co.z
        
        v.co.x = (orig_x - cx) * scale_factor
        v.co.y = -orig_z * scale_factor
        v.co.z = (orig_y - cy) * scale_factor

    o.data.update()

# 7. Materials
mat_blue = bpy.data.materials.new(name="TS_Blue_Mat")
mat_blue.use_nodes = True
bsdf_blue = mat_blue.node_tree.nodes.get("Principled BSDF")
if bsdf_blue:
    # Official TypeScript Blue (#3178C6) in linear sRGB
    bsdf_blue.inputs['Base Color'].default_value = (0.028, 0.182, 0.565, 1.0)
    bsdf_blue.inputs['Roughness'].default_value = 0.20
    bsdf_blue.inputs['Metallic'].default_value = 0.05

mat_white = bpy.data.materials.new(name="TS_White_Mat")
mat_white.use_nodes = True
bsdf_white = mat_white.node_tree.nodes.get("Principled BSDF")
if bsdf_white:
    # Pure White (#FFFFFF)
    bsdf_white.inputs['Base Color'].default_value = (1.0, 1.0, 1.0, 1.0)
    bsdf_white.inputs['Roughness'].default_value = 0.16
    bsdf_white.inputs['Metallic'].default_value = 0.02

badge_obj.data.materials.clear()
badge_obj.data.materials.append(mat_blue)

for o in [t_obj, s_obj]:
    o.data.materials.clear()
    o.data.materials.append(mat_white)

# 8. Smooth shading
for o in [badge_obj, t_obj, s_obj]:
    for p in o.data.polygons:
        p.use_smooth = True

bpy.context.view_layer.update()

# 9. Print final bounds in Blender
for o in [badge_obj, t_obj, s_obj]:
    xs = [v.co.x for v in o.data.vertices]
    ys = [v.co.y for v in o.data.vertices]
    zs = [v.co.z for v in o.data.vertices]
    print(f"Final {o.name}:")
    print(f"  X: {min(xs):.3f} to {max(xs):.3f}")
    print(f"  Y (depth in Blender): {min(ys):.3f} to {max(ys):.3f}")
    print(f"  Z (height in Blender): {min(zs):.3f} to {max(zs):.3f}")

# 10. Export to GLB
output_path = "public/models/typescript.glb"
bpy.ops.export_scene.gltf(
    filepath=output_path,
    export_format='GLB',
    export_apply=True,
    export_materials='EXPORT',
    export_colors=True,
    export_cameras=False,
    export_lights=False
)

print(f"Successfully exported {output_path}!")

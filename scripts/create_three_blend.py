import bpy
import mathutils

print("=== Building Three.js 3D Logo (Triangle Lattice Only, No Badge, No T) ===")

# 1. Clean scene
bpy.ops.wm.read_factory_settings(use_empty=True)

# 2. Import SVG
svg_path = 'public/three_model.svg'
bpy.ops.import_curve.svg(filepath=svg_path)

objs = list(bpy.data.objects)
print("Imported objects count:", len(objs))

triangle_obj = objs[0]
triangle_obj.name = "Three_Triangle"

# 3. Curve extrusion & bevel
triangle_obj.data.dimensions = '2D'
triangle_obj.data.fill_mode = 'BOTH'
triangle_obj.data.extrude = 0.005
triangle_obj.data.bevel_depth = 0.0008
triangle_obj.data.bevel_resolution = 3

# 4. Convert to MESH
bpy.context.view_layer.objects.active = triangle_obj
triangle_obj.select_set(True)
bpy.ops.object.convert(target='MESH')
triangle_obj.select_set(False)

# 5. Measure bounds
xs = [v.co.x for v in triangle_obj.data.vertices]
ys = [v.co.y for v in triangle_obj.data.vertices]
zs = [v.co.z for v in triangle_obj.data.vertices]

min_x, max_x = min(xs), max(xs)
min_y, max_y = min(ys), max(ys)
min_z, max_z = min(zs), max(zs)

cx = (min_x + max_x) / 2.0
cy = (min_y + max_y) / 2.0
cz = (min_z + max_z) / 2.0

width = max_x - min_x
height = max_y - min_y
max_dim = max(width, height)
target_dim = 2.40
scale_factor = target_dim / max_dim

print(f"Triangle dimensions: W={width:.4f}, H={height:.4f}, scale={scale_factor:.3f}")

# 6. Center XY, rotate 90 around X, scale to 2.40
for v in triangle_obj.data.vertices:
    orig_x = v.co.x
    orig_y = v.co.y
    orig_z = v.co.z
    
    v.co.x = (orig_x - cx) * scale_factor
    v.co.y = -(orig_z - cz) * scale_factor
    v.co.z = (orig_y - cy) * scale_factor

triangle_obj.data.update()

# 7. Material
mat_white = bpy.data.materials.new(name="Three_Mat_White")
mat_white.use_nodes = True
bsdf_white = mat_white.node_tree.nodes.get("Principled BSDF")
if bsdf_white:
    bsdf_white.inputs['Base Color'].default_value = (1.0, 1.0, 1.0, 1.0)
    bsdf_white.inputs['Roughness'].default_value = 0.16
    bsdf_white.inputs['Metallic'].default_value = 0.04

triangle_obj.data.materials.clear()
triangle_obj.data.materials.append(mat_white)

# Smooth shading
for p in triangle_obj.data.polygons:
    p.use_smooth = True

bpy.context.view_layer.update()

# 8. Export to GLB
output_path = "public/models/three.glb"
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

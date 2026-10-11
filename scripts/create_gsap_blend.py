import bpy
import mathutils

print("=== Building GSAP 3D Logo (Letters Only, No Badge) ===")

# 1. Clean scene
bpy.ops.wm.read_factory_settings(use_empty=True)

# 2. Import SVG
svg_path = 'public/gsap_model.svg'
bpy.ops.import_curve.svg(filepath=svg_path)

objs = list(bpy.data.objects)
print("Imported objects count:", len(objs))

letters_obj = objs[0]
letters_obj.name = "GSAP_Letters"

# 3. Curve extrusion & bevel
letters_obj.data.dimensions = '2D'
letters_obj.data.fill_mode = 'BOTH'
letters_obj.data.extrude = 0.005
letters_obj.data.bevel_depth = 0.0008
letters_obj.data.bevel_resolution = 3

# 4. Convert to MESH
bpy.context.view_layer.objects.active = letters_obj
letters_obj.select_set(True)
bpy.ops.object.convert(target='MESH')
letters_obj.select_set(False)

# 5. Measure bounds
xs = [v.co.x for v in letters_obj.data.vertices]
ys = [v.co.y for v in letters_obj.data.vertices]
zs = [v.co.z for v in letters_obj.data.vertices]

min_x, max_x = min(xs), max(xs)
min_y, max_y = min(ys), max(ys)
min_z, max_z = min(zs), max(zs)

cx = (min_x + max_x) / 2.0
cy = (min_y + max_y) / 2.0
cz = (min_z + max_z) / 2.0

width = max_x - min_x
height = max_y - min_y

target_width = 2.60
scale_factor = target_width / width

print(f"GSAP letters dimensions: W={width:.4f}, H={height:.4f}, scale={scale_factor:.3f}")

# 6. Center XY, rotate 90 around X, scale
for v in letters_obj.data.vertices:
    orig_x = v.co.x
    orig_y = v.co.y
    orig_z = v.co.z
    
    v.co.x = (orig_x - cx) * scale_factor
    v.co.y = -(orig_z - cz) * scale_factor
    v.co.z = (orig_y - cy) * scale_factor

letters_obj.data.update()

# 7. Material (Rich warm ivory cream #FFFDE8)
mat_cream = bpy.data.materials.new(name="GSAP_Mat_Cream")
mat_cream.use_nodes = True
bsdf_cream = mat_cream.node_tree.nodes.get("Principled BSDF")
if bsdf_cream:
    bsdf_cream.inputs['Base Color'].default_value = (1.0, 0.98, 0.88, 1.0)
    bsdf_cream.inputs['Roughness'].default_value = 0.16
    bsdf_cream.inputs['Metallic'].default_value = 0.04

letters_obj.data.materials.clear()
letters_obj.data.materials.append(mat_cream)

# Smooth shading
for p in letters_obj.data.polygons:
    p.use_smooth = True

bpy.context.view_layer.update()

# 8. Export to GLB
output_path = "public/models/gsap.glb"
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

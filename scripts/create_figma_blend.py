import bpy
import mathutils

print("=== Building Figma 3D Logo (Pure Logo, No Badge) ===")

# 1. Clean scene
bpy.ops.wm.read_factory_settings(use_empty=True)

# 2. Import SVG
svg_path = 'public/figma_model.svg'
bpy.ops.import_curve.svg(filepath=svg_path)

shapes = list(bpy.data.objects)
print("Imported shapes count:", len(shapes))

# 3. Curve extrusion & bevel
for o in shapes:
    o.data.dimensions = '2D'
    o.data.fill_mode = 'BOTH'
    o.data.extrude = 0.006
    o.data.bevel_depth = 0.0012
    o.data.bevel_resolution = 4

# 4. Convert all to MESH
for o in shapes:
    bpy.context.view_layer.objects.active = o
    o.select_set(True)
    bpy.ops.object.convert(target='MESH')
    o.select_set(False)

# 5. Measure combined bounds across all 5 shapes
all_xs = [v.co.x for o in shapes for v in o.data.vertices]
all_ys = [v.co.y for o in shapes for v in o.data.vertices]
all_zs = [v.co.z for o in shapes for v in o.data.vertices]

min_x, max_x = min(all_xs), max(all_xs)
min_y, max_y = min(all_ys), max(all_ys)
min_z, max_z = min(all_zs), max(all_zs)

cx = (min_x + max_x) / 2.0
cy = (min_y + max_y) / 2.0
cz = (min_z + max_z) / 2.0

height = max_y - min_y
target_height = 2.40
scale_factor = target_height / height

print(f"Figma combined size: W={max_x - min_x:.4f}, H={height:.4f}, scale={scale_factor:.3f}")

# 6. Transform vertices: center at (0, 0, 0), rotate 90 around X, scale to 2.40
for o in shapes:
    for v in o.data.vertices:
        orig_x = v.co.x
        orig_y = v.co.y
        orig_z = v.co.z
        
        v.co.x = (orig_x - cx) * scale_factor
        v.co.y = -(orig_z - cz) * scale_factor
        v.co.z = (orig_y - cy) * scale_factor

    o.data.update()

# 7. Identify the 5 shapes by their 3D positions
for o in shapes:
    cen_x = sum(v.co.x for v in o.data.vertices) / len(o.data.vertices)
    cen_z = sum(v.co.z for v in o.data.vertices) / len(o.data.vertices)
    if cen_z > 0.35:
        if cen_x < 0:
            o.name = "Figma_TopLeft"
        else:
            o.name = "Figma_TopRight"
    elif cen_z < -0.35:
        o.name = "Figma_BottomLeft"
    else:
        if cen_x < 0:
            o.name = "Figma_MidLeft"
        else:
            o.name = "Figma_MidRight"

print("Identified shapes:", [o.name for o in shapes])

# 8. PBR Materials
def make_pbr_mat(name, rgba, roughness=0.16, metalness=0.04):
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs['Base Color'].default_value = rgba
        bsdf.inputs['Roughness'].default_value = roughness
        bsdf.inputs['Metallic'].default_value = metalness
    return mat

mat_orange = make_pbr_mat("Figma_Mat_Orange", (0.88, 0.07, 0.01, 1.0)) # #F24E1E
mat_coral = make_pbr_mat("Figma_Mat_Coral", (1.0, 0.16, 0.12, 1.0))    # #FF7262
mat_purple = make_pbr_mat("Figma_Mat_Purple", (0.36, 0.10, 1.0, 1.0))  # #A259FF
mat_blue = make_pbr_mat("Figma_Mat_Blue", (0.01, 0.51, 0.99, 1.0))     # #1ABCFE
mat_green = make_pbr_mat("Figma_Mat_Green", (0.003, 0.62, 0.22, 1.0))  # #0ACF83

mat_map = {
    "Figma_TopLeft": mat_orange,
    "Figma_TopRight": mat_coral,
    "Figma_MidLeft": mat_purple,
    "Figma_MidRight": mat_blue,
    "Figma_BottomLeft": mat_green
}

for o in shapes:
    o.data.materials.clear()
    mat = mat_map.get(o.name, mat_coral)
    o.data.materials.append(mat)

# Smooth shading
for o in shapes:
    for p in o.data.polygons:
        p.use_smooth = True

bpy.context.view_layer.update()

# 9. Export to GLB
output_path = "public/models/figma.glb"
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

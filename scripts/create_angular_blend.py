import bpy
import bmesh
import mathutils

# 1. Clear existing scene
bpy.ops.wm.read_factory_settings(use_empty=True)

# Coordinates matching the official Angular 17 logo in centered space (-1.2 to 1.2)
# Scale factor to make the logo ~2.4 units tall
scale = 2.4 / 24.0

def to_coords(x, y):
    # In SVG: x goes right (0 to 24), y goes down (0 to 24)
    # In 3D: X is right (-1.2 to 1.2), Z is up (-1.2 to 1.2)
    return ((x - 12.0) * scale, (-(y - 12.0)) * scale)

# The 4 polygon pieces
pieces_data = [
    {
        "name": "Angular_LeftWing",
        "coords": [
            to_coords(9.308, 0.0),
            to_coords(0.662, 3.999),
            to_coords(1.476, 16.855)
        ]
    },
    {
        "name": "Angular_RightWing",
        "coords": [
            to_coords(14.692, 0.0),
            to_coords(22.524, 16.855),
            to_coords(23.338, 3.999)
        ]
    },
    {
        "name": "Angular_CenterTriangle",
        "coords": [
            to_coords(8.903, 13.93),
            to_coords(15.101, 13.93),
            to_coords(12.0, 6.396)
        ]
    },
    {
        "name": "Angular_BottomTip",
        "coords": [
            to_coords(16.712, 17.711),
            to_coords(7.288, 17.711),
            to_coords(6.084, 20.627),
            to_coords(12.0, 24.0),
            to_coords(17.916, 20.627)
        ]
    }
]

# Color gradient function matching https://fr.wikipedia.org/wiki/Fichier:Angular_gradient_logo.png
# Gradient flows from Bottom Red -> Center Magenta/Pink -> Top Right Purple/Orchid
def get_gradient_color(x, z):
    # Normalized coords: x in [-1.2, 1.2], z in [-1.2, 1.2]
    # Factor t from 0 (bottom-left) to 1 (top-right)
    nx = (x + 1.2) / 2.4 # 0 to 1
    nz = (z + 1.2) / 2.4 # 0 to 1
    t = max(0.0, min(1.0, nz * 0.72 + nx * 0.28))

    # Color stops
    # 0.00: Fiery Electric Red #FF003C
    # 0.35: Hot Neon Pink #FF1A85
    # 0.70: Electric Violet #C020F5
    # 1.00: Deep Orchid / Royal Purple #7B1FA2
    if t < 0.35:
        f = t / 0.35
        # Red (1.0, 0.0, 0.24) to Hot Pink (1.0, 0.10, 0.52)
        r = 1.0
        g = 0.0 + f * 0.10
        b = 0.24 + f * 0.28
    elif t < 0.70:
        f = (t - 0.35) / 0.35
        # Hot Pink (1.0, 0.10, 0.52) to Electric Violet (0.75, 0.12, 0.96)
        r = 1.0 - f * 0.25
        g = 0.10 + f * 0.02
        b = 0.52 + f * 0.44
    else:
        f = (t - 0.70) / 0.30
        # Electric Violet (0.75, 0.12, 0.96) to Royal Purple (0.48, 0.12, 0.88)
        r = 0.75 - f * 0.27
        g = 0.12
        b = 0.96 - f * 0.08
    return (r, g, b, 1.0)

created_objects = []
depth = 0.36
half_depth = depth / 2.0
bevel_width = 0.045

for piece in pieces_data:
    mesh = bpy.data.meshes.new(piece["name"] + "_Mesh")
    obj = bpy.data.objects.new(piece["name"], mesh)
    bpy.context.collection.objects.link(obj)
    created_objects.append(obj)

    bm = bmesh.new()

    # Create front and back vertices (standing upright: X=width, Y=depth, Z=height)
    verts_front = []
    verts_back = []

    for x, z in piece["coords"]:
        # Front has +half_depth, Back has -half_depth
        v_f = bm.verts.new((x, half_depth, z))
        v_b = bm.verts.new((x, -half_depth, z))
        verts_front.append(v_f)
        verts_back.append(v_b)

    bm.verts.ensure_lookup_table()

    # Front face (counter-clockwise looking from +Y)
    # Looking down -Y into +Y: normal points towards +Y
    bm.faces.new(verts_front)

    # Back face (reversed)
    bm.faces.new(list(reversed(verts_back)))

    # Side faces
    n = len(piece["coords"])
    for i in range(n):
        next_i = (i + 1) % n
        bm.faces.new([
            verts_front[next_i],
            verts_front[i],
            verts_back[i],
            verts_back[next_i]
        ])

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)

    # Add vertex color layer for smooth, continuous gradient across each face
    color_layer = bm.loops.layers.color.new("COLOR_0")
    for face in bm.faces:
        for loop in face.loops:
            vx = loop.vert.co.x
            vz = loop.vert.co.z
            loop[color_layer] = get_gradient_color(vx, vz)

    bm.to_mesh(mesh)
    bm.free()

    # Add Bevel modifier with round segments for smooth pillowed 3D edges
    bevel_mod = obj.modifiers.new(name="Bevel", type='BEVEL')
    bevel_mod.width = bevel_width
    bevel_mod.segments = 4
    bevel_mod.limit_method = 'ANGLE'
    bevel_mod.angle_limit = 0.523599 # 30 deg
    bevel_mod.profile = 0.7

    # Calculate average color for the material base color fallback
    avg_x = sum(c[0] for c in piece["coords"]) / len(piece["coords"])
    avg_z = sum(c[1] for c in piece["coords"]) / len(piece["coords"])
    base_col = get_gradient_color(avg_x, avg_z)

    # Material with PBR sheen matching the Vue logo style
    mat = bpy.data.materials.new(name=piece["name"] + "_Mat")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs['Base Color'].default_value = base_col
        bsdf.inputs['Roughness'].default_value = 0.22
        bsdf.inputs['Metallic'].default_value = 0.05
    obj.data.materials.append(mat)

# Smooth shading
for obj in created_objects:
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    for f in obj.data.polygons:
        f.use_smooth = True

bpy.context.view_layer.update()

# Export to GLB with applied modifiers and vertex colors
output_path = "public/models/angular.glb"
bpy.ops.export_scene.gltf(
    filepath=output_path,
    export_format='GLB',
    export_apply=True,
    export_materials='EXPORT',
    export_colors=True,
    export_cameras=False,
    export_lights=False
)

print(f"Successfully exported {output_path} with upright 3D Angular logo and gradient!")

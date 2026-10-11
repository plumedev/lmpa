import bpy
import mathutils

print("Starting Blender export script...")
print("Existing objects:", [obj.name for obj in bpy.data.objects])

# Remove studio background, camera, lights, spheres, cylinders
for obj in list(bpy.data.objects):
    name_lower = obj.name.lower()
    if 'vue' not in name_lower:
        print(f"Removing non-vue object: {obj.name}")
        bpy.data.objects.remove(obj, do_unlink=True)

vue_objs = [obj for obj in bpy.data.objects if obj.type == 'MESH']
print("Remaining Vue objects:", [obj.name for obj in vue_objs])

if not vue_objs:
    raise Exception("No Vue mesh objects found!")

# Calculate overall bounding box to center at (0, 0, 0)
min_coord = [float('inf')] * 3
max_coord = [float('-inf')] * 3
for obj in vue_objs:
    for v in obj.bound_box:
        world_v = obj.matrix_world @ mathutils.Vector(v)
        for i in range(3):
            min_coord[i] = min(min_coord[i], world_v[i])
            max_coord[i] = max(max_coord[i], world_v[i])

center = mathutils.Vector([(min_coord[i] + max_coord[i]) / 2 for i in range(3)])
print(f"Computed bounding box center: {center}")

# Select all Vue objects and center them
bpy.ops.object.select_all(action='DESELECT')
for obj in vue_objs:
    obj.select_set(True)
    obj.location -= center

bpy.context.view_layer.update()

# Export to GLB with applied modifiers (subsurf!)
output_path = "public/models/vue.glb"
print(f"Exporting to {output_path}...")
bpy.ops.export_scene.gltf(
    filepath=output_path,
    export_format='GLB',
    export_apply=True,
    export_materials='EXPORT',
    export_colors=True,
    export_cameras=False,
    export_lights=False,
    use_selection=True
)
print("Export complete!")

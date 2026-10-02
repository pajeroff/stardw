extends Node2D
class_name GameWorld

signal world_regenerated(new_seed: int, stats: Dictionary)
signal inventory_updated(inventory: Dictionary)

@export var map_width: int = 88
@export var map_height: int = 68
@export var world_seed: int = 20261002

const TILE_SIZE: int = 16
const WORLD_OBJECT_SCENE: PackedScene = preload("res://scenes/world_object.tscn")

@onready var ground_layer: TileMapLayer = $GroundLayer
@onready var decor_layer: TileMapLayer = $DecorLayer
@onready var y_sort_root: Node2D = $YSortRoot
@onready var objects_container: Node2D = $YSortRoot/ObjectsContainer
@onready var player: Player = $YSortRoot/Player
@onready var border_body: StaticBody2D = $MapBorders
@onready var debug_overlay: Node2D = $DebugCollisionOverlay

var tile_set_resource: TileSet
var water_cells: Array[Vector2i] = []
var debug_collisions: bool = false
var _water_anim_timer: float = 0.0
var _water_anim_phase: int = 0

var inventory: Dictionary = {
	"wood": 0,
	"stone": 0,
	"berry": 0,
	"watered": 0,
}


func _ready() -> void:
	_build_tileset_with_collisions()
	ground_layer.tile_set = tile_set_resource
	decor_layer.tile_set = tile_set_resource

	_setup_map_borders()

	if player:
		player.tool_used.connect(_on_player_tool_used)

	generate_world(world_seed)


func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed("regenerate_world"):
		regenerate_random_world()
	elif event.is_action_pressed("toggle_debug_collisions"):
		toggle_collision_debug()


func _process(delta: float) -> void:
	# Animate water ripples on river & lake tiles
	_water_anim_timer += delta
	if _water_anim_timer >= 0.55:
		_water_anim_timer = 0.0
		_water_anim_phase = (_water_anim_phase + 1) % 4
		_animate_water_tiles()


func regenerate_random_world() -> void:
	var rng := RandomNumberGenerator.new()
	rng.randomize()
	var next_seed: int = rng.randi_range(100000, 999999)
	generate_world(next_seed)


func toggle_collision_debug() -> void:
	debug_collisions = not debug_collisions
	if player:
		player.set_debug_draw(debug_collisions)
	for child in objects_container.get_children():
		if child.has_method("set_debug_draw"):
			child.set_debug_draw(debug_collisions)
	if debug_overlay:
		debug_overlay.queue_redraw()


func _build_tileset_with_collisions() -> void:
	tile_set_resource = TileSet.new()
	tile_set_resource.tile_size = Vector2i(TILE_SIZE, TILE_SIZE)

	# Physics Layer 0: Water & Impassable Terrain (Collision Layer 1)
	tile_set_resource.add_physics_layer()
	tile_set_resource.set_physics_layer_collision_layer(0, 1)
	tile_set_resource.set_physics_layer_collision_mask(0, 0)

	var atlas_tex: Texture2D = load("res://assets/tilesets/world_tileset.png")
	var source := TileSetAtlasSource.new()
	source.texture = atlas_tex
	source.texture_region_size = Vector2i(TILE_SIZE, TILE_SIZE)

	var cols: int = 16
	var rows: int = 5
	var full_tile_poly := PackedVector2Array([
		Vector2(-8, -8),
		Vector2(8, -8),
		Vector2(8, 8),
		Vector2(-8, 8),
	])

	for ry in range(rows):
		for cx in range(cols):
			var coords := Vector2i(cx, ry)
			source.create_tile(coords)
			var tile_data: TileData = source.get_tile_data(coords, 0)
			# Row 0 contains all water tiles (Deep lake, Shallow lake, River, Lilypads)
			# Give them solid physics collision on Physics Layer 0!
			if ry == 0:
				tile_data.add_collision_polygon(0)
				tile_data.set_collision_polygon_points(0, 0, full_tile_poly)

	tile_set_resource.add_source(source, 0)


func _setup_map_borders() -> void:
	for child in border_body.get_children():
		child.queue_free()

	var half_w: float = (map_width * TILE_SIZE) * 0.5
	var half_h: float = (map_height * TILE_SIZE) * 0.5
	var thickness: float = 32.0

	var walls: Array[Dictionary] = [
		{"pos": Vector2(0, -half_h - thickness * 0.5), "size": Vector2(half_w * 2.0 + 64.0, thickness)},
		{"pos": Vector2(0, half_h + thickness * 0.5),  "size": Vector2(half_w * 2.0 + 64.0, thickness)},
		{"pos": Vector2(-half_w - thickness * 0.5, 0), "size": Vector2(thickness, half_h * 2.0 + 64.0)},
		{"pos": Vector2(half_w + thickness * 0.5, 0),  "size": Vector2(thickness, half_h * 2.0 + 64.0)},
	]

	for w in walls:
		var shape_node := CollisionShape2D.new()
		var rect := RectangleShape2D.new()
		rect.size = w["size"]
		shape_node.shape = rect
		shape_node.position = w["pos"]
		border_body.add_child(shape_node)


func generate_world(new_seed: int) -> void:
	world_seed = new_seed
	ground_layer.clear()
	decor_layer.clear()
	water_cells.clear()

	for child in objects_container.get_children():
		child.queue_free()

	# Configure 3 FastNoiseLite layers for Lakes, Rivers, and Forest Biomes
	var elev_noise := FastNoiseLite.new()
	elev_noise.seed = world_seed
	elev_noise.noise_type = FastNoiseLite.TYPE_SIMPLEX_SMOOTH
	elev_noise.frequency = 0.032
	elev_noise.fractal_octaves = 3

	var river_noise := FastNoiseLite.new()
	river_noise.seed = world_seed + 1013
	river_noise.noise_type = FastNoiseLite.TYPE_SIMPLEX_SMOOTH
	river_noise.frequency = 0.021
	river_noise.fractal_octaves = 2

	var forest_noise := FastNoiseLite.new()
	forest_noise.seed = world_seed + 4099
	forest_noise.noise_type = FastNoiseLite.TYPE_SIMPLEX_SMOOTH
	forest_noise.frequency = 0.055
	forest_noise.fractal_octaves = 2

	var rng := RandomNumberGenerator.new()
	rng.seed = world_seed

	var x_min: int = -map_width / 2
	var x_max: int = map_width / 2
	var y_min: int = -map_height / 2
	var y_max: int = map_height / 2

	var tree_count: int = 0
	var rock_count: int = 0
	var water_count: int = 0
	var bridge_count: int = 0

	# Track occupied cells for object placement
	var water_lookup: Dictionary = {}
	var bridge_lookup: Dictionary = {}
	var path_lookup: Dictionary = {}

	# Pass 1: Generate Ground & Water & Bridges
	for ty in range(y_min, y_max):
		for tx in range(x_min, x_max):
			var cell := Vector2i(tx, ty)
			var dist_from_spawn: float = Vector2(tx, ty).length()
			var elev: float = elev_noise.get_noise_2d(float(tx), float(ty))
			var r_val: float = absf(river_noise.get_noise_2d(float(tx), float(ty)))
			var f_val: float = forest_noise.get_noise_2d(float(tx), float(ty))

			# Keep spawn area around (0,0) dry land
			if dist_from_spawn < 6.0:
				var spawn_blend: float = clampf((6.0 - dist_from_spawn) / 6.0, 0.0, 1.0)
				elev = maxf(elev, 0.08 * spawn_blend)
				r_val = maxf(r_val, 0.12 * spawn_blend)

			var is_river: bool = (r_val < 0.058)
			var is_deep_lake: bool = (elev < -0.28)
			var is_shallow_lake: bool = (elev < -0.15)
			var is_water: bool = is_river or is_deep_lake or is_shallow_lake

			# Winding main paths along X and Y axes near center so bridges cross rivers
			var on_ns_trail: bool = abs(tx - int(round(sin(float(ty) * 0.12) * 2.0))) <= 1
			var on_ew_trail: bool = abs(ty - int(round(cos(float(tx) * 0.12) * 2.0))) <= 1
			var is_trail: bool = on_ns_trail or on_ew_trail

			var variant: int = posmod(tx * 7 + ty * 13, 4)

			if is_water:
				# Place wooden bridges where trails cross rivers or narrow water!
				if is_trail and (is_river or not is_deep_lake):
					var bridge_col: int = (variant % 2) if on_ew_trail else (2 + (variant % 2))
					ground_layer.set_cell(cell, 0, Vector2i(bridge_col, 2))
					bridge_lookup[cell] = true
					bridge_count += 1
				else:
					var water_col: int = variant
					if is_deep_lake:
						water_col = variant  # Cols 0..3: Deep Water
					elif is_river:
						water_col = 8 + variant  # Cols 8..11: River Water
					else:
						# Shallow lake water or lilypad
						if rng.randf() < 0.14:
							water_col = 12 + variant  # Cols 12..15: Lilypads
						else:
							water_col = 4 + variant  # Cols 4..7: Shallow Water

					ground_layer.set_cell(cell, 0, Vector2i(water_col, 0))
					water_cells.append(cell)
					water_lookup[cell] = water_col
					water_count += 1
			else:
				# Land biomes
				if is_trail:
					ground_layer.set_cell(cell, 0, Vector2i(12 + variant, 1))  # Dirt path
					path_lookup[cell] = true
				elif elev < -0.06 or r_val < 0.088:
					# Sandy beach / riverbank
					ground_layer.set_cell(cell, 0, Vector2i(variant, 1))
				elif f_val > 0.12 or elev > 0.22:
					# Rich dark forest floor
					ground_layer.set_cell(cell, 0, Vector2i(8 + variant, 1))
				else:
					# Lush meadow grass
					ground_layer.set_cell(cell, 0, Vector2i(4 + variant, 1))

	# Pass 2: Populate Decor & Collidable Forest/Rock Objects
	var occupied_cells: Dictionary = {}

	for ty in range(y_min + 2, y_max - 2):
		for tx in range(x_min + 2, x_max - 2):
			var cell := Vector2i(tx, ty)
			if water_lookup.has(cell) or bridge_lookup.has(cell) or path_lookup.has(cell):
				continue

			var dist_from_spawn: float = Vector2(tx, ty).length()
			if dist_from_spawn < 3.5:
				continue

			# Check if adjacent to water so we keep shorelines mostly passable
			var near_water: bool = false
			for oy in range(-1, 2):
				for ox in range(-1, 2):
					if water_lookup.has(Vector2i(tx + ox, ty + oy)):
						near_water = true
						break

			var elev: float = elev_noise.get_noise_2d(float(tx), float(ty))
			var f_val: float = forest_noise.get_noise_2d(float(tx), float(ty))
			var roll: float = rng.randf()

			# Forest trees in forest biomes (with spacing check so player can walk through groves)
			if not near_water and not _has_neighbor_in_dict(occupied_cells, cell, 1):
				if f_val > 0.15 and roll < 0.30:
					var tree_kind: String = "tree_oak"
					if elev > 0.28:
						tree_kind = "tree_pine"
					elif f_val > 0.42:
						tree_kind = "tree_birch" if (tx + ty) % 2 == 0 else "tree_oak"
					_spawn_world_object(tree_kind, cell)
					occupied_cells[cell] = true
					tree_count += 1
					continue
				elif f_val > 0.05 and roll < 0.045:
					var sub_kind: String = "bush_berry" if rng.randf() < 0.65 else "log_fallen"
					_spawn_world_object(sub_kind, cell)
					occupied_cells[cell] = true
					tree_count += 1
					continue
				elif elev > 0.18 and roll > 0.93:
					var rock_kind: String = "rock_large" if rng.randf() < 0.35 else ("rock_ore" if rng.randf() < 0.45 else "rock_small")
					_spawn_world_object(rock_kind, cell)
					occupied_cells[cell] = true
					rock_count += 1
					continue
				elif near_water and roll < 0.04:
					_spawn_world_object("rock_small", cell)
					occupied_cells[cell] = true
					rock_count += 1
					continue

			# Ground decor (flowers, tall grass, mushrooms, pebbles) - non-colliding
			if rng.randf() < 0.14:
				var d_var: int = rng.randi_range(0, 3)
				if f_val > 0.20:
					# Forest mushrooms or tall grass
					var d_col: int = (8 + d_var) if rng.randf() < 0.45 else (4 + d_var)
					decor_layer.set_cell(cell, 0, Vector2i(d_col, 3))
				elif elev < 0.0:
					# Shore pebbles
					decor_layer.set_cell(cell, 0, Vector2i(12 + d_var, 3))
				else:
					# Meadow wildflowers or grass tufts
					var d_col: int = d_var if rng.randf() < 0.55 else (4 + d_var)
					decor_layer.set_cell(cell, 0, Vector2i(d_col, 3))

	# Reset player to safe center spawn
	if player:
		player.global_position = Vector2.ZERO
		player.velocity = Vector2.ZERO

	if debug_overlay:
		debug_overlay.queue_redraw()

	world_regenerated.emit(world_seed, {
		"trees": tree_count,
		"rocks": rock_count,
		"water_tiles": water_count,
		"bridges": bridge_count,
	})


func _has_neighbor_in_dict(dict: Dictionary, cell: Vector2i, radius: int) -> bool:
	for dy in range(-radius, radius + 1):
		for dx in range(-radius, radius + 1):
			if dict.has(Vector2i(cell.x + dx, cell.y + dy)):
				return true
	return false


func _spawn_world_object(kind: String, cell: Vector2i) -> void:
	var obj: WorldObject = WORLD_OBJECT_SCENE.instantiate()
	obj.object_type = kind
	obj.position = ground_layer.map_to_local(cell)
	obj.debug_draw_enabled = debug_collisions
	obj.resource_dropped.connect(_on_object_resource_dropped)
	objects_container.add_child(obj)


func _on_player_tool_used(tool_id: String, target_global_pos: Vector2, _facing_dir: Vector2) -> void:
	# 1. Check for interactive WorldObjects within reach
	var closest_obj: WorldObject = null
	var best_dist: float = 20.0

	for child in objects_container.get_children():
		if child is WorldObject:
			var d: float = child.global_position.distance_to(target_global_pos)
			if d < best_dist:
				best_dist = d
				closest_obj = child

	if closest_obj != null:
		closest_obj.apply_tool_hit(tool_id)
		return

	# 2. If using Watering Can on ground tile, water the soil & sprout flowers!
	if tool_id == "water":
		var local_pos: Vector2 = ground_layer.to_local(target_global_pos)
		var cell: Vector2i = ground_layer.local_to_map(local_pos)
		var atlas_coords: Vector2i = ground_layer.get_cell_atlas_coords(cell)
		# Only water land tiles (Row 1: sand/grass/forest/dirt)
		if atlas_coords.y == 1:
			var variant: int = posmod(cell.x + cell.y, 4)
			ground_layer.set_cell(cell, 0, Vector2i(4 + variant, 2))
			if decor_layer.get_cell_source_id(cell) == -1:
				decor_layer.set_cell(cell, 0, Vector2i(variant, 3))
			inventory["watered"] += 1
			inventory_updated.emit(inventory)


func _on_object_resource_dropped(resource_type: String, amount: int, _world_pos: Vector2) -> void:
	if inventory.has(resource_type):
		inventory[resource_type] += amount
		inventory_updated.emit(inventory)


func _animate_water_tiles() -> void:
	for cell in water_cells:
		var coords: Vector2i = ground_layer.get_cell_atlas_coords(cell)
		if coords.y == 0 and coords.x < 12:
			var group_base: int = (coords.x / 4) * 4
			var next_col: int = group_base + ((coords.x + 1) % 4)
			ground_layer.set_cell(cell, 0, Vector2i(next_col, 0))

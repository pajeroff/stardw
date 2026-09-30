class_name MapGen
extends RefCounted
## Deterministic island layout. Produces a tile grid, water-type map, props,
## buildings and named spots. Consumed by world.gd.

const W := 64
const H := 48

var seed: int = 7
var grid: Dictionary = {}          # Vector2i -> tile name
var water: Dictionary = {}         # Vector2i -> "lake"/"river"/"ocean"/"pond"
var props: Array = []              # [{type, cell}]
var buildings: Array = []          # [{type, cell}]
var player_start := Vector2i(14, 30)
var spots: Dictionary = {}

var _rng := RandomNumberGenerator.new()

func generate(s: int = 7) -> void:
	seed = s
	_rng.seed = s
	_fill_grass()
	_carve_lake()
	_carve_river()
	_carve_ocean()
	_carve_pond()
	_edges_and_beaches()
	_paths()
	_scatter_nature()
	_place_buildings()

func _cell(x: int, y: int) -> Vector2i:
	return Vector2i(x, y)

func inb(c: Vector2i) -> bool:
	return c.x >= 0 and c.y >= 0 and c.x < W and c.y < H

func _fill_grass() -> void:
	for y in H:
		for x in W:
			var r := _rng.randf()
			var t := "grass_a"
			if r > 0.86:
				t = "grass_b"
			elif r > 0.94:
				t = "grass_c"
			if _rng.randf() < 0.05:
				t = "grass_dark"
			grid[_cell(x, y)] = t

func _ellipse(cx: float, cy: float, rx: float, ry: float) -> Array:
	var out: Array = []
	for y in range(maxi(0, int(cy - ry - 1)), mini(H, int(cy + ry + 2))):
		for x in range(maxi(0, int(cx - rx - 1)), mini(W, int(cx + rx + 2))):
			var dx := (x - cx) / rx
			var dy := (y - cy) / ry
			if dx * dx + dy * dy <= 1.0:
				out.append(_cell(x, y))
	return out

func _carve_lake() -> void:
	for c in _ellipse(40, 18, 13, 8):
		water[c] = "lake"
		grid[c] = "water_mid"
	# shallow ring
	for c in water.keys():
		if grid[c] == "water_mid":
			for n in [c + Vector2i(1, 0), c + Vector2i(-1, 0), c + Vector2i(0, 1), c + Vector2i(0, -1)]:
				if inb(n) and not water.has(n):
					grid[n] = "sand_wet"

func _carve_river() -> void:
	var x := 7.0
	for y in range(0, H):
		x += sin(y * 0.35) * 0.6 + _rng.randf_range(-0.3, 0.3)
		x = clampf(x, 4.0, 11.0)
		for dx in range(0, 3):
			var c := _cell(int(x) + dx, y)
			if inb(c):
				water[c] = "river"
				grid[c] = "water_river"

func _carve_ocean() -> void:
	for y in H:
		for x in W:
			# bottom-right diagonal beyond a line
			if x + y >= W + H - 26 + int(sin(x * 0.3) * 2):
				var c := _cell(x, y)
				if not water.has(c):
					water[c] = "ocean"
					grid[c] = "water_deep" if (x + y) > W + H - 20 else "water_shallow"

func _carve_pond() -> void:
	for c in _ellipse(20, 38, 4, 3):
		water[c] = "pond"
		grid[c] = "water_shallow"

func _edges_and_beaches() -> void:
	for y in H:
		for x in W:
			var c := _cell(x, y)
			if water.has(c):
				continue
			# beach next to ocean
			var near_ocean := false
			var near_any_water := false
			for n in [c + Vector2i(1, 0), c + Vector2i(-1, 0), c + Vector2i(0, 1), c + Vector2i(0, -1)]:
				if water.has(n):
					near_any_water = true
					if water[n] == "ocean":
						near_ocean = true
			if near_ocean:
				grid[c] = "sand"
			elif near_any_water and _rng.randf() < 0.4:
				grid[c] = "sand"

func _paths() -> void:
	# house -> shop -> lake pier -> beach
	var path_pts := [Vector2i(14, 30), Vector2i(20, 28), Vector2i(26, 27), Vector2i(30, 24), Vector2i(30, 20),
					 Vector2i(30, 26), Vector2i(30, 32), Vector2i(36, 38), Vector2i(44, 40)]
	for i in range(path_pts.size() - 1):
		var a := path_pts[i]
		var b := path_pts[i + 1]
		var steps := maxi(absi(b.x - a.x), absi(b.y - a.y))
		for s in range(steps + 1):
			var t := float(s) / float(maxi(1, steps))
			var c := _cell(int(lerpf(a.x, b.x, t)), int(lerpf(a.y, b.y, t)))
			if inb(c) and not water.has(c):
				grid[c] = "path"
	spots["house"] = Vector2i(13, 27)
	spots["shop"] = Vector2i(24, 27)
	spots["board"] = Vector2i(28, 27)
	spots["well"] = Vector2i(17, 31)
	spots["campfire"] = Vector2i(46, 41)
	spots["pier"] = Vector2i(30, 18)
	spots["boat"] = Vector2i(50, 42)

func _scatter_nature() -> void:
	for y in H:
		for x in W:
			var c := _cell(x, y)
			if water.has(c) or grid[c] == "path":
				continue
			var r := _rng.randf()
			# forest borders
			var border := (x < 3 or y < 2 or x > W - 4 or y > H - 4)
			if border and r < 0.5:
				props.append({"type": "tree", "cell": c})
			elif r < 0.012:
				props.append({"type": "tree", "cell": c})
			elif r < 0.02:
				props.append({"type": "rock", "cell": c})
			elif r < 0.03:
				props.append({"type": "flower", "cell": c})
			elif r < 0.045:
				props.append({"type": "tall_grass", "cell": c})
			# waterside reeds
			for n in [c + Vector2i(0, 1)]:
				if water.has(n) and _rng.randf() < 0.12:
					props.append({"type": "reeds", "cell": c})

func _place_buildings() -> void:
	buildings.append({"type": "house", "cell": spots["house"]})
	buildings.append({"type": "shop", "cell": spots["shop"]})
	buildings.append({"type": "board", "cell": spots["board"]})
	buildings.append({"type": "well", "cell": spots["well"]})
	buildings.append({"type": "campfire", "cell": spots["campfire"]})
	buildings.append({"type": "boat", "cell": spots["boat"]})
	# pier posts into the lake
	for i in 5:
		buildings.append({"type": "pier_post", "cell": _cell(30, 18 - i)})

func is_water(c: Vector2i) -> bool:
	return water.has(c)

func water_type(c: Vector2i) -> String:
	return water.get(c, "")

func tile(c: Vector2i) -> String:
	return grid.get(c, "grass_a")

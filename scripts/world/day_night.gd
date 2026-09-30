extends CanvasModulate
## Tints the world by time of day.

func _ready() -> void:
	Game.clock_changed.connect(func(_h, _m): _update())
	_update()

func _update() -> void:
	var h := (Game.clock / 60) % 24
	var f := float(h) + (Game.clock % 60) / 60.0
	color = _color_at(f)

func _color_at(h: float) -> Color:
	# keyframes: hour -> color
	var keys := {
		0.0: Color(0.25, 0.28, 0.45),
		5.0: Color(0.35, 0.35, 0.5),
		6.5: Color(0.9, 0.75, 0.6),
		8.0: Color(1.0, 0.98, 0.92),
		16.0: Color(1.0, 0.98, 0.92),
		18.0: Color(1.0, 0.8, 0.55),
		19.5: Color(0.6, 0.5, 0.65),
		21.0: Color(0.3, 0.32, 0.5),
		24.0: Color(0.25, 0.28, 0.45),
	}
	var ks := keys.keys()
	ks.sort()
	for i in range(ks.size() - 1):
		if h >= ks[i] and h <= ks[i + 1]:
			var t := (h - ks[i]) / maxf(0.001, ks[i + 1] - ks[i])
			return keys[ks[i]].lerp(keys[ks[i + 1]], t)
	return Color(1, 1, 1)

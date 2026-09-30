class_name UIUtil
extends RefCounted
## Small helpers to build themed UI from the generated atlas.

static func theme() -> Theme:
	var t := Theme.new()
	var font: Font = load("res://assets/fonts/DejaVuSans.ttf")
	var bold: Font = load("res://assets/fonts/DejaVuSans-Bold.ttf")
	t.default_font = font
	t.default_font_size = 15
	t.set_font("font", "Label", font)
	t.set_font("font", "Button", font)
	t.set_font("font", "RichTextLabel", font)
	if bold:
		t.set_type_variation("Title", "Label")
	return t

static func label(text: String, size: int = 15, color: Color = Color.WHITE) -> Label:
	var l := Label.new()
	l.text = text
	l.add_theme_font_size_override("font_size", size)
	l.add_theme_color_override("font_color", color)
	return l

static func flat(color: Color, border: Color = Color(0, 0, 0, 0), bw: int = 0, radius: int = 4) -> StyleBoxFlat:
	var sb := StyleBoxFlat.new()
	sb.bg_color = color
	if bw > 0:
		sb.border_color = border
		sb.set_border_width_all(bw)
	sb.set_corner_radius_all(radius)
	return sb

static func button(text: String, red: bool = false) -> Button:
	var b := Button.new()
	b.text = text
	var base := Color(0.24, 0.42, 0.26) if not red else Color(0.5, 0.24, 0.22)
	b.add_theme_stylebox_override("normal", flat(base, Color(0, 0, 0, 0.6), 2, 6))
	b.add_theme_stylebox_override("hover", flat(base.lightened(0.2), Color(0, 0, 0, 0.6), 2, 6))
	b.add_theme_stylebox_override("pressed", flat(base.darkened(0.2), Color(0, 0, 0, 0.6), 2, 6))
	b.add_theme_color_override("font_color", Color(0.95, 0.95, 0.9))
	b.add_theme_font_size_override("font_size", 15)
	return b

static func icon(name: String, size: int = 20) -> TextureRect:
	var tr := TextureRect.new()
	tr.texture = Art.tex(name)
	tr.custom_minimum_size = Vector2(size, size)
	tr.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	return tr

static func panel_container(margin: int = 10) -> PanelContainer:
	var p := PanelContainer.new()
	var sb := StyleBoxFlat.new()
	sb.bg_color = Color(0.10, 0.13, 0.18, 0.94)
	sb.border_color = Color(0.35, 0.5, 0.65)
	sb.set_border_width_all(3)
	sb.set_corner_radius_all(8)
	sb.content_margin_left = margin
	sb.content_margin_right = margin
	sb.content_margin_top = margin
	sb.content_margin_bottom = margin
	p.add_theme_stylebox_override("panel", sb)
	return p

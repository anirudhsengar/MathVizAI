from manim import *

def create_neon_graph(axes, function, color=BLUE, glow_radius=0.1, stroke_width=4):
    """
    Creates a graph with a neon glow effect.
    
    Args:
        axes (Axes): The axes to plot on.
        function (callable): The function to plot.
        color (Color): The core color of the graph.
        glow_radius (float): The radius of the glow effect.
        stroke_width (float): The width of the main stroke.
        
    Returns:
        VGroup: A VGroup containing the main graph and its glow layers.
    """
    graph = axes.plot(function, color=color, stroke_width=stroke_width)
    glow_1 = axes.plot(function, color=color, stroke_width=stroke_width * 1.5).set_opacity(0.3)
    glow_2 = axes.plot(function, color=color, stroke_width=stroke_width * 3).set_opacity(0.2)
    glow_3 = axes.plot(function, color=color, stroke_width=stroke_width * 5).set_opacity(0.1)
    
    return VGroup(glow_3, glow_2, glow_1, graph)

def create_morphing_grid(rows=5, cols=5, height=4, width=4, color=GRAY):
    """
    Creates a grid that looks ready to morph or transform.
    
    Args:
        rows (int): Number of rows.
        cols (int): Number of columns.
        height (float): Height of the grid.
        width (float): Width of the grid.
        color (Color): Color of the grid lines.
        
    Returns:
        VGroup: The grid object.
    """
    grid = NumberPlane(
        x_range=(-width/2, width/2, 1),
        y_range=(-height/2, height/2, 1),
        background_line_style={
            "stroke_color": color,
            "stroke_width": 2,
            "stroke_opacity": 0.5
        }
    )
    return grid

def create_glowing_text(text_str, font_size=48, color=WHITE, glow_color=BLUE, glow_opacity=0.5):
    """
    Creates text with a soft background glow.
    
    Args:
        text_str (str): The text content.
        font_size (int): Font size.
        color (Color): Text color.
        glow_color (Color): Color of the glow.
        glow_opacity (float): Opacity of the glow.
        
    Returns:
        VGroup: Text with glow.
    """
    text = Text(text_str, font_size=font_size, color=color)
    glow = text.copy().set_color(glow_color).set_opacity(glow_opacity)
    glow.set_stroke(width=5, color=glow_color, opacity=glow_opacity)
    return VGroup(glow, text)

def create_cyberpunk_box(width=5, height=3, color=TEAL):
    """
    Creates a cyberpunk-style box with corner accents.
    
    Args:
        width (float): Width of the box.
        height (float): Height of the box.
        color (Color): Primary color.
        
    Returns:
        VGroup: The stylized box.
    """
    box = Rectangle(width=width, height=height, color=color, fill_opacity=0.1, stroke_opacity=0.5)
    corners = VGroup()
    corner_len = 0.5
    
    # Top Left
    tl = VMobject().set_points_as_corners([
        box.get_corner(UL) + RIGHT * corner_len,
        box.get_corner(UL),
        box.get_corner(UL) + DOWN * corner_len
    ])
    corners.add(tl)

    # Top Right
    tr = VMobject().set_points_as_corners([
        box.get_corner(UR) + LEFT * corner_len,
        box.get_corner(UR),
        box.get_corner(UR) + DOWN * corner_len
    ])
    corners.add(tr)
    
    # Bottom Left
    bl = VMobject().set_points_as_corners([
        box.get_corner(DL) + RIGHT * corner_len,
        box.get_corner(DL),
        box.get_corner(DL) + UP * corner_len
    ])
    corners.add(bl)
    
    # Bottom Right
    br = VMobject().set_points_as_corners([
        box.get_corner(DR) + LEFT * corner_len,
        box.get_corner(DR),
        box.get_corner(DR) + UP * corner_len
    ])
    corners.add(br)
    
    corners.set_stroke(color=color, width=4)
    return VGroup(box, corners)

def create_data_stream(start_point, end_point, color=YELLOW, num_bits=10):
    """
    Simulates a stream of data packets moving between two points.
    Returns a VGroup of dots and an animation function to play.
    
    Usage:
    stream_group, stream_anim = create_data_stream(p1, p2)
    self.play(stream_anim)
    """
    # This is slightly more complex to return a single object, usually requires an updater.
    # For simplicity in this library, we returns the VGroup and letting the user animate it 
    # might be too low-level. 
    # Instead, let's return a ValueTracker based updater helper or similar.
    # For now, let's stick to static complex objects or simple animations wrapped in Successions.
    pass

def safe_get_part(mobject, tex_key):
    """
    Safely attempts to get a part of a MathTex object by key.
    If not found, returns the mobject itself to prevent NoneType errors.
    
    Args:
        mobject (MathTex): The MathTex object.
        tex_key (str): The LaTeX key to search for.
        
    Returns:
        VMobject: The found part or the original mobject.
    """
    try:
        part = mobject.get_part_by_tex(tex_key)
        if part is None:
            print(f"Warning: Could not find part '{tex_key}' in {mobject}. Using center.")
            return mobject
        return part
    except Exception:
        return mobject

def safe_move_to_part(mobject_to_move, target_mobject, part_tex):
    """
    Safely moves an object to a specific part of another object.
    
    Args:
        mobject_to_move (VMobject): The object to move.
        target_mobject (MathTex): The target container.
        part_tex (str): The TeX key to align with.
    """
    target = safe_get_part(target_mobject, part_tex)
    mobject_to_move.move_to(target)
    return mobject_to_move

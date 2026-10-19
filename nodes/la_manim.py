"""Shared manim helpers for the linear algebra notes.

Every animation cell in the notes does `from la_manim import *`, defines one Scene,
and ends with `show(SceneName)`, which renders the scene and embeds the video in the
notebook output. Rendering needs manim (https://docs.manim.community); viewing the
rendered notes does not.
"""
import numpy as np
from manim import *
from IPython.display import Video

config.media_dir = "/tmp/manim-la"
config.pixel_width, config.pixel_height, config.frame_rate = 960, 540, 30
config.frame_width, config.frame_height = 10, 5.625   # 1 unit = 96 px
config.background_color = "#ffffff"   # white, like the static figures
config.verbosity, config.progress_bar = "WARNING", "none"

# palette (same hues as the static figures)
C_BLUE, C_ORANGE, C_AQUA, C_YELLOW = "#2a78d6", "#eb6834", "#1baf7a", "#eda100"
C_MAGENTA, C_GREEN, C_VIOLET, C_RED = "#e87ba4", "#008300", "#6250d6", "#e34948"
C_INK, C_MUTED, C_GRID = "#0b0b0b", "#52514e", "#d9d8d4"
C_FAINT = "#a3a29a"     # recessive grey for "ordinary" vectors

# manim's defaults are white-on-black; make un-coloured text and shapes dark
for _cls in (MathTex, Tex, Text, DecimalNumber, Integer, Line, DashedLine, Arrow, Dot, Circle):
    _cls.set_default(color=C_INK)


def show(scene_cls, width=760):
    """Render `scene_cls` and embed the resulting video in the notebook."""
    scene = scene_cls()
    scene.render()
    return Video(str(scene.renderer.file_writer.movie_file_path), embed=True, width=width,
                 html_attributes="controls autoplay loop muted playsinline")


def caption(tex, corner=UL, scale=0.8):
    """A formula on a white backing, pinned to a corner of the frame."""
    m = MathTex(tex, color=C_INK).scale(scale)
    m.to_corner(corner, buff=0.3)
    return VGroup(BackgroundRectangle(m, fill_opacity=0.85, buff=0.12, color=config.background_color), m)


def text_caption(s, corner=DL, scale=0.62):
    t = Tex(s, color=C_INK).scale(scale)
    t.to_corner(corner, buff=0.3)
    return VGroup(BackgroundRectangle(t, fill_opacity=0.85, buff=0.12, color=config.background_color), t)


class GridScene(Scene):
    """A 2D scene with a faint fixed grid and a coloured grid that linear maps act on."""
    x_range = (-8, 8, 1)
    y_range = (-5, 5, 1)

    def setup(self):
        self.bg = NumberPlane(x_range=self.x_range, y_range=self.y_range,
                              background_line_style={"stroke_color": C_GRID, "stroke_width": 1},
                              axis_config={"stroke_color": C_GRID, "stroke_width": 1})
        self.plane = NumberPlane(x_range=(-16, 16, 1), y_range=(-12, 12, 1),
                                 background_line_style={"stroke_color": C_BLUE, "stroke_width": 1.2,
                                                        "stroke_opacity": 0.35},
                                 axis_config={"stroke_color": C_MUTED, "stroke_width": 1.6},
                                 faded_line_ratio=1)
        self.add(self.bg, self.plane)
        self.vectors = []            # (arrow, current coordinates) moved by transform()
        self.tracked = []            # other mobjects moved by transform()

    def track_point(self, mob, point):
        """Register a mobject (e.g. a Dot) whose *position* follows the map without being deformed."""
        self.points = getattr(self, "points", [])
        self.points.append((mob, np.array([point[0], point[1], 0.0], dtype=float)))
        return mob

    def track(self, *mobs):
        """Register mobjects (lines, polygons, dots) that linear maps should act on."""
        self.tracked.extend(mobs)
        return mobs[0] if len(mobs) == 1 else mobs

    def vec(self, v, color, label=None, label_dir=UR, add=True):
        v = np.array([v[0], v[1], 0.0], dtype=float)
        arrow = Arrow(ORIGIN, v, buff=0, color=color, stroke_width=5,
                      max_tip_length_to_length_ratio=0.25, tip_length=0.22)
        group = VGroup(arrow)
        if label is not None:
            lab = MathTex(label, color=color).scale(0.8)
            lab.add_updater(lambda m, a=arrow, d=label_dir: m.next_to(a.get_end(), d, buff=0.08))
            group.add(lab)
        self.vectors.append((arrow, v))
        if add:
            self.add(group)
        return group

    def transform(self, M, run_time=2.5, extra=(), path=None):
        """Animate the linear map with matrix M acting on the grid and all registered vectors."""
        M = np.array(M, dtype=float)
        M3 = np.eye(3)
        M3[:2, :2] = M
        start_plane = self.plane.copy()
        starts = [(a, v.copy()) for a, v in self.vectors]
        start_tracked = [(m, m.copy()) for m in self.tracked]
        start_points = [(m, p.copy()) for m, p in getattr(self, "points", [])]

        def update(_, alpha):
            Mt = np.eye(3) + alpha * (M3 - np.eye(3))
            new = start_plane.copy()
            new.apply_matrix(Mt, about_point=ORIGIN)
            self.plane.become(new)
            for m, m0 in start_tracked:
                m.become(m0.copy().apply_matrix(Mt, about_point=ORIGIN))
            for m, p in start_points:
                m.move_to(Mt @ p)
            for a, v in starts:
                end = Mt @ v
                if np.linalg.norm(end) < 1e-3:
                    end = end + np.array([1e-3, 0, 0])
                a.put_start_and_end_on(ORIGIN, end)

        self.play(UpdateFromAlphaFunc(self.plane, update), *extra, run_time=run_time, rate_func=smooth)
        self.vectors = [(a, M3 @ v) for a, v in starts]
        self.points = [(m, M3 @ p) for m, p in start_points]

    def reset_grid(self, run_time=1.0):
        """Fade back to the identity picture (used between two maps)."""
        new_plane = NumberPlane(x_range=(-16, 16, 1), y_range=(-12, 12, 1),
                                background_line_style={"stroke_color": C_BLUE, "stroke_width": 1.2,
                                                       "stroke_opacity": 0.35},
                                axis_config={"stroke_color": C_MUTED, "stroke_width": 1.6},
                                faded_line_ratio=1)
        self.play(Transform(self.plane, new_plane), run_time=run_time)

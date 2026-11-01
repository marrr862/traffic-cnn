"""Spatial accumulation of vehicle positions and trajectory rendering."""
import numpy as np


class Heatmap:
    def __init__(self, width, height, cell=16):
        self.cell = cell
        self.grid = np.zeros((height // cell + 1, width // cell + 1), np.float32)
        self.width, self.height = width, height

    def add(self, point):
        x, y = int(point[0]) // self.cell, int(point[1]) // self.cell
        if 0 <= y < self.grid.shape[0] and 0 <= x < self.grid.shape[1]:
            self.grid[y, x] += 1

    def render(self, background, alpha=0.55):
        import cv2
        if self.grid.max() <= 0:
            return background.copy()
        smooth = cv2.GaussianBlur(self.grid, (0, 0), 1.5)
        scaled = np.log1p(smooth) / np.log1p(smooth.max())
        image = cv2.resize((scaled * 255).astype(np.uint8), (self.width, self.height), interpolation=cv2.INTER_LINEAR)
        colored = cv2.applyColorMap(image, cv2.COLORMAP_JET)
        mask = (image > 8)[..., None]
        blended = cv2.addWeighted(background, 1 - alpha, colored, alpha, 0)
        return np.where(mask, blended, background)


def draw_trajectories(background, tracks, color_by_class=None):
    """tracks: {id: (class_name, [(x, y), ...])}."""
    import cv2
    palette = color_by_class or {'car': (255, 140, 0), 'van': (0, 200, 255), 'truck': (0, 0, 255),
                                 'bus': (0, 255, 0), 'motorcycle': (255, 0, 255)}
    image = background.copy()
    thickness = max(2, background.shape[1] // 900)
    for cls, points in tracks.values():
        if len(points) > 1:
            cv2.polylines(image, [np.asarray(points, np.int32)], False, palette.get(cls, (255, 255, 255)), thickness)
    return image

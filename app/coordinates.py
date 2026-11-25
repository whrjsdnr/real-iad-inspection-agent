"""Versioned affine coordinates. All image relationships must be explicit.

No inference or stored inspection values are changed here. LUT registration is
independent of a model's preprocessing, even when dimensions happen to match.
"""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np

TRANSFORM_VERSION = 'coordinates-affine-v1'

class UnverifiedTransform(ValueError):
    pass

@dataclass(frozen=True)
class Size:
    width: int
    height: int
    def __post_init__(self):
        if self.width <= 0 or self.height <= 0:
            raise ValueError('Image dimensions must be positive')

@dataclass(frozen=True)
class Transform:
    source: str
    target: str
    source_size: Size
    target_size: Size
    matrix: tuple[tuple[float, float, float], ...]
    provenance: str
    version: str = TRANSFORM_VERSION

    def __post_init__(self):
        m = np.asarray(self.matrix, dtype=float)
        if not self.provenance:
            raise UnverifiedTransform('Coordinate provenance is required')
        if m.shape != (3, 3) or not np.isfinite(m).all() or not np.allclose(m[2], [0, 0, 1]) or abs(np.linalg.det(m)) < np.finfo(float).eps:
            raise ValueError('Invalid invertible affine matrix')

    @classmethod
    def resize(cls, source, target, source_size, target_size, *, provenance):
        """Use only when the pipeline confirms direct anisotropic resize."""
        return cls(source, target, source_size, target_size,
                   ((target_size.width/source_size.width, 0, 0),
                    (0, target_size.height/source_size.height, 0), (0, 0, 1)), provenance)

    @classmethod
    def crop_resize_pad(cls, source, target, source_size, target_size, *, crop, scale, padding, provenance):
        x0, y0, x1, y1 = crop
        sx, sy = scale
        left, top, right, bottom = padding
        if not (0 <= x0 < x1 <= source_size.width and 0 <= y0 < y1 <= source_size.height) or min(sx, sy) <= 0 or min(padding) < 0:
            raise ValueError('Invalid explicit crop/resize/padding metadata')
        if not np.allclose([(x1-x0)*sx+left+right, (y1-y0)*sy+top+bottom], [target_size.width, target_size.height]):
            raise ValueError('Crop, scale, padding and target dimensions disagree')
        return cls(source, target, source_size, target_size,
                   ((sx, 0, left-x0*sx), (0, sy, top-y0*sy), (0, 0, 1)), provenance)

    def points(self, points):
        a = np.asarray(points, dtype=float)
        if a.ndim != 2 or a.shape[1] != 2 or not np.isfinite(a).all():
            raise ValueError('Expected finite Nx2 coordinates')
        h = np.c_[a, np.ones(len(a))]
        return (h @ np.asarray(self.matrix).T)[:, :2].tolist()

    polygon = points

    def bbox(self, bbox):
        x1, y1, x2, y2 = bbox
        if not np.isfinite(bbox).all() or x1 >= x2 or y1 >= y2:
            raise ValueError('Expected finite positive-area xyxy box')
        p = np.asarray(self.points([[x1, y1], [x2, y1], [x2, y2], [x1, y2]]))
        return [*p.min(axis=0), *p.max(axis=0)]

    def inverse(self):
        return Transform(self.target, self.source, self.target_size, self.source_size,
                         tuple(map(tuple, np.linalg.inv(self.matrix))), self.provenance)

    def then(self, other):
        if self.target != other.source or self.target_size != other.source_size:
            raise ValueError('Transform chain mismatch')
        return Transform(self.source, other.target, self.source_size, other.target_size,
                         tuple(map(tuple, np.asarray(other.matrix) @ np.asarray(self.matrix))),
                         self.provenance+'; '+other.provenance)

    def valid(self, points, *, target=True):
        size = self.target_size if target else self.source_size
        p = np.asarray(points, dtype=float)
        return bool(np.isfinite(p).all() and ((p >= 0) & (p <= [size.width, size.height])).all())

    def warp_map(self, array, *, mask=False):
        """Includes inverse sampling and padding removal via the affine mapping.

        Coordinates use edge xyxy; pixel centers need half-pixel offsets.
        """
        import cv2
        a = np.asarray(array)
        if a.shape[:2] != (self.source_size.height, self.source_size.width) or not np.isfinite(a).all():
            raise ValueError('Map does not match source metadata')
        plus = np.array([[1, 0, .5], [0, 1, .5], [0, 0, 1]])
        minus = np.array([[1, 0, -.5], [0, 1, -.5], [0, 0, 1]])
        pixel = minus @ np.asarray(self.matrix) @ plus
        return cv2.warpAffine(a, pixel[:2], (self.target_size.width, self.target_size.height),
                              flags=cv2.INTER_NEAREST if mask else cv2.INTER_LINEAR,
                              borderMode=cv2.BORDER_CONSTANT, borderValue=0)


def normalized(source, target, size, *, provenance):
    return Transform.resize(source, target, size, Size(1, 1), provenance=provenance)


def map_registered_bbox(item, camera, bbox, *, registration: Transform | None, mapping_version):
    """Never infer original→LUT correspondence from size alone."""
    from .rois import rois_for, _CONFIG
    if registration is None:
        return {'part_id': 'unknown', 'status': 'unverified',
                'reason': 'lut_registration_missing', 'mapping_version': mapping_version,
                'transform_version': TRANSFORM_VERSION}
    reference = _CONFIG['mappings'].get(mapping_version)
    if reference is None:
        raise ValueError('Unknown ROI mapping version')
    native = reference['image_size']
    if registration.target_size != Size(native['width'], native['height']):
        return {'part_id': 'unknown', 'status': 'unverified', 'reason': 'lut_dimensions_mismatch',
                'mapping_version': mapping_version, 'transform_version': registration.version}
    if not registration.valid([[bbox[0], bbox[1]], [bbox[2], bbox[3]]], target=False):
        return {'part_id': 'unknown', 'status': 'unmapped', 'reason': 'outside_original_bounds',
                'mapping_version': mapping_version, 'transform_version': registration.version}
    lut_box = registration.bbox(bbox)
    if not registration.valid([[lut_box[0], lut_box[1]], [lut_box[2], lut_box[3]]]):
        return {'part_id': 'unknown', 'status': 'unmapped', 'reason': 'outside_lut_bounds'}
    cx, cy = (lut_box[0]+lut_box[2])/2, (lut_box[1]+lut_box[3])/2
    matches = []
    for part, (x1,y1,x2,y2) in rois_for(item,camera,mapping_version):
        if x1 <= cx <= x2 and y1 <= cy <= y2:
            matches.append(((x2-x1)*(y2-y1), part))
    part = min(matches)[1] if matches else 'unknown'
    return {'part_id': part, 'status': 'mapped' if part != 'unknown' else 'unmapped',
            'reason': None if part != 'unknown' else 'outside_defined_regions',
            'mapping_version': mapping_version, 'transform_version': registration.version,
            'provenance': registration.provenance}

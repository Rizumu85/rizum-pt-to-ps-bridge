"""Geometry Mask rasterization for Photoshop build bundles."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path


class GeometryMaskExportError(RuntimeError):
    """Geometry Mask export failure with serializable diagnostics."""

    def __init__(self, message, diagnostics=None):
        super().__init__(message)
        self.diagnostics = diagnostics or {"error": message}


class GeometryMaskBaker:
    """Export the project mesh once and rasterize mesh selections in UV space."""

    def __init__(self, checkpoint=None):
        self._temporary_dir = None
        self._faces = None
        self._uv_faces = None
        self._available_names = set()
        self._available_materials = set()
        self._cache = {}
        self._indexed_faces = None
        self._face_indices_by_name = {}
        self._coverage_path_cache = {}
        self._uv_map_cache = {}
        self._checkpoint_callback = checkpoint

    def close(self):
        if self._temporary_dir is not None:
            self._temporary_dir.cleanup()
            self._temporary_dir = None
        self._coverage_path_cache.clear()
        self._uv_map_cache.clear()

    def bake(self, asset, output_path):
        self._checkpoint()
        self._ensure_mesh()
        width, height = [int(value) for value in asset["resolution"]]
        tile = asset["uv_tile"]
        mesh_names = tuple(sorted(str(name) for name in asset["enabled_meshes"]))
        padding = str(asset.get("padding") or "Transparent")
        dilation = max(0, int(asset.get("dilation") or 0))
        cache_key = (
            str(asset.get("texture_set") or ""),
            str(asset.get("texture_set_original") or ""),
            mesh_names,
            int(tile["u"]),
            int(tile["v"]),
            width,
            height,
            padding.casefold(),
            dilation,
        )
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)

        if cache_key in self._cache:
            png_bytes, matched_names, face_count = self._cache[cache_key]
            output.write_bytes(png_bytes)
            return self._diagnostic(
                asset,
                matched_names,
                cached=True,
                face_count=face_count,
            )

        matched_names = self._matched_names(mesh_names)
        if mesh_names and not matched_names:
            diagnostics = self._diagnostic(asset, [], cached=False)
            raise GeometryMaskExportError(
                "Painter Geometry Mask mesh names did not match the exported project mesh. "
                f"Requested: {', '.join(mesh_names)}. Available OBJ names: "
                f"{', '.join(sorted(self._available_names)) or '(none)' }.",
                diagnostics,
            )

        png_bytes, face_count = self._rasterize(
            matched_names,
            _matching_materials(
                self._available_materials,
                asset.get("texture_set"),
                asset.get("texture_set_original"),
            ),
            tile,
            width,
            height,
            padding=padding,
            dilation=dilation,
        )
        self._checkpoint()
        output.write_bytes(png_bytes)
        self._cache[cache_key] = (png_bytes, matched_names, face_count)
        return self._diagnostic(
            asset,
            matched_names,
            cached=False,
            face_count=face_count,
        )

    def bake_uv_map(self, asset, output_path):
        """Rasterize the current texture-set UV wireframe with transparency."""
        self._checkpoint()
        self._ensure_mesh()
        width, height = [int(value) for value in asset["resolution"]]
        tile = asset["uv_tile"]
        matching_materials = _matching_materials(
            self._available_materials,
            asset.get("texture_set"),
            asset.get("texture_set_original"),
        )
        diagnostics = {
            "texture_set": asset.get("texture_set"),
            "texture_set_original": asset.get("texture_set_original"),
            "uv_tile": tile,
            "matched_obj_materials": sorted(matching_materials),
            "available_obj_materials": sorted(self._available_materials),
        }
        if not matching_materials:
            raise GeometryMaskExportError(
                "Painter texture set did not match an exported project mesh material "
                "for UV Map generation.",
                diagnostics,
            )

        cache_key = (
            tuple(sorted(matching_materials)),
            int(tile["u"]),
            int(tile["v"]),
            width,
            height,
        )
        png_bytes = self._uv_map_cache.get(cache_key)
        cached = png_bytes is not None
        if png_bytes is None:
            png_bytes = self._rasterize_uv_map(
                matching_materials,
                tile,
                width,
                height,
            )
            self._uv_map_cache[cache_key] = png_bytes

        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(png_bytes)
        diagnostics["cached"] = cached
        return diagnostics

    def _ensure_mesh(self):
        if self._faces is not None:
            return

        try:
            import substance_painter.export as painter_export
        except ImportError as exc:
            raise GeometryMaskExportError(
                "Geometry Masks can only be rasterized inside Substance 3D Painter."
            ) from exc

        # Exporting a temporary OBJ keeps Geometry Mask support read-only; changing
        # Painter layer visibility would dirty history and previously caused stalls.
        self._temporary_dir = tempfile.TemporaryDirectory(prefix="rizum_geometry_mask_")
        mesh_path = Path(self._temporary_dir.name) / "project.obj"
        result = painter_export.export_mesh(
            str(mesh_path),
            painter_export.MeshExportOption.BaseMesh,
        )
        self._checkpoint()
        if not mesh_path.exists():
            raise GeometryMaskExportError(
                "Painter did not produce the temporary OBJ required for Geometry Masks.",
                {
                    "mesh_export_status": str(getattr(result, "status", "unknown")),
                    "mesh_export_message": str(getattr(result, "message", "")),
                },
            )
        (
            self._faces,
            self._uv_faces,
            self._available_names,
            self._available_materials,
        ) = _parse_obj(mesh_path, checkpoint=self._checkpoint)

    def _matched_names(self, requested_names):
        aliases = {}
        for available in self._available_names:
            for alias in _name_aliases(available):
                aliases.setdefault(alias, set()).add(available)

        matched = set()
        for requested in requested_names:
            for alias in _name_aliases(requested):
                matched.update(aliases.get(alias, ()))
        return matched

    def _rasterize(
        self,
        matched_names,
        matching_materials,
        tile,
        width,
        height,
        padding="Transparent",
        dilation=0,
    ):
        try:
            from PySide6 import QtCore, QtGui
        except ImportError as exc:
            raise GeometryMaskExportError(
                "PySide6 is required to rasterize Geometry Masks."
            ) from exc

        image_format = getattr(QtGui.QImage, "Format_ARGB32", None)
        if image_format is None:
            image_format = QtGui.QImage.Format.Format_ARGB32
        image = QtGui.QImage(width, height, image_format)
        # Photoshop Place Embedded honors PNG physical resolution. Qt's 96 dpi
        # default shrinks a 4096 px geometry mask inside our 72 ppi PSD, so use
        # the same 72 ppi metadata as Painter's exported layer and mask PNGs.
        image.setDotsPerMeterX(2835)
        image.setDotsPerMeterY(2835)
        black = QtGui.QColor(0, 0, 0, 255)
        white = QtGui.QColor(255, 255, 255, 255)
        winding_fill = getattr(QtCore.Qt, "WindingFill", None)
        if winding_fill is None:
            winding_fill = QtCore.Qt.FillRule.WindingFill

        tile_u = int(tile["u"])
        tile_v = int(tile["v"])
        self._ensure_face_index()
        selection_path, face_count = self._selection_path(
            QtCore,
            QtGui,
            winding_fill,
            matched_names,
            matching_materials,
            tile_u,
            tile_v,
            width,
            height,
        )
        coverage_path = self._coverage_path(
            QtCore,
            QtGui,
            winding_fill,
            matching_materials,
            tile_u,
            tile_v,
            width,
            height,
        )

        padding_mode = str(padding or "Transparent").casefold()
        if padding_mode == "infinite" and face_count:
            image.fill(white)
        else:
            image.fill(black)

        painter = QtGui.QPainter(image)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
        dilation = max(0, int(dilation or 0))
        if padding_mode != "infinite" and dilation:
            # The Geometry Mask is generated outside mapexport, so reproduce
            # the user's payload dilation here instead of silently clipping it
            # back to the exact UV boundary during PSD mask composition.
            dilation_pen = QtGui.QPen(white)
            dilation_pen.setWidthF(float(dilation * 2))
            painter.strokePath(selection_path, dilation_pen)
        if coverage_path is not None:
            # Restore every UV island before filling the selected meshes. This
            # protects excluded geometry without rebuilding its large path for
            # each Geometry Mask in the stack.
            painter.fillPath(coverage_path, black)
        painter.fillPath(selection_path, white)
        painter.end()

        buffer = QtCore.QBuffer()
        buffer.open(QtCore.QIODevice.OpenModeFlag.WriteOnly)
        if not image.save(buffer, "PNG"):
            raise GeometryMaskExportError("Could not encode the Geometry Mask PNG.")
        return bytes(buffer.data()), face_count

    def _rasterize_uv_map(self, matching_materials, tile, width, height):
        try:
            from PySide6 import QtCore, QtGui
        except ImportError as exc:
            raise GeometryMaskExportError(
                "PySide6 is required to rasterize the UV Map."
            ) from exc

        image_format = getattr(QtGui.QImage, "Format_ARGB32", None)
        if image_format is None:
            image_format = QtGui.QImage.Format.Format_ARGB32
        image = QtGui.QImage(width, height, image_format)
        image.fill(0)
        image.setDotsPerMeterX(2835)
        image.setDotsPerMeterY(2835)

        tile_u = int(tile["u"])
        tile_v = int(tile["v"])
        wireframe_path = self._uv_wireframe_path(
            QtCore,
            QtGui,
            matching_materials,
            tile_u,
            tile_v,
            width,
            height,
        )
        if wireframe_path.isEmpty():
            raise GeometryMaskExportError(
                "No UV faces were found for this texture set and UV tile."
            )

        painter = QtGui.QPainter(image)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
        # Keep the guide transparent but use black lines so it remains useful
        # as the familiar UV reference layer once it reaches Photoshop.
        pen = QtGui.QPen(QtGui.QColor(0, 0, 0, 255))
        pen.setWidthF(max(1.0, min(width, height) / 2048.0))
        painter.strokePath(wireframe_path, pen)
        painter.end()

        buffer = QtCore.QBuffer()
        buffer.open(QtCore.QIODevice.OpenModeFlag.WriteOnly)
        if not image.save(buffer, "PNG"):
            raise GeometryMaskExportError("Could not encode the UV Map PNG.")
        return bytes(buffer.data())

    def _uv_wireframe_path(
        self,
        QtCore,
        QtGui,
        matching_materials,
        tile_u,
        tile_v,
        width,
        height,
    ):
        path = QtGui.QPainterPath()
        for index, (_names, material_name, uvs) in enumerate(self._uv_faces or ()):
            if index % 2048 == 0:
                self._checkpoint()
            if material_name not in matching_materials:
                continue
            if not _face_intersects_tile(uvs, tile_u, tile_v):
                continue
            _add_face_to_path(QtCore, QtGui, path, uvs, tile_u, tile_v, width, height)
        return path

    def _ensure_face_index(self):
        if self._faces is self._indexed_faces:
            return
        indices_by_name = {}
        for index, (names, _material_name, _uvs) in enumerate(self._faces):
            if index % 2048 == 0:
                self._checkpoint()
            for name in names:
                indices_by_name.setdefault(name, []).append(index)
        self._face_indices_by_name = indices_by_name
        self._coverage_path_cache.clear()
        self._indexed_faces = self._faces

    def _selection_path(
        self,
        QtCore,
        QtGui,
        winding_fill,
        matched_names,
        matching_materials,
        tile_u,
        tile_v,
        width,
        height,
    ):
        face_indices = set()
        for name in matched_names:
            face_indices.update(self._face_indices_by_name.get(name, ()))
        path = QtGui.QPainterPath()
        path.setFillRule(winding_fill)
        face_count = 0
        for offset, index in enumerate(sorted(face_indices)):
            if offset % 2048 == 0:
                self._checkpoint()
            _names, material_name, uvs = self._faces[index]
            if matching_materials and material_name not in matching_materials:
                continue
            if not _face_intersects_tile(uvs, tile_u, tile_v):
                continue
            _add_face_to_path(QtCore, QtGui, path, uvs, tile_u, tile_v, width, height)
            face_count += 1
        return path, face_count

    def _coverage_path(
        self,
        QtCore,
        QtGui,
        winding_fill,
        matching_materials,
        tile_u,
        tile_v,
        width,
        height,
    ):
        if not matching_materials:
            return None
        key = (
            tuple(sorted(matching_materials)),
            tile_u,
            tile_v,
            width,
            height,
        )
        cached = self._coverage_path_cache.get(key)
        if cached is not None:
            return cached
        path = QtGui.QPainterPath()
        path.setFillRule(winding_fill)
        for index, (_names, material_name, uvs) in enumerate(self._faces):
            if index % 2048 == 0:
                self._checkpoint()
            if material_name not in matching_materials:
                continue
            if not _face_intersects_tile(uvs, tile_u, tile_v):
                continue
            _add_face_to_path(QtCore, QtGui, path, uvs, tile_u, tile_v, width, height)
        self._coverage_path_cache[key] = path
        return path

    def _checkpoint(self):
        if self._checkpoint_callback is not None:
            self._checkpoint_callback()

    def _diagnostic(self, asset, matched_names, cached, face_count=0):
        return {
            "uid": asset.get("uid"),
            "label": asset.get("label"),
            "texture_set": asset.get("texture_set"),
            "uv_tile": asset.get("uv_tile"),
            "requested_meshes": list(asset.get("enabled_meshes", [])),
            "matched_obj_names": sorted(matched_names),
            "available_obj_names": sorted(self._available_names),
            "available_obj_materials": sorted(self._available_materials),
            "rasterized_faces": int(face_count),
            "padding": str(asset.get("padding") or "Transparent"),
            "dilation": max(0, int(asset.get("dilation") or 0)),
            "cached": bool(cached),
        }


def combine_masks(base_path, geometry_path):
    """Multiply a Geometry Mask into Painter's regular layer mask."""
    try:
        from PySide6 import QtGui
    except ImportError as exc:
        raise GeometryMaskExportError("PySide6 is required to combine masks.") from exc

    base = QtGui.QImage(str(base_path))
    geometry = QtGui.QImage(str(geometry_path))
    if base.isNull() or geometry.isNull():
        raise GeometryMaskExportError(
            "Could not read the regular or Geometry Mask PNG for combination."
        )
    if base.size() != geometry.size():
        raise GeometryMaskExportError(
            "Regular and Geometry Mask PNG dimensions do not match."
        )

    image_format = getattr(QtGui.QImage, "Format_ARGB32", None)
    if image_format is None:
        image_format = QtGui.QImage.Format.Format_ARGB32
    # Photoshop exposes one user-mask slot, so authored and geometry masks must
    # be collapsed into their effective grayscale result before PSD assembly.
    combined = base.convertToFormat(image_format)
    painter = QtGui.QPainter(combined)
    painter.setCompositionMode(
        QtGui.QPainter.CompositionMode.CompositionMode_Multiply
    )
    painter.drawImage(0, 0, geometry.convertToFormat(image_format))
    painter.end()
    if not combined.save(str(base_path), "PNG"):
        raise GeometryMaskExportError("Could not save the combined mask PNG.")


def write_error_diagnostics(path, error):
    Path(path).write_text(
        json.dumps(error.diagnostics, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _add_face_to_path(QtCore, QtGui, path, uvs, tile_u, tile_v, width, height):
    points = [
        QtCore.QPointF(
            (u - tile_u) * width,
            (1.0 - (v - tile_v)) * height,
        )
        for u, v in uvs
    ]
    # Geometry Masks are face unions, but exported meshes can contain coincident
    # front/back UV faces with opposite winding. Normalizing every subpath keeps
    # WindingFill from cancelling valid interiors and leaving only UV edges.
    signed_area = sum(
        points[index].x() * points[(index + 1) % len(points)].y()
        - points[(index + 1) % len(points)].x() * points[index].y()
        for index in range(len(points))
    )
    if signed_area < 0:
        points.reverse()
    polygon = QtGui.QPolygonF(points)
    path.addPolygon(polygon)
    path.closeSubpath()


def _parse_obj(path, checkpoint=None):
    texture_coordinates = [None]
    faces = []
    uv_faces = []
    available_names = set()
    available_materials = set()
    shared_name_sets = {}
    object_name = ""
    group_names = set()
    material_name = ""

    # OBJ files from production characters can be large; streaming and sharing
    # repeated face-name sets keeps Geometry Mask export bounded by mesh data.
    with Path(path).open("r", encoding="utf-8", errors="replace") as obj_file:
        for line_index, raw_line in enumerate(obj_file):
            # Large production meshes can otherwise monopolize Painter's UI
            # thread long enough for Windows to present the export as hung.
            if checkpoint is not None and line_index % 2048 == 0:
                checkpoint()
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            command, _, value = line.partition(" ")
            value = value.strip()
            if command == "o":
                object_name = value
                if value:
                    available_names.add(value)
            elif command == "g":
                group_names = {name for name in value.split() if name}
                available_names.update(group_names)
            elif command == "usemtl":
                material_name = value
                if value:
                    available_materials.add(value)
            elif command == "vt":
                values = value.split()
                if len(values) >= 2:
                    texture_coordinates.append((float(values[0]), float(values[1])))
            elif command == "f":
                refs = value.split()
                uvs = []
                for ref in refs:
                    parts = ref.split("/")
                    if len(parts) < 2 or not parts[1]:
                        continue
                    index = int(parts[1])
                    if index < 0:
                        index = len(texture_coordinates) + index
                    if 0 < index < len(texture_coordinates):
                        uvs.append(texture_coordinates[index])
                if len(uvs) < 3:
                    continue
                name_key = tuple(
                    sorted(
                        {name for name in (object_name, material_name) if name}
                        | group_names
                    )
                )
                names = shared_name_sets.setdefault(name_key, frozenset(name_key))
                polygon_uvs = tuple(uvs)
                uv_faces.append((names, material_name, polygon_uvs))
                # Geometry Masks need triangles for predictable fill behavior,
                # while UV guides must retain source polygon boundaries so the
                # exporter does not invent diagonals that were never modeled.
                for index in range(1, len(uvs) - 1):
                    faces.append(
                        (
                            names,
                            material_name,
                            (
                                polygon_uvs[0],
                                polygon_uvs[index],
                                polygon_uvs[index + 1],
                            ),
                        )
                    )

    return faces, uv_faces, available_names, available_materials


def _name_aliases(name):
    text = str(name or "").strip().casefold()
    if not text:
        return set()
    aliases = {text}
    for separator in ("|", ":"):
        aliases.add(text.rsplit(separator, 1)[-1])
    return aliases


def _matching_materials(available_materials, *texture_set_names):
    wanted = set()
    for name in texture_set_names:
        wanted.update(_name_aliases(name))
    return {
        material
        for material in available_materials
        if wanted.intersection(_name_aliases(material))
    }


def _face_intersects_tile(uvs, tile_u, tile_v):
    min_u = min(point[0] for point in uvs)
    max_u = max(point[0] for point in uvs)
    min_v = min(point[1] for point in uvs)
    max_v = max(point[1] for point in uvs)
    return not (
        max_u < tile_u
        or min_u > tile_u + 1
        or max_v < tile_v
        or min_v > tile_v + 1
    )

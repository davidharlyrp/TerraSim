import ezdxf
import os

def get_dxf_units(filepath: str) -> str:
    """
    Detect the units from DXF header $INSUNITS.
    Returns: 'm', 'mm', 'cm', 'in', 'ft', or 'unspecified'
    """
    try:
        doc = ezdxf.readfile(filepath)
        insunits = doc.header.get("$INSUNITS", 0)
        
        mapping = {
            1: "in",
            2: "ft",
            4: "mm",
            5: "cm",
            6: "m"
        }
        return mapping.get(insunits, "m") # Default to meters if unsure
    except Exception:
        return "m"

def extract_polygons_from_dxf(filepath: str, scale: float = 1.0) -> list[list[dict]]:
    """
    Parses a DXF file and extracts vertices from closed polylines.
    Returns a list of lists of vertices: [[ {"x": 1.0, "y": 2.0}, ... ], ...]
    """
    polygons = []
    try:
        doc = ezdxf.readfile(filepath)
        msp = doc.modelspace()
        
        # 1. Handle LWPOLYLINE (Modern 2D Polylines)
        for poly in msp.query('LWPOLYLINE'):
            if poly.is_closed:
                points = []
                # poly.get_points() returns (x, y, [start_width, end_width, bulge])
                for p in poly.get_points():
                    points.append({"x": p[0] * scale, "y": p[1] * scale})
                if points:
                    polygons.append(points)
        
        # 2. Handle POLYLINE (Older Polylines / 3D Polylines used for 2D)
        for poly in msp.query('POLYLINE'):
            if poly.is_closed:
                points = []
                for p in poly.points():
                    points.append({"x": p[0] * scale, "y": p[1] * scale})
                if points:
                    polygons.append(points)
                    
        # 3. Handle HATCH boundaries (Commonly used for 'regions')
        for hatch in msp.query('HATCH'):
            for path in hatch.paths:
                # We only care about the boundary path points
                points = []
                # In ezdxf, path vertices can be complex. We'll try to get them as points.
                # Hatch paths are often closed by definition if they have fill.
                # Here we simplify: if it's a PolylinePath
                if hasattr(path, 'vertices'):
                    for v in path.vertices:
                        # v is usually (x, y)
                        points.append({"x": v[0] * scale, "y": v[1] * scale})
                
                if points:
                    polygons.append(points)

        # 4. Handle REGION (Advanced)
        # Note: REGION entities in DXF are SAT data (ACIS). 
        # ezdxf allows getting their boundaries if they have a mesh or similar, 
        # but it's very complex. For now, we rely on polylines/hatches which 
        # cover 95% of use cases.

    except Exception as e:
        print(f"Error parsing DXF: {e}")
        
    return polygons

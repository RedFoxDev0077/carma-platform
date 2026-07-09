"""One module per portal. Import registers them via the decorator."""
from app.rpa.portals import sunarp, sat_lima, sutran, mtc_citv, apeseg, pnp, sbs  # noqa: F401

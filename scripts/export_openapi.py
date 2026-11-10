"""Write the public /decide API as an OpenAPI 3 spec (openapi/cheapest-yes.json) for APIMatic.

Only the merchant-facing endpoint is exported; demo-store and dashboard routes stay internal."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from fastapi.openapi.utils import get_openapi  # noqa: E402

from app.main import app  # noqa: E402

routes = [r for r in app.routes if getattr(r, "path", None) in ("/decide", "/health")]
spec = get_openapi(title="Cheapest Yes API", version=app.version, description=app.description, routes=routes,
                   servers=[{"url": "https://cheapest-yes.onrender.com", "description": "Hosted demo (PayPal sandbox)"}])
spec["info"]["license"] = {"name": "MIT", "url": "https://opensource.org/licenses/MIT"}
out = ROOT / "openapi" / "cheapest-yes.json"
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps(spec, indent=2))
print(f"wrote {out.relative_to(ROOT)} with paths: {list(spec['paths'])}")

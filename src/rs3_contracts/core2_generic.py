import importlib
import logging
from copy import deepcopy
from typing import Any, Dict, List, Tuple

logger = logging.getLogger(__name__)

# ---------- helpers d'import core2 tolérants + fallbacks ----------

def _import_core2_build_pipeline():
    """Retourne core2.pipeline.build_pipeline si dispo, sinon None."""
    try:
        mod = importlib.import_module("core2.pipeline")
        if hasattr(mod, "build_pipeline"):
            return getattr(mod, "build_pipeline")
    except Exception:
        pass
    return None


def _import_core2_pipeline_class():
    """Retourne une classe pipeline exploitable si dispo (priorité PipelineSimulator), sinon None."""
    try:
        mod = importlib.import_module("core2.pipeline")
        for name in ("PipelineSimulator", "Pipeline", "CorePipeline", "PipelineV2", "PipelineImpl"):
            if hasattr(mod, name):
                return getattr(mod, name)
    except Exception:
        pass
    return None


def _import_core2_context_factory():
    """Retourne une fabrique/Classe de contexte si dispo, sinon None."""
    try:
        mod = importlib.import_module("core2.context")
        for name in ("Context", "build_context", "make_context", "create_context"):
            if hasattr(mod, name):
                return getattr(mod, name)
    except Exception:
        pass
    return None


class _MinimalPipeline:
    def __init__(self, name: str, stages: List[Any]):
        self.name = name
        self.stages = stages
    def run(self, ctx):
        log = logging.getLogger("core2.pipeline")
        total = len(self.stages)
        log.info(f"[PIPELINE] {self.name} — {total} stages")
        for i, stage in enumerate(self.stages, 1):
            label = getattr(stage, "__class__", type(stage)).__name__
            try:
                log.info(f"[STAGE {i}/{total}] {label} — start")
                stage.run(ctx)
                log.info(f"[STAGE {i}/{total}] {label} — OK")
            except Exception as e:
                log.error(f"[STAGE {i}/{total}] {label} — CRASH: {e}")
                raise


class _MinimalContext:
    def __init__(self, cfg: Dict[str, Any] | None = None):
        self.cfg = cfg or {}


# ---------- utilitaires "stops" (simples et génériques) ----------

def _stop_to_plain_dict(s: Any) -> Dict[str, Any]:
    """
    Accepte dicts ou petits objets avec attrs 'type', 'location'({lat,lon}), 'lat', 'lon', etc.
    Retourne un dict uniformisé.
    """
    if isinstance(s, dict):
        t = s.get("type", "delivery")
        lat = s.get("lat", s.get("location", {}).get("lat", 0.0))
        lon = s.get("lon", s.get("location", {}).get("lon", 0.0))
        out = {
            "type": t,
            "lat": float(lat or 0.0),
            "lon": float(lon or 0.0),
            "is_depot": bool(s.get("is_depot", t == "depot")),
            "is_start": bool(s.get("is_start", False)),
            "is_end": bool(s.get("is_end", False)),
            "service_s": int(s.get("service_s", 0)),
            "name": s.get("name", ""),
        }
        # fenêtres de temps si présentes
        if "tw_start" in s:
            out["tw_start"] = s["tw_start"]
        if "tw_end" in s:
            out["tw_end"] = s["tw_end"]
        return out

    # objet : on tente de lire des attributs usuels
    try:
        t = getattr(s, "type", "delivery")
        loc = getattr(s, "location", {}) or {}
        lat = getattr(s, "lat", loc.get("lat", 0.0))
        lon = getattr(s, "lon", loc.get("lon", 0.0))
        out = {
            "type": t,
            "lat": float(lat or 0.0),
            "lon": float(lon or 0.0),
            "is_depot": bool(getattr(s, "is_depot", t == "depot")),
            "is_start": bool(getattr(s, "is_start", False)),
            "is_end": bool(getattr(s, "is_end", False)),
            "service_s": int(getattr(s, "service_s", 0)),
            "name": getattr(s, "name", ""),
        }
        if hasattr(s, "tw_start"):
            out["tw_start"] = getattr(s, "tw_start")
        if hasattr(s, "tw_end"):
            out["tw_end"] = getattr(s, "tw_end")
        return out
    except Exception:
        # fallback très basique
        return {
            "type": "delivery",
            "lat": 0.0,
            "lon": 0.0,
            "is_depot": False,
            "is_start": False,
            "is_end": False,
            "service_s": 0,
            "name": "",
        }


def _ensure_valid_stops(stops: List[Any]) -> List[Dict[str, Any]]:
    """
    Règles minimales pour LegsPlan :
    - au moins 2 stops,
    - le 1er = dépôt de départ (is_depot/is_start),
    - le dernier = dépôt d'arrivée (is_depot/is_end, service_s=0).
    """
    if not stops:
        return []

    plain = [_stop_to_plain_dict(s) for s in stops]

    if len(plain) == 1:
        first = deepcopy(plain[0])
        end = deepcopy(first)
        end["is_end"] = True
        end["is_depot"] = True
        end["service_s"] = 0
        end["name"] = (first.get("name") or "DEPOT") + "-END"
        plain.append(end)

    # force le départ
    plain[0]["is_depot"] = True
    plain[0]["is_start"] = True
    # force la fin
    plain[-1]["is_depot"] = True
    plain[-1]["is_end"] = True
    plain[-1]["service_s"] = 0

    return plain


def _extract_vehicle_stops(vehicle_cfg: Dict[str, Any]) -> List[Any]:
    """
    Extraction volontairement simple et prévisible :
    - priorité à vehicle.stops
    - sinon vehicle.route.stops
    (pas d’autres chemins magiques : c’est un adapter générique)
    """
    if not isinstance(vehicle_cfg, dict):
        return []
    if isinstance(vehicle_cfg.get("stops"), list):
        return vehicle_cfg["stops"]
    route = vehicle_cfg.get("route") or {}
    if isinstance(route.get("stops"), list):
        return route["stops"]
    return []


def _to_legsplan_stops(valid_stops: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Format minimal attendu par LegsPlan :
      - id (optionnel), lat, lon, service_s
      - tw_start / tw_end si présents
    """
    out = []
    for s in valid_stops:
        d = {
            "id": str(s.get("id", s.get("name", ""))),
            "lat": float(s.get("lat", 0.0)),
            "lon": float(s.get("lon", 0.0)),
            "service_s": int(s.get("service_s", 0)),
        }
        if "tw_start" in s:
            d["tw_start"] = s["tw_start"]
        if "tw_end" in s:
            d["tw_end"] = s["tw_end"]
        out.append(d)
    return out


def _inject_legsplan_stops_into_cfg(cfg: Dict[str, Any], valid_stops: List[Dict[str, Any]]) -> None:
    """
    Dépose les stops au format LegsPlan directement dans cfg['stops'].
    Initialise aussi un start_time_utc par défaut s’il manque.
    """
    cfg["stops"] = _to_legsplan_stops(valid_stops)

    # start_time_utc par défaut si absent
    if not cfg.get("start_time_utc"):
        from datetime import datetime, timezone
        cfg["start_time_utc"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


# ---------- instantiation helpers ----------

def _instantiate_stage(spec: Any) -> Any:
    """
    Résout "pkg.mod:Class" ou dict {"class": "pkg.mod:Class", ...}
    (utile si un builder attend des instances — on reste générique).
    """
    if isinstance(spec, str):
        mod, cls = spec.split(":", 1)
        stage_cls = getattr(importlib.import_module(mod), cls)
        return stage_cls()
    if isinstance(spec, dict) and "class" in spec:
        mod, cls = spec["class"].split(":", 1)
        stage_cls = getattr(importlib.import_module(mod), cls)
        params = {k: v for k, v in spec.items() if k != "class"}
        try:
            return stage_cls(**params)
        except TypeError:
            return stage_cls()
    return spec


# ---------- API builders attendus par les adapters ----------

def build_pipeline(cfg: Dict[str, Any]):
    """Builder générique: instancie les stages et retourne un Pipeline core2.
    Cette fonction est volontairement côté "contracts" mais importe core2 ici,
    pour éviter tout import core2 dans les plugins MIT.
    """
    # 1) Déléguer si core2.pipeline.build_pipeline est présent
    delegated = _import_core2_build_pipeline()
    if delegated is not None:
        return delegated(cfg)

    # 2) Sinon, tenter une classe pipeline connue (PipelineSimulator, Pipeline, ...)
    name = cfg.get("name", "rs3-pipeline")
    stages_specs = cfg.get("stages", []) or []
    instances = [_instantiate_stage(s) for s in stages_specs]

    P = _import_core2_pipeline_class()
    if P is not None:
        return P(name, instances)

    # 3) Dernier recours: pipeline minimal local
    logger.warning("[contracts] Aucun Pipeline core2 détecté — utilisation d'un pipeline minimal (fallback)")
    return _MinimalPipeline(name, instances)


def build_context(cfg: Dict[str, Any]):
    """Fabrique minimale de contexte core2.
    Place l'import ici pour conserver le découplage au niveau des plugins.
    """
    C = _import_core2_context_factory()
    if C is not None:
        try:
            return C(cfg)
        except TypeError:
            ctx = C()
            try:
                setattr(ctx, "cfg", cfg)
            except Exception:
                pass
            return ctx

    logger.warning("[contracts] Aucun Context core2 détecté — utilisation d'un contexte minimal (fallback)")
    return _MinimalContext(cfg)


# ---------- API principale ----------

def build_pipeline_and_ctx(cfg: Dict[str, Any], config_path: str) -> Tuple[Any, Any]:
    """
    Adapter générique pour un véhicule unique.
    - Normalise et injecte les stops,
    - Construit pipeline & contexte via les symboles du YAML.
    """
    # 0) On travaille sur une copie pour ne pas surprendre l’appelant
    local_cfg = deepcopy(cfg)

    # 1) Normaliser les stops du véhicule 0 (le runner fournit déjà un cfg mono-véhicule)
    vehicles = local_cfg.get("vehicles") or []
    if vehicles:
        v0 = vehicles[0] or {}
        stops = _extract_vehicle_stops(v0)
        if stops:
            valid = _ensure_valid_stops(stops)
            _inject_legsplan_stops_into_cfg(local_cfg, valid)
        else:
            logger.warning("[adapter-generic] Aucun stop trouvé pour le véhicule courant.")

    # 2) Construire le pipeline via ce module (pas d'import core2 côté plugin)
    pipeline = build_pipeline(local_cfg)

    # 3) Construire le contexte via ce module
    ctx = build_context(local_cfg)

    try:
        n = len(getattr(pipeline, "stages", []))
        logger.debug(f"[adapter-generic] Pipeline construit avec {n} stage(s).")
    except Exception:
        logger.debug("[adapter-generic] Pipeline construit.")

    return pipeline, ctx
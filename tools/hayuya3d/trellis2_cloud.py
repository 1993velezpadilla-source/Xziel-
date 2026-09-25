#!/usr/bin/env python3
from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from gradio_client import Client, handle_file


def _named_endpoints(client: Client) -> dict:
    api=client.view_api(print_info=False,return_format="dict")
    return api.get("named_endpoints",{}) if isinstance(api,dict) else {}


def _endpoint(named: dict, preferred: str, contains: str) -> tuple[str,dict]:
    if preferred in named:
        return preferred,named[preferred]
    key=next((k for k in named if contains.lower() in str(k).lower()),None)
    if key is None:
        raise RuntimeError(
            f"TRELLIS.2 endpoint {preferred} unavailable; found {list(named)}"
        )
    return key,named[key]


def _parameter_names(spec: dict) -> list[str]:
    return [
        str(p.get("parameter_name") or "")
        for p in spec.get("parameters",[])
    ]


def _call_named(client: Client, endpoint: str, spec: dict, values: dict[str,Any]):
    params=_parameter_names(spec)
    missing=[name for name in params if name not in values]
    if missing:
        raise RuntimeError(
            f"TRELLIS.2 endpoint {endpoint} has unsupported parameters: {missing}"
        )
    return client.predict(
        *[values[name] for name in params],
        api_name=endpoint,
    )


def _walk_paths(value):
    if isinstance(value,str):
        yield value
    elif isinstance(value,dict):
        for v in value.values():
            yield from _walk_paths(v)
    elif isinstance(value,(list,tuple)):
        for v in value:
            yield from _walk_paths(v)
    else:
        for attr in ("path","url"):
            v=getattr(value,attr,None)
            if isinstance(v,str):
                yield v


def _state_from_generation(result):
    if isinstance(result,dict) and "res" in result and "coords" in result:
        return result
    if isinstance(result,(list,tuple)):
        for value in result:
            state=_state_from_generation(value)
            if state is not None:
                return state
    if isinstance(result,dict):
        for value in result.values():
            state=_state_from_generation(value)
            if state is not None:
                return state
    return None


def generate(
    image: Path,
    output: Path,
    *,
    token: str | None = None,
    quality: str = "high",
    seed: int = 1993,
    space: str = "microsoft/TRELLIS.2",
) -> dict:
    """
    Generate one modern full-PBR candidate through Microsoft's public TRELLIS.2
    Space. The caller owns fallback policy; this function never hides failure.
    """
    kwargs={"verbose":True,"httpx_kwargs":{"timeout":180.0}}
    if token:
        kwargs["token"]=token
    client=Client(space,**kwargs)
    named=_named_endpoints(client)

    preprocess_ep,preprocess_spec=_endpoint(
        named,"/preprocess_image","preprocess_image"
    )
    preprocess_params=_parameter_names(preprocess_spec)
    if len(preprocess_params)!=1:
        raise RuntimeError(
            f"Unexpected TRELLIS.2 preprocess signature: {preprocess_params}"
        )
    processed=client.predict(
        handle_file(str(image.resolve())),
        api_name=preprocess_ep,
    )

    generate_ep,generate_spec=_endpoint(
        named,"/image_to_3d","image_to_3d"
    )
    resolution="1536" if quality=="ultra" else "1024"
    generate_values={
        "image":processed,
        "input":processed,
        "seed":int(seed),
        "resolution":resolution,
        "ss_guidance_strength":7.5,
        "ss_guidance_rescale":0.7,
        "ss_sampling_steps":12,
        "ss_rescale_t":5.0,
        "shape_slat_guidance_strength":7.5,
        "shape_slat_guidance_rescale":0.5,
        "shape_slat_sampling_steps":12,
        "shape_slat_rescale_t":3.0,
        "tex_slat_guidance_strength":1.0,
        "tex_slat_guidance_rescale":0.0,
        "tex_slat_sampling_steps":12,
        "tex_slat_rescale_t":3.0,
    }
    generation=_call_named(
        client,generate_ep,generate_spec,generate_values
    )
    state=_state_from_generation(generation)

    extract_ep,extract_spec=_endpoint(named,"/extract_glb","extract_glb")
    texture_size=4096 if quality in {"high","ultra"} else 2048
    faces=500000 if quality=="ultra" else 300000
    extract_values={
        "state":state,
        "output_buf":state,
        "decimation_target":faces,
        "texture_size":texture_size,
    }
    # Gradio session state is sometimes intentionally hidden from the public
    # signature. In that case the same Client session carries it implicitly.
    for param in _parameter_names(extract_spec):
        if param in {"state","output_buf"} and extract_values[param] is None:
            raise RuntimeError(
                "TRELLIS.2 exposed state as an API parameter but generation "
                "did not return a serializable state"
            )
    extracted=_call_named(client,extract_ep,extract_spec,extract_values)

    candidates=[]
    for value in _walk_paths(extracted):
        path=Path(value)
        if value.lower().endswith(".glb") and path.is_file():
            candidates.append(path)
    if not candidates:
        raise RuntimeError(
            f"TRELLIS.2 extraction returned no downloaded GLB: {extracted!r}"
        )

    source=candidates[-1]
    output.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(source,output)
    data=output.read_bytes()
    if data[:4]!=b"glTF" or len(data)<1024:
        raise RuntimeError(
            f"TRELLIS.2 produced invalid GLB: magic={data[:16]!r} bytes={len(data)}"
        )
    return {
        "path":str(output),
        "generator":"microsoft/TRELLIS.2-4B",
        "space":space,
        "resolution":int(resolution),
        "texture_size":texture_size,
        "faces_target":faces,
        "bytes":len(data),
    }

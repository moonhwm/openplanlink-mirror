#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""glb_inspect.py — GLB 资产体检（纯标准库，零依赖）。

用途：对 .glb 文件做只读体检——头部合法性、JSON 块摘要（网格/蒙皮/关节数/动画/
材质/贴图）、meshopt 压缩与量化扩展检测、字节量。用于导出验收与质量闸前置：
「导出物是否真含 skin/动画」不靠文件名猜，靠本脚本实测。

用法：
    python3 glb_inspect.py <file.glb> [<file2.glb> ...]

退出码：0=全部合法 GLB；1=任一文件非法/缺失。
"""
import json
import struct
import sys


def inspect(path: str) -> dict:
    with open(path, "rb") as f:
        data = f.read()
    if len(data) < 12 or data[:4] != b"glTF":
        raise ValueError("not a GLB (bad magic or truncated header)")
    version, total_len = struct.unpack_from("<II", data, 4)
    if total_len != len(data):
        raise ValueError(f"length mismatch: header={total_len} actual={len(data)}")
    # chunk 0 must be JSON
    clen, ctype = struct.unpack_from("<II", data, 12)
    if ctype != 0x4E4F534A:  # 'JSON'
        raise ValueError("chunk0 is not JSON")
    gltf = json.loads(data[20 : 20 + clen].decode("utf-8"))

    skins = gltf.get("skins", [])
    anims = gltf.get("animations", [])
    meshes = gltf.get("meshes", [])
    exts = gltf.get("extensionsUsed", [])
    joints_max = max((len(s.get("joints", [])) for s in skins), default=0)
    tris = 0
    for m in meshes:
        for prim in m.get("primitives", []):
            idx = prim.get("indices")
            if idx is not None:
                tris += gltf["accessors"][idx].get("count", 0) // 3
    anim_channels = sum(len(a.get("channels", [])) for a in anims)
    dur = 0.0
    for a in anims:
        for s_ in a.get("samplers", []):
            acc = gltf["accessors"][s_["input"]]
            if acc.get("max"):
                dur = max(dur, acc["max"][0])
    return {
        "path": path,
        "bytes": len(data),
        "gltf_version": version,
        "meshes": len(meshes),
        "triangles": tris,
        "skins": len(skins),
        "joints_max": joints_max,
        "animations": len(anims),
        "anim_channels": anim_channels,
        "anim_duration_s": round(dur, 3),
        "materials": len(gltf.get("materials", [])),
        "images": len(gltf.get("images", [])),
        "meshopt": "EXT_meshopt_compression" in exts,
        "quantized": "KHR_mesh_quantization" in exts,
    }


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 1
    rc = 0
    for p in argv[1:]:
        try:
            r = inspect(p)
            print(json.dumps(r, ensure_ascii=False))
        except Exception as e:  # noqa: BLE001 - report and continue
            print(json.dumps({"path": p, "error": str(e)}, ensure_ascii=False))
            rc = 1
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv))

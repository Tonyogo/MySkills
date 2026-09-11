#!/usr/bin/env python3
"""
Full-Stack Microservice & Micro-Frontend Workspace Scanner
Scans workspace directories and generates/updates service-map.md according to the 5-layer architecture.
Standard library only (zero external dependencies).
"""

import argparse
import datetime
import json
import os
import re
import sys
from pathlib import Path

IGNORE_DIRS = {
    ".git", ".svn", ".hg", "node_modules", "dist", "build", "target",
    "vendor", ".venv", "venv", "env", "__pycache__", ".idea", ".vscode",
    ".next", ".nuxt", ".output", ".turbo", "coverage", "bin", "obj"
}

def scan_workspace(root_path: Path):
    """Recursively scan root_path for manifests and service markers."""
    root_path = root_path.resolve()
    
    layers = {
        "frontend": [],
        "gateway": [],
        "backend": [],
        "infra_iot": [],
        "mq_mesh": []
    }
    
    
    for dirpath, dirnames, filenames in os.walk(root_path):
        # Filter ignored directories in-place
        dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS and not d.startswith(".")]
        current_dir = Path(dirpath)
        rel_path = current_dir.relative_to(root_path)
        
        # 1. Check Frontend (package.json)
        if "package.json" in filenames:
            pkg_file = current_dir / "package.json"
            try:
                with open(pkg_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    name = data.get("name", current_dir.name)
                    deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
                    
                    tech_tags = []
                    if "qiankun" in deps or "wujie" in deps or "single-spa" in deps:
                        tech_tags.append("Micro-Frontend")
                    if "react" in deps:
                        tech_tags.append("React")
                    if "vue" in deps:
                        tech_tags.append("Vue")
                    if "@angular/core" in deps:
                        tech_tags.append("Angular")
                    if "svelte" in deps or "@sveltejs/kit" in deps:
                        tech_tags.append("Svelte")
                    if "solid-js" in deps:
                        tech_tags.append("SolidJS")
                    if "vite" in deps:
                        tech_tags.append("Vite")
                    if "next" in deps:
                        tech_tags.append("Next.js")
                    if "nuxt" in deps:
                        tech_tags.append("Nuxt")
                    if "three" in deps:
                        tech_tags.append("Three.js")
                    if "antd" in deps or "@ant-design/icons" in deps:
                        tech_tags.append("AntD")
                    if "element-plus" in deps or "@element-plus/icons-vue" in deps:
                        tech_tags.append("Element Plus")
                    
                    tag_str = ", ".join(tech_tags) if tech_tags else "JavaScript/TypeScript"
                    
                    entry = {
                        "name": name,
                        "path": str(rel_path) if str(rel_path) != "." else "./",
                        "tags": tag_str,
                        "description": data.get("description", "")
                    }
                    
                    # Check if it's a Node Gateway/BFF or pure frontend
                    if any(k in name.lower() for k in ["gateway", "bff", "proxy"]):
                        layers["gateway"].append(entry)
                    else:
                        layers["frontend"].append(entry)
            except Exception as e:
                print(f"⚠️  Warning: Failed to parse {pkg_file}: {e}", file=sys.stderr)

        # 2. Check Go Services (go.mod)
        if "go.mod" in filenames:
            go_file = current_dir / "go.mod"
            try:
                with open(go_file, "r", encoding="utf-8") as f:
                    content = f.read()
                    mod_match = re.search(r"^module\s+([^\s]+)", content, re.MULTILINE)
                    mod_name = mod_match.group(1) if mod_match else current_dir.name
                    simple_name = mod_name.split("/")[-1]
                    
                    tags = ["Go"]
                    if "gin-gonic/gin" in content:
                        tags.append("Gin")
                    if "go-chi/chi" in content:
                        tags.append("Chi")
                    if "danielgtaylor/huma" in content:
                        tags.append("Huma")
                    if "go-kratos/kratos" in content:
                        tags.append("Kratos")
                    if "dubbo.apache.org" in content:
                        tags.append("Dubbo-Go")
                    if "dapr/go-sdk" in content:
                        tags.append("Dapr")
                    if "nats-io/nats.go" in content:
                        tags.append("NATS")
                    if "segmentio/kafka-go" in content or "Shopify/sarama" in content:
                        tags.append("Kafka")
                    
                    entry = {
                        "name": simple_name,
                        "path": str(rel_path) if str(rel_path) != "." else "./",
                        "tags": ", ".join(tags),
                        "description": f"Go module (`{mod_name}`)"
                    }
                    
                    if any(k in simple_name.lower() for k in ["gateway", "bff", "proxy", "gw"]):
                        layers["gateway"].append(entry)
                    elif any(k in simple_name.lower() for k in ["iot", "codec", "hardware", "device", "things", "xiot"]):
                        layers["infra_iot"].append(entry)
                    else:
                        layers["backend"].append(entry)
            except Exception as e:
                print(f"⚠️  Warning: Failed to parse {go_file}: {e}", file=sys.stderr)

        # 3. Check Java / Maven / Gradle
        if "pom.xml" in filenames or "build.gradle" in filenames or "build.gradle.kts" in filenames:
            is_maven = "pom.xml" in filenames
            is_aggregator_pom = False
            proj_name = current_dir.name
            tags = ["Java"]
            if is_maven:
                try:
                    with open(current_dir / "pom.xml", "r", encoding="utf-8") as f:
                        xml_content = f.read()
                        # Skip aggregator/parent POMs that don't produce deployable artifacts
                        if re.search(r'<packaging>\s*pom\s*</packaging>', xml_content):
                            is_aggregator_pom = True
                        else:
                            art_match = re.search(r"<artifactId>(.*?)</artifactId>", xml_content)
                            if art_match:
                                proj_name = art_match.group(1)
                            if "spring-boot" in xml_content:
                                tags.append("Spring Boot")
                            if "spring-cloud" in xml_content:
                                tags.append("Spring Cloud")
                            if "dubbo" in xml_content:
                                tags.append("Dubbo")
                except Exception as e:
                    print(f"⚠️  Warning: Failed to parse {current_dir / 'pom.xml'}: {e}", file=sys.stderr)
            else:
                # Gradle — try to extract dependency info from build file
                gradle_file = "build.gradle.kts" if "build.gradle.kts" in filenames else "build.gradle"
                try:
                    with open(current_dir / gradle_file, "r", encoding="utf-8") as f:
                        gradle_content = f.read()
                        if "spring-boot" in gradle_content or "org.springframework.boot" in gradle_content:
                            tags.append("Spring Boot")
                        if "spring-cloud" in gradle_content:
                            tags.append("Spring Cloud")
                        if "dubbo" in gradle_content:
                            tags.append("Dubbo")
                        if "kotlin" in gradle_content or gradle_file.endswith(".kts"):
                            tags.append("Kotlin")
                except Exception as e:
                    print(f"⚠️  Warning: Failed to parse {current_dir / gradle_file}: {e}", file=sys.stderr)
                tags.append("Gradle")
            
            if not is_aggregator_pom:
                entry = {
                    "name": proj_name,
                    "path": str(rel_path) if str(rel_path) != "." else "./",
                    "tags": ", ".join(tags),
                    "description": "Java service"
                }
                if any(k in proj_name.lower() for k in ["gateway", "bff", "proxy", "zuul"]):
                    layers["gateway"].append(entry)
                else:
                    layers["backend"].append(entry)

        # 4. Check Python (pyproject.toml / requirements.txt / setup.py)
        if ("pyproject.toml" in filenames or "requirements.txt" in filenames or "setup.py" in filenames) and not ("package.json" in filenames or "go.mod" in filenames):
            py_name = current_dir.name
            tags = ["Python"]
            req_content = ""
            for fname in ["pyproject.toml", "requirements.txt"]:
                fpath = current_dir / fname
                if fpath.exists():
                    try:
                        with open(fpath, "r", encoding="utf-8") as f:
                            req_content += f.read()
                    except Exception as e:
                        print(f"⚠️  Warning: Failed to read {fpath}: {e}", file=sys.stderr)
            
            if "fastapi" in req_content.lower():
                tags.append("FastAPI")
            if "django" in req_content.lower():
                tags.append("Django")
            if "flask" in req_content.lower():
                tags.append("Flask")
            if "dapr" in req_content.lower():
                tags.append("Dapr")
                
            entry = {
                "name": py_name,
                "path": str(rel_path) if str(rel_path) != "." else "./",
                "tags": ", ".join(tags),
                "description": "Python service"
            }
            # Note: "api" alone is too broad — projects like "user-api" would be misclassified
            if any(k in py_name.lower() for k in ["gateway", "bff", "proxy", "api-gateway", "apigateway"]):
                layers["gateway"].append(entry)
            else:
                layers["backend"].append(entry)

        # 5. Check Rust (Cargo.toml)
        if "Cargo.toml" in filenames and not "go.mod" in filenames:
            rust_name = current_dir.name
            rust_tags = ["Rust"]
            try:
                with open(current_dir / "Cargo.toml", "r", encoding="utf-8") as f:
                    cargo_content = f.read()
                    name_match = re.search(r'^\s*name\s*=\s*"([^"]+)"', cargo_content, re.MULTILINE)
                    if name_match:
                        rust_name = name_match.group(1)
                    if "axum" in cargo_content:
                        rust_tags.append("Axum")
                    if "actix-web" in cargo_content:
                        rust_tags.append("Actix-web")
                    if "tonic" in cargo_content:
                        rust_tags.append("tonic/gRPC")
                    if "tokio" in cargo_content:
                        rust_tags.append("Tokio")
            except Exception as e:
                print(f"⚠️  Warning: Failed to parse {current_dir / 'Cargo.toml'}: {e}", file=sys.stderr)
            entry = {
                "name": rust_name,
                "path": str(rel_path) if str(rel_path) != "." else "./",
                "tags": ", ".join(rust_tags),
                "description": f"Rust crate (`{rust_name}`)"
            }
            if any(k in rust_name.lower() for k in ["gateway", "bff", "proxy", "gw"]):
                layers["gateway"].append(entry)
            elif any(k in rust_name.lower() for k in ["iot", "codec", "device"]):
                layers["infra_iot"].append(entry)
            else:
                layers["backend"].append(entry)

        # 6. Check Dapr components / Proto definitions / IoT configs
        proto_files = [f for f in filenames if f.endswith(".proto")]
        if proto_files:
            layers["infra_iot"].append({
                "name": f"Protobuf Definitions ({current_dir.name})",
                "path": str(rel_path),
                "tags": "gRPC / Protobuf",
                "description": f"{len(proto_files)} proto files ({', '.join(proto_files[:3])}{'...' if len(proto_files) > 3 else ''})"
            })

        # Check PubSub / MQ configs
        yaml_files = [f for f in filenames if f.endswith(".yaml") or f.endswith(".yml")]
        for yf in yaml_files:
            if "pubsub" in yf.lower() or "dapr" in str(rel_path).lower():
                layers["mq_mesh"].append({
                    "name": f"Dapr PubSub Config ({yf})",
                    "path": str(rel_path / yf),
                    "tags": "Dapr Pub/Sub Component",
                    "description": f"Component configuration in {rel_path}"
                })
                break

    return layers

def generate_markdown_service_map(layers: dict, workspace_root: Path, hints: str = "") -> str:
    today_str = datetime.date.today().strftime("%Y-%m-%d")
    
    md_lines = [
        "# Universal Full-Stack Service Map Index",
        "",
        "> **Note**: This index is generated by `scripts/scan_services.py` for `/man-system` skill.",
        f"> **Last updated**: {today_str}",
        f"> **Workspace Root**: `{workspace_root}`",
    ]
    
    if hints:
        md_lines.extend([
            f"> **Architecture Hints**: {hints}",
        ])
    
    md_lines.append("")
    md_lines.append("---")
    md_lines.append("")
    
    # 1. Frontend
    md_lines.append("## 🌐 1. Frontend Applications & Micro-Frontends")
    md_lines.append("")
    if layers["frontend"]:
        for item in layers["frontend"]:
            desc = f" - {item['description']}" if item['description'] else ""
            md_lines.append(f"- **`{item['name']}`** (`{item['path']}`): {item['tags']}{desc}")
    else:
        md_lines.append("_No standalone frontend packages discovered._")
    md_lines.append("")
    md_lines.append("---")
    md_lines.append("")
    
    # 2. Gateways & BFF
    md_lines.append("## 🚪 2. Gateways & BFF Layer")
    md_lines.append("")
    if layers["gateway"]:
        for item in layers["gateway"]:
            desc = f" - {item['description']}" if item['description'] else ""
            md_lines.append(f"- **`{item['name']}`** (`{item['path']}`): {item['tags']}{desc}")
    else:
        md_lines.append("_No specialized gateway/BFF services detected (or direct backend routing)._")
    md_lines.append("")
    md_lines.append("---")
    md_lines.append("")
    
    # 3. Core Microservices
    md_lines.append("## ⚙️ 3. Core Microservices & Backend Domains")
    md_lines.append("")
    if layers["backend"]:
        for item in layers["backend"]:
            desc = f" - {item['description']}" if item['description'] else ""
            md_lines.append(f"- **`{item['name']}`** (`{item['path']}`): {item['tags']}{desc}")
    else:
        md_lines.append("_No backend services discovered._")
    md_lines.append("")
    md_lines.append("---")
    md_lines.append("")
    
    # 4. IoT & Infra
    md_lines.append("## 🔌 4. Infrastructure, Protocols & IoT Layer")
    md_lines.append("")
    if layers["infra_iot"]:
        for item in layers["infra_iot"]:
            desc = f" - {item['description']}" if item['description'] else ""
            md_lines.append(f"- **`{item['name']}`** (`{item['path']}`): {item['tags']}{desc}")
    else:
        md_lines.append("_No hardware/IoT or proto modules detected._")
    md_lines.append("")
    md_lines.append("---")
    md_lines.append("")
    
    # 5. MQ & Event Mesh
    md_lines.append("## 📨 5. Distributed Event Mesh & Communication Topology")
    md_lines.append("")
    if layers["mq_mesh"]:
        for item in layers["mq_mesh"]:
            desc = f" - {item['description']}" if item['description'] else ""
            md_lines.append(f"- **`{item['name']}`** (`{item['path']}`): {item['tags']}{desc}")
    else:
        md_lines.append("- **Standard Pub/Sub & MQ Channels** (Kafka, RabbitMQ, NATS, Dapr): Verify per-service configs in backend references.")
    md_lines.append("")
    
    return "\n".join(md_lines)

def main():
    parser = argparse.ArgumentParser(description="Scan workspace and generate service-map.md for man-system skill.")
    parser.add_argument("workspace_dir", nargs="?", default=".", help="Root directory of workspace to scan (default: current dir)")
    parser.add_argument("-o", "--output", help="Path to write the generated markdown service map")
    parser.add_argument("--hints", default="", help="Optional user architecture hints or context")
    parser.add_argument("--dry-run", action="store_true", help="Print result to stdout instead of writing to file")
    
    args = parser.parse_args()
    workspace_path = Path(args.workspace_dir).resolve()
    
    if not workspace_path.exists():
        print(f"Error: Target path '{workspace_path}' does not exist.", file=sys.stderr)
        sys.exit(1)
        
    layers = scan_workspace(workspace_path)
    md_content = generate_markdown_service_map(layers, workspace_path, hints=args.hints)
    
    if args.dry_run or not args.output:
        print(md_content)
        if args.output:
            print(f"\n[Dry Run] Would write to: {args.output}", file=sys.stderr)
    else:
        out_path = Path(args.output).resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(md_content)
        print(f"✅ Full-stack service map successfully generated at: {out_path}")

if __name__ == "__main__":
    main()
